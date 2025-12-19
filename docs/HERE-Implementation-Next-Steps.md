# HERE Maps Provider - Próximos Passos para Implementação Completa

**Status**: Quase Completo
**Data**: 2025-12-18
**Fase Atual**: Fase Final
**Completude**: ~90% (4 de 5 funcionalidades)

---

## 1. Estado Atual

### ✅ Implementado e Funcional

- **Geocoding** (`geocode`)
  - Localização: `api/providers/here/provider.py:106-234`
  - Endpoint: HERE Geocoding API v7
  - Cache: Implementado
  - Testes: 17 testes passando
  - Status: ✅ Produção

- **Reverse Geocoding** (`reverse_geocode`)
  - Localização: `api/providers/here/provider.py:236-377`
  - Endpoint: HERE Reverse Geocoding API v7
  - Cache: Implementado
  - Status: ✅ Produção

- **POI Search** (`search_pois`)
  - Localização: `api/providers/here/provider.py:401-555`
  - Endpoint: HERE Browse API v1
  - Cache: Implementado
  - API Call Logging: Implementado
  - Testes: 5 testes específicos + testes de parsing
  - Status: ✅ Produção

- **POI Details** (`get_poi_details`)
  - Localização: `api/providers/here/provider.py:557-671`
  - Endpoint: HERE Lookup API v1
  - Cache: Implementado
  - API Call Logging: Implementado
  - Status: ✅ Produção

- **Category Mapping**
  - `CATEGORY_TO_HERE`: Mapeamento de 14 categorias MapaLinear → HERE
  - `HERE_PREFIX_TO_CATEGORY`: Mapeamento reverso de 13 prefixos HERE → MapaLinear
  - `_map_categories_to_here()`: Helper para conversão
  - `_map_here_category_to_mapalinear()`: Helper para conversão reversa
  - Testes: 4 testes específicos
  - Status: ✅ Produção

- **POI Parsing** (`_parse_here_place_to_poi`)
  - Extração de: posição, endereço, contatos, horários, categorias, referências externas
  - Testes: 3 testes específicos
  - Status: ✅ Produção

- **Infraestrutura**
  - Sistema multi-provider: ✅
  - Cache unificado (PostgreSQL): ✅
  - Configuração (settings): ✅
  - Rate limiting: ✅
  - HTTP client (httpx): ✅
  - API Call Logging: ✅

### ⚠️ Pendente de Implementação

- **Route Calculation** (`calculate_route`) - NotImplementedError

---

## 2. ✅ Funcionalidade 1: POI Search (COMPLETO)

> **Status**: ✅ Implementado e testado em produção
> **Data de conclusão**: 2025-12-18

### Implementação

- **Arquivo**: `api/providers/here/provider.py`
- **Método**: `search_pois` (linhas 401-555)
- **Endpoint**: `https://browse.search.hereapi.com/v1/browse`

### Recursos Implementados

- ✅ Mapeamento de 14 categorias MapaLinear → HERE (`CATEGORY_TO_HERE`)
- ✅ Mapeamento reverso de 13 prefixos HERE → MapaLinear (`HERE_PREFIX_TO_CATEGORY`)
- ✅ Cache com PostgreSQL
- ✅ API Call Logging para monitoramento de custos
- ✅ Tratamento de erros robusto
- ✅ Rate limiting

### Testes Implementados

```
tests/providers/test_here_provider.py:
├── TestHEREProviderPOISearch (5 testes)
│   ├── test_search_pois_basic
│   ├── test_search_pois_respects_limit
│   ├── test_search_pois_caches_results
│   ├── test_search_pois_handles_api_error
│   └── test_search_pois_empty_categories
├── TestHEREProviderCategoryMapping (4 testes)
│   ├── test_map_gas_station_category
│   ├── test_map_restaurant_category
│   ├── test_map_hotel_category
│   └── test_map_multiple_categories
└── TestHEREProviderPOIParsing (3 testes)
    ├── test_parse_poi_with_full_data
    ├── test_parse_poi_with_minimal_data
    └── test_parse_poi_stores_here_id
```

### Critérios de Aceitação

- [x] Busca retorna POIs corretos para cada categoria
- [x] Cache funciona corretamente
- [x] Mapeamento de categorias completo
- [x] Parser extrai todos os campos relevantes
- [x] Testes unitários passam (17 testes)
- [x] Documentação atualizada

---

## 3. Funcionalidade 2: Route Calculation

### 3.1. Objetivo

Implementar cálculo de rotas usando HERE Routing API v8.

### 3.2. Localização

- **Arquivo**: `api/providers/here/provider.py`
- **Método**: `calculate_route` (linhas 200-220)
- **Assinatura**:
```python
async def calculate_route(
    self,
    origin: GeoLocation,
    destination: GeoLocation,
    waypoints: Optional[List[GeoLocation]] = None,
    avoid: Optional[List[str]] = None
) -> Optional[Route]
```

### 3.3. Documentação da API HERE

- **Endpoint**: `https://router.hereapi.com/v8/routes`
- **Documentação**: https://developer.here.com/documentation/routing-api/dev_guide/index.html
- **Parâmetros principais**:
  - `origin`: Coordenadas de origem (lat,lng)
  - `destination`: Coordenadas de destino (lat,lng)
  - `via`: Waypoints intermediários
  - `transportMode`: car, truck, pedestrian, bicycle
  - `return`: polyline, summary, actions, elevation

### 3.4. Passos de Implementação

#### Passo 1: Implementar cálculo de rota

```python
async def calculate_route(
    self,
    origin: GeoLocation,
    destination: GeoLocation,
    waypoints: Optional[List[GeoLocation]] = None,
    avoid: Optional[List[str]] = None
) -> Optional[Route]:
    """Calculate route using HERE Routing API v8."""

    # 1. Check cache
    if self._cache:
        cache_key = {
            "origin": f"{origin.latitude},{origin.longitude}",
            "destination": f"{destination.latitude},{destination.longitude}",
            "waypoints": [f"{w.latitude},{w.longitude}" for w in (waypoints or [])],
            "avoid": avoid or []
        }
        cached_result = await self._cache.get(
            provider=self.provider_type,
            operation="route",
            params=cache_key
        )
        if cached_result is not None:
            return cached_result

    # 2. Prepare request
    params = {
        "origin": f"{origin.latitude},{origin.longitude}",
        "destination": f"{destination.latitude},{destination.longitude}",
        "transportMode": "car",
        "return": "polyline,summary,actions,elevation",
        "apiKey": self._api_key,
        "lang": "pt-BR"
    }

    # Add waypoints if provided
    if waypoints:
        for i, wp in enumerate(waypoints):
            params[f"via"] = f"{wp.latitude},{wp.longitude}"

    # Add avoidance features if provided
    if avoid:
        params["avoid[features]"] = ",".join(avoid)

    # 3. Make request
    try:
        response = await self._client.get(
            "https://router.hereapi.com/v8/routes",
            params=params
        )
        response.raise_for_status()
        data = response.json()

        # 4. Parse route
        if not data.get("routes"):
            logger.warning("No routes found")
            return None

        route = self._parse_here_route(data["routes"][0], origin, destination)

        # 5. Cache result
        if self._cache and route:
            await self._cache.set(
                provider=self.provider_type,
                operation="route",
                params=cache_key,
                data=route
            )

        return route

    except httpx.HTTPError as e:
        logger.error(f"HERE Routing API error: {e}")
        return None
    except Exception as e:
        logger.error(f"Error calculating route: {e}")
        return None
```

#### Passo 2: Implementar parser de rota

```python
def _parse_here_route(
    self,
    route_data: dict,
    origin: GeoLocation,
    destination: GeoLocation
) -> Route:
    """
    Parse HERE route response to Route model.

    Args:
        route_data: HERE API route object
        origin: Origin location
        destination: Destination location

    Returns:
        Route object
    """
    try:
        sections = route_data.get("sections", [])

        # Extract main section (first section for now)
        main_section = sections[0] if sections else {}

        # Extract summary
        summary = main_section.get("summary", {})
        distance_m = summary.get("length", 0)
        duration_s = summary.get("duration", 0)

        # Decode polyline
        polyline_data = main_section.get("polyline", "")
        geometry_points = self._decode_here_polyline(polyline_data)

        # Create segments from actions
        segments = []
        actions = main_section.get("actions", [])

        for i, action in enumerate(actions):
            if action.get("action") == "arrive":
                continue  # Skip arrival action

            instruction = action.get("instruction", "")
            offset = action.get("offset", 0)

            # Extract segment geometry from polyline
            next_offset = actions[i + 1].get("offset") if i + 1 < len(actions) else len(geometry_points)
            segment_geometry = geometry_points[offset:next_offset]

            if len(segment_geometry) >= 2:
                segment = RouteSegment(
                    name=instruction,
                    distance_km=action.get("length", 0) / 1000,
                    duration_seconds=action.get("duration", 0),
                    geometry=segment_geometry,
                    road_type=None,  # HERE doesn't provide this directly
                    max_speed=None,
                    instructions=instruction
                )
                segments.append(segment)

        return Route(
            origin=origin,
            destination=destination,
            distance_km=distance_m / 1000,
            duration_seconds=duration_s,
            geometry=geometry_points,
            segments=segments if segments else None,
            provider_data={
                "here_route_id": route_data.get("id"),
                "sections_count": len(sections),
            }
        )

    except Exception as e:
        logger.error(f"Error parsing HERE route: {e}")
        raise

def _decode_here_polyline(self, encoded: str) -> List[List[float]]:
    """
    Decode HERE flexible polyline encoding.

    HERE uses a custom encoding format. This is a simplified version.
    For production, use: https://github.com/heremaps/flexible-polyline

    Args:
        encoded: Encoded polyline string

    Returns:
        List of [longitude, latitude] pairs
    """
    try:
        # Use HERE's flexible-polyline library
        from flexpolyline import decode

        # decode returns list of (lat, lng, elevation) tuples
        decoded = decode(encoded)

        # Convert to [lng, lat] format for GeoJSON compatibility
        return [[point[1], point[0]] for point in decoded]

    except ImportError:
        logger.error("flexpolyline library not installed. Install with: pip install flexpolyline")
        return []
    except Exception as e:
        logger.error(f"Error decoding HERE polyline: {e}")
        return []
```

#### Passo 3: Adicionar dependência

Adicionar ao `pyproject.toml`:

```toml
[tool.poetry.dependencies]
flexpolyline = "^0.3.0"
```

Executar:
```bash
poetry add flexpolyline
```

### 3.5. Testes Necessários

```python
@pytest.mark.asyncio
async def test_calculate_route_basic():
    """Test basic route calculation with HERE provider."""
    provider = HEREProvider(api_key="test_key")

    origin = GeoLocation(latitude=-23.5505, longitude=-46.6333)
    destination = GeoLocation(latitude=-23.5489, longitude=-46.6388)

    mock_response = {
        "routes": [{
            "id": "route-123",
            "sections": [{
                "summary": {
                    "length": 1500,  # meters
                    "duration": 300   # seconds
                },
                "polyline": "BG05xgKnpxK...",  # Encoded polyline
                "actions": [
                    {
                        "action": "depart",
                        "instruction": "Siga na Av. Paulista",
                        "length": 1000,
                        "duration": 200,
                        "offset": 0
                    },
                    {
                        "action": "arrive",
                        "instruction": "Chegue ao destino",
                        "offset": 10
                    }
                ]
            }]
        }]
    }

    with patch.object(provider._client, 'get') as mock_get:
        mock_get.return_value.json.return_value = mock_response
        mock_get.return_value.raise_for_status = lambda: None

        with patch.object(provider, '_decode_here_polyline') as mock_decode:
            mock_decode.return_value = [
                [-46.6333, -23.5505],
                [-46.6388, -23.5489]
            ]

            route = await provider.calculate_route(origin, destination)

            assert route is not None
            assert route.distance_km == 1.5
            assert route.duration_seconds == 300
            assert len(route.geometry) == 2
            assert len(route.segments) == 1
```

### 3.6. Critérios de Aceitação

- [ ] Rota calculada corretamente entre dois pontos
- [ ] Waypoints intermediários funcionam
- [ ] Geometria decodificada corretamente
- [ ] Segmentos criados com instruções
- [ ] Cache funciona
- [ ] Testes unitários passam
- [ ] Testes de integração com API real passam

---

## 4. ✅ Funcionalidade 3: POI Details (COMPLETO)

> **Status**: ✅ Implementado e testado em produção
> **Data de conclusão**: 2025-12-18

### Implementação

- **Arquivo**: `api/providers/here/provider.py`
- **Método**: `get_poi_details` (linhas 557-671)
- **Endpoint**: `https://lookup.search.hereapi.com/v1/lookup`

### Recursos Implementados

- ✅ Cache com PostgreSQL
- ✅ API Call Logging para monitoramento de custos
- ✅ Tratamento de erros robusto
- ✅ Reutiliza `_parse_here_place_to_poi()` para parsing

### Critérios de Aceitação

- [x] Detalhes do POI recuperados corretamente
- [x] Cache funciona
- [x] Tratamento de erros adequado
- [x] API Call Logging implementado

---

## 5. ✅ Testes (COMPLETO)

### Status Atual dos Testes

```bash
# Executar todos os testes
poetry run python -m pytest tests/ -v

# Resultado: 204 passed ✅
```

### Testes HERE Provider Implementados

Arquivo: `tests/providers/test_here_provider.py`

```
TestHEREProviderBasics (3 testes)
├── test_provider_type_identification
├── test_offline_export_support
└── test_rate_limiting_configuration

TestHEREProviderPOISearch (5 testes)
├── test_search_pois_basic
├── test_search_pois_respects_limit
├── test_search_pois_caches_results
├── test_search_pois_handles_api_error
└── test_search_pois_empty_categories

TestHEREProviderCategoryMapping (4 testes)
├── test_map_gas_station_category
├── test_map_restaurant_category
├── test_map_hotel_category
└── test_map_multiple_categories

TestHEREProviderPOIParsing (3 testes)
├── test_parse_poi_with_full_data
├── test_parse_poi_with_minimal_data
└── test_parse_poi_stores_here_id

TestHEREProviderInitialization (2 testes)
├── test_api_key_handling_without_key
└── test_uses_api_key_from_settings
```

### Testes Pendentes (para Route Calculation)

Quando `calculate_route()` for implementado, adicionar:

```python
@pytest.mark.asyncio
async def test_calculate_route_basic(self, here_provider):
    """Test basic route calculation."""
    # TODO: Implementar quando calculate_route() estiver pronto

@pytest.mark.asyncio
async def test_calculate_route_with_waypoints(self, here_provider):
    """Test route with waypoints."""
    # TODO: Implementar quando calculate_route() estiver pronto
```

---

## 6. Checklist Completo de Implementação

### ✅ Fase 1: POI Search (COMPLETO)
- [x] Criar mapeamento de categorias HERE ↔ MapaLinear
- [x] Implementar `_map_categories_to_here()`
- [x] Implementar `_map_here_category_to_mapalinear()`
- [x] Implementar `search_pois()` com cache
- [x] Implementar `_parse_here_place_to_poi()`
- [x] Criar testes unitários com mocks
- [x] Atualizar documentação

### ⚠️ Fase 2: Route Calculation (PENDENTE)
- [ ] Adicionar dependência `flexpolyline`
- [ ] Implementar `calculate_route()` com cache
- [ ] Implementar `_parse_here_route()`
- [ ] Implementar `_decode_here_polyline()`
- [ ] Criar testes unitários com mocks
- [ ] Testar manualmente com API real
- [ ] Validar geometria e segmentos
- [ ] Atualizar documentação

### ✅ Fase 3: POI Details (COMPLETO)
- [x] Implementar `get_poi_details()` com cache
- [x] API Call Logging implementado
- [x] Atualizar documentação

### ✅ Fase 4: Testes (COMPLETO)
- [x] Suite de testes unitários criada (17 testes HERE)
- [x] 204 testes passando no total
- [x] Cobertura adequada

### ✅ Fase 5: Testes OSM (COMPLETO)
- [x] Todos os testes OSM passando
- [x] 100% dos testes passando

### ✅ Fase 6: Documentação (EM ANDAMENTO)
- [x] CLAUDE.md atualizado
- [x] Este documento atualizado
- [ ] Atualizar PRD com status final quando Route Calculation estiver completo

---

## 7. Estimativa de Esforço

| Tarefa | Estimativa | Status |
|--------|-----------|--------|
| POI Search | 1-2 dias | ✅ COMPLETO |
| POI Details | 0.5 dia | ✅ COMPLETO |
| Testes | 1 dia | ✅ COMPLETO |
| **Route Calculation** | **2-3 dias** | ⚠️ PENDENTE |
| Documentação Final | 0.5 dia | ⏳ EM ANDAMENTO |
| **Total Restante** | **~3 dias** | - |

---

## 8. Recursos e Referências

### Documentação HERE Maps
- [HERE Developer Portal](https://developer.here.com/)
- [Routing API v8](https://developer.here.com/documentation/routing-api/dev_guide/index.html)
- [Places API](https://developer.here.com/documentation/places/dev_guide/topics/search.html)
- [Geocoding API](https://developer.here.com/documentation/geocoding-search-api/dev_guide/index.html)
- [Category System](https://developer.here.com/documentation/geocoding-search-api/dev_guide/topics-places/places-category-system-full.html)

### Bibliotecas
- [flexpolyline](https://github.com/heremaps/flexible-polyline) - Polyline encoding/decoding
- [httpx](https://www.python-httpx.org/) - HTTP client (já instalado)
- [pytest-asyncio](https://pytest-asyncio.readthedocs.io/) - Async tests (já instalado)

### Código de Referência
- `api/providers/osm/provider.py` - Implementação OSM como referência
- `api/providers/base.py` - Interface GeoProvider
- `api/providers/models.py` - Modelos unificados

---

## 9. Riscos e Mitigações

### Riscos Mitigados ✅
| Risco | Status | Mitigação Aplicada |
|-------|--------|-------------------|
| Rate limiting da API HERE | ✅ Mitigado | Cache PostgreSQL + rate limiter implementados |
| Mapeamento de categorias incompleto | ✅ Mitigado | 14 categorias mapeadas + fallback para OTHER |
| Testes de integração falham | ✅ Mitigado | 204 testes passando com mocks |

### Riscos Pendentes (Route Calculation)
| Risco | Probabilidade | Impacto | Mitigação |
|-------|--------------|---------|-----------|
| Decodificação de polyline falha | Baixa | Alto | Usar biblioteca oficial flexpolyline |
| Custo de API inesperado | Baixa | Alto | API Call Logging já implementado para monitoramento |

---

## 10. Próximas Ações Imediatas

A única funcionalidade pendente é **Route Calculation**:

1. **Instalar dependências**: `poetry add flexpolyline`
2. **Implementar `calculate_route()`** com cache e API Call Logging
3. **Implementar `_parse_here_route()`** para parsear resposta da API
4. **Implementar `_decode_here_polyline()`** usando biblioteca flexpolyline
5. **Criar testes unitários** com mocks
6. **Testar manualmente** com API real
7. **Atualizar documentação** e marcar como completo

---

**Documento criado por**: Claude Code
**Data**: 2025-01-13
**Última atualização**: 2025-12-18
**Versão**: 2.0
**Status**: Em Progresso (90% completo - apenas Route Calculation pendente)
