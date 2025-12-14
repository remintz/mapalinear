"""
HERE Maps Provider implementation.

This module implements the GeoProvider interface for HERE Maps services,
providing access to HERE's geocoding, routing, and Places APIs.
"""

import httpx
import logging
from typing import List, Optional, Dict, Any
from ..base import GeoProvider, ProviderType
from ..models import GeoLocation, Route, POI, POICategory
from ..cache import UnifiedCache

logger = logging.getLogger(__name__)

# Mapping from MapaLinear POICategory to HERE category IDs
# Reference: https://developer.here.com/documentation/geocoding-search-api/dev_guide/topics-places/places-category-system-full.html
CATEGORY_TO_HERE = {
    POICategory.GAS_STATION: "700-7600-0116",  # Petrol/Gasoline Station
    POICategory.RESTAURANT: "100-1000",  # Restaurant
    POICategory.HOTEL: "500-5000,500-5100",  # Hotel, Motel
    POICategory.HOSPITAL: "800-8000-0159",  # Hospital
    POICategory.PHARMACY: "600-6400-0000",  # Pharmacy
    POICategory.ATM: "700-7010-0108",  # ATM
    POICategory.POLICE: "700-7300-0000",  # Police Station
    POICategory.MECHANIC: "700-7850-0000",  # Vehicle Repair
    POICategory.REST_AREA: "700-7600-0000",  # Parking/Rest Area
    POICategory.SUPERMARKET: "600-6300-0066",  # Grocery Store
    POICategory.SHOPPING: "600-6000",  # Shopping
    POICategory.TOURIST_ATTRACTION: "300-3000",  # Tourist Attraction
    POICategory.CAFE: "100-1100",  # Coffee/Tea
    POICategory.FAST_FOOD: "100-1000-0001",  # Fast Food
    POICategory.OTHER: "",  # No specific mapping
}

# Reverse mapping from HERE category prefix to MapaLinear category
HERE_PREFIX_TO_CATEGORY = {
    "700-7600": POICategory.GAS_STATION,
    "100-1000": POICategory.RESTAURANT,
    "100-1100": POICategory.CAFE,
    "500-5000": POICategory.HOTEL,
    "500-5100": POICategory.HOTEL,
    "800-8000": POICategory.HOSPITAL,
    "600-6400": POICategory.PHARMACY,
    "700-7010": POICategory.ATM,
    "700-7300": POICategory.POLICE,
    "700-7850": POICategory.MECHANIC,
    "600-6300": POICategory.SUPERMARKET,
    "600-6000": POICategory.SHOPPING,
    "300-3000": POICategory.TOURIST_ATTRACTION,
}


class HEREProvider(GeoProvider):
    """
    HERE Maps provider implementation.
    
    Provides access to HERE Maps APIs for geocoding, routing, and POI search.
    Requires HERE_API_KEY environment variable to be set.
    """
    
    def __init__(self, cache: Optional[UnifiedCache] = None):
        """
        Initialize HERE provider.
        
        Args:
            cache: Optional unified cache instance
            
        Raises:
            ValueError: If HERE_API_KEY is not configured
        """
        from ..settings import get_settings
        
        self._cache = cache
        settings = get_settings()
        self._api_key = settings.here_api_key
        
        if not self._api_key:
            raise ValueError(
                "HERE_API_KEY is required for HERE provider. Please set it in environment or .env file"
            )
        
        self._client = httpx.AsyncClient(
            timeout=30.0,
            headers={
                "User-Agent": "MapaLinear/1.0"
            }
        )
        
        # HERE API endpoints
        self._geocode_url = "https://geocode.search.hereapi.com/v1/geocode"
        self._reverse_geocode_url = "https://revgeocode.search.hereapi.com/v1/revgeocode"
        self._routing_url = "https://router.hereapi.com/v8/routes"
        self._places_url = "https://discover.search.hereapi.com/v1/discover"
        
        logger.info("HERE provider initialized successfully")
    
    async def geocode(self, address: str) -> Optional[GeoLocation]:
        """
        Convert address to coordinates using HERE Geocoding API.
        
        Args:
            address: Address to geocode
            
        Returns:
            GeoLocation with coordinates and address details
        """
        # Check cache first
        if self._cache:
            cached_result = await self._cache.get(
                provider=self.provider_type,
                operation="geocode",
                params={"address": address}
            )
            if cached_result is not None:
                return cached_result
        
        params = {
            "q": address,
            "apiKey": self._api_key,
            "limit": 1,
            "lang": "pt-BR"
        }
        
        try:
            response = await self._client.get(self._geocode_url, params=params)
            response.raise_for_status()
            
            data = response.json()
            
            if not data.get("items"):
                logger.warning(f"No geocoding results for address: {address}")
                return None
            
            item = data["items"][0]
            position = item["position"]
            address_data = item.get("address", {})
            
            result = GeoLocation(
                latitude=position["lat"],
                longitude=position["lng"],
                address=item.get("title", address),
                city=address_data.get("city"),
                state=address_data.get("state"),
                country=address_data.get("countryName", "Brasil"),
                postal_code=address_data.get("postalCode")
            )
            
            # Cache the result
            if self._cache:
                await self._cache.set(
                    provider=self.provider_type,
                    operation="geocode",
                    params={"address": address},
                    data=result
                )
            
            logger.debug(f"Geocoded '{address}' to {position['lat']}, {position['lng']}")
            return result
            
        except httpx.HTTPError as e:
            logger.error(f"HERE geocoding API error: {e}")
            return None
        except Exception as e:
            logger.error(f"Error geocoding address '{address}': {e}")
            return None
    
    async def reverse_geocode(
        self,
        latitude: float,
        longitude: float,
        poi_name: Optional[str] = None
    ) -> Optional[GeoLocation]:
        """
        Convert coordinates to address using HERE Reverse Geocoding API.

        Args:
            latitude: Latitude coordinate
            longitude: Longitude coordinate
            poi_name: Optional POI name for cache key differentiation

        Returns:
            GeoLocation with address details
        """
        # Build cache params - include poi_name if provided
        cache_params = {
            "latitude": latitude,
            "longitude": longitude
        }
        if poi_name:
            cache_params["poi_name"] = poi_name

        # Check cache first
        if self._cache:
            cached_result = await self._cache.get(
                provider=self.provider_type,
                operation="reverse_geocode",
                params=cache_params
            )
            if cached_result is not None:
                return cached_result
        
        params = {
            "at": f"{latitude},{longitude}",
            "apiKey": self._api_key,
            "lang": "pt-BR"
        }
        
        try:
            response = await self._client.get(self._reverse_geocode_url, params=params)
            response.raise_for_status()
            
            data = response.json()
            
            if not data.get("items"):
                logger.warning(f"No reverse geocoding results for {latitude}, {longitude}")
                return None
            
            item = data["items"][0]
            address_data = item.get("address", {})
            
            result = GeoLocation(
                latitude=latitude,
                longitude=longitude,
                address=item.get("title"),
                city=address_data.get("city"),
                state=address_data.get("state"), 
                country=address_data.get("countryName", "Brasil"),
                postal_code=address_data.get("postalCode")
            )
            
            # Cache the result
            if self._cache:
                await self._cache.set(
                    provider=self.provider_type,
                    operation="reverse_geocode",
                    params=cache_params,
                    data=result
                )
            
            logger.debug(f"Reverse geocoded {latitude}, {longitude} to '{result.address}'")
            return result
            
        except httpx.HTTPError as e:
            logger.error(f"HERE reverse geocoding API error: {e}")
            return None
        except Exception as e:
            logger.error(f"Error reverse geocoding {latitude}, {longitude}: {e}")
            return None
    
    async def calculate_route(
        self, 
        origin: GeoLocation, 
        destination: GeoLocation,
        waypoints: Optional[List[GeoLocation]] = None,
        avoid: Optional[List[str]] = None
    ) -> Optional[Route]:
        """
        Calculate route using HERE Routing API v8.
        
        Args:
            origin: Starting location
            destination: Ending location  
            waypoints: Optional intermediate points
            avoid: Optional list of things to avoid
            
        Returns:
            Route with geometry and segments
        """
        # TODO: Will be implemented in Phase 3
        raise NotImplementedError("HERE routing will be implemented in Phase 3")
    
    async def search_pois(
        self,
        location: GeoLocation,
        radius: float,
        categories: List[POICategory],
        limit: int = 50
    ) -> List[POI]:
        """
        Search POIs using HERE Browse API.

        Args:
            location: Center point for search
            radius: Search radius in meters
            categories: POI categories to search for
            limit: Maximum results to return

        Returns:
            List of found POIs
        """
        # Map categories to HERE format
        here_categories = self._map_categories_to_here(categories)
        if not here_categories:
            logger.warning(f"No valid HERE categories for: {categories}")
            return []

        # Build cache key
        cache_params = {
            "location": f"{location.latitude},{location.longitude}",
            "radius": radius,
            "categories": [c.value for c in categories],
            "limit": limit
        }

        # Check cache first
        if self._cache:
            cached_result = await self._cache.get(
                provider=self.provider_type,
                operation="poi_search",
                params=cache_params
            )
            if cached_result is not None:
                logger.debug(f"Cache hit for HERE POI search at {location.latitude},{location.longitude}")
                return cached_result

        # HERE Browse API endpoint
        browse_url = "https://browse.search.hereapi.com/v1/browse"

        params = {
            "at": f"{location.latitude},{location.longitude}",
            "categories": here_categories,
            "limit": min(limit, 100),  # HERE max is 100
            "apiKey": self._api_key,
            "lang": "pt-BR",
            "in": f"circle:{location.latitude},{location.longitude};r={int(radius)}"
        }

        try:
            response = await self._client.get(browse_url, params=params)
            response.raise_for_status()
            data = response.json()

            pois = []
            for item in data.get("items", []):
                poi = self._parse_here_place_to_poi(item, location)
                if poi:
                    pois.append(poi)

            # Cache the results
            if self._cache:
                await self._cache.set(
                    provider=self.provider_type,
                    operation="poi_search",
                    params=cache_params,
                    data=pois
                )

            logger.debug(f"Found {len(pois)} POIs via HERE near {location.latitude},{location.longitude}")
            return pois

        except httpx.HTTPError as e:
            logger.error(f"HERE Browse API error: {e}")
            return []
        except Exception as e:
            logger.error(f"Error searching POIs via HERE: {e}")
            return []

    async def get_poi_details(self, poi_id: str) -> Optional[POI]:
        """
        Get detailed POI information from HERE Lookup API.

        Args:
            poi_id: HERE place ID (format: "here:pds:place:...")

        Returns:
            POI with detailed information or None
        """
        # Extract HERE ID from our format (remove "here/" prefix if present)
        here_id = poi_id.replace("here/", "") if poi_id.startswith("here/") else poi_id

        # Check cache
        if self._cache:
            cached_result = await self._cache.get(
                provider=self.provider_type,
                operation="poi_details",
                params={"poi_id": poi_id}
            )
            if cached_result is not None:
                return cached_result

        lookup_url = "https://lookup.search.hereapi.com/v1/lookup"

        params = {
            "id": here_id,
            "apiKey": self._api_key,
            "lang": "pt-BR"
        }

        try:
            response = await self._client.get(lookup_url, params=params)
            response.raise_for_status()
            data = response.json()

            # Parse using existing parser (reference location not important for details)
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
            logger.error(f"Error getting POI details from HERE: {e}")
            return None

    def _map_categories_to_here(self, categories: List[POICategory]) -> str:
        """
        Map MapaLinear POI categories to HERE category IDs.

        Args:
            categories: List of MapaLinear categories

        Returns:
            Comma-separated string of HERE category IDs
        """
        here_ids = []
        for cat in categories:
            here_id = CATEGORY_TO_HERE.get(cat, "")
            if here_id:
                here_ids.append(here_id)
            else:
                logger.debug(f"No HERE mapping for category: {cat}")

        return ",".join(here_ids) if here_ids else ""

    def _map_here_category_to_mapalinear(self, here_category_id: str) -> POICategory:
        """
        Map HERE category ID back to MapaLinear POICategory.

        Args:
            here_category_id: HERE category ID (e.g., "700-7600-0116")

        Returns:
            Corresponding POICategory or OTHER if not found
        """
        # Try to match by prefix (first two parts of the ID)
        for prefix, category in HERE_PREFIX_TO_CATEGORY.items():
            if here_category_id.startswith(prefix):
                return category
        return POICategory.OTHER

    def _parse_here_place_to_poi(
        self,
        place: Dict[str, Any],
        reference_location: GeoLocation
    ) -> Optional[POI]:
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
            references = place.get("references", [])

            # Extract primary category
            poi_category = POICategory.OTHER
            subcategory = None
            if categories:
                primary_cat = categories[0]
                category_id = primary_cat.get("id", "")
                poi_category = self._map_here_category_to_mapalinear(category_id)
                subcategory = primary_cat.get("name")

            # Extract phone
            phone = None
            if contacts:
                for contact in contacts:
                    if contact.get("phone"):
                        phone = contact["phone"][0].get("value")
                        break

            # Extract website
            website = None
            if contacts:
                for contact in contacts:
                    if contact.get("www"):
                        website = contact["www"][0].get("value")
                        break

            # Build opening hours dict
            hours_dict = None
            if opening_hours:
                hours_dict = {}
                for oh in opening_hours:
                    if oh.get("text"):
                        # text can be a list of strings
                        text = oh["text"]
                        if isinstance(text, list):
                            hours_dict["general"] = "; ".join(text)
                        else:
                            hours_dict["general"] = text

            # Determine if open
            is_open = None
            if opening_hours:
                for oh in opening_hours:
                    if "isOpen" in oh:
                        is_open = oh["isOpen"]
                        break

            # Build structured address for here_data
            structured_address = {
                "street": address.get("street"),
                "houseNumber": address.get("houseNumber"),
                "district": address.get("district"),
                "postalCode": address.get("postalCode"),
                "city": address.get("city"),
                "state": address.get("state"),
                "countryCode": address.get("countryCode"),
            }

            # Extract external references (TripAdvisor, Yelp, etc.)
            external_refs = {}
            for ref in references:
                supplier_id = ref.get("supplier", {}).get("id")
                if supplier_id and supplier_id != "core":
                    external_refs[supplier_id] = ref.get("id")

            # Build provider_data with HERE-specific info
            provider_data = {
                "here_id": place.get("id"),
                "here_categories": categories,
                "distance": place.get("distance"),
                "address_structured": structured_address,
                "references": external_refs,
            }

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
                subcategory=subcategory,
                description=None,  # HERE doesn't provide descriptions in browse
                amenities=[],  # Not provided in basic response
                services=[],
                rating=None,  # HERE doesn't provide ratings directly
                review_count=None,
                is_open=is_open,
                phone=phone,
                website=website,
                opening_hours=hours_dict,
                provider_data=provider_data
            )

        except Exception as e:
            logger.error(f"Error parsing HERE place: {e}")
            return None
    
    @property
    def provider_type(self) -> ProviderType:
        """Return HERE provider type."""
        return ProviderType.HERE
    
    @property
    def supports_offline_export(self) -> bool:
        """HERE data can be cached for offline use."""
        return True
    
    @property 
    def rate_limit_per_second(self) -> float:
        """HERE API rate limit."""
        return 5.0  # 5 requests per second (conservative estimate)
    
    async def __aenter__(self):
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self._client.aclose()