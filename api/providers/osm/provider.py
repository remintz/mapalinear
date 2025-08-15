"""
OSM Provider implementation - refactored from OSMService.

This provider implements the GeoProvider interface using OpenStreetMap data sources.
"""

import asyncio
import logging
from typing import List, Optional
from ..base import GeoProvider, ProviderType
from ..models import GeoLocation, Route, POI, POICategory
from ..cache import UnifiedCache

logger = logging.getLogger(__name__)


class OSMProvider(GeoProvider):
    """
    OpenStreetMap provider implementation.
    
    This provider uses OSM data sources including:
    - Nominatim for geocoding
    - Overpass API for POI searches
    - OSMnx for routing calculations
    """
    
    def __init__(self, cache: Optional[UnifiedCache] = None):
        """Initialize OSM provider with required clients."""
        import httpx
        import asyncio
        import time
        from geopy.geocoders import Nominatim
        
        self._cache = cache
        self._http_client = httpx.AsyncClient(
            timeout=httpx.Timeout(30.0),
            headers={'User-Agent': 'mapalinear/1.0 (https://github.com/your-repo)'}
        )
        
        # Nominatim geolocator for geocoding
        self.geolocator = Nominatim(user_agent="mapalinear/1.0")
        
        # Rate limiting attributes
        self._last_request_time: float = 0.0
        self._query_delay: float = 1.0  # 1 second between requests
        self._request_lock = asyncio.Lock()
        
        # Overpass API endpoint
        self.overpass_endpoint = "https://overpass-api.de/api/interpreter"
        
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
            
            result = GeoLocation(
                latitude=location.latitude,
                longitude=location.longitude,
                address=location.address,
                city=self._extract_city_from_address(location.address),
                state=self._extract_state_from_address(location.address),
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
            
            result = GeoLocation(
                latitude=latitude,
                longitude=longitude,
                address=location.address,
                city=self._extract_city_from_address(location.address),
                state=self._extract_state_from_address(location.address),
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
                return cached_result
        
        try:
            route_data = await self._calculate_osm_route(origin, destination, waypoints, avoid)
            
            if not route_data:
                return None
            
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
            logger.error(f"Route calculation error: {e}")
            return None
    
    async def search_pois(
        self,
        location: GeoLocation,
        radius: float,
        categories: List[POICategory],
        limit: int = 50
    ) -> List[POI]:
        """Search POIs using Overpass API."""
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
                return cached_result
        
        try:
            query = self._generate_overpass_query(location, radius, categories)
            overpass_data = await self._make_overpass_request(query)
            
            pois = []
            for element in overpass_data.get('elements', []):
                poi = self._parse_osm_element_to_poi(element)
                if poi:
                    pois.append(poi)
                    if len(pois) >= limit:
                        break
            
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
            logger.error(f"POI search error: {e}")
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
        """Calculate route using simplified routing logic."""
        # For now, return a simplified route calculation
        # This could be enhanced with OSMnx or other routing engines
        
        import math
        
        # Calculate straight-line distance as approximation
        lat_diff = destination.latitude - origin.latitude
        lon_diff = destination.longitude - origin.longitude
        
        # Haversine formula for distance
        R = 6371  # Earth radius in km
        lat1_rad = math.radians(origin.latitude)
        lat2_rad = math.radians(destination.latitude)
        delta_lat = math.radians(lat_diff)
        delta_lon = math.radians(lon_diff)
        
        a = (math.sin(delta_lat/2) * math.sin(delta_lat/2) +
             math.cos(lat1_rad) * math.cos(lat2_rad) *
             math.sin(delta_lon/2) * math.sin(delta_lon/2))
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        distance = R * c * 1000  # Convert to meters
        
        # Estimate duration (assuming 60 km/h average speed)
        duration = (distance / 1000) / 60 * 3600  # seconds
        
        # Create simplified geometry
        geometry = [
            (origin.latitude, origin.longitude),
            (destination.latitude, destination.longitude)
        ]
        
        return {
            'distance': distance,
            'duration': duration,
            'geometry': geometry
        }
    
    def _generate_overpass_query(self, location: GeoLocation, radius: float, categories: List[POICategory]) -> str:
        """Generate Overpass query for POI search."""
        # Convert radius to degrees (approximate)
        radius_deg = radius / 111000  # Rough conversion
        
        # Calculate bounding box
        bbox = {
            'south': location.latitude - radius_deg,
            'west': location.longitude - radius_deg,
            'north': location.latitude + radius_deg,
            'east': location.longitude + radius_deg
        }
        
        # Map categories to OSM amenity tags
        amenity_filters = []
        for category in categories:
            osm_amenities = self._get_osm_amenities_for_category(category)
            amenity_filters.extend(osm_amenities)
        
        # Build query
        bbox_str = f"{bbox['south']},{bbox['west']},{bbox['north']},{bbox['east']}"
        
        query_parts = ['[out:json];', '(']
        for amenity in amenity_filters:
            query_parts.append(f'  node["amenity"="{amenity}"]({bbox_str});')
            query_parts.append(f'  way["amenity"="{amenity}"]({bbox_str});')
        
        query_parts.extend([');', 'out meta;'])
        
        return '\n'.join(query_parts)
    
    async def _make_overpass_request(self, query: str) -> dict:
        """Make request to Overpass API."""
        await self._wait_before_request()
        
        response = await self._http_client.post(
            self.overpass_endpoint,
            data={'data': query},
            headers={'Content-Type': 'application/x-www-form-urlencoded'}
        )
        
        response.raise_for_status()
        return response.json()
    
    async def _make_nominatim_request(self, params: dict) -> dict:
        """Make request to Nominatim API (for mocking in tests)."""
        # This is primarily for test mocking
        # Real implementation uses geopy's Nominatim client
        return {}
    
    def _parse_osm_element_to_poi(self, element: dict) -> Optional[POI]:
        """Parse OSM element to POI object."""
        try:
            tags = element.get('tags', {})
            
            # Skip elements without required data
            if not tags.get('name') and not tags.get('amenity'):
                return None
            
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
            
            # Extract amenities
            amenities = []
            if tags.get('opening_hours'):
                amenities.append(f"Horário: {tags['opening_hours']}")
            if tags.get('wifi') in ['yes', 'free']:
                amenities.append('WiFi')
            if tags.get('parking') == 'yes':
                amenities.append('Estacionamento')
            
            return POI(
                id=poi_id,
                name=name,
                location=GeoLocation(latitude=lat, longitude=lon),
                category=category,
                subcategory=tags.get('cuisine') or tags.get('shop'),
                amenities=amenities,
                phone=tags.get('phone'),
                website=tags.get('website'),
                provider_data={'osm_tags': tags}
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
            POICategory.RESTAURANT: ['restaurant', 'fast_food'],
            POICategory.HOTEL: ['hotel'],
            POICategory.HOSPITAL: ['hospital'],
            POICategory.PHARMACY: ['pharmacy'],
            POICategory.BANK: ['bank'],
            POICategory.ATM: ['atm'],
            POICategory.SHOPPING: ['shop'],
            POICategory.PARKING: ['parking'],
            POICategory.FOOD: ['restaurant', 'fast_food', 'cafe', 'food_court']
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