# Processo de Geração do Mapa Linear - MapaLinear

**Versão**: 1.0
**Data**: 2025-01-13
**Autor**: Documentação Técnica MapaLinear

---

## 📋 Índice

1. [Visão Geral](#visão-geral)
2. [Fluxo Completo do Processo](#fluxo-completo-do-processo)
3. [Etapa 1: Geocodificação](#etapa-1-geocodificação)
4. [Etapa 2: Cálculo da Rota](#etapa-2-cálculo-da-rota)
5. [Etapa 3: Segmentação Linear](#etapa-3-segmentação-linear)
6. [Etapa 4: Amostragem de Pontos](#etapa-4-amostragem-de-pontos)
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

Saída:   [Mapa Linear com segmentos de 10km e POIs]

         0km    10km   20km   30km   40km   50km  ...  450km
         |------|------|------|------|------|-----|-----|
         SP    [⛽]  [🍔]  [⛽]  [⛽]      [🏨]     RJ
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
│ ETAPA 1: GEOCODIFICAÇÃO                                         │
│ Converter endereços textuais em coordenadas geográficas         │
└─────────────────────────────────────────────────────────────────┘
     │
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
│ Dividir rota em segmentos de tamanho fixo (padrão: 10km)        │
└─────────────────────────────────────────────────────────────────┘
     │
     │  segments = [
     │      Segment(0-10km),
     │      Segment(10-20km),
     │      ...
     │      Segment(440-450km)
     │  ]  # Total: 45 segmentos
     │
     ▼
┌─────────────────────────────────────────────────────────────────┐
│ ETAPA 4: AMOSTRAGEM DE PONTOS                                   │
│ Gerar pontos ao longo da rota para buscar POIs (intervalo: 5km) │
└─────────────────────────────────────────────────────────────────┘
     │
     │  sample_points = [
     │      (lat1, lon1, 0km),
     │      (lat2, lon2, 5km),
     │      (lat3, lon3, 10km),
     │      ...
     │  ]  # Total: ~90 pontos
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

## Etapa 1: Geocodificação

### Objetivo
Converter endereços em formato texto para coordenadas geográficas precisas.

### Processo

```python
# INPUT
origin = "São Paulo, SP"
destination = "Rio de Janeiro, RJ"

# PROCESSO
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
Calcular a melhor rota entre origem e destino, obtendo geometria detalhada e metadados.

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

## Etapa 4: Amostragem de Pontos

### Objetivo
Gerar pontos equidistantes ao longo da rota onde serão realizadas buscas de POIs.

### Processo

```python
def _sample_points_along_route(route, interval_km=5.0):
    """
    Gera pontos de amostragem a cada 5km ao longo da rota.
    """
    points = []
    current_distance = 0.0

    while current_distance <= route.distance_km:
        # Interpolar coordenada nesta distância
        coord = interpolate_at_distance(route.geometry, current_distance)
        points.append((coord, current_distance))
        current_distance += interval_km

    return points

# Exemplo de saída para rota de 450km:
sample_points = [
    ((lat=-23.5505, lon=-46.6333), 0.0),      # km 0
    ((lat=-23.5312, lon=-46.6145), 5.0),      # km 5
    ((lat=-23.5123, lon=-46.5987), 10.0),     # km 10
    ((lat=-23.4934, lon=-46.5829), 15.0),     # km 15
    # ... mais 86 pontos ...
    ((lat=-22.9068, lon=-43.1729), 450.0)     # km 450
]  # Total: 91 pontos
```

### Diagrama Visual

```
ROTA COMPLETA (450km):
════════════════════════════════════════════════════════════════
SP ●─────────────────────────────────────────────────────────● RJ
   0                      225km                            450km

                  ▼ AMOSTRAGEM (intervalo: 5km) ▼

PONTOS DE AMOSTRAGEM (91 pontos):
════════════════════════════════════════════════════════════════
SP ●────●────●────●────●────●────●────●────●────●────●────●─ RJ
   0    5   10   15   20   25   30   35   40   45   50   55km...

   P0   P1   P2   P3   P4   P5   P6   P7   P8   P9  P10  P11

Cada ponto será usado para buscar POIs em um raio de 3km:

        Raio de busca (3km)
              ╱───╲
   P1 ──────●───────────  (km 5)
            │ Buscar:    │
            │ - Postos   │
            │ - Comida   │
            │ - Hotéis   │
            │ - Pedágios │
             ╲───╱
```

### Por que 5km de intervalo?

**Vantagens**:
- ✅ **Cobertura completa**: Com raio de busca de 3km, garante overlap
- ✅ **Balanceamento**: Não sobrecarrega API (91 requisições vs 450 com 1km)
- ✅ **Precisão adequada**: Não perde POIs importantes
- ✅ **Performance**: Tempo de processamento aceitável (~3-5 minutos)

**Overlap dos raios de busca**:
```
         [─── 3km ───]
    P1 ──────●──────────────
                 [─── 3km ───]
            P2 ──────●──────────────
                         [─── 3km ───]
                    P3 ──────●──────────────

    Overlap: 1km entre buscas consecutivas
    Garante que nenhum POI seja perdido
```

---

## Etapa 5: Busca de POIs

### Objetivo
Para cada ponto de amostragem, buscar POIs relevantes em um raio configurável.

### Processo

```python
async def _find_milestones_along_route(route, categories, max_distance_from_road=3000):
    """
    Busca POIs ao longo da rota.

    Args:
        route: Rota calculada
        categories: [POICategory.GAS_STATION, POICategory.RESTAURANT, ...]
        max_distance_from_road: Raio de busca em metros (padrão: 3000m = 3km)
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

RESTAURANT             →  FOOD (alimentação)
FOOD                   →  FOOD
CAFE                   →  FOOD
FAST_FOOD              →  FOOD

HOTEL                  →  LODGING (hospedagem)
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
    include_food: bool = False,                     # Incluir comida
    include_toll_booths: bool = True,               # Incluir pedágios
    max_distance_from_road: float = 3000,           # Raio busca (metros)
    min_distance_from_origin_km: float = 5.0,       # Ignorar início
    segment_length_km: float = 10.0,                # Tamanho segmento
    progress_callback: Optional[Callable] = None    # Callback progresso
) -> LinearMapResponse:
```

### Impacto dos Parâmetros

#### `segment_length_km` (Tamanho do Segmento)

```
segment_length_km = 5.0:
   0    5   10   15   20   25   30  km
   |────|────|────|────|────|────|
   S1   S2   S3   S4   S5   S6   S7

   ✓ Mais segmentos (90 para 450km)
   ✓ Mais granular
   ✗ Mais dados para processar
   ✗ UI pode ficar carregada

segment_length_km = 10.0 (PADRÃO):
   0    10   20   30   40   50   60  km
   |─────|─────|─────|─────|─────|
   S1    S2    S3    S4    S5    S6

   ✓ Balanceado (45 segmentos)
   ✓ Boa granularidade
   ✓ Performance adequada

segment_length_km = 20.0:
   0     20    40    60    80   100  km
   |──────|──────|──────|──────|
   S1     S2     S3     S4     S5

   ✓ Menos segmentos (23 para 450km)
   ✓ Mais rápido
   ✗ Menos granular
   ✗ Pode perder detalhes
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

#### `min_distance_from_origin_km` (Ignorar Início)

```
Sem filtro (min_distance = 0):
SP ●⛽🍔⛽🍔⛽────────────────────────────● RJ
   0  2 4 6 8        ...              450km

   ✗ Muitos POIs no início (redundante)
   ✗ Usuário já conhece a região

Com filtro (min_distance = 5km, PADRÃO):
SP ●──────────⛽────🍔────⛽────────────● RJ
   0    5    10   15   20   25  ...  450km

   ✓ Ignora região conhecida
   ✓ Foca na viagem real
   ✓ Menos processamento
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
    segment_length_km=10.0
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
            end_distance_km: 10.0,
            milestones: []  # Ignorados (min_distance=5km)
        },
        LinearRoadSegment {
            id: "segment_2",
            start_distance_km: 10.0,
            end_distance_km: 20.0,
            milestones: [
                RoadMilestone {
                    name: "Posto Ipiranga",
                    type: FUEL,
                    distance_from_origin_km: 15.3,
                    amenities: ["24h", "banheiro", "loja"]
                }
            ]
        },
        LinearRoadSegment {
            id: "segment_3",
            start_distance_km: 20.0,
            end_distance_km: 30.0,
            milestones: [
                RoadMilestone {
                    name: "Restaurante Famiglia",
                    type: FOOD,
                    distance_from_origin_km: 23.7,
                    amenities: ["wifi", "estacionamento"]
                },
                RoadMilestone {
                    name: "Pedágio Jacareí",
                    type: TOLL,
                    distance_from_origin_km: 28.5
                }
            ]
        },
        // ... mais 42 segmentos
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
  0  │    S1    │ (início ignorado)
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
    segment_length_km=5.0,  # Segmentos menores
    max_distance_from_road=2000,  # Raio menor
    include_gas_stations=True,
    include_food=False  # Não incluir comida
)

# RESULTADO
LinearMapResponse {
    total_length_km: 87.0,
    segments: [
        # 18 segmentos de 5km cada
        # (87km / 5km = ~18 segmentos)
    ],
    milestones: [
        # ~25 milestones (apenas postos)
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
       │        └─► Divide rota em segmentos de 10km
       │
       ├─► [4] Amostragem de Pontos (local)
       │        └─► Gera pontos a cada 5km
       │
       ├─► [5] Busca de POIs (geo_provider.search_pois × 91)
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
| **Segmento** | Trecho linear de 10km da rota |
| **Milestone** | Ponto de interesse (POI) ao longo da rota |
| **POI** | Point of Interest - estabelecimento ou local relevante |
| **Geocodificação** | Conversão de endereço texto → coordenadas |
| **Geometria** | Sequência de coordenadas que define o caminho exato |
| **Interpolação** | Cálculo de coordenada intermediária entre dois pontos |
| **Amostragem** | Seleção de pontos equidistantes para busca de POIs |
| **Provider** | Fonte de dados geográficos (OSM, HERE, etc.) |
| **Quality Score** | Métrica de completude dos dados de um POI |

---

## Referências

- **Código fonte**: `api/services/road_service.py`
- **Modelos de dados**: `api/models/`
- **Providers**: `api/providers/`
- **Documentação OSM**: https://wiki.openstreetmap.org/
- **HERE Maps API**: https://developer.here.com/documentation

---

**Versão do documento**: 1.0
**Última atualização**: 2025-01-13
**Autor**: Equipe MapaLinear

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
