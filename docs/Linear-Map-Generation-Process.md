# Processo de Geração do Mapa Linear - MapaLinear

**Versão**: 1.2
**Data**: 2025-01-19
**Autor**: Documentação Técnica MapaLinear

---

## 📋 Índice

1. [Visão Geral](#visão-geral)
2. [Fluxo Completo do Processo](#fluxo-completo-do-processo)
3. [Etapa 1: Geocodificação e Extração de Cidade](#etapa-1-geocodificação-e-extração-de-cidade)
4. [Etapa 2: Cálculo da Rota](#etapa-2-cálculo-da-rota)
5. [Etapa 3: Segmentação Linear](#etapa-3-segmentação-linear)
6. [Etapa 4: Extração de Pontos de Busca](#etapa-4-extração-de-pontos-de-busca)
7. [Etapa 5: Busca de POIs](#etapa-5-busca-de-pois)
8. [Etapa 6: Criação de Milestones](#etapa-6-criação-de-milestones)
9. [Etapa 7: Atribuição aos Segmentos](#etapa-7-atribuição-aos-segmentos)
10. [Estrutura de Dados](#estrutura-de-dados)
11. [Parâmetros Configuráveis](#parâmetros-configuráveis)
12. [Exemplos Práticos](#exemplos-práticos)

---

## Visão Geral

O **MapaLinear** transforma uma rota geográfica complexa em uma representação linear simplificada, destacando pontos de interesse (POIs) ao longo do caminho. Este documento descreve detalhadamente como esse processo funciona.

### Conceito Principal

```
Entrada: "São Paulo, SP" → "Rio de Janeiro, RJ"

Saída:   [Mapa Linear com segmentos de 1km e POIs]

         0km  1  2  3  4  5  6  7  8  9  10km ... 450km
         |---|---|---|---|---|---|---|---|---|---| ... |
         SP     [⛽]     [🍔]  [⛽]        [🏨]    RJ
```

### Objetivo

- **Simplificar** rotas longas em segmentos lineares
- **Identificar** pontos de interesse relevantes
- **Facilitar** o planejamento de paradas
- **Otimizar** para uso offline durante viagens

---

## Fluxo Completo do Processo

```
┌─────────────────────────────────────────────────────────────────┐
│                    GERAÇÃO DO MAPA LINEAR                       │
└─────────────────────────────────────────────────────────────────┘

   INPUT: origin="São Paulo, SP", destination="Rio de Janeiro, RJ"
     │
     ▼
┌─────────────────────────────────────────────────────────────────┐
│ ETAPA 1: GEOCODIFICAÇÃO E EXTRAÇÃO DE CIDADE                    │
│ Converter endereços em coordenadas + extrair cidade de origem   │
└─────────────────────────────────────────────────────────────────┘
     │
     │  origin_city = "São Paulo"  # Extraído de "São Paulo, SP"
     │  origin_location = GeoLocation(lat=-23.5505, lon=-46.6333)
     │  destination_location = GeoLocation(lat=-22.9068, lon=-43.1729)
     │
     ▼
┌─────────────────────────────────────────────────────────────────┐
│ ETAPA 2: CÁLCULO DA ROTA                                        │
│ Usar geo provider (OSM/HERE) para calcular melhor rota          │
└─────────────────────────────────────────────────────────────────┘
     │
     │  route = Route(
     │      distance_km=450.0,
     │      geometry=[(lat1,lon1), (lat2,lon2), ...],  # ~500-1000 pontos
     │      road_names=["Via Dutra", "BR-116"]
     │  )
     │
     ▼
┌─────────────────────────────────────────────────────────────────┐
│ ETAPA 3: SEGMENTAÇÃO LINEAR                                     │
│ Dividir rota em segmentos de tamanho fixo (padrão: 1km)         │
└─────────────────────────────────────────────────────────────────┘
     │
     │  segments = [
     │      Segment(0-1km),
     │      Segment(1-2km),
     │      ...
     │      Segment(449-450km)
     │  ]  # Total: 450 segmentos
     │
     ▼
┌─────────────────────────────────────────────────────────────────┐
│ ETAPA 4: EXTRAÇÃO DE PONTOS DE BUSCA                            │
│ Usar coordenadas de início/fim dos segmentos para buscar POIs   │
└─────────────────────────────────────────────────────────────────┘
     │
     │  search_points = [
     │      (lat_seg1_start, lon_seg1_start, 0km),     # início seg 1
     │      (lat_seg1_end, lon_seg1_end, 1km),         # fim seg 1
     │      (lat_seg2_end, lon_seg2_end, 2km),         # fim seg 2
     │      ...
     │  ]  # Total: ~450 pontos (1 por km)
     │
     ▼
┌─────────────────────────────────────────────────────────────────┐
│ ETAPA 5: BUSCA DE POIs                                          │
│ Para cada ponto de amostragem, buscar POIs em um raio de 3km    │
└─────────────────────────────────────────────────────────────────┘
     │
     │  Para cada ponto:
     │    - Buscar POIs (postos, restaurantes, hotéis, pedágios)
     │    - Filtrar por qualidade
     │    - Remover duplicatas
     │    - Excluir POIs da cidade de origem (via reverse geocoding)
     │
     ▼
┌─────────────────────────────────────────────────────────────────┐
│ ETAPA 6: CRIAÇÃO DE MILESTONES                                  │
│ Converter POIs em milestones com metadados enriquecidos         │
└─────────────────────────────────────────────────────────────────┘
     │
     │  milestones = [
     │      Milestone(name="Posto Shell", type="fuel", distance=15.3km),
     │      Milestone(name="Rest. Família", type="food", distance=23.7km),
     │      ...
     │  ]
     │
     ▼
┌─────────────────────────────────────────────────────────────────┐
│ ETAPA 7: ATRIBUIÇÃO AOS SEGMENTOS                               │
│ Alocar cada milestone ao segmento correspondente                │
└─────────────────────────────────────────────────────────────────┘
     │
     │  Para cada segmento:
     │    segment.milestones = [m for m in milestones
     │                          if segment.start <= m.distance <= segment.end]
     │
     ▼
┌─────────────────────────────────────────────────────────────────┐
│ OUTPUT: LinearMapResponse                                       │
│   - 45 segmentos lineares                                       │
│   - ~150 milestones distribuídos                                │
│   - Metadados completos para cada POI                           │
└─────────────────────────────────────────────────────────────────┘
```

---

## Etapa 1: Geocodificação e Extração de Cidade

### Objetivo
Converter endereços em formato texto para coordenadas geográficas precisas e extrair o nome da cidade de origem para filtragem de POIs.

### Processo

```python
# INPUT
origin = "São Paulo, SP"
destination = "Rio de Janeiro, RJ"

# PASSO 1: Extrair nome da cidade de origem
origin_city = origin.split(',')[0].strip()  # "São Paulo"
# Esta cidade será usada para filtrar POIs posteriormente

# PASSO 2: Geocodificar origem e destino
origin_location = await geo_provider.geocode(origin)
# Resultado: GeoLocation(
#     latitude=-23.5505,
#     longitude=-46.6333,
#     address="São Paulo, SP, Brasil"
# )

destination_location = await geo_provider.geocode(destination)
# Resultado: GeoLocation(
#     latitude=-22.9068,
#     longitude=-43.1729,
#     address="Rio de Janeiro, RJ, Brasil"
# )
```

### Extração de Cidade

A extração do nome da cidade é simples e eficaz:

```python
# Exemplos de extração
"São Paulo, SP"           → "São Paulo"
"Belo Horizonte, MG"      → "Belo Horizonte"
"Rio de Janeiro, RJ"      → "Rio de Janeiro"
"Campinas, SP"            → "Campinas"

# Normalização para comparação (feita posteriormente)
"São Paulo"  → "são paulo"  (lowercase + trim)
"Belo Horizonte" → "belo horizonte"
```

**Por que extrair do input do usuário?**
- ✅ Mais simples e confiável
- ✅ Evita inconsistências da API de geocoding
- ✅ Funciona offline (não depende de API)
- ✅ Formato previsível ("Cidade, UF")

### Diagrama Visual

```
Texto                     API Geocoding              Coordenadas
─────                     ─────────────              ───────────

"São Paulo, SP"    ───►   [GeoProvider]    ───►    (-23.5505, -46.6333)
                          (OSM/HERE)

"Rio de Janeiro"   ───►   [GeoProvider]    ───►    (-22.9068, -43.1729)
```

### Providers Suportados
- **OSM (OpenStreetMap)**: Nominatim API - Gratuito
- **HERE Maps**: Geocoding API v7 - Freemium (250k/mês grátis)

---

## Etapa 2: Cálculo da Rota

### Objetivo
Calcular a melhor rota entre origem e destino, obtendo geometria detalhada e metadados usando **OSRM** (Open Source Routing Machine).

### Motor de Roteamento

**OSRM (Open Source Routing Machine)** é o provider principal de roteamento:
- ✅ Roteamento otimizado para estradas
- ✅ Geometria de alta qualidade (500-1000 pontos)
- ✅ Gratuito e open-source
- ✅ API pública disponível
- ✅ Fallback para cálculo direto se OSRM falhar

### Processo

```python
# INPUT
origin_location = GeoLocation(lat=-23.5505, lon=-46.6333)
destination_location = GeoLocation(lat=-22.9068, lon=-43.1729)

# PROCESSO
route = await geo_provider.calculate_route(
    origin=origin_location,
    destination=destination_location
)

# OUTPUT
route = Route(
    distance_km=450.0,
    duration_seconds=16200,  # ~4.5 horas
    geometry=[
        (-23.5505, -46.6333),  # Ponto 1: São Paulo
        (-23.5489, -46.6350),  # Ponto 2
        (-23.5470, -46.6368),  # Ponto 3
        # ... ~500-1000 pontos intermediários
        (-22.9068, -43.1729)   # Ponto final: Rio
    ],
    road_names=["Via Dutra", "BR-116"],
    segments=[...]  # Detalhes da rota (opcional)
)
```

### Diagrama Visual

```
     São Paulo                                    Rio de Janeiro
        (-23.55, -46.63)                          (-22.91, -43.17)
           ●                                            ●
           │                                            │
           │  ┌──────────────────────────────────────┐ │
           └──┤     ROTEAMENTO (OSRM/HERE)          ├─┘
              │                                      │
              │  • Calcular melhor caminho           │
              │  • Considerar tipo de via            │
              │  • Gerar geometria detalhada         │
              │  • Estimar tempo/distância           │
              └──────────────────────────────────────┘
                              │
                              ▼
                    ┌─────────────────────┐
                    │   ROTA CALCULADA    │
                    ├─────────────────────┤
                    │ Distância: 450 km   │
                    │ Tempo: 4h30min      │
                    │ Via: BR-116         │
                    │ Pontos: ~800        │
                    └─────────────────────┘
```

### Geometria da Rota

A geometria é uma sequência de coordenadas que representa o caminho exato:

```
Visualização da geometria (simplificada):

SP ●─────●─────●─────●─────●─────●─────●─────● RJ
   0km   50km  100km 150km 200km 250km 300km  450km

   Cada ● representa múltiplos pontos na geometria real
   Na prática: ~500-1000 pontos para alta precisão
```

---

## Etapa 3: Segmentação Linear

### Objetivo
Dividir a rota em segmentos lineares de tamanho fixo para facilitar a navegação e organização dos POIs.

### Processo

```python
def _process_route_into_segments(route, segment_length_km=10.0):
    segments = []
    current_distance = 0.0
    segment_id = 1

    while current_distance < route.distance_km:
        start_km = current_distance
        end_km = min(current_distance + segment_length_km, route.distance_km)

        # Interpolar coordenadas nos pontos de início e fim
        start_coord = interpolate_at_distance(route.geometry, start_km)
        end_coord = interpolate_at_distance(route.geometry, end_km)

        segment = LinearRoadSegment(
            id=f"segment_{segment_id}",
            start_distance_km=start_km,
            end_distance_km=end_km,
            start_coordinates=start_coord,
            end_coordinates=end_coord,
            milestones=[]  # Preenchido depois
        )

        segments.append(segment)
        current_distance = end_km
        segment_id += 1

    return segments
```

### Diagrama Visual

```
ROTA ORIGINAL (450km com geometria complexa):
════════════════════════════════════════════════════════════════
   SP                                                        RJ
   ●───●──●───●──●───●──●───●──●───●──●───●──●───●──●───●──●
   │ Curvas, subidas, descidas, mudanças de direção...      │
════════════════════════════════════════════════════════════════

                         ▼ TRANSFORMAÇÃO ▼

MAPA LINEAR (segmentos de 10km):
════════════════════════════════════════════════════════════════
   0    10   20   30   40   50   60   70   80   90   100  ...  450
   |────|────|────|────|────|────|────|────|────|────|────|────|
   S1   S2   S3   S4   S5   S6   S7   S8   S9   S10  S11  ... S45

   Cada segmento: 10km lineares
   Total: 45 segmentos
════════════════════════════════════════════════════════════════

DETALHES DO SEGMENTO 1 (0-10km):
┌─────────────────────────────────────────────────────────┐
│ ID: segment_1                                           │
│ Nome: Via Dutra                                         │
│ Início: 0.0 km    → (-23.5505, -46.6333)              │
│ Fim: 10.0 km      → (-23.5123, -46.5987)              │
│ Comprimento: 10.0 km                                    │
│ Milestones: [] (preenchido na próxima etapa)           │
└─────────────────────────────────────────────────────────┘
```

### Interpolação de Coordenadas

Como determinar a coordenada exata em uma distância específica:

```
Exemplo: Encontrar coordenada no km 15.3

Geometria da rota (simplificada):
  Ponto 0: (lat=-23.55, lon=-46.63) → km 0
  Ponto 1: (lat=-23.54, lon=-46.62) → km 10
  Ponto 2: (lat=-23.53, lon=-46.61) → km 20
  ...

Processo:
1. Distância alvo: 15.3 km
2. Total da rota: 450 km
3. Razão: 15.3 / 450 = 0.034 (3.4% do caminho)
4. Total de pontos: 800
5. Índice interpolado: 0.034 × 800 = 27.2
6. Interpolar entre pontos 27 e 28
7. Resultado: (lat=-23.5312, lon=-46.6145)

Algoritmo simplificado:
  ratio = target_distance / total_distance
  point_index = ratio × (total_points - 1)
  point_before = geometry[floor(point_index)]
  point_after = geometry[ceil(point_index)]
  local_ratio = point_index - floor(point_index)

  result_lat = point_before.lat + (point_after.lat - point_before.lat) × local_ratio
  result_lon = point_before.lon + (point_after.lon - point_before.lon) × local_ratio
```

---

## Etapa 4: Extração de Pontos de Busca

### Objetivo
Extrair coordenadas dos segmentos lineares (1km) para usar como pontos de busca de POIs, eliminando a necessidade de amostragem arbitrária.

### Processo

**Mudança importante**: Eliminamos a amostragem de pontos a cada 5km. Agora usamos as coordenadas de início e fim de cada segmento de 1km diretamente.

```python
def _extract_search_points_from_segments(segments: List[LinearRoadSegment]):
    """
    Extrai pontos de busca das coordenadas dos segmentos.

    Para cada segmento de 1km, usamos as coordenadas de início e fim
    como pontos onde buscaremos POIs em um raio de 3km.
    """
    search_points = []

    for segment in segments:
        # Usar coordenadas de início e fim de cada segmento
        start_point = (
            segment.start_coordinates.latitude,
            segment.start_coordinates.longitude
        )
        end_point = (
            segment.end_coordinates.latitude,
            segment.end_coordinates.longitude
        )

        search_points.append((start_point, segment.start_distance_km))
        search_points.append((end_point, segment.end_distance_km))

    # Remover duplicatas (fim de um segmento = início do próximo)
    search_points = list(dict.fromkeys(search_points))

    return search_points

# Exemplo de saída para rota de 450km com segmentos de 1km:
search_points = [
    ((lat=-23.5505, lon=-46.6333), 0.0),      # início seg 1 (km 0)
    ((lat=-23.5501, lon=-46.6320), 1.0),      # fim seg 1 = início seg 2 (km 1)
    ((lat=-23.5497, lon=-46.6307), 2.0),      # fim seg 2 (km 2)
    ((lat=-23.5493, lon=-46.6294), 3.0),      # fim seg 3 (km 3)
    # ... mais 447 pontos ...
    ((lat=-22.9068, lon=-43.1729), 450.0)     # fim último segmento (km 450)
]  # Total: ~450 pontos (1 por km)
```

**Vantagens**:
- ✅ Granularidade de 1km (vs 5km antigamente)
- ✅ Não perde POIs entre pontos de amostragem
- ✅ Código mais simples (não precisa interpolar)
- ✅ Coordenadas precisas já calculadas na segmentação
- ✅ Melhor cobertura de POIs

### Diagrama Visual

**Processo Antigo (DESCONTINUADO)**: Amostragem a cada 5km
```
SP ●────●────●────●────●────●────● RJ
   0    5   10   15   20   25   30km...

   Problemas: ~91 pontos, pode perder POIs entre amostragens
```

**Processo Atual**: Pontos de busca dos segmentos de 1km
```
SEGMENTOS DE 1KM:
════════════════════════════════════════════════════════════════
        Segmento 1     Segmento 2     Segmento 3     Segmento 4
   0km  ├─────────┤  ├─────────┤  ├─────────┤  ├─────────┤  4km
   SP   ●─────────●──●─────────●──●─────────●──●─────────●
        ↑         ↑  ↑         ↑  ↑         ↑  ↑         ↑
      início    fim  início    fim início    fim início    fim
        P0       P1  (P1)      P2  (P2)      P3  (P3)      P4

   Cada coordenada de início/fim é um ponto de busca
   Total: ~450 pontos para rota de 450km

BUSCA DE POIs EM CADA PONTO (raio: 3km):
════════════════════════════════════════════════════════════════

        Raio de busca (3km)          Raio de busca (3km)
              ╱───╲                        ╱───╲
   ●──────────●──────────●──────────●──────────●──────────●
   0km       P1         2km        P3         4km        P5

              [──── overlap ────]

   Overlap total: Cada POI pode ser encontrado em múltiplos pontos
   Garante cobertura completa sem perder POIs
```

### Por que usar coordenadas dos segmentos?

**Vantagens sobre amostragem de 5km**:
- ✅ **Granularidade superior**: 1km vs 5km
- ✅ **Cobertura completa**: Não perde POIs entre pontos
- ✅ **Coordenadas precisas**: Já calculadas na segmentação
- ✅ **Código simples**: Não precisa interpolar
- ✅ **Melhor qualidade**: Mais POIs descobertos

**Trade-off**:
- ⚠️ Mais requisições à API: ~450 vs ~91 (mas com cache, não é problema)
- ✅ Muito melhor detecção de POIs compensa o aumento

---

## Etapa 5: Busca de POIs

### Objetivo
Para cada ponto de amostragem, buscar POIs relevantes em um raio configurável.

### Processo

```python
async def _find_milestones_along_route(
    route,
    categories,
    max_distance_from_road=3000,
    exclude_cities=None  # Lista de cidades a excluir (ex: ["São Paulo"])
):
    """
    Busca POIs ao longo da rota.

    Args:
        route: Rota calculada
        categories: [POICategory.GAS_STATION, POICategory.RESTAURANT, ...]
        max_distance_from_road: Raio de busca em metros (padrão: 3000m = 3km)
        exclude_cities: Lista de nomes de cidades cujos POIs devem ser excluídos
    """
    milestones = []

    # Gerar pontos de amostragem a cada 5km
    sample_points = _sample_points_along_route(route, interval_km=5.0)

    for point, distance_from_origin in sample_points:
        # Buscar POIs ao redor deste ponto
        pois = await geo_provider.search_pois(
            location=GeoLocation(latitude=point[0], longitude=point[1]),
            radius=max_distance_from_road,  # 3000 metros
            categories=categories,
            limit=20  # Máximo 20 POIs por ponto
        )

        # Converter POIs em milestones (próxima etapa)
        for poi in pois:
            # Evitar duplicatas
            if not any(m.id == poi.id for m in milestones):
                milestone = create_milestone_from_poi(poi, distance_from_origin)
                milestones.append(milestone)

    # Enriquecer milestones com informações de cidade (reverse geocoding)
    await enrich_milestones_with_cities(milestones)

    # Filtrar POIs da cidade de origem
    if exclude_cities:
        exclude_cities_normalized = [city.strip().lower() for city in exclude_cities]
        milestones = [
            m for m in milestones
            if not m.city or m.city.strip().lower() not in exclude_cities_normalized
        ]

    return milestones
```

### Diagrama Visual: Busca em um Ponto

```
PONTO DE AMOSTRAGEM P5 (km 25):
════════════════════════════════════════════════════════════════

                        Raio de busca: 3km
                     ╱──────────────────╲
                    │                    │
                    │     ⛽ Posto 1     │  (2.1km do ponto)
         Rota       │                    │
    ●───────────────●────────────────────●──────────
                  (P5)
                    │   🍔 Restaurante   │  (1.5km do ponto)
                    │                    │
                    │     ⛽ Posto 2     │  (2.8km do ponto)
                    │                    │
                     ╲──────────────────╱

API Request para P5:
  POST /api/search-pois
  {
    "latitude": -23.4567,
    "longitude": -46.5432,
    "radius": 3000,  // metros
    "categories": ["fuel", "restaurant", "hotel"],
    "limit": 20
  }

Response:
  {
    "pois": [
      {
        "id": "node/123456",
        "name": "Posto Shell Via Dutra",
        "category": "fuel",
        "location": {"lat": -23.4589, "lon": -46.5456},
        "distance": 2100,  // metros do ponto P5
        ...
      },
      {
        "id": "node/234567",
        "name": "Restaurante Família",
        "category": "restaurant",
        "location": {"lat": -23.4578, "lon": -46.5445},
        "distance": 1500,
        ...
      },
      ...
    ]
  }
```

### Filtragem de Qualidade

Nem todos os POIs retornados são incluídos. Há um sistema de qualidade:

```python
def _meets_quality_threshold(poi_tags, quality_score):
    """
    Filtra POIs por qualidade dos dados.

    Score calculado baseado em:
    - Tem nome? (+14%)
    - Tem operador/marca? (+14%)
    - Tem telefone? (+14%)
    - Tem horário de funcionamento? (+14%)
    - Tem website? (+14%)
    - Tem informações específicas? (+14%)
    - Tem endereço estruturado? (+14%)

    Thresholds:
    - Postos de gasolina: >= 30%
    - Restaurantes: >= 40%
    - Outros: >= 30%
    """
    if poi_tags['amenity'] == 'fuel':
        return quality_score >= 0.3  # Posto precisa de pelo menos nome/marca

    if poi_tags['amenity'] == 'restaurant':
        return quality_score >= 0.4  # Restaurante precisa de mais info

    return quality_score >= 0.3
```

### Exemplo de Filtragem

```
POIs encontrados no km 25:

✅ ACEITO (score: 71%)
   Nome: Posto Ipiranga Via Dutra
   Marca: Ipiranga
   Telefone: +55 11 3456-7890
   Horário: 24/7
   Amenidades: banheiro, loja conveniência

❌ REJEITADO (score: 14%)
   Nome: (sem nome)
   Marca: (sem marca)
   Apenas: amenity=fuel

✅ ACEITO (score: 57%)
   Nome: Restaurante Família Mancini
   Cozinha: Italiana
   Telefone: +55 11 3456-1234
   Horário: 11:00-23:00
```

### Filtragem por Cidade

Após buscar e filtrar POIs por qualidade, o sistema aplica filtragem por cidade para remover POIs da cidade de origem:

```python
def filter_by_city(milestones, exclude_cities):
    """
    Filtra milestones excluindo POIs das cidades especificadas.

    Args:
        milestones: Lista de RoadMilestone com campo 'city' preenchido
        exclude_cities: Lista de nomes de cidades a excluir (ex: ["São Paulo"])

    Returns:
        Lista filtrada de milestones
    """
    # Normalizar nomes de cidades para comparação (lowercase, trim)
    exclude_cities_normalized = [city.strip().lower() for city in exclude_cities]

    filtered = [
        m for m in milestones
        if not m.city or m.city.strip().lower() not in exclude_cities_normalized
    ]

    return filtered
```

**Exemplo: Rota "São Paulo, SP" → "Rio de Janeiro, RJ"**

```
POIs encontrados após busca e filtragem de qualidade:

✅ INCLUÍDO - Posto Shell
   Cidade: Guarulhos
   Distância: 25.3km
   Motivo: Cidade diferente de São Paulo

✅ INCLUÍDO - Restaurante Estrada
   Cidade: Jacareí
   Distância: 87.5km
   Motivo: Cidade diferente de São Paulo

❌ EXCLUÍDO - Posto Ipiranga Marginal
   Cidade: São Paulo
   Distância: 8.2km
   Motivo: Cidade de origem (São Paulo)

❌ EXCLUÍDO - Restaurante Paulista
   Cidade: são paulo  # Normalizado para comparação
   Distância: 12.1km
   Motivo: Cidade de origem (São Paulo)

✅ INCLUÍDO - Hotel Via Dutra
   Cidade: Rio de Janeiro
   Distância: 442.8km
   Motivo: Cidade de destino (incluída)
```

**Enriquecimento com Reverse Geocoding**

Para cada milestone, fazemos reverse geocoding para obter o nome da cidade:

```python
async def enrich_milestones_with_cities(milestones):
    """
    Enriquece milestones com informações de cidade via reverse geocoding.
    """
    for milestone in milestones:
        if not milestone.city:  # Se ainda não tem cidade
            location = await geo_provider.reverse_geocode(
                milestone.coordinates.latitude,
                milestone.coordinates.longitude
            )
            # Extrair cidade do resultado
            milestone.city = location.city or location.town or location.village
```

---

## Etapa 6: Criação de Milestones

### Objetivo
Converter POIs brutos em milestones enriquecidos com metadados específicos para o contexto da viagem.

### Processo

```python
def create_milestone_from_poi(poi, distance_from_origin, route_point):
    """
    Converte um POI em um Milestone.

    Args:
        poi: POI retornado pela busca
        distance_from_origin: Distância do ponto de origem (km)
        route_point: Ponto da rota mais próximo (para calcular distância)
    """
    # Calcular distância do POI até a estrada
    distance_from_road = haversine_distance(
        poi.location.latitude, poi.location.longitude,
        route_point[0], route_point[1]
    )

    # Mapear categoria POI → tipo de milestone
    milestone_type = map_category_to_type(poi.category)

    # Criar milestone
    milestone = RoadMilestone(
        id=poi.id,
        name=poi.name,
        type=milestone_type,  # fuel, food, lodging, services
        coordinates=Coordinates(
            latitude=poi.location.latitude,
            longitude=poi.location.longitude
        ),
        distance_from_origin_km=distance_from_origin,
        distance_from_road_meters=distance_from_road,
        side="center",  # TODO: Determinar lado da pista

        # Metadados enriquecidos
        operator=poi.subcategory,  # ex: "Ipiranga", "Famiglia Mancini"
        brand=poi.subcategory,
        opening_hours=format_opening_hours(poi.opening_hours),
        phone=poi.phone,
        website=poi.website,
        amenities=poi.amenities,  # ["24h", "banheiro", "wifi"]
        quality_score=poi.rating,
        tags=poi.provider_data  # Dados brutos do provider
    )

    return milestone
```

### Diagrama Visual: Transformação POI → Milestone

```
POI BRUTO (do OpenStreetMap):
┌──────────────────────────────────────────────────────────┐
│ OSM Element                                              │
├──────────────────────────────────────────────────────────┤
│ type: "node"                                             │
│ id: 9158284853                                           │
│ lat: -23.4589                                            │
│ lon: -46.5456                                            │
│ tags: {                                                  │
│   "amenity": "fuel",                                     │
│   "brand": "Ipiranga",                                   │
│   "name": "Posto Ipiranga Via Dutra",                    │
│   "operator": "Ipiranga S.A.",                           │
│   "opening_hours": "24/7",                               │
│   "phone": "+55 11 3456-7890",                           │
│   "fuel:diesel": "yes",                                  │
│   "fuel:ethanol": "yes",                                 │
│   "toilets": "yes",                                      │
│   "car_wash": "yes",                                     │
│   "shop": "convenience"                                  │
│ }                                                        │
└──────────────────────────────────────────────────────────┘
                         │
                         │ TRANSFORMAÇÃO
                         ▼
MILESTONE ENRIQUECIDO:
┌──────────────────────────────────────────────────────────┐
│ RoadMilestone                                            │
├──────────────────────────────────────────────────────────┤
│ id: "node/9158284853"                                    │
│ name: "Posto Ipiranga Via Dutra"                         │
│ type: MilestoneType.FUEL                                 │
│                                                          │
│ coordinates:                                             │
│   latitude: -23.4589                                     │
│   longitude: -46.5456                                    │
│                                                          │
│ distance_from_origin_km: 25.3                            │
│ distance_from_road_meters: 350                           │
│ side: "right"                                            │
│                                                          │
│ operator: "Ipiranga"                                     │
│ brand: "Ipiranga"                                        │
│ opening_hours: "24 horas"                                │
│ phone: "+55 11 3456-7890"                                │
│ website: null                                            │
│                                                          │
│ amenities: [                                             │
│   "24h",                                                 │
│   "banheiro",                                            │
│   "lava-jato",                                           │
│   "loja conveniência",                                   │
│   "diesel",                                              │
│   "etanol"                                               │
│ ]                                                        │
│                                                          │
│ quality_score: 0.85                                      │
│                                                          │
│ tags: { ... dados brutos OSM ... }                       │
└──────────────────────────────────────────────────────────┘
```

### Mapeamento de Categorias

```
POICategory (genérica)  →  MilestoneType (específica)
══════════════════════════════════════════════════════

GAS_STATION            →  FUEL (combustível)
FUEL                   →  FUEL

RESTAURANT             →  RESTAURANT (restaurante)
FAST_FOOD              →  FAST_FOOD (fast food)
CAFE                   →  CAFE (café)
BAR                    →  BAR (bar)
PUB                    →  PUB (pub)
FOOD_COURT             →  FOOD_COURT (praça de alimentação)
BAKERY                 →  BAKERY (padaria)
ICE_CREAM              →  ICE_CREAM (sorveteria)

HOTEL                  →  HOTEL (hospedagem)
MOTEL                  →  LODGING

HOSPITAL               →  SERVICES (serviços)
PHARMACY               →  SERVICES
ATM                    →  SERVICES
POLICE                 →  SERVICES
MECHANIC               →  SERVICES
REST_AREA              →  SERVICES

TOLL_BOOTH             →  TOLL (pedágio)

CITY                   →  CITY (cidade)
TOWN                   →  CITY
```

### Cálculo de Entroncamento para POIs Afastados

**Problema**: POIs distantes da estrada (>500m) requerem que o viajante saia da rodovia principal. A distância do POI até a origem não reflete onde o viajante deve realmente sair da estrada.

**Solução**: Para POIs afastados, o sistema calcula o **entroncamento** (junction) - o ponto exato na rota principal onde o viajante deve sair para acessar o POI.

#### Quando é Aplicado

```
Critério de ativação: distance_from_road_meters > 500

POI próximo (≤500m):               POI afastado (>500m):
════════════════════════            ════════════════════════
        ⛽ (300m)                            🏨 (2500m)
         |                                    |
    ─────●─────  Rota                    ─────●─────  Rota
         ↑                                    ↑
    Acesso direto                       Precisa de entroncamento!
    (não calcula junction)              (calcula junction)
```

#### Estratégia: Routing Regional com Lookback

O sistema usa uma estratégia de "lookback" inteligente:

```python
1. Detecta POI afastado (>500m da estrada)
2. Calcula ponto de lookback:
   - Mínimo: 5km antes do ponto de detecção
   - Máximo: 20km antes do ponto de detecção
   - Dinâmico: baseado na distância do POI da estrada

3. Calcula rota do ponto de lookback até o POI
4. Encontra interseção entre essa rota e a rota principal
5. Marca a interseção como entroncamento
```

#### Diagrama Visual: Processo de Cálculo

```
SITUAÇÃO: Hotel encontrado no km 45, mas está 2.5km distante da estrada

════════════════════════════════════════════════════════════════════
ROTA PRINCIPAL (Via Dutra):
                                        ● Hotel (2.5km da estrada)
                                       ╱
   Origem ●──────────────────────────●───────────────────── Destino
          0km    10km   20km   30km  40km   50km   60km
                                     ↑
                              Ponto de detecção
                              (km 45 - mais próximo)

PASSO 1: Calcular lookback dinâmico
   POI distance: 2.5km → lookback: min(2.5 × 4, 20) = 10km
   Lookback point: 45km - 10km = 35km

PASSO 2: Calcular rota de acesso (lookback → POI)
   ════════════════════════════════════════════════════════════════
                                        ● Hotel
                                       ╱│
                                      ╱ │
   Origem ●────────────────────●─────●──●──────────────── Destino
          0km              Lookback  │  45km
                           (35km)    │
                                     ↓
                              Rota de acesso calculada
                              (via OSRM routing)

PASSO 3: Encontrar interseção (com tolerância de 150m)
   ════════════════════════════════════════════════════════════════
                                        ● Hotel
                                       ╱
                                      ╱
   Origem ●────────────────────●─────◆──●──────────────── Destino
          0km              35km    42.5km 45km
                                     ↑
                              Entroncamento encontrado!
                              (interseção das rotas)

RESULTADO: Milestone com informações de entroncamento
   ════════════════════════════════════════════════════════════════
   RoadMilestone {
       name: "Hotel Fazenda Via Dutra",
       distance_from_origin_km: 45.0,        ← Onde foi detectado
       distance_from_road_meters: 2500,       ← Distância do POI

       requires_detour: true,                 ← POI requer desvio
       junction_distance_km: 42.5,            ← Onde SAIR da estrada
       junction_coordinates: (lat, lon)       ← Coordenadas da saída
   }
```

#### Parâmetros do Algoritmo

```python
# Limiar para POI afastado
DISTANCE_THRESHOLD = 500  # metros

# Lookback dinâmico
MIN_LOOKBACK_KM = 5       # Mínimo de lookback
MAX_LOOKBACK_KM = 20      # Máximo de lookback
LOOKBACK_FACTOR = 4       # Multiplicador da distância do POI

lookback_km = min(
    max(poi_distance_km * LOOKBACK_FACTOR, MIN_LOOKBACK_KM),
    MAX_LOOKBACK_KM
)

# Tolerância para encontrar interseção
INTERSECTION_TOLERANCE = 150  # metros
```

#### Exemplo Prático

```
Cenário: Rota São Paulo → Rio de Janeiro

POI encontrado no km 87.5:
   Nome: "Restaurante Panorama"
   Distância da estrada: 1800 metros (>500m ✓)
   Coordenadas: (-23.2145, -45.8976)

Cálculo do entroncamento:
   1. Lookback: 1.8km × 4 = 7.2km
   2. Lookback point: 87.5 - 7.2 = 80.3km
   3. Rota calculada: Ponto(80.3km) → Restaurante
   4. Interseção encontrada: km 84.7

Resultado no milestone:
   distance_from_origin_km: 87.5      # Detecção original
   junction_distance_km: 84.7          # Onde realmente sair!
   requires_detour: true

Mensagem para o viajante:
   "No km 84.7, saia da rodovia para acessar o
    Restaurante Panorama (1.8km da estrada)"
```

#### Casos Especiais

**Caso 1: Entroncamento não encontrado**
```
Se a interseção não for encontrada dentro da tolerância:
   → POI é ABANDONADO (não incluído no mapa)
   → Motivo: Provavelmente inacessível ou rota muito indireta
```

**Caso 2: Lookback muito próximo do início**
```
Se lookback_point < 0:
   → Usa lookback_point = 0 (início da rota)
   → Garante que sempre há um ponto de partida válido
```

**Caso 3: POI próximo da estrada**
```
Se distance_from_road <= 500m:
   → junction_distance_km: null
   → junction_coordinates: null
   → requires_detour: false
   → Acesso direto, sem necessidade de cálculo
```

#### Performance

```
Impacto no tempo de processamento:

Rota de 450km com 150 POIs:
   - POIs próximos (≤500m): 130 POIs → sem cálculo extra
   - POIs afastados (>500m): 20 POIs → +20 cálculos de rota

Tempo adicional:
   - Com cache: ~2-3 segundos
   - Sem cache: ~40-60 segundos (20 rotas × 2-3s cada)

Trade-off: ✅ Informação precisa vale o custo adicional
```

---

## Etapa 7: Atribuição aos Segmentos

### Objetivo
Alocar cada milestone ao(s) segmento(s) correto(s) baseado na distância da origem.

### Processo

```python
def assign_milestones_to_segments(segments, milestones):
    """
    Atribui milestones aos segmentos baseado em distância.

    Um milestone pertence a um segmento se:
      segment.start_km <= milestone.distance_km <= segment.end_km
    """
    # Ordenar milestones por distância
    milestones.sort(key=lambda m: m.distance_from_origin_km)

    # Para cada segmento, encontrar seus milestones
    for segment in segments:
        segment.milestones = [
            m for m in milestones
            if segment.start_distance_km <= m.distance_from_origin_km <= segment.end_distance_km
        ]

        # Ordenar milestones dentro do segmento
        segment.milestones.sort(key=lambda m: m.distance_from_origin_km)

    return segments
```

### Diagrama Visual: Atribuição

```
SEGMENTOS E MILESTONES:
════════════════════════════════════════════════════════════════

Segmentos (10km cada):
   0      10     20     30     40     50     60     70    km
   |──S1──|──S2──|──S3──|──S4──|──S5──|──S6──|──S7──|

Milestones encontrados:
   M1(⛽)  M2(🍔)  M3(⛽)  M4(🏨)  M5(⛽)  M6(🍔)  M7(⛽)
   3.2km  8.7km  15.3km 23.7km 34.5km 42.1km 55.8km

                  ▼ ATRIBUIÇÃO ▼

Segment 1 (0-10km):
├─ M1: Posto Shell (3.2km)
└─ M2: Restaurante Família (8.7km)

Segment 2 (10-20km):
└─ M3: Posto Ipiranga (15.3km)

Segment 3 (20-30km):
└─ M4: Hotel Via Dutra (23.7km)

Segment 4 (30-40km):
└─ M5: Posto BR (34.5km)

Segment 5 (40-50km):
└─ M6: Lanchonete KM 42 (42.1km)

Segment 6 (50-60km):
└─ M7: Auto Posto Guararema (55.8km)

Segment 7 (60-70km):
└─ (sem milestones neste segmento)
```

### Caso Especial: Milestone na Fronteira

```
Milestone exatamente no limite de dois segmentos:

   Segment 1 (0-10km)      Segment 2 (10-20km)
   |──────────────────|────|──────────────────|
                      ●
                   M (10.0km)

Regra: Pertence ao segmento seguinte (Segment 2)

Implementação:
  if start_km <= milestone_km <= end_km:
      # <= em ambos os lados
      # Mas em prática, o primeiro segmento que satisfaz ganha
```

---

## Estrutura de Dados

### LinearMapResponse

```python
@dataclass
class LinearMapResponse:
    """Resposta completa do mapa linear."""
    origin: str                          # "São Paulo, SP"
    destination: str                     # "Rio de Janeiro, RJ"
    total_length_km: float               # 450.0
    segments: List[LinearRoadSegment]    # 45 segmentos
    milestones: List[RoadMilestone]      # ~150 milestones
    road_id: str                         # "route_12345"
```

### LinearRoadSegment

```python
@dataclass
class LinearRoadSegment:
    """Um segmento linear da rota."""
    id: str                              # "segment_1"
    name: str                            # "Via Dutra"
    start_distance_km: float             # 0.0
    end_distance_km: float               # 10.0
    length_km: float                     # 10.0
    start_coordinates: Dict              # {"latitude": -23.55, "longitude": -46.63}
    end_coordinates: Dict                # {"latitude": -23.51, "longitude": -46.60}
    milestones: List[RoadMilestone]      # POIs neste segmento
```

### RoadMilestone

```python
@dataclass
class RoadMilestone:
    """Um ponto de interesse ao longo da rota."""
    id: str                              # "node/123456"
    name: str                            # "Posto Ipiranga Via Dutra"
    type: MilestoneType                  # FUEL, FOOD, LODGING, SERVICES
    coordinates: Coordinates             # (lat, lon)
    distance_from_origin_km: float       # 25.3
    distance_from_road_meters: float     # 350
    side: str                            # "right", "left", "center"

    # Metadados
    operator: Optional[str]              # "Ipiranga"
    brand: Optional[str]                 # "Ipiranga"
    opening_hours: Optional[str]         # "24 horas"
    phone: Optional[str]                 # "+55 11 3456-7890"
    website: Optional[str]               # "https://..."
    amenities: List[str]                 # ["24h", "banheiro", "wifi"]
    quality_score: Optional[float]       # 0.85
    tags: Dict                           # Dados brutos do provider

    # Informações de entroncamento (para POIs afastados)
    junction_distance_km: Optional[float]      # 42.5 - Distância do entroncamento desde a origem
    junction_coordinates: Optional[Coordinates] # Coordenadas do entroncamento/saída
    requires_detour: bool                      # True se POI está >500m da estrada
```

---

## Parâmetros Configuráveis

### Parâmetros do `generate_linear_map`

```python
def generate_linear_map(
    origin: str,                                    # Obrigatório
    destination: str,                               # Obrigatório
    road_id: Optional[str] = None,                  # ID customizado
    include_cities: bool = True,                    # Incluir cidades
    include_gas_stations: bool = True,              # Incluir postos
    include_food: bool = False,                     # Incluir estabelecimentos de alimentação (8 tipos)
    include_toll_booths: bool = True,               # Incluir pedágios
    max_distance_from_road: float = 3000,           # Raio busca (metros)
    min_distance_from_origin_km: float = 0.0,       # DEPRECATED - use filtragem por cidade
    segment_length_km: float = 1.0,                 # Tamanho segmento (padrão: 1km)
    progress_callback: Optional[Callable] = None    # Callback progresso
) -> LinearMapResponse:
```

### Impacto dos Parâmetros

#### `include_food` (Estabelecimentos de Alimentação)

**Mudança importante**: Substituiu `include_restaurants` e agora inclui **8 tipos** de estabelecimentos de alimentação.

```
include_food=True busca os seguintes tipos:

📍 Refeições:
   - restaurant     (restaurantes)
   - fast_food      (fast food)
   - food_court     (praças de alimentação)

📍 Bebidas:
   - cafe           (cafés e cafeterias)
   - bar            (bares)
   - pub            (pubs)

📍 Doces:
   - bakery         (padarias)
   - ice_cream      (sorveterias)

Vantagem: Cobertura completa de opções de alimentação para viajantes
```

**Exemplo de query OSM**:
```
amenity~"restaurant|fast_food|cafe|bar|pub|food_court|ice_cream"
shop="bakery"
```

#### `segment_length_km` (Tamanho do Segmento)

**Mudança importante**: O padrão mudou de 10km para **1km** para melhor detecção de POIs.

```
segment_length_km = 1.0 (PADRÃO ATUAL):
   0   1   2   3   4   5   6   7   8   9   10  km
   |---|---|---|---|---|---|---|---|---|----| ...
   S1  S2  S3  S4  S5  S6  S7  S8  S9  S10

   ✓ Alta granularidade (450 segmentos para 450km)
   ✓ Detecção precisa de POIs
   ✓ Elimina necessidade de amostragem intermediária
   ✓ Coordenadas de início/fim de cada segmento usadas diretamente
   ✗ Mais segmentos na resposta

segment_length_km = 5.0:
   0    5   10   15   20   25   30  km
   |────|────|────|────|────|────|
   S1   S2   S3   S4   S5   S6   S7

   ✓ Menos segmentos (90 para 450km)
   ✓ Granularidade média
   ✗ Pode perder alguns POIs

segment_length_km = 10.0 (ANTIGO PADRÃO):
   0    10   20   30   40   50   60  km
   |─────|─────|─────|─────|─────|
   S1    S2    S3    S4    S5    S6

   ✓ Poucos segmentos (45 para 450km)
   ✓ Resposta mais compacta
   ✗ Menor granularidade
   ✗ Pode perder POIs entre segmentos
```

#### `max_distance_from_road` (Raio de Busca)

```
max_distance = 1000m (1km):
        [─ 1km ─]
   ●────────●────────  Rota
        🅿️           ⛽ (fora do raio)

   ✓ Apenas POIs muito próximos
   ✗ Pode perder opções úteis

max_distance = 3000m (3km, PADRÃO):
        [───── 3km ─────]
   ●────────────●────────────  Rota
        🅿️      ⛽     🍔

   ✓ Boa cobertura
   ✓ Não inclui POIs muito distantes
   ✓ Balanceado

max_distance = 5000m (5km):
        [─────────── 5km ───────────]
   ●────────────────●────────────────  Rota
        🅿️  ⛽  🍔  🏨  ⛽

   ✓ Máxima cobertura
   ✗ Pode incluir POIs impraticáveis
   ✗ Muitos resultados
```

#### Filtragem por Cidade de Origem

**Nota**: O parâmetro `min_distance_from_origin_km` foi descontinuado. O sistema agora usa **filtragem inteligente por cidade**.

```
Como funciona:

1. Extração do nome da cidade:
   Input: "São Paulo, SP"
   Cidade extraída: "São Paulo"

2. Filtragem de POIs:
   ✓ POIs em outras cidades são incluídos
   ✗ POIs na cidade de origem são excluídos

Exemplo: Rota "São Paulo, SP" → "Rio de Janeiro, RJ"

SP (cidade de origem) ●──────────────────────────────────● RJ (cidade de destino)
   |                                                        |
   | POIs em São Paulo: ❌ Excluídos                       |
   | POIs em Guarulhos: ✅ Incluídos                       |
   | POIs em Jacareí: ✅ Incluídos                         |
   | POIs em outras cidades: ✅ Incluídos                  |
   | POIs no Rio de Janeiro: ✅ Incluídos (destino)        |

Vantagens:
   ✓ Mais preciso que filtro por distância
   ✓ Exclui apenas POIs que o usuário já conhece (cidade de origem)
   ✓ Mantém POIs úteis em cidades próximas
   ✓ Normalização inteligente (ignora maiúsculas/espaços)
   ✓ Funciona com cidades de qualquer tamanho

Comparação com cidade:
   - "são paulo" == "São Paulo" ✅
   - "Belo Horizonte" == "belo horizonte" ✅
   - "Rio de Janeiro" == "rio de janeiro" ✅
```

---

## Exemplos Práticos

### Exemplo 1: São Paulo → Rio de Janeiro (450km)

```python
# REQUEST
linear_map = road_service.generate_linear_map(
    origin="São Paulo, SP",
    destination="Rio de Janeiro, RJ",
    include_gas_stations=True,
    include_food=True,
    include_toll_booths=True,
    segment_length_km=1.0  # Padrão: 1km
)

# RESULTADO
LinearMapResponse {
    origin: "São Paulo, SP",
    destination: "Rio de Janeiro, RJ",
    total_length_km: 450.0,
    segments: [
        LinearRoadSegment {
            id: "segment_1",
            name: "Via Dutra",
            start_distance_km: 0.0,
            end_distance_km: 1.0,
            milestones: []  # POIs filtrados (cidade de origem: São Paulo)
        },
        LinearRoadSegment {
            id: "segment_2",
            start_distance_km: 1.0,
            end_distance_km: 2.0,
            milestones: []  # Ainda em São Paulo
        },
        // ... segmentos 3-14 (ainda em São Paulo) ...
        LinearRoadSegment {
            id: "segment_15",
            start_distance_km: 14.0,
            end_distance_km: 15.0,
            milestones: []
        },
        LinearRoadSegment {
            id: "segment_16",
            start_distance_km: 15.0,
            end_distance_km: 16.0,
            milestones: [
                RoadMilestone {
                    name: "Posto Ipiranga",
                    type: GAS_STATION,
                    distance_from_origin_km: 15.3,
                    city: "Guarulhos",  # Primeira cidade fora de SP
                    amenities: ["24h", "banheiro", "loja"]
                }
            ]
        },
        // ... mais 434 segmentos (450 total) ...
    ],
    milestones: [  // Lista completa ordenada
        // ~150 milestones
    ]
}
```

### Visualização do Resultado

```
═══════════════════════════════════════════════════════════════════
                    SÃO PAULO → RIO DE JANEIRO
                         Via Dutra (BR-116)
                          Total: 450 km
═══════════════════════════════════════════════════════════════════

 KM  │ SEGMENTO │ MILESTONES
═════╪══════════╪═══════════════════════════════════════════════════
  0  │    S1    │ (POIs de São Paulo filtrados)
 10  │    S2    │ ⛽ Posto Ipiranga (15.3km)
 20  │    S3    │ 🍔 Restaurante Famiglia (23.7km)
     │          │ 🎫 Pedágio Jacareí (28.5km)
 30  │    S4    │ ⛽ Auto Posto São José (34.5km)
 40  │    S5    │ 🍔 Lanchonete KM 42 (42.1km)
 50  │    S6    │ ⛽ Posto Shell (55.8km)
 60  │    S7    │ (sem POIs)
 70  │    S8    │ 🏨 Hotel Fazenda (73.2km)
     │          │ ⛽ Posto BR (76.9km)
 80  │    S9    │ 🎫 Pedágio Roseira (85.4km)
     │          │ ⛽ Posto Petrobrás (88.1km)
 ...│   ...    │ ...
440  │   S44    │ ⛽ Posto Ipiranga (445.7km)
450  │   S45    │ 🏁 RIO DE JANEIRO
═══════════════════════════════════════════════════════════════════
```

### Exemplo 2: Rota Curta (50km)

```python
# REQUEST
linear_map = road_service.generate_linear_map(
    origin="Belo Horizonte, MG",
    destination="Ouro Preto, MG",
    segment_length_km=1.0,  # Padrão: 1km
    max_distance_from_road=2000,  # Raio menor
    include_gas_stations=True,
    include_food=False  # Não incluir comida
)

# RESULTADO
LinearMapResponse {
    total_length_km: 87.0,
    segments: [
        # 87 segmentos de 1km cada
        # Granularidade fina para rota curta
    ],
    milestones: [
        # ~30 milestones (apenas postos)
        # Mais POIs encontrados devido à granularidade de 1km
    ]
}
```

---

## Performance e Otimizações

### Tempo de Processamento

```
Rota São Paulo → Rio (450km):
┌─────────────────────────────────────┬──────────────┐
│ Etapa                               │ Tempo        │
├─────────────────────────────────────┼──────────────┤
│ 1. Geocodificação (2 requests)     │ ~1-2s        │
│ 2. Cálculo da rota (1 request)     │ ~2-3s        │
│ 3. Segmentação (local)             │ <0.1s        │
│ 4. Amostragem (local)              │ <0.1s        │
│ 5. Busca POIs (91 requests)        │ ~60-120s (*) │
│ 6. Criação milestones (local)      │ ~1s          │
│ 7. Atribuição (local)              │ <0.1s        │
├─────────────────────────────────────┼──────────────┤
│ TOTAL                               │ ~65-130s     │
└─────────────────────────────────────┴──────────────┘

(*) Depende do rate limit do provider e cache hits
```

### Uso de Cache

```
Primeiro acesso (cache vazio):
  ✗ Geocodificação: 2 requests à API
  ✗ Rota: 1 request à API
  ✗ POIs: 91 requests à API
  Tempo total: ~120s

Segundo acesso (cache completo):
  ✓ Geocodificação: cache hit
  ✓ Rota: cache hit
  ✓ POIs: 91 cache hits
  Tempo total: ~2s (99% mais rápido!)
```

### Otimizações Implementadas

1. **Cache Unificado**: Reutiliza dados entre providers
2. **Deduplicação de POIs**: Evita milestones duplicados
3. **Filtragem de Qualidade**: Reduz POIs irrelevantes
4. **Rate Limiting**: Respeita limites das APIs
5. **Processamento Assíncrono**: Busca POIs em paralelo (quando possível)
6. **Early Exit**: Para se muitos erros consecutivos

---

## Diagrama Completo do Sistema

```
┌─────────────────────────────────────────────────────────────────┐
│                         MAPALINEAR                              │
│                   Geração de Mapa Linear                        │
└─────────────────────────────────────────────────────────────────┘

┌─────────────┐
│   CLIENTE   │ (Frontend PWA / CLI / API)
└──────┬──────┘
       │ POST /api/linear-map
       │ { origin: "SP", destination: "RJ" }
       ▼
┌─────────────────────────────────────────────────────────────────┐
│                       API LAYER                                 │
│                    (FastAPI Router)                             │
└──────┬──────────────────────────────────────────────────────────┘
       │ road_service.generate_linear_map(origin, destination)
       ▼
┌─────────────────────────────────────────────────────────────────┐
│                    SERVICE LAYER                                │
│                    (RoadService)                                │
└──────┬──────────────────────────────────────────────────────────┘
       │
       ├─► [1] Geocodificação (geo_provider.geocode)
       │        └─► OSM/HERE Geocoding API
       │
       ├─► [2] Cálculo Rota (geo_provider.calculate_route)
       │        └─► OSRM/HERE Routing API
       │
       ├─► [3] Segmentação Linear (local)
       │        └─► Divide rota em segmentos de 1km
       │
       ├─► [4] Extração de Pontos de Busca (local)
       │        └─► Extrai coordenadas start/end dos segmentos (1 por km)
       │
       ├─► [5] Busca de POIs (geo_provider.search_pois × ~450)
       │        └─► OSM Overpass/HERE Places API
       │
       ├─► [6] Criação Milestones (local)
       │        └─► Converte POIs → Milestones
       │
       └─► [7] Atribuição Segmentos (local)
                └─► Distribui milestones pelos segmentos
       │
       ▼
┌─────────────────────────────────────────────────────────────────┐
│                    PROVIDER LAYER                               │
│            (GeoProvider: OSM / HERE / TomTom)                   │
└──────┬──────────────────────────────────────────────────────────┘
       │
       ├─► OSMProvider
       │    ├─► Nominatim (geocoding)
       │    ├─► OSRM (routing)
       │    └─► Overpass API (POI search)
       │
       └─► HEREProvider
            ├─► Geocoding API v7
            ├─► Routing API v8 (em desenvolvimento)
            └─► Places API (em desenvolvimento)
       │
       ▼
┌─────────────────────────────────────────────────────────────────┐
│                      CACHE LAYER                                │
│               (UnifiedCache - Redis/Memory)                     │
└─────────────────────────────────────────────────────────────────┘
       │
       ├─► Geocoding (TTL: 7 dias)
       ├─► Routes (TTL: 6 horas)
       └─► POIs (TTL: 1 dia)
```

---

## Glossário

| Termo | Definição |
|-------|-----------|
| **Linear Map** | Representação simplificada de uma rota em formato linear |
| **Segmento** | Trecho linear de 1km da rota (padrão) |
| **Milestone** | Ponto de interesse (POI) ao longo da rota |
| **POI** | Point of Interest - estabelecimento ou local relevante |
| **Geocodificação** | Conversão de endereço texto → coordenadas |
| **Geometria** | Sequência de coordenadas que define o caminho exato |
| **Interpolação** | Cálculo de coordenada intermediária entre dois pontos |
| **Amostragem** | Seleção de pontos equidistantes para busca de POIs |
| **Provider** | Fonte de dados geográficos (OSM, HERE, etc.) |
| **Quality Score** | Métrica de completude dos dados de um POI |
| **Entroncamento** | Ponto exato na rota principal onde sair para acessar POI afastado |
| **Junction** | Ver Entroncamento (termo técnico em inglês) |
| **Lookback** | Distância retroativa usada para calcular rota de acesso ao POI |

---

## Referências

- **Código fonte**: `api/services/road_service.py`
- **Modelos de dados**: `api/models/`
- **Providers**: `api/providers/`
- **Documentação OSM**: https://wiki.openstreetmap.org/
- **HERE Maps API**: https://developer.here.com/documentation

---

**Versão do documento**: 1.2
**Última atualização**: 2025-01-19
**Mudanças v1.2**: Adicionado cálculo de entroncamento para POIs afastados (>500m) usando estratégia de routing regional com lookback dinâmico
**Mudanças v1.1**: Substituído filtro de distância mínima por filtragem inteligente por cidade
**Autor**: Equipe MapaLinear

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
