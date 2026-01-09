# PRD: Segmentos de Rota Reutilizáveis

## 1. Resumo Executivo

### Visão Geral
Este documento descreve a arquitetura de segmentos reutilizáveis para o MapaLinear, onde os mapas são compostos de segmentos baseados nos "steps" retornados pelo OSRM. Segmentos já calculados por mapas anteriores podem ser reutilizados, evitando reprocessamento de POIs.

### Motivação
- **Economia de recursos**: Reutilização de dados reduz chamadas às APIs externas (Overpass, HERE, Google Places)
- **Performance**: Mapas com segmentos pré-calculados são gerados instantaneamente
- **Consistência**: POIs idênticos em rotas sobrepostas apresentam mesmas informações
- **Escalabilidade**: Base de segmentos cresce organicamente com uso do sistema

### Exemplo de Uso
1. Usuário A cria mapa **Belo Horizonte → Ouro Preto**
   - Sistema calcula 45 segmentos (steps do OSRM)
   - Busca POIs para cada segmento
   - Armazena segmentos e POIs associados

2. Usuário B cria mapa **Betim, MG → Mariana, MG**
   - Rota compartilha 30 segmentos com o mapa anterior
   - Sistema reutiliza esses 30 segmentos (POIs já calculados)
   - Processa apenas 15 segmentos novos

**Economia**: 67% menos chamadas às APIs

## 2. Conceitos Fundamentais

### Step vs Segmento
- **Step (OSRM)**: Trecho de rota entre duas manobras, retornado pela API de roteamento
- **Segmento (MapaLinear)**: Representação persistente de um step, identificado por hash único

### Identificação de Segmentos
Cada segmento é identificado por um hash MD5 das coordenadas de início e fim, arredondadas para 4 casas decimais (~11 metros de precisão):

```python
def calculate_segment_hash(start_lat: float, start_lon: float,
                           end_lat: float, end_lon: float) -> str:
    """
    Calcula hash único para identificação de segmento.

    Arredondamento para 4 decimais garante:
    - Precisão de ~11 metros
    - Matching de steps equivalentes mesmo com pequenas variações
    - Chave consistente entre requisições
    """
    start_norm = (round(start_lat, 4), round(start_lon, 4))
    end_norm = (round(end_lat, 4), round(end_lon, 4))

    key = f"{start_norm[0]},{start_norm[1]}|{end_norm[0]},{end_norm[1]}"
    return hashlib.md5(key.encode()).hexdigest()
```

### Associação POI-Segmento vs POI-Mapa
**Modelo Atual**: POIs são associados diretamente ao mapa via `map_poi`
**Novo Modelo**: POIs são associados ao segmento via `segment_poi`, e segmentos são associados ao mapa via `map_segment`

```
┌──────────┐     ┌─────────────┐     ┌───────────────┐     ┌─────┐
│   Map    │────▶│ map_segment │────▶│ route_segment │◀────│ POI │
└──────────┘     └─────────────┘     └───────────────┘     └─────┘
                                            │                  ▲
                                            ▼                  │
                                     ┌─────────────┐           │
                                     │ segment_poi │───────────┘
                                     └─────────────┘
```

### Separação de Responsabilidades: Busca vs Cálculo de Junction

**IMPORTANTE**: O cálculo de junction (ponto de saída da rota para chegar ao POI) e lado (left/right) depende do **contexto do mapa completo**, não apenas do segmento isolado. Isso porque:

1. O lookback de 10km para calcular a melhor rota de acesso pode cruzar múltiplos segmentos
2. POIs no início de um segmento precisam do contexto dos segmentos anteriores
3. O lado (left/right) depende da direção de aproximação no contexto da viagem

**Consequência**: Dividimos os dados em duas categorias:

| Dados Reutilizáveis (segment_poi) | Dados Calculados por Mapa (map_poi) |
|-----------------------------------|-------------------------------------|
| Quais POIs existem no segmento | Junction (lat, lon) |
| Search point que encontrou o POI | Distância da junction desde origem |
| Distância em linha reta (aproximada) | Lado (left/right) |
| | Distância real da rota ao POI |
| | Se requer desvio |
| | Distância do desvio |

## 3. Arquitetura de Dados

### Novos Modelos de Banco de Dados

#### Tabela `route_segment`
Armazena segmentos únicos identificados por hash, incluindo seus search points pré-calculados.

| Campo | Tipo | Descrição |
|-------|------|-----------|
| `id` | UUID | Identificador único |
| `segment_hash` | VARCHAR(32) | Hash MD5 único (índice único) |
| `start_lat` | DECIMAL(9,6) | Latitude início |
| `start_lon` | DECIMAL(9,6) | Longitude início |
| `end_lat` | DECIMAL(9,6) | Latitude fim |
| `end_lon` | DECIMAL(9,6) | Longitude fim |
| `road_name` | VARCHAR(255) | Nome da via (ex: "BR-040", "Av. Afonso Pena") |
| `length_km` | DECIMAL(8,3) | Comprimento em km |
| `geometry` | JSONB | Polyline completo do segmento |
| `search_points` | JSONB | **NOVO**: Lista de search points pré-calculados (ver estrutura abaixo) |
| `osrm_instruction` | TEXT | Instrução de manobra do OSRM |
| `osrm_maneuver_type` | VARCHAR(50) | Tipo de manobra (turn, merge, etc.) |
| `usage_count` | INTEGER | Contador de mapas que usam este segmento |
| `pois_fetched_at` | TIMESTAMP | Quando os POIs foram buscados |
| `created_at` | TIMESTAMP | Data de criação |
| `updated_at` | TIMESTAMP | Data de atualização |

**Estrutura do campo `search_points` (JSONB)**:
```json
[
  {
    "index": 0,
    "lat": -19.9167,
    "lon": -43.9345,
    "distance_from_segment_start_km": 0.0
  },
  {
    "index": 1,
    "lat": -19.9245,
    "lon": -43.9280,
    "distance_from_segment_start_km": 1.0
  }
]
```

**Índices**:
- `UNIQUE` em `segment_hash`
- `INDEX` em `(start_lat, start_lon)` para busca espacial
- `INDEX` em `road_name` para análise

#### Tabela `segment_poi`
Associa POIs a segmentos. Armazena apenas dados reutilizáveis (busca), **não** dados de junction.

| Campo | Tipo | Descrição |
|-------|------|-----------|
| `id` | UUID | Identificador único |
| `segment_id` | UUID | FK para `route_segment` |
| `poi_id` | UUID | FK para `poi` |
| `search_point_index` | INTEGER | Índice do search point que encontrou este POI |
| `straight_line_distance_m` | INTEGER | Distância em linha reta do search point ao POI (aproximada) |
| `created_at` | TIMESTAMP | Data de criação |

**Nota**: Campos como `junction_lat/lon`, `side`, `requires_detour` são calculados no contexto do mapa (ver `map_poi`).

**Índices**:
- `UNIQUE` em `(segment_id, poi_id)` - evita duplicatas
- `INDEX` em `segment_id` para busca de POIs do segmento

#### Tabela `map_segment`
Liga mapas aos seus segmentos componentes.

| Campo | Tipo | Descrição |
|-------|------|-----------|
| `id` | UUID | Identificador único |
| `map_id` | UUID | FK para `map` |
| `segment_id` | UUID | FK para `route_segment` |
| `sequence_order` | INTEGER | Ordem do segmento no mapa (0, 1, 2...) |
| `distance_from_origin_km` | DECIMAL(8,3) | Distância acumulada até o início deste segmento |
| `created_at` | TIMESTAMP | Data de criação |

**Índices**:
- `UNIQUE` em `(map_id, segment_id)` - cada segmento aparece uma vez por mapa
- `INDEX` em `(map_id, sequence_order)` para ordenação

### Alterações em Modelos Existentes

#### Tabela `map_poi` (alterada)
Armazena junction e lado calculados no contexto do mapa específico.

| Campo | Tipo | Descrição | Novo? |
|-------|------|-----------|-------|
| `segment_poi_id` | UUID | FK para `segment_poi` | Sim |
| `distance_from_origin_km` | DECIMAL(8,3) | Distância absoluta desde origem do mapa | Não |
| `junction_lat` | DECIMAL(9,6) | Latitude do ponto de junção | Não (já existe) |
| `junction_lon` | DECIMAL(9,6) | Longitude do ponto de junção | Não (já existe) |
| `junction_distance_km` | DECIMAL(8,3) | Distância da junção desde origem | Não (já existe) |
| `distance_from_road_meters` | INTEGER | Distância perpendicular da rota ao POI | Não (já existe) |
| `side` | VARCHAR(10) | "left", "right", ou "center" | Não (já existe) |
| `requires_detour` | BOOLEAN | Se requer desvio (>500m) | Não (já existe) |
| `access_route_distance_km` | DECIMAL(8,3) | Distância do desvio | Não (já existe) |

**IMPORTANTE**: Todos os campos de junction e lado são calculados no momento da montagem do mapa, usando lookback de 10km. Esses valores são específicos para cada mapa e não são reutilizados.

## 4. Fluxo de Geração de Mapa

### Diagrama de Fluxo

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         GERAÇÃO DE MAPA - NOVO FLUXO                        │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  1. GEOCODING                                                               │
│     ├── Origem: "Belo Horizonte, MG" → (-19.9167, -43.9345)                │
│     └── Destino: "Ouro Preto, MG" → (-20.3855, -43.5035)                   │
│                                                                             │
│  2. ROTEAMENTO (OSRM com steps=true)                                        │
│     └── Retorna: 45 steps com geometry, maneuver, distance                  │
│                                                                             │
│  3. PROCESSAMENTO DE CADA STEP (busca de POIs)                              │
│     │                                                                       │
│     │  ┌──────────────────────────────────────────────────────────────┐     │
│     │  │ Para cada step:                                              │     │
│     │  │                                                              │     │
│     │  │  a) Calcular segment_hash                                    │     │
│     │  │     hash = MD5(start_lat, start_lon, end_lat, end_lon)       │     │
│     │  │                                                              │     │
│     │  │  b) Buscar no BD: SELECT * FROM route_segment                │     │
│     │  │                   WHERE segment_hash = ?                     │     │
│     │  │                                                              │     │
│     │  │  c) SE EXISTE (cache hit):                                   │     │
│     │  │     - Incrementar usage_count                                │     │
│     │  │     - Carregar POIs via segment_poi (apenas IDs)             │     │
│     │  │     - Carregar search_points do segmento                     │     │
│     │  │     - SKIP busca de POIs                                     │     │
│     │  │                                                              │     │
│     │  │  d) SE NÃO EXISTE (cache miss):                              │     │
│     │  │     - Criar route_segment                                    │     │
│     │  │     - Gerar e salvar search_points                           │     │
│     │  │     - Buscar POIs via Overpass/HERE                          │     │
│     │  │     - Salvar segment_poi (POI + search_point_index)          │     │
│     │  │     - NÃO calcular junction ainda                            │     │
│     │  └──────────────────────────────────────────────────────────────┘     │
│                                                                             │
│  4. MONTAGEM DA SEQUÊNCIA DE SEGMENTOS                                      │
│     ├── Criar registros map_segment com sequence_order                      │
│     ├── Calcular distance_from_origin_km para cada segmento                 │
│     └── Agregar search_points de todos os segmentos (lista global)          │
│                                                                             │
│  5. CÁLCULO DE JUNCTION PARA CADA POI (ver seção 6)                         │
│     │                                                                       │
│     │  ┌──────────────────────────────────────────────────────────────┐     │
│     │  │ Para cada POI encontrado nos segmentos:                      │     │
│     │  │                                                              │     │
│     │  │  a) Identificar search_point mais próximo do POI             │     │
│     │  │     (via segment_poi.search_point_index + mapa de offsets)   │     │
│     │  │                                                              │     │
│     │  │  b) Calcular distância absoluta do search_point              │     │
│     │  │     (segment.distance_from_origin + sp.distance_in_segment)  │     │
│     │  │                                                              │     │
│     │  │  c) Encontrar lookback_point:                                │     │
│     │  │     - Procurar primeiro search_point na direção da origem    │     │
│     │  │       com >= 10km de distância                               │     │
│     │  │                                                              │     │
│     │  │  d) Calcular rota: lookback_point → POI                      │     │
│     │  │     (via OSRM)                                               │     │
│     │  │                                                              │     │
│     │  │  e) Encontrar junction (onde rota diverge da principal)      │     │
│     │  │                                                              │     │
│     │  │  f) Determinar lado (left/right) baseado na direção          │     │
│     │  │                                                              │     │
│     │  │  g) Salvar map_poi com todos os dados calculados             │     │
│     │  └──────────────────────────────────────────────────────────────┘     │
│                                                                             │
│  6. DEDUPLICAÇÃO E ORDENAÇÃO                                                │
│     ├── Remover POIs duplicados (manter menor distance_from_road)           │
│     └── Ordenar por distance_from_origin_km                                 │
│                                                                             │
│  7. RESPOSTA                                                                │
│     └── Retornar mapa com POIs ordenados                                    │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Extração de Steps do OSRM

O OSRM deve ser chamado com parâmetros específicos:

```python
# api/providers/osm/provider.py

async def calculate_route(
    self,
    origin: GeoLocation,
    destination: GeoLocation,
    waypoints: Optional[List[GeoLocation]] = None,
    avoid: Optional[List[str]] = None
) -> Optional[Route]:
    """
    Calcula rota com steps detalhados.
    """
    url = "http://router.project-osrm.org/route/v1/driving"
    coords = f"{origin.longitude},{origin.latitude};{destination.longitude},{destination.latitude}"

    params = {
        "overview": "full",
        "geometries": "geojson",
        "annotations": "true",
        "steps": "true"  # CRÍTICO: habilita steps
    }

    response = await self.http_client.get(f"{url}/{coords}", params=params)
    data = response.json()

    route = data["routes"][0]

    # Extrair steps
    steps = []
    for leg in route["legs"]:
        for step in leg["steps"]:
            steps.append(RouteStep(
                geometry=step["geometry"]["coordinates"],
                distance_m=step["distance"],
                duration_s=step["duration"],
                name=step.get("name", ""),
                maneuver_type=step["maneuver"]["type"],
                maneuver_modifier=step["maneuver"].get("modifier"),
                maneuver_location=step["maneuver"]["location"]
            ))

    return Route(
        origin=origin,
        destination=destination,
        total_distance=route["distance"] / 1000,
        total_duration=route["duration"] / 60,
        geometry=self._convert_geometry(route["geometry"]),
        steps=steps  # NOVO: lista de steps
    )
```

## 5. Critérios para Search Points

### Regras de Geração

Os search points são usados para buscar POIs ao redor da rota. As regras são:

1. **Segmentos < 1km**: Não geram search points
   - São muito curtos para busca significativa
   - POIs relevantes serão capturados pelos segmentos adjacentes

2. **Segmentos >= 1km**:
   - **Primeiro search point**: Coordenada de início do segmento
   - **Search points intermediários**: A cada 1km ao longo do segmento
   - **Último search point**: Coordenada de fim (se não coincidir com intermediário)

### Algoritmo

```python
def generate_search_points(segment: RouteSegment) -> List[SearchPoint]:
    """
    Gera search points para um segmento.

    Args:
        segment: Segmento com geometry e length_km

    Returns:
        Lista de SearchPoint com coordenadas e distance_from_segment_start
    """
    if segment.length_km < 1.0:
        return []  # Segmentos < 1km não geram search points

    search_points = []
    geometry = segment.geometry  # Lista de (lat, lon)

    # Primeiro search point: início do segmento
    search_points.append(SearchPoint(
        latitude=geometry[0][0],
        longitude=geometry[0][1],
        distance_from_segment_start_km=0.0
    ))

    # Interpolar search points a cada 1km
    current_distance = 0.0
    target_distance = 1.0  # Próximo ponto em 1km

    for i in range(1, len(geometry)):
        prev = geometry[i-1]
        curr = geometry[i]
        segment_distance = haversine(prev, curr)

        while current_distance + segment_distance >= target_distance:
            # Interpolar ponto no km exato
            ratio = (target_distance - current_distance) / segment_distance
            point = interpolate(prev, curr, ratio)

            search_points.append(SearchPoint(
                latitude=point[0],
                longitude=point[1],
                distance_from_segment_start_km=target_distance
            ))

            target_distance += 1.0

        current_distance += segment_distance

    # Último search point: fim do segmento (se necessário)
    last = geometry[-1]
    if len(search_points) == 0 or haversine(
        (search_points[-1].latitude, search_points[-1].longitude),
        (last[0], last[1])
    ) > 0.5:  # Adiciona se distância > 500m do último ponto
        search_points.append(SearchPoint(
            latitude=last[0],
            longitude=last[1],
            distance_from_segment_start_km=segment.length_km
        ))

    return search_points
```

### Exemplo Visual

```
Segmento de 3.5km:
├────────────────────────────────────────────────────────────────────┤
0km                1km               2km               3km         3.5km
 ●                  ●                 ●                 ●             ●
 │                  │                 │                 │             │
 SP1               SP2               SP3               SP4           SP5
(início)                                                            (fim)

Segmento de 0.8km:
├─────────────────────────┤
0km                     0.8km
(sem search points - segmento muito curto)
```

## 6. Cálculo de Junction com Lookback de 10km

### O Problema

O cálculo da junction (ponto onde o motorista deve sair da rota principal para acessar o POI) e do lado (left/right) depende do contexto da viagem. Para calcular a melhor rota de acesso, precisamos simular a aproximação do veículo vindo de ~10km antes.

Com segmentos reutilizáveis, um POI no início de um segmento não tem contexto do que vem antes. Por isso, o cálculo de junction é feito **após** a montagem completa do mapa.

### Agregação de Search Points

Quando o mapa é montado com N segmentos, agregamos todos os search points em uma lista global ordenada:

```python
def aggregate_search_points(
    map_segments: List[MapSegment],
    segments: Dict[UUID, RouteSegment]
) -> List[GlobalSearchPoint]:
    """
    Agrega search points de todos os segmentos em lista ordenada.

    Returns:
        Lista de GlobalSearchPoint com distância absoluta desde origem
    """
    global_points = []

    for map_seg in sorted(map_segments, key=lambda s: s.sequence_order):
        segment = segments[map_seg.segment_id]
        segment_start = map_seg.distance_from_origin_km

        for sp in segment.search_points:
            global_points.append(GlobalSearchPoint(
                segment_id=segment.id,
                local_index=sp["index"],
                lat=sp["lat"],
                lon=sp["lon"],
                distance_from_origin_km=segment_start + sp["distance_from_segment_start_km"]
            ))

    return global_points
```

**Exemplo Visual**:
```
Segmento A (0-5km)          Segmento B (5-12km)         Segmento C (12-18km)
├─────────────────────┤     ├───────────────────────┤   ├─────────────────────┤
SP0  SP1  SP2  SP3  SP4     SP5  SP6  SP7  SP8  SP9     SP10 SP11 SP12 SP13
0km  1km  2km  3km  4km     5km  6km  7km  8km  9km     12km 13km 14km 15km

Lista global: [SP0, SP1, SP2, SP3, SP4, SP5, SP6, SP7, SP8, SP9, SP10, SP11, SP12, SP13]
```

### Algoritmo de Lookback

Para cada POI, encontramos o lookback point (ponto 10km antes):

```python
def find_lookback_point(
    poi_search_point_distance_km: float,
    global_search_points: List[GlobalSearchPoint],
    lookback_distance_km: float = 10.0
) -> GlobalSearchPoint:
    """
    Encontra o search point que está ~10km antes do POI.

    Args:
        poi_search_point_distance_km: Distância do search point que encontrou o POI
        global_search_points: Lista global de search points ordenada
        lookback_distance_km: Distância de lookback (default 10km)

    Returns:
        Search point mais adequado para início do cálculo de rota
    """
    target_distance = poi_search_point_distance_km - lookback_distance_km

    if target_distance <= 0:
        # POI está a menos de 10km da origem, usar primeiro search point
        return global_search_points[0]

    # Encontrar primeiro search point com distância >= target
    # (procurando da origem em direção ao POI)
    for sp in global_search_points:
        if sp.distance_from_origin_km >= target_distance:
            return sp

    # Fallback: retornar o último antes do POI
    return global_search_points[-1]
```

### Exemplo Prático

```
POI "Posto Shell" encontrado pelo SP9 (distância 9km da origem)

Lookback target: 9km - 10km = -1km → usar SP0 (origem)

Cálculo:
1. Rota OSRM de SP0 até Posto Shell
2. Encontrar onde essa rota diverge da rota principal
3. Junction = ponto de divergência
4. Side = baseado na direção da rota de acesso

---

POI "Hotel Fazenda" encontrado pelo SP12 (distância 14km da origem)

Lookback target: 14km - 10km = 4km → usar SP4 (ou SP5 se mais próximo)

Cálculo:
1. Rota OSRM de SP4 até Hotel Fazenda
2. Encontrar onde essa rota diverge da rota principal
3. Junction = ponto de divergência (provavelmente entre SP4 e SP12)
4. Side = baseado na direção da rota de acesso
```

### Implementação

```python
async def calculate_junction_for_poi(
    poi: POI,
    segment_poi: SegmentPOI,
    map_segment: MapSegment,
    segment: RouteSegment,
    global_search_points: List[GlobalSearchPoint],
    route_geometry: List[Tuple[float, float]],
    geo_provider: GeoProvider
) -> MapPOI:
    """
    Calcula junction e lado para um POI no contexto do mapa.
    """
    # 1. Identificar search point que encontrou o POI
    poi_sp = segment.search_points[segment_poi.search_point_index]
    poi_sp_distance = map_segment.distance_from_origin_km + poi_sp["distance_from_segment_start_km"]

    # 2. Encontrar lookback point (10km antes)
    lookback_point = find_lookback_point(poi_sp_distance, global_search_points)

    # 3. Calcular rota do lookback_point até o POI
    access_route = await geo_provider.calculate_route(
        origin=GeoLocation(
            latitude=lookback_point.lat,
            longitude=lookback_point.lon
        ),
        destination=GeoLocation(
            latitude=poi.latitude,
            longitude=poi.longitude
        )
    )

    # 4. Encontrar junction (onde access_route diverge da rota principal)
    junction = find_route_intersection(
        access_route.geometry,
        route_geometry,
        tolerance_meters=50
    )

    # 5. Calcular distância da junction desde a origem
    junction_distance_km = calculate_distance_along_route(
        route_geometry,
        junction
    )

    # 6. Determinar lado
    side = determine_side(
        route_geometry,
        junction,
        poi.location
    )

    # 7. Calcular distância do desvio
    access_distance_km = calculate_access_distance(
        access_route.geometry,
        junction
    )

    return MapPOI(
        poi_id=poi.id,
        segment_poi_id=segment_poi.id,
        distance_from_origin_km=junction_distance_km,
        junction_lat=junction[0],
        junction_lon=junction[1],
        junction_distance_km=junction_distance_km,
        distance_from_road_meters=int(access_distance_km * 1000),  # aproximado
        side=side,
        requires_detour=access_distance_km > 0.5,
        access_route_distance_km=access_distance_km
    )
```

### Otimização: POIs Próximos

Para POIs com `straight_line_distance_m < 500` (armazenado no segment_poi), podemos simplificar:
- Não calcular rota via OSRM
- Junction = search point mais próximo
- Side = cálculo geométrico direto (cross product)
- Isso economiza chamadas ao OSRM

```python
if segment_poi.straight_line_distance_m < 500:
    # POI próximo: cálculo simplificado
    junction = (poi_sp["lat"], poi_sp["lon"])
    side = calculate_side_geometric(route_geometry, junction, poi.location)
    # ...
else:
    # POI distante: calcular rota de acesso
    access_route = await geo_provider.calculate_route(...)
    # ...
```

## 7. Deduplicação de POIs

### Cenário de Duplicação

Um mesmo POI pode aparecer em múltiplos segmentos adjacentes:

```
Segmento A (km 10-15)     Segmento B (km 15-20)
├──────────────────────┤  ├──────────────────────┤
                    14.8km                   15.2km
                       ●──────Posto Shell──────●

O mesmo "Posto Shell" é encontrado na busca a partir do
fim do Segmento A e do início do Segmento B.
```

### Algoritmo de Deduplicação

```python
def deduplicate_pois(
    segments: List[MapSegment],
    segment_pois: Dict[UUID, List[SegmentPOI]]
) -> List[MapPOI]:
    """
    Deduplica POIs ao agregar segmentos em um mapa.

    Regras:
    1. Identificar POIs com mesmo poi_id
    2. Para duplicatas, manter o registro com menor distance_from_road
    3. Recalcular distance_from_origin considerando posição do segmento

    Args:
        segments: Segmentos do mapa ordenados por sequence_order
        segment_pois: Dict mapeando segment_id para seus POIs

    Returns:
        Lista de MapPOI únicos com distance_from_origin calculado
    """
    seen_pois: Dict[UUID, MapPOI] = {}  # poi_id -> melhor MapPOI

    for segment in segments:
        segment_start_km = segment.distance_from_origin_km

        for sp in segment_pois.get(segment.segment_id, []):
            # Calcular distância absoluta desde origem do mapa
            absolute_distance = segment_start_km + sp.junction_distance_km

            map_poi = MapPOI(
                poi_id=sp.poi_id,
                segment_poi_id=sp.id,
                distance_from_origin_km=absolute_distance,
                distance_from_road_meters=sp.distance_from_road_meters,
                side=sp.side,
                junction_lat=sp.junction_lat,
                junction_lon=sp.junction_lon,
                requires_detour=sp.requires_detour
            )

            # Verificar duplicata
            if sp.poi_id in seen_pois:
                existing = seen_pois[sp.poi_id]

                # Manter o mais próximo da rota
                if map_poi.distance_from_road_meters < existing.distance_from_road_meters:
                    seen_pois[sp.poi_id] = map_poi
            else:
                seen_pois[sp.poi_id] = map_poi

    # Ordenar por distância da origem
    return sorted(seen_pois.values(), key=lambda p: p.distance_from_origin_km)
```

## 7. Requisitos Funcionais

### RF1: Extração de Steps do OSRM
- **RF1.1**: Requisições ao OSRM devem incluir `steps=true`
- **RF1.2**: Cada step deve ser parseado para `RouteStep` model
- **RF1.3**: Geometry, distance, duration, maneuver devem ser extraídos

### RF2: Identificação e Armazenamento de Segmentos
- **RF2.1**: Calcular hash único com coordenadas arredondadas para 4 decimais
- **RF2.2**: Verificar existência no BD antes de processar
- **RF2.3**: Criar `route_segment` para novos segmentos
- **RF2.4**: Incrementar `usage_count` para segmentos reutilizados

### RF3: Geração de Search Points
- **RF3.1**: Ignorar segmentos < 1km para busca de POIs
- **RF3.2**: Gerar search point no início de segmentos >= 1km
- **RF3.3**: Gerar search points intermediários a cada 1km
- **RF3.4**: Gerar search point no fim se distância > 500m do último

### RF4: Associação POI-Segmento (Dados Reutilizáveis)
- **RF4.1**: POIs são associados via `segment_poi` com dados básicos
- **RF4.2**: `segment_poi` armazena apenas: `poi_id`, `search_point_index`, `straight_line_distance_m`
- **RF4.3**: `segment_poi` **NÃO** armazena junction, side, ou distance_from_road
- **RF4.4**: Esses dados são calculados no contexto do mapa (ver RF6)

### RF5: Montagem de Mapa
- **RF5.1**: Criar `map_segment` com `sequence_order` correto
- **RF5.2**: Calcular `distance_from_origin_km` acumulativo para cada segmento
- **RF5.3**: Agregar search_points de todos os segmentos em lista global
- **RF5.4**: Search points globais têm distância absoluta desde origem

### RF6: Cálculo de Junction (Dados Específicos do Mapa)
- **RF6.1**: Para cada POI, identificar search_point que o encontrou
- **RF6.2**: Calcular distância absoluta do search_point (segment offset + local distance)
- **RF6.3**: Encontrar lookback_point: primeiro search_point >= 10km antes
- **RF6.4**: Calcular rota de acesso via OSRM (lookback_point → POI)
- **RF6.5**: Encontrar junction (onde rota diverge da principal)
- **RF6.6**: Determinar lado (left/right) baseado na direção
- **RF6.7**: Otimização: POIs < 500m usam cálculo geométrico (sem OSRM)

### RF7: Deduplicação e Ordenação
- **RF7.1**: Agregar POIs de todos os segmentos
- **RF7.2**: Deduplicar por `poi_id` mantendo menor `distance_from_road`
- **RF7.3**: Ordenar por `distance_from_origin_km`

### RF8: Tratamento de Mapas Existentes
- **RF8.1**: Mapas existentes serão recalculados a partir de origem/destino
- **RF8.2**: Não há migração de dados - mapas antigos são regenerados sob demanda
- **RF8.3**: Ao regenerar, mapas passam a usar a nova arquitetura de segmentos

## 8. Requisitos Não-Funcionais

### Performance
- **RNF1**: Segmentos reutilizados devem ser carregados em < 50ms
- **RNF2**: Cache hit rate esperado > 40% após warm-up (3 meses de uso)
- **RNF3**: Busca por `segment_hash` deve usar índice (O(1))

### Escalabilidade
- **RNF4**: Sistema deve suportar 1M+ segmentos armazenados
- **RNF5**: Consultas espaciais devem usar índices geográficos

### Confiabilidade
- **RNF6**: Transações atômicas para criação de segmento + POIs
- **RNF7**: Rollback em caso de falha parcial

### Manutenibilidade
- **RNF8**: Cobertura de testes > 85% para novo código
- **RNF9**: Logs detalhados para cache hits/misses

## 9. Migrações de Banco de Dados

### Ordem de Execução

1. **Criar tabela `route_segment`**
2. **Criar tabela `segment_poi`**
3. **Criar tabela `map_segment`**
4. **Alterar tabela `map_poi`** (adicionar `segment_poi_id`)

### Migration 1: route_segment

```python
# alembic/versions/xxxx_create_route_segment.py

def upgrade():
    op.create_table(
        'route_segment',
        sa.Column('id', sa.UUID(), primary_key=True),
        sa.Column('segment_hash', sa.String(32), unique=True, nullable=False, index=True),
        sa.Column('start_lat', sa.Numeric(9, 6), nullable=False),
        sa.Column('start_lon', sa.Numeric(9, 6), nullable=False),
        sa.Column('end_lat', sa.Numeric(9, 6), nullable=False),
        sa.Column('end_lon', sa.Numeric(9, 6), nullable=False),
        sa.Column('road_name', sa.String(255), nullable=True),
        sa.Column('length_km', sa.Numeric(8, 3), nullable=False),
        sa.Column('geometry', sa.JSON(), nullable=False),
        sa.Column('search_points', sa.JSON(), nullable=False),  # NOVO: search points pré-calculados
        sa.Column('osrm_instruction', sa.Text(), nullable=True),
        sa.Column('osrm_maneuver_type', sa.String(50), nullable=True),
        sa.Column('usage_count', sa.Integer(), default=0),
        sa.Column('pois_fetched_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), onupdate=sa.func.now()),
    )

    # Índice espacial para busca por coordenadas
    op.create_index(
        'ix_route_segment_start_coords',
        'route_segment',
        ['start_lat', 'start_lon']
    )
```

### Migration 2: segment_poi

```python
def upgrade():
    op.create_table(
        'segment_poi',
        sa.Column('id', sa.UUID(), primary_key=True),
        sa.Column('segment_id', sa.UUID(), sa.ForeignKey('route_segment.id'), nullable=False),
        sa.Column('poi_id', sa.UUID(), sa.ForeignKey('poi.id'), nullable=False),
        sa.Column('search_point_index', sa.Integer(), nullable=False),  # Índice do SP que encontrou
        sa.Column('straight_line_distance_m', sa.Integer(), nullable=False),  # Distância aproximada
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
    )

    # Nota: junction_lat/lon, side, requires_detour etc são calculados no map_poi

    op.create_index(
        'ix_segment_poi_segment_id',
        'segment_poi',
        ['segment_id']
    )

    op.create_unique_constraint(
        'uq_segment_poi_segment_poi',
        'segment_poi',
        ['segment_id', 'poi_id']
    )
```

### Migration 3: map_segment

```python
def upgrade():
    op.create_table(
        'map_segment',
        sa.Column('id', sa.UUID(), primary_key=True),
        sa.Column('map_id', sa.UUID(), sa.ForeignKey('map.id'), nullable=False),
        sa.Column('segment_id', sa.UUID(), sa.ForeignKey('route_segment.id'), nullable=False),
        sa.Column('sequence_order', sa.Integer(), nullable=False),
        sa.Column('distance_from_origin_km', sa.Numeric(8, 3), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
    )

    op.create_index(
        'ix_map_segment_map_order',
        'map_segment',
        ['map_id', 'sequence_order']
    )

    op.create_unique_constraint(
        'uq_map_segment_map_segment',
        'map_segment',
        ['map_id', 'segment_id']
    )
```

### Migration 4: alter_map_poi

```python
def upgrade():
    # Nota: mapas existentes serão recalculados, não migrados
    # Por isso segment_poi_id é NOT NULL
    op.add_column(
        'map_poi',
        sa.Column('segment_poi_id', sa.UUID(), sa.ForeignKey('segment_poi.id'), nullable=False)
    )

    op.create_index(
        'ix_map_poi_segment_poi_id',
        'map_poi',
        ['segment_poi_id']
    )
```

## 10. Arquivos a Criar/Modificar

### Novos Arquivos

| Arquivo | Descrição |
|---------|-----------|
| `api/database/models/route_segment.py` | Model SQLAlchemy para `route_segment` |
| `api/database/models/segment_poi.py` | Model SQLAlchemy para `segment_poi` |
| `api/database/models/map_segment.py` | Model SQLAlchemy para `map_segment` |
| `api/database/repositories/route_segment.py` | Repository para segmentos |
| `api/database/repositories/segment_poi.py` | Repository para POIs de segmento |
| `api/services/segment_service.py` | Serviço de gerenciamento de segmentos |
| `api/services/segment_poi_service.py` | Serviço de POIs por segmento |
| `tests/services/test_segment_service.py` | Testes unitários |

### Arquivos a Modificar

| Arquivo | Alterações |
|---------|------------|
| `api/providers/osm/provider.py` | Extrair steps do OSRM |
| `api/providers/models.py` | Adicionar `RouteStep` model |
| `api/database/models/__init__.py` | Exportar novos models |
| `api/database/models/map_poi.py` | Adicionar `segment_poi_id` |
| `api/services/road_service.py` | Usar `SegmentService` no fluxo |
| `api/services/poi_search_service.py` | Associar POIs a segmentos |
| `api/services/map_storage_service_db.py` | Salvar map_segments |

## 11. Estimativa de Economia

### Cenário: 1000 mapas/mês

**Premissas:**
- Média de 50 segmentos por mapa
- 30% de sobreposição entre rotas (conservador para Brasil)
- ~20 POIs por segmento

**Sem reutilização:**
- 1000 mapas × 50 segmentos × 5 search points = 250.000 buscas de POI/mês

**Com reutilização (30% cache hit):**
- 175.000 buscas de POI/mês (30% economia)
- ~75.000 chamadas evitadas às APIs externas

### Projeção de Cache Hit Rate

| Período | Cache Hit Esperado | Justificativa |
|---------|-------------------|---------------|
| Mês 1 | 10-15% | Base inicial sendo construída |
| Mês 3 | 25-35% | Rotas principais cobertas |
| Mês 6 | 40-50% | Saturação de rotas comuns |
| Mês 12 | 50-60% | Cobertura ampla |

## 12. Riscos e Mitigações

| Risco | Probabilidade | Impacto | Mitigação |
|-------|--------------|---------|-----------|
| Segmentos muito granulares (muitos steps curtos) | Média | Baixo | Filtrar steps < 100m |
| POIs desatualizados em segmentos antigos | Média | Médio | Campo `pois_fetched_at` para refresh |
| Aumento significativo no tamanho do BD | Baixa | Médio | Monitorar crescimento, cleanup de segmentos não usados |
| Recálculo de mapas existentes lento | Baixa | Baixo | Processar em background sob demanda |

## 13. Métricas de Sucesso

| Métrica | Target | Medição |
|---------|--------|---------|
| Cache hit rate (3 meses) | > 30% | Logs de `usage_count` |
| Redução de API calls | > 25% | Comparar com baseline |
| Tempo de geração (cache hit) | < 2s | P95 latency |
| Cobertura de testes | > 85% | pytest-cov |

## 14. Cronograma Sugerido

### Fase 1: Fundação
- Criar models e migrations
- Implementar `SegmentService` básico
- Extrair steps do OSRM

### Fase 2: Integração
- Modificar `road_service.py` para usar segmentos
- Implementar busca/reutilização de segmentos
- Adaptar `poi_search_service.py`

### Fase 3: Deduplicação e Testes
- Implementar deduplicação de POIs
- Testes unitários e integração
- Ajustes de performance

### Fase 4: Deploy e Monitoramento
- Deploy em staging
- Métricas e logs
- Deploy em produção

---

**Documento criado por**: MapaLinear Team
**Data**: 2025-01-04
**Versão**: 1.1
**Status**: DRAFT

## Changelog

### Versão 1.1 (2025-01-04)
- **IMPORTANTE**: Separação entre dados reutilizáveis e dados específicos do mapa
- `segment_poi` agora armazena apenas: `poi_id`, `search_point_index`, `straight_line_distance_m`
- Junction, side, distance_from_road são calculados no `map_poi` (contexto do mapa)
- Adicionado campo `search_points` (JSONB) na tabela `route_segment`
- Nova seção 6: "Cálculo de Junction com Lookback de 10km"
- Algoritmo de agregação de search points globais
- Algoritmo de lookback para encontrar ponto 10km antes do POI
- Otimização: POIs < 500m usam cálculo geométrico (sem OSRM)
- RF8 atualizado: mapas existentes serão recalculados (sem migração de dados)

### Versão 1.0 (2025-01-04)
- Documento inicial
- Arquitetura de segmentos reutilizáveis baseados em steps OSRM
- Hash com 4 casas decimais (~11m precisão)
- Regras de search points para segmentos >= 1km
