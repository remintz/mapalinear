"""
OSM Provider implementation - refactored from OSMService.

This provider implements the GeoProvider interface using OpenStreetMap data sources.
"""

import asyncio
import logging
from typing import List, Optional, Dict, Any
from ..base import GeoProvider, ProviderType
from ..models import GeoLocation, Route, POI, POICategory
from ..cache import UnifiedCache

logger = logging.getLogger(__name__)


class OSMProvider(GeoProvider):
    """
    OpenStreetMap provider implementation.

    This provider uses OSM data sources including:
    - Nominatim for geocoding (with city extraction from address dictionary)
    - Overpass API for POI searches
    - OSMnx for routing calculations
    """
    
    def __init__(self, cache: Optional[UnifiedCache] = None):
        """Initialize OSM provider with required clients."""
        import asyncio
        import time
        from geopy.geocoders import Nominatim
        
        self._cache = cache
        
        # Nominatim geolocator for geocoding
        self.geolocator = Nominatim(user_agent="mapalinear/1.0")
        
        # Rate limiting attributes
        self._last_request_time: float = 0.0
        self._query_delay: float = 1.0  # 1 second between requests
        self._request_lock = asyncio.Lock()
        
        # Multiple Overpass API endpoints for fallback
        self.overpass_endpoints = [
            "https://overpass-api.de/api/interpreter",
            "https://overpass.kumi.systems/api/interpreter",
            "https://overpass.openstreetmap.ru/api/interpreter",
            "https://overpass.osm.ch/api/interpreter"
        ]
        self.current_endpoint_index = 0
        
        # Category mapping from OSM amenities to our POI categories
        self._category_mapping = {
            'fuel': POICategory.GAS_STATION,
            'restaurant': POICategory.RESTAURANT,
            'hotel': POICategory.HOTEL,
            'hospital': POICategory.HOSPITAL,
            'pharmacy': POICategory.PHARMACY,
            'bank': POICategory.BANK,
            'atm': POICategory.ATM,
            'shop': POICategory.SHOPPING,
            'tourism': POICategory.TOURIST_ATTRACTION,
            'parking': POICategory.PARKING,
            'food_court': POICategory.FOOD,
            'fast_food': POICategory.FOOD,
            'cafe': POICategory.FOOD
        }
    
    def _get_http_client(self):
        """
        Create a new HTTP client for the current async context.
        
        Returns a context manager that provides an httpx.AsyncClient
        configured for OSM API requests.
        """
        import httpx
        return httpx.AsyncClient(
            timeout=httpx.Timeout(30.0),
            headers={'User-Agent': 'mapalinear/1.0 (https://github.com/your-repo)'}
        )
    
    async def geocode(self, address: str) -> Optional[GeoLocation]:
        """Convert address to coordinates using Nominatim."""
        import asyncio
        
        # Check cache first
        if self._cache:
            cached_result = await self._cache.get(
                provider=ProviderType.OSM,
                operation="geocode",
                params={"address": address}
            )
            if cached_result:
                return cached_result
        
        try:
            # Use Nominatim for geocoding
            await self._wait_before_request()
            
            # Try with Brasil first, then without
            location = None
            for search_term in [f"{address}, Brasil", address]:
                location = await asyncio.to_thread(
                    self.geolocator.geocode, search_term
                )
                if location:
                    break
            
            if not location:
                return None

            # Debug: check what's in location.raw
            logger.debug(f"📍 location.raw = {location.raw if hasattr(location, 'raw') else 'NO RAW ATTRIBUTE'}")

            # Extract city from the address dictionary (not the string)
            address_dict = location.raw.get('address', {}) if hasattr(location, 'raw') else {}

            logger.debug(f"📍 Geocode address dict: {address_dict}")

            city = (address_dict.get('city') or
                   address_dict.get('town') or
                   address_dict.get('village') or
                   address_dict.get('municipality') or
                   address_dict.get('county'))

            state = address_dict.get('state')

            logger.debug(f"📍 Extracted city={city}, state={state} from geocoding")

            result = GeoLocation(
                latitude=location.latitude,
                longitude=location.longitude,
                address=location.address,
                city=city,
                state=state,
                country="Brasil"
            )
            
            # Cache the result
            if self._cache:
                await self._cache.set(
                    provider=ProviderType.OSM,
                    operation="geocode",
                    params={"address": address},
                    data=result
                )
            
            return result
            
        except Exception as e:
            logger.error(f"Geocoding error for '{address}': {e}")
            return None
    
    async def reverse_geocode(self, latitude: float, longitude: float) -> Optional[GeoLocation]:
        """Convert coordinates to address using Nominatim."""
        import asyncio
        
        # Check cache first
        if self._cache:
            cached_result = await self._cache.get(
                provider=ProviderType.OSM,
                operation="reverse_geocode",
                params={"latitude": latitude, "longitude": longitude}
            )
            if cached_result:
                return cached_result
        
        try:
            await self._wait_before_request()
            
            location = await asyncio.to_thread(
                self.geolocator.reverse, f"{latitude}, {longitude}"
            )
            
            if not location:
                return None
            
            # Extract city from the address dictionary (not the string)
            address_dict = location.raw.get('address', {}) if hasattr(location, 'raw') else {}

            logger.debug(f"🌍 Reverse geocode address dict: {address_dict}")

            city = (address_dict.get('city') or
                   address_dict.get('town') or
                   address_dict.get('village') or
                   address_dict.get('municipality') or
                   address_dict.get('county'))

            state = address_dict.get('state')

            logger.debug(f"🌍 Extracted city={city}, state={state} from reverse geocoding")

            result = GeoLocation(
                latitude=latitude,
                longitude=longitude,
                address=location.address,
                city=city,
                state=state,
                country="Brasil"
            )
            
            # Cache the result
            if self._cache:
                await self._cache.set(
                    provider=ProviderType.OSM,
                    operation="reverse_geocode",
                    params={"latitude": latitude, "longitude": longitude},
                    data=result
                )
            
            return result
            
        except Exception as e:
            logger.error(f"Reverse geocoding error for ({latitude}, {longitude}): {e}")
            return None
    
    async def calculate_route(
        self, 
        origin: GeoLocation, 
        destination: GeoLocation,
        waypoints: Optional[List[GeoLocation]] = None,
        avoid: Optional[List[str]] = None
    ) -> Optional[Route]:
        """Calculate route using OSMnx or basic routing."""
        logger.info(f"🗺️ Calculando rota OSM: origem=({origin.latitude:.6f}, {origin.longitude:.6f}), destino=({destination.latitude:.6f}, {destination.longitude:.6f})")
        
        # Check cache first
        cache_key_params = {
            "origin_lat": origin.latitude,
            "origin_lon": origin.longitude,
            "dest_lat": destination.latitude,
            "dest_lon": destination.longitude,
            "waypoints": [f"{w.latitude},{w.longitude}" for w in (waypoints or [])],
            "avoid": avoid or []
        }
        
        if self._cache:
            cached_result = await self._cache.get(
                provider=ProviderType.OSM,
                operation="route",
                params=cache_key_params
            )
            if cached_result:
                logger.debug(f"🗺️ Cache hit: retornando rota do cache")
                return cached_result
        
        try:
            logger.info(f"🗺️ Calculando nova rota...")
            route_data = await self._calculate_osm_route(origin, destination, waypoints, avoid)
            
            if not route_data:
                logger.warning(f"🗺️ Falha ao calcular rota - route_data vazio")
                return None
            
            logger.info(f"🗺️ Dados da rota obtidos:")
            logger.info(f"🗺️ - Distância: {route_data['distance']/1000:.1f} km")
            logger.info(f"🗺️ - Duração: {route_data['duration']/60:.1f} min")
            logger.info(f"🗺️ - Pontos na geometria: {len(route_data['geometry'])}")
            
            result = Route(
                origin=origin,
                destination=destination,
                total_distance=route_data['distance'] / 1000.0,  # Convert to km
                total_duration=route_data['duration'] / 60.0,   # Convert to minutes
                geometry=route_data['geometry'],
                waypoints=waypoints or []
            )
            
            # Cache the result
            if self._cache:
                await self._cache.set(
                    provider=ProviderType.OSM,
                    operation="route",
                    params=cache_key_params,
                    data=result
                )
            
            return result
            
        except Exception as e:
            logger.error(f"🗺️ Erro no cálculo da rota: {e}")
            return None
    
    async def search_pois(
        self,
        location: GeoLocation,
        radius: float,
        categories: List[POICategory],
        limit: int = 50
    ) -> List[POI]:
        """Search POIs using Overpass API."""
        # logger.debug(f"🔎 OSM POI Search: lat={location.latitude:.6f}, lon={location.longitude:.6f}, radius={radius}m")
        # logger.debug(f"🔎 Categorias solicitadas: {[cat.value for cat in categories]}")
        
        # Check cache first
        cache_key_params = {
            "latitude": location.latitude,
            "longitude": location.longitude,
            "radius": radius,
            "categories": [cat.value for cat in categories],
            "limit": limit
        }
        
        if self._cache:
            cached_result = await self._cache.get(
                provider=ProviderType.OSM,
                operation="poi_search",
                params=cache_key_params
            )
            if cached_result:
                logger.debug(f"🔎 Cache hit: retornando {len(cached_result)} POIs do cache")
                return cached_result
        
        try:
            query = self._generate_overpass_query(location, radius, categories)
            # logger.debug(f"🔎 Query Overpass gerada:\n{query}")
            
            overpass_data = await self._make_overpass_request(query)
            logger.debug(f"🔎 Overpass retornou {len(overpass_data.get('elements', []))} elementos")
            
            pois = []
            for i, element in enumerate(overpass_data.get('elements', [])):
                # logger.debug(f"🔎 Elemento {i}: {element.get('tags', {}).get('name', 'sem nome')} - {element.get('tags', {})}")
                poi = self._parse_osm_element_to_poi(element)
                if poi:
                    pois.append(poi)
                    # logger.debug(f"🔎 POI criado: {poi.name} ({poi.category.value})")
                    if len(pois) >= limit:
                        break
                else:
                    logger.debug(f"🔎 Elemento {i} não foi convertido em POI")
            
            logger.debug(f"🔎 Resultado: {len(pois)} POIs processados com sucesso")
            
            # Cache the result
            if self._cache:
                await self._cache.set(
                    provider=ProviderType.OSM,
                    operation="poi_search",
                    params=cache_key_params,
                    data=pois
                )
            
            return pois
            
        except Exception as e:
            logger.error(f"🔎 Erro na busca de POIs: {e}")
            return []
    
    async def get_poi_details(self, poi_id: str) -> Optional[POI]:
        """Get detailed POI information."""
        try:
            # Extract OSM ID from poi_id (format: "node/123456" or "way/123456")
            osm_type, osm_id = poi_id.split('/', 1)
            
            query = f"""
            [out:json];
            {osm_type}({osm_id});
            out meta;
            """
            
            overpass_data = await self._make_overpass_request(query)
            elements = overpass_data.get('elements', [])
            
            if elements:
                return self._parse_osm_element_to_poi(elements[0])
            
            return None
            
        except Exception as e:
            logger.error(f"POI details error for {poi_id}: {e}")
            return None
    
    @property
    def provider_type(self) -> ProviderType:
        """Return OSM provider type."""
        return ProviderType.OSM
    
    @property
    def supports_offline_export(self) -> bool:
        """OSM data can be exported for offline use."""
        return True
    
    @property
    def rate_limit_per_second(self) -> float:
        """OSM Overpass API rate limit."""
        return 1.0  # 1 request per second for Overpass API
    
    # Helper methods
    
    async def _wait_before_request(self):
        """Implement rate limiting for OSM requests."""
        async with self._request_lock:
            import time
            current_time = time.time()
            time_since_last = current_time - self._last_request_time
            
            if time_since_last < self._query_delay:
                await asyncio.sleep(self._query_delay - time_since_last)
            
            self._last_request_time = time.time()
    
    async def _calculate_osm_route(
        self, 
        origin: GeoLocation, 
        destination: GeoLocation, 
        waypoints: Optional[List[GeoLocation]] = None,
        avoid: Optional[List[str]] = None
    ) -> Optional[dict]:
        """Calculate route using OSRM API."""
        try:
            # Try OSRM first for real routing
            osrm_result = await self._calculate_osrm_api_route(origin, destination)
            if osrm_result:
                return osrm_result
            
            logger.warning(f"🗺️ OSRM falhou")
        except Exception as e:
            logger.warning(f"🗺️ Erro no OSRM: {e}")
        return None

    async def _calculate_osrm_api_route(
        self, 
        origin: GeoLocation, 
        destination: GeoLocation
    ) -> Optional[dict]:
        """Calculate route using OSRM API."""
        # OSRM demo server - use with caution in production
        osrm_url = f"http://router.project-osrm.org/route/v1/driving/{origin.longitude},{origin.latitude};{destination.longitude},{destination.latitude}"
        params = {
            'overview': 'full',
            'geometries': 'geojson',
            'annotations': 'true'
        }
        
        logger.debug(f"🗺️ Consultando OSRM: {osrm_url}")
        
        try:
            # Use context manager to ensure proper client lifecycle
            async with self._get_http_client() as client:
                response = await client.get(osrm_url, params=params, timeout=30)
                
                if response.status_code != 200:
                    logger.warning(f"🗺️ OSRM retornou status {response.status_code}")
                    return None
                
                data = response.json()
                
                if data.get('code') != 'Ok':
                    logger.warning(f"🗺️ OSRM erro: {data.get('message', 'Unknown error')}")
                    return None
                
                if not data.get('routes'):
                    logger.warning(f"🗺️ OSRM não retornou rotas")
                    return None
                
                route = data['routes'][0]
                geometry = route['geometry']['coordinates']
                
                # Convert to (lat, lon) format
                geometry_converted = [(coord[1], coord[0]) for coord in geometry]
                
                distance = route['distance']  # meters
                duration = route['duration']  # seconds
                
                logger.debug(f"🗺️ OSRM: {distance/1000:.1f}km, {len(geometry_converted)} pontos na geometria")
                
                return {
                    'distance': distance,
                    'duration': duration, 
                    'geometry': geometry_converted
                }
            
        except Exception as e:
            logger.warning(f"🗺️ Erro na requisição OSRM: {e}")
            return None

    
    def _generate_overpass_query(self, location: GeoLocation, radius: float, categories: List[POICategory]) -> str:
        """Generate Overpass query for POI search."""
        logger.debug(f"🔧 Gerando query Overpass para categorias: {[cat.value for cat in categories]}")
        
        # Convert radius to degrees (approximate)
        radius_deg = radius / 111000  # Rough conversion
        
        # Calculate bounding box
        bbox = {
            'south': location.latitude - radius_deg,
            'west': location.longitude - radius_deg,
            'north': location.latitude + radius_deg,
            'east': location.longitude + radius_deg
        }
        
        # logger.debug(f"🔧 Bounding box: {bbox}")
        
        # Map categories to OSM amenity tags (use set to avoid duplicates)
        amenity_filters = set()
        for category in categories:
            osm_amenities = self._get_osm_amenities_for_category(category)
            # logger.debug(f"🔧 Categoria {category.value} -> amenities OSM: {osm_amenities}")
            amenity_filters.update(osm_amenities)
        
        amenity_filters = list(amenity_filters)  # Convert back to list
        logger.info(f"🔧 Amenities OSM únicos para busca: {amenity_filters}")
        
        # Build query
        bbox_str = f"{bbox['south']},{bbox['west']},{bbox['north']},{bbox['east']}"
        
        query_parts = ['[out:json];', '(']
        for amenity in amenity_filters:
            query_parts.append(f'  node["amenity"="{amenity}"]({bbox_str});')
            query_parts.append(f'  way["amenity"="{amenity}"]({bbox_str});')
        
        query_parts.extend([');', 'out meta;'])
        
        final_query = '\n'.join(query_parts)
        # logger.debug(f"🔧 Query final:\n{final_query}")
        return final_query
    
    async def _make_overpass_request(self, query: str) -> dict:
        """Make request to Overpass API with fallback endpoints."""
        await self._wait_before_request()
        
        last_exception = None
        
        # Try all available endpoints
        for attempt in range(len(self.overpass_endpoints)):
            endpoint = self.overpass_endpoints[self.current_endpoint_index]
            
            try:
                logger.debug(f"Trying Overpass endpoint: {endpoint}")
                
                # Use context manager to ensure proper client lifecycle
                async with self._get_http_client() as client:
                    response = await client.post(
                        endpoint,
                        data={'data': query},
                        headers={'Content-Type': 'application/x-www-form-urlencoded'}
                    )
                    
                    response.raise_for_status()
                    
                    result = response.json()
                    logger.info(f"🌐 Overpass response: {len(result.get('elements', []))} elementos retornados")
                    
                    logger.debug(f"Overpass request successful using {endpoint}")
                    return result
                
            except Exception as e:
                last_exception = e
                logger.warning(f"🌐 Overpass endpoint {endpoint} failed: {e}")
                
                # Move to next endpoint for next attempt
                self.current_endpoint_index = (self.current_endpoint_index + 1) % len(self.overpass_endpoints)
                
                # If this was a timeout or server error, try next endpoint immediately
                if any(error_code in str(e).lower() for error_code in ['timeout', '504', '502', '503']):
                    continue
                else:
                    # For other errors, don't try more endpoints
                    break
        
        # All endpoints failed
        if last_exception:
            logger.error(f"All Overpass endpoints failed. Last error: {last_exception}")
            raise last_exception
        else:
            raise RuntimeError("No Overpass endpoints available")
    
    async def _make_nominatim_request(self, params: dict) -> dict:
        """Make request to Nominatim API (for mocking in tests)."""
        # This is primarily for test mocking
        # Real implementation uses geopy's Nominatim client
        return {}
    
    def _parse_osm_element_to_poi(self, element: dict) -> Optional[POI]:
        """Parse OSM element to POI object with quality filtering."""
        try:
            tags = element.get('tags', {})
            
            # Skip elements without required data
            if not tags.get('name') and not tags.get('amenity'):
                return None
            
            # Skip abandoned POIs
            if self._is_poi_abandoned(tags):
                return None

            # Calculate quality score (always calculate for metadata)
            quality_score = self._calculate_poi_quality_score(tags)

            # TEMPORARILY DISABLED: Quality threshold filtering
            # if not self._meets_quality_threshold(tags, quality_score):
            #     return None

            # Get coordinates
            if 'lat' in element and 'lon' in element:
                lat, lon = element['lat'], element['lon']
            elif 'center' in element:
                lat, lon = element['center']['lat'], element['center']['lon']
            else:
                return None
            
            # Determine category
            category = self._map_osm_amenity_to_category(tags.get('amenity', ''))
            if not category:
                category = POICategory.SERVICES  # Default category
            
            # Create POI
            poi_id = f"{element['type']}/{element['id']}"
            name = tags.get('name', tags.get('amenity', 'Unknown POI'))
            
            # Extract amenities using improved method
            amenities = self._extract_amenities_from_tags(tags)
            
            # Extract opening hours as dict
            opening_hours = None
            if tags.get('opening_hours'):
                # For now, store as simple string - could be enhanced to parse into dict
                opening_hours = {'general': tags['opening_hours']}
            
            # Determine if open (basic logic)
            is_open = None
            if opening_hours:
                if '24/7' in tags.get('opening_hours', ''):
                    is_open = True
                # Could add more sophisticated opening hours parsing here
            
            # Extract rating if available
            rating = None
            if tags.get('stars'):
                try:
                    rating = float(tags['stars'])
                except (ValueError, TypeError):
                    pass
            
            return POI(
                id=poi_id,
                name=name,
                location=GeoLocation(latitude=lat, longitude=lon),
                category=category,
                subcategory=tags.get('cuisine') or tags.get('shop') or tags.get('brand'),
                amenities=amenities,
                phone=tags.get('phone') or tags.get('contact:phone'),
                website=tags.get('website') or tags.get('contact:website'),
                opening_hours=opening_hours,
                rating=rating,
                is_open=is_open,
                provider_data={
                    'osm_tags': tags,
                    'quality_score': quality_score,
                    'element_type': element['type'],
                    'osm_id': element['id']
                }
            )
            
        except Exception as e:
            logger.error(f"Error parsing OSM element: {e}")
            return None
    
    def _map_osm_amenity_to_category(self, amenity: str) -> Optional[POICategory]:
        """Map OSM amenity tag to our POI category."""
        return self._category_mapping.get(amenity)
    
    def _get_osm_amenities_for_category(self, category: POICategory) -> List[str]:
        """Get OSM amenity tags for a given category."""
        category_to_amenities = {
            POICategory.GAS_STATION: ['fuel'],
            POICategory.FUEL: ['fuel'],  # Added missing mapping
            POICategory.RESTAURANT: ['restaurant', 'fast_food'],
            POICategory.FOOD: ['restaurant', 'fast_food', 'cafe', 'food_court'],
            POICategory.HOTEL: ['hotel'],
            POICategory.LODGING: ['hotel', 'motel', 'hostel', 'guest_house'],
            POICategory.CAMPING: ['camp_site', 'caravan_site'],
            POICategory.HOSPITAL: ['hospital'],
            POICategory.PHARMACY: ['pharmacy'],
            POICategory.BANK: ['bank'],
            POICategory.ATM: ['atm'],
            POICategory.SHOPPING: ['shop'],
            POICategory.PARKING: ['parking'],
            POICategory.SERVICES: ['townhall', 'community_centre', 'post_office', 'police']  # Added missing mapping for services
        }
        return category_to_amenities.get(category, [])
    
    def _extract_city_from_address(self, address: str) -> Optional[str]:
        """Extract city from address string."""
        if not address:
            return None
        
        # Simple extraction - can be improved
        parts = address.split(', ')
        for part in parts:
            if any(uf in part for uf in ['SP', 'RJ', 'MG', 'RS', 'PR', 'SC']):
                # Previous part is likely the city
                idx = parts.index(part)
                if idx > 0:
                    return parts[idx - 1]
        return None
    
    def _extract_state_from_address(self, address: str) -> Optional[str]:
        """Extract state from address string."""
        if not address:
            return None
        
        # Look for Brazilian state abbreviations
        states = ['SP', 'RJ', 'MG', 'RS', 'PR', 'SC', 'BA', 'GO', 'PE', 'CE', 'PA', 'DF']
        for state in states:
            if state in address:
                return state
        return None  # 1 request per second for Overpass API

    def _is_poi_abandoned(self, tags: Dict[str, Any]) -> bool:
        """
        Check if a POI is abandoned or out of use.
        
        Args:
            tags: OSM tags dictionary
            
        Returns:
            True if POI should be excluded for being abandoned
        """
        abandonment_indicators = [
            'abandoned', 'disused', 'demolished', 'razed', 'removed', 
            'ruins', 'former', 'closed', 'destroyed'
        ]
        
        # Check direct abandonment tags
        for indicator in abandonment_indicators:
            if tags.get(indicator) in ['yes', 'true', '1']:
                return True
            # Check prefixes (e.g. abandoned:amenity=fuel)
            for key in tags.keys():
                if key.startswith(f"{indicator}:"):
                    return True
        
        # Check specific status
        if tags.get('opening_hours') in ['closed', 'no']:
            return True
            
        return False
    
    def _calculate_poi_quality_score(self, tags: Dict[str, Any]) -> float:
        """
        Calculate quality score for a POI based on data completeness.
        
        Args:
            tags: OSM tags dictionary
            
        Returns:
            Score from 0.0 to 1.0, where 1.0 is best quality
        """
        score = 0.0
        max_score = 7.0  # Number of quality criteria
        
        # Criterion 1: Has name
        if tags.get('name'):
            score += 1.0
        
        # Criterion 2: Has operator or brand
        if tags.get('operator') or tags.get('brand'):
            score += 1.0
        
        # Criterion 3: Has phone
        if tags.get('phone') or tags.get('contact:phone'):
            score += 1.0
        
        # Criterion 4: Has opening hours
        if tags.get('opening_hours'):
            score += 1.0
        
        # Criterion 5: Has website
        if tags.get('website') or tags.get('contact:website'):
            score += 1.0
        
        # Criterion 6: For restaurants, has cuisine type
        if tags.get('amenity') == 'restaurant' and tags.get('cuisine'):
            score += 1.0
        elif tags.get('amenity') != 'restaurant':
            score += 1.0  # Don't penalize non-restaurants
            
        # Criterion 7: Has structured address
        if any(tags.get(f'addr:{field}') for field in ['street', 'housenumber', 'city']):
            score += 1.0
        
        return score / max_score
    
    def _meets_quality_threshold(self, tags: Dict[str, Any], quality_score: float) -> bool:
        """
        Check if POI meets minimum quality threshold.
        
        Args:
            tags: OSM tags dictionary
            quality_score: Calculated quality score
            
        Returns:
            True if POI should be included
        """
        amenity = tags.get('amenity')
        barrier = tags.get('barrier')
        
        # For gas stations, require name OR brand OR operator
        if amenity == 'fuel':
            if not (tags.get('name') or tags.get('brand') or tags.get('operator')):
                return False
            return quality_score >= 0.3  # Lower threshold for gas stations
        
        # For food establishments, require name
        food_amenities = ['restaurant', 'fast_food', 'cafe', 'bar', 'pub', 'food_court', 'ice_cream']
        food_shops = ['bakery']
        
        if amenity in food_amenities or tags.get('shop') in food_shops:
            if not tags.get('name'):
                return False
            return quality_score >= 0.4  # Medium threshold for food establishments
        
        # For toll booths, always include (even without name)
        if barrier == 'toll_booth':
            return True
        
        # For other types, default threshold
        return quality_score >= 0.3
    
    def _extract_amenities_from_tags(self, tags: Dict[str, Any]) -> List[str]:
        """
        Extract amenities list from OSM tags.
        
        Args:
            tags: OSM tags dictionary
            
        Returns:
            List of amenities found
        """
        amenities = []
        
        # Mapping from OSM tags to readable amenities
        amenity_mappings = {
            # Connectivity
            'internet_access': {'wifi', 'internet'},
            'wifi': {'wifi'},
            
            # Parking
            'parking': {'estacionamento'},
            'parking:fee': {'estacionamento pago'},
            
            # Accessibility
            'wheelchair': {'acessível'},
            
            # Payment
            'payment:cash': {'dinheiro'},
            'payment:cards': {'cartão'},
            'payment:contactless': {'contactless'},
            'payment:credit_cards': {'cartão de crédito'},
            'payment:debit_cards': {'cartão de débito'},
            
            # Fuel specific
            'fuel:diesel': {'diesel'},
            'fuel:octane_91': {'gasolina comum'},
            'fuel:octane_95': {'gasolina aditivada'},
            'fuel:lpg': {'GNV'},
            'fuel:ethanol': {'etanol'},
            
            # Services
            'toilets': {'banheiro'},
            'shower': {'chuveiro'},
            'restaurant': {'restaurante'},
            'cafe': {'café'},
            'shop': {'loja'},
            'atm': {'caixa eletrônico'},
            'car_wash': {'lava-jato'},
            'compressed_air': {'calibragem'},
            'vacuum_cleaner': {'aspirador'},
            
            # Others
            'outdoor_seating': {'área externa'},
            'air_conditioning': {'ar condicionado'},
            'takeaway': {'delivery'},
            'delivery': {'delivery'},
            'drive_through': {'drive-thru'},
        }
        
        # Check each tag and add corresponding amenities
        for tag_key, tag_value in tags.items():
            # Normalize tag value
            if isinstance(tag_value, str):
                tag_value = tag_value.lower()
            
            # Check if tag indicates presence of amenity
            if tag_value in ['yes', 'true', '1', 'available']:
                if tag_key in amenity_mappings:
                    amenities.extend(amenity_mappings[tag_key])
                elif tag_key.startswith('payment:') and tag_key in amenity_mappings:
                    amenities.extend(amenity_mappings[tag_key])
        
        # Special amenities based on type
        amenity_type = tags.get('amenity')
        if amenity_type == 'fuel':
            # For gas stations, assume basic amenities if not specified
            if not any('banheiro' in a for a in amenities) and tags.get('toilets') != 'no':
                amenities.append('banheiro')
        
        # Hours-based amenities
        opening_hours = tags.get('opening_hours', '')
        if '24/7' in opening_hours or 'Mo-Su 00:00-24:00' in opening_hours:
            amenities.append('24h')
        
        # Remove duplicates and sort
        amenities = sorted(list(set(amenities)))
        
        return amenities
