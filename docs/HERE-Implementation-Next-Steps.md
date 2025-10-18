# HERE Maps Provider - Próximos Passos para Implementação Completa

**Status**: Em Progresso
**Data**: 2025-01-13
**Fase Atual**: Fase 3 (Semanas 5-6)
**Completude**: ~40% (2 de 5 funcionalidades)

---

## 1. Estado Atual

### ✅ Implementado e Funcional

- **Geocoding** (`geocode`)
  - Localização: `api/providers/here/provider.py:61-129`
  - Endpoint: HERE Geocoding API v7
  - Cache: Implementado
  - Testes: Validado manualmente
  - Status: ✅ Produção

- **Reverse Geocoding** (`reverse_geocode`)
  - Localização: `api/providers/here/provider.py:131-198`
  - Endpoint: HERE Reverse Geocoding API v7
  - Cache: Implementado
  - Status: ✅ Produção

- **Infraestrutura**
  - Sistema multi-provider: ✅
  - Cache unificado: ✅
  - Configuração (settings): ✅
  - Rate limiting: ✅
  - HTTP client (httpx): ✅

### ⚠️ Pendente de Implementação

- **POI Search** (`search_pois`) - NotImplementedError
- **Route Calculation** (`calculate_route`) - NotImplementedError
- **POI Details** (`get_poi_details`) - Stub (retorna None)

---

## 2. Funcionalidade 1: POI Search

### 2.1. Objetivo

Implementar busca de Points of Interest (POIs) usando HERE Places API.

### 2.2. Localização

- **Arquivo**: `api/providers/here/provider.py`
- **Método**: `search_pois` (linhas 222-242)
- **Assinatura**:
```python
async def search_pois(
    self,
    location: GeoLocation,
    radius: float,
    categories: List[POICategory],
    limit: int = 50
) -> List[POI]
```

### 2.3. Documentação da API HERE

- **Endpoint**: `https://browse.search.hereapi.com/v1/browse`
- **Documentação**: https://developer.here.com/documentation/places/dev_guide/topics/search.html
- **Parâmetros principais**:
  - `at`: Coordenadas (lat,lng)
  - `limit`: Máximo de resultados
  - `categories`: IDs de categorias HERE
  - `in`: Busca em círculo (formato: `circle:lat,lng;r=radius`)

### 2.4. Mapeamento de Categorias

O MapaLinear usa categorias genéricas (`POICategory` enum), que precisam ser mapeadas para IDs HERE:

```python
# Mapeamento proposto (expandir conforme necessário)
CATEGORY_MAPPING = {
    POICategory.GAS_STATION: "700-7600-0116",  # Petrol/Gasoline Station
    POICategory.RESTAURANT: "100-1000",         # Restaurant
    POICategory.HOTEL: "500-5000",              # Hotel/Motel
    POICategory.HOSPITAL: "800-8000",           # Hospital/Healthcare
    POICategory.PHARMACY: "900-9100-0102",      # Pharmacy
    POICategory.ATM: "900-9400-0000",           # ATM/Banking
    POICategory.POLICE: "900-9300-0100",        # Police Station
    POICategory.MECHANIC: "700-7850",           # Vehicle Repair
    POICategory.REST_AREA: "700-7600-0000",     # Parking/Rest Area
    POICategory.SUPERMARKET: "600-6300",        # Grocery Store
    POICategory.SHOPPING: "600-6000",           # Shopping
    POICategory.TOURISM: "200-2000",            # Sightseeing/Tourist Attraction
}
```

**Referência completa**: https://developer.here.com/documentation/geocoding-search-api/dev_guide/topics-places/places-category-system-full.html

### 2.5. Passos de Implementação

#### Passo 1: Criar mapeamento de categorias

```python
# No início da classe HEREProvider, adicionar:
_CATEGORY_MAPPING = {
    POICategory.GAS_STATION: "700-7600-0116",
    POICategory.RESTAURANT: "100-1000",
    # ... adicionar todas as categorias do enum POICategory
}
```

#### Passo 2: Implementar método helper para mapear categorias

```python
def _map_categories_to_here(self, categories: List[POICategory]) -> str:
    """
    Map MapaLinear POI categories to HERE category IDs.

    Returns:
        Comma-separated string of HERE category IDs
    """
    here_ids = []
    for cat in categories:
        if cat in self._CATEGORY_MAPPING:
            here_ids.append(self._CATEGORY_MAPPING[cat])
        else:
            logger.warning(f"No HERE mapping for category: {cat}")

    return ",".join(here_ids) if here_ids else ""
```

#### Passo 3: Implementar busca na API

```python
async def search_pois(
    self,
    location: GeoLocation,
    radius: float,
    categories: List[POICategory],
    limit: int = 50
) -> List[POI]:
    """Search POIs using HERE Places API."""

    # 1. Check cache
    if self._cache:
        cache_key = {
            "location": f"{location.latitude},{location.longitude}",
            "radius": radius,
            "categories": [c.value for c in categories],
            "limit": limit
        }
        cached_result = await self._cache.get(
            provider=self.provider_type,
            operation="poi_search",
            params=cache_key
        )
        if cached_result is not None:
            return cached_result

    # 2. Map categories
    here_categories = self._map_categories_to_here(categories)
    if not here_categories:
        logger.warning("No valid HERE categories found")
        return []

    # 3. Prepare request
    params = {
        "at": f"{location.latitude},{location.longitude}",
        "categories": here_categories,
        "limit": min(limit, 100),  # HERE max is 100
        "apiKey": self._api_key,
        "lang": "pt-BR"
    }

    # 4. Make request
    try:
        response = await self._client.get(
            "https://browse.search.hereapi.com/v1/browse",
            params=params
        )
        response.raise_for_status()
        data = response.json()

        # 5. Parse results
        pois = []
        for item in data.get("items", []):
            poi = self._parse_here_place_to_poi(item, location)
            if poi:
                pois.append(poi)

        # 6. Cache results
        if self._cache:
            await self._cache.set(
                provider=self.provider_type,
                operation="poi_search",
                params=cache_key,
                data=pois
            )

        logger.debug(f"Found {len(pois)} POIs near {location.latitude},{location.longitude}")
        return pois

    except httpx.HTTPError as e:
        logger.error(f"HERE Places API error: {e}")
        return []
    except Exception as e:
        logger.error(f"Error searching POIs: {e}")
        return []
```

#### Passo 4: Implementar parser de resultados

```python
def _parse_here_place_to_poi(self, place: dict, reference_location: GeoLocation) -> Optional[POI]:
    """
    Parse HERE Place item to POI model.

    Args:
        place: HERE API place item
        reference_location: Reference point for distance calculation

    Returns:
        POI object or None if parsing fails
    """
    try:
        position = place.get("position", {})
        address = place.get("address", {})
        contacts = place.get("contacts", [])
        opening_hours = place.get("openingHours", [])
        categories = place.get("categories", [])

        # Extract category
        poi_category = POICategory.OTHER
        if categories:
            # Map back from HERE category to our enum
            category_id = categories[0].get("id", "")
            poi_category = self._map_here_category_to_mapalinear(category_id)

        # Extract phone
        phone = None
        if contacts:
            phone_contacts = [c for c in contacts if c.get("phone")]
            if phone_contacts:
                phone = phone_contacts[0]["phone"][0].get("value")

        # Extract website
        website = None
        if contacts:
            www_contacts = [c for c in contacts if c.get("www")]
            if www_contacts:
                website = www_contacts[0]["www"][0].get("value")

        # Build opening hours dict
        hours_dict = None
        if opening_hours:
            hours_dict = {}
            for oh in opening_hours:
                if oh.get("text"):
                    hours_dict["general"] = oh["text"]

        # Determine if open
        is_open = None
        if opening_hours:
            for oh in opening_hours:
                if "isOpen" in oh:
                    is_open = oh["isOpen"]
                    break

        return POI(
            id=f"here/{place.get('id', '')}",
            name=place.get("title", "Unknown"),
            location=GeoLocation(
                latitude=position.get("lat"),
                longitude=position.get("lng"),
                address=address.get("label"),
                city=address.get("city"),
                state=address.get("state"),
                country=address.get("countryName", "Brasil"),
                postal_code=address.get("postalCode")
            ),
            category=poi_category,
            subcategory=categories[0].get("name") if categories else None,
            description=place.get("description"),
            amenities=[],  # HERE doesn't provide detailed amenities
            services=[],
            rating=None,  # Would need separate API call
            review_count=None,
            is_open=is_open,
            phone=phone,
            website=website,
            opening_hours=hours_dict,
            provider_data={
                "here_id": place.get("id"),
                "here_categories": categories,
                "distance": place.get("distance"),
            }
        )

    except Exception as e:
        logger.error(f"Error parsing HERE place: {e}")
        return None

def _map_here_category_to_mapalinear(self, here_category_id: str) -> POICategory:
    """Map HERE category ID back to MapaLinear POICategory."""
    # Reverse mapping
    for mapalinear_cat, here_id in self._CATEGORY_MAPPING.items():
        if here_category_id.startswith(here_id.split("-")[0]):
            return mapalinear_cat
    return POICategory.OTHER
```

### 2.6. Testes Necessários

Criar arquivo `tests/providers/test_here_provider.py`:

```python
import pytest
from unittest.mock import AsyncMock, patch
from api.providers.here.provider import HEREProvider
from api.providers.models import GeoLocation, POICategory

@pytest.mark.asyncio
async def test_search_pois_basic():
    """Test basic POI search with HERE provider."""
    provider = HEREProvider(api_key="test_key")
    location = GeoLocation(latitude=-23.5505, longitude=-46.6333)

    mock_response = {
        "items": [
            {
                "id": "here:pds:place:123",
                "title": "Posto Shell",
                "position": {"lat": -23.5505, "lng": -46.6333},
                "address": {"label": "Av. Paulista, 1000"},
                "categories": [{"id": "700-7600-0116", "name": "Gas Station"}],
                "distance": 100
            }
        ]
    }

    with patch.object(provider._client, 'get') as mock_get:
        mock_get.return_value.json.return_value = mock_response
        mock_get.return_value.raise_for_status = lambda: None

        results = await provider.search_pois(
            location,
            radius=1000,
            categories=[POICategory.GAS_STATION],
            limit=10
        )

        assert len(results) == 1
        assert results[0].name == "Posto Shell"
        assert results[0].category == POICategory.GAS_STATION
```

### 2.7. Critérios de Aceitação

- [ ] Busca retorna POIs corretos para cada categoria
- [ ] Cache funciona corretamente
- [ ] Mapeamento de categorias completo
- [ ] Parser extrai todos os campos relevantes
- [ ] Testes unitários passam
- [ ] Testes de integração com API real passam
- [ ] Documentação atualizada

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

## 4. Funcionalidade 3: POI Details

### 4.1. Objetivo

Obter detalhes completos de um POI específico.

### 4.2. Localização

- **Arquivo**: `api/providers/here/provider.py`
- **Método**: `get_poi_details` (linhas 244-247)
- **Assinatura**:
```python
async def get_poi_details(self, poi_id: str) -> Optional[POI]
```

### 4.3. Documentação da API HERE

- **Endpoint**: `https://lookup.search.hereapi.com/v1/lookup`
- **Documentação**: https://developer.here.com/documentation/geocoding-search-api/dev_guide/topics/endpoint-lookup-brief.html
- **Parâmetro**: `id` (HERE place ID)

### 4.4. Implementação Simplificada

```python
async def get_poi_details(self, poi_id: str) -> Optional[POI]:
    """
    Get detailed information about a specific POI.

    Args:
        poi_id: HERE place ID (format: "here/pds:place:...")

    Returns:
        POI with detailed information or None
    """
    # Extract HERE ID from our format
    here_id = poi_id.replace("here/", "")

    # Check cache
    if self._cache:
        cached_result = await self._cache.get(
            provider=self.provider_type,
            operation="poi_details",
            params={"poi_id": poi_id}
        )
        if cached_result is not None:
            return cached_result

    params = {
        "id": here_id,
        "apiKey": self._api_key,
        "lang": "pt-BR"
    }

    try:
        response = await self._client.get(
            "https://lookup.search.hereapi.com/v1/lookup",
            params=params
        )
        response.raise_for_status()
        data = response.json()

        # Parse using existing parser
        reference_location = GeoLocation(latitude=0, longitude=0)
        poi = self._parse_here_place_to_poi(data, reference_location)

        # Cache result
        if self._cache and poi:
            await self._cache.set(
                provider=self.provider_type,
                operation="poi_details",
                params={"poi_id": poi_id},
                data=poi
            )

        return poi

    except httpx.HTTPError as e:
        logger.error(f"HERE Lookup API error: {e}")
        return None
    except Exception as e:
        logger.error(f"Error getting POI details: {e}")
        return None
```

### 4.5. Critérios de Aceitação

- [ ] Detalhes do POI recuperados corretamente
- [ ] Cache funciona
- [ ] Tratamento de erros adequado
- [ ] Teste unitário passa

---

## 5. Testes de Integração

### 5.1. Criar Suite de Testes

Arquivo: `tests/integration/test_here_integration.py`

```python
import pytest
import os
from api.providers.here.provider import HEREProvider
from api.providers.models import GeoLocation, POICategory

# Skip tests if no API key
pytestmark = pytest.mark.skipif(
    not os.getenv("HERE_API_KEY"),
    reason="HERE_API_KEY not set"
)

class TestHEREIntegration:
    """Integration tests for HERE provider with real API."""

    @pytest.fixture
    async def provider(self):
        """Create HERE provider instance."""
        api_key = os.getenv("HERE_API_KEY")
        provider = HEREProvider(api_key=api_key)
        async with provider:
            yield provider

    @pytest.mark.asyncio
    async def test_geocode_sao_paulo(self, provider):
        """Test geocoding São Paulo."""
        result = await provider.geocode("São Paulo, SP")

        assert result is not None
        assert -24 < result.latitude < -23
        assert -47 < result.longitude < -46
        assert "São Paulo" in result.address

    @pytest.mark.asyncio
    async def test_search_gas_stations_sao_paulo(self, provider):
        """Test POI search for gas stations in São Paulo."""
        location = GeoLocation(latitude=-23.5505, longitude=-46.6333)

        pois = await provider.search_pois(
            location=location,
            radius=5000,
            categories=[POICategory.GAS_STATION],
            limit=10
        )

        assert len(pois) > 0
        assert all(poi.category == POICategory.GAS_STATION for poi in pois)
        assert all(poi.name for poi in pois)
        assert all(poi.location for poi in pois)

    @pytest.mark.asyncio
    async def test_calculate_route_sp_rj(self, provider):
        """Test route calculation São Paulo to Rio de Janeiro."""
        origin = GeoLocation(latitude=-23.5505, longitude=-46.6333)
        destination = GeoLocation(latitude=-22.9068, longitude=-43.1729)

        route = await provider.calculate_route(origin, destination)

        assert route is not None
        assert route.distance_km > 400  # ~450km
        assert route.duration_seconds > 14400  # > 4 hours
        assert len(route.geometry) > 10
        assert route.segments is not None
        assert len(route.segments) > 5
```

### 5.2. Executar Testes

```bash
# Testes unitários (com mocks)
poetry run pytest tests/providers/test_here_provider.py -v

# Testes de integração (com API real)
HERE_API_KEY=your_key poetry run pytest tests/integration/test_here_integration.py -v

# Todos os testes
poetry run pytest tests/providers/ tests/integration/ -v
```

---

## 6. Checklist Completo de Implementação

### Fase 1: POI Search (1-2 dias)
- [ ] Criar mapeamento de categorias HERE ↔ MapaLinear
- [ ] Implementar `_map_categories_to_here()`
- [ ] Implementar `_map_here_category_to_mapalinear()`
- [ ] Implementar `search_pois()` com cache
- [ ] Implementar `_parse_here_place_to_poi()`
- [ ] Criar testes unitários com mocks
- [ ] Testar manualmente com API real
- [ ] Atualizar documentação

### Fase 2: Route Calculation (2-3 dias)
- [ ] Adicionar dependência `flexpolyline`
- [ ] Implementar `calculate_route()` com cache
- [ ] Implementar `_parse_here_route()`
- [ ] Implementar `_decode_here_polyline()`
- [ ] Criar testes unitários com mocks
- [ ] Testar manualmente com API real
- [ ] Validar geometria e segmentos
- [ ] Atualizar documentação

### Fase 3: POI Details (0.5 dia)
- [ ] Implementar `get_poi_details()` com cache
- [ ] Criar testes unitários
- [ ] Testar manualmente
- [ ] Atualizar documentação

### Fase 4: Testes de Integração (1 dia)
- [ ] Criar suite de testes de integração
- [ ] Executar testes com API real
- [ ] Validar cobertura de testes (meta: >90%)
- [ ] Corrigir bugs encontrados

### Fase 5: Correção de Testes OSM (0.5 dia)
- [ ] Corrigir `test_search_pois_basic` (OSM)
- [ ] Corrigir `test_parse_osm_element_to_poi` (OSM)
- [ ] Validar 100% dos testes passando

### Fase 6: Documentação Final (0.5 dia)
- [ ] Atualizar CLAUDE.md
- [ ] Atualizar README.md
- [ ] Documentar exemplos de uso
- [ ] Atualizar PRD com status "Concluído"

---

## 7. Estimativa de Esforço

| Tarefa | Estimativa | Prioridade |
|--------|-----------|-----------|
| POI Search | 1-2 dias | Alta |
| Route Calculation | 2-3 dias | Alta |
| POI Details | 0.5 dia | Média |
| Testes de Integração | 1 dia | Alta |
| Correção Testes OSM | 0.5 dia | Alta |
| Documentação | 0.5 dia | Média |
| **Total** | **5-7 dias** | - |

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

| Risco | Probabilidade | Impacto | Mitigação |
|-------|--------------|---------|-----------|
| Rate limiting da API HERE | Média | Alto | Implementar cache agressivo, usar rate limiter |
| Mapeamento de categorias incompleto | Alta | Médio | Adicionar categoria OTHER como fallback |
| Decodificação de polyline falha | Baixa | Alto | Usar biblioteca oficial flexpolyline |
| Testes de integração falham | Média | Médio | Usar mocks para testes unitários, skip tests sem API key |
| Custo de API inesperado | Baixa | Alto | Monitorar uso, configurar alertas no HERE dashboard |

---

## 10. Próximas Ações Imediatas

1. **Decidir prioridade**: POI Search vs Route Calculation
2. **Instalar dependências**: `poetry add flexpolyline`
3. **Criar branch**: `git checkout -b feature/here-complete-implementation`
4. **Implementar POI Search** (recomendado começar por esta)
5. **Criar testes unitários** conforme implementa
6. **Testar manualmente** com API real
7. **Code review** e ajustes
8. **Merge** quando 100% dos testes passarem

---

**Documento criado por**: Claude Code
**Data**: 2025-01-13
**Versão**: 1.0
**Status**: Proposta de Implementação
