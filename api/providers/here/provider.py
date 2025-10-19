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
        Search POIs using HERE Places API.
        
        Args:
            location: Center point for search
            radius: Search radius in meters
            categories: POI categories to search for
            limit: Maximum results to return
            
        Returns:
            List of found POIs
        """
        # TODO: Will be implemented in Phase 3
        raise NotImplementedError("HERE POI search will be implemented in Phase 3")
    
    async def get_poi_details(self, poi_id: str) -> Optional[POI]:
        """Get detailed POI information from HERE."""
        # TODO: Will be implemented in Phase 3
        raise NotImplementedError("HERE POI details will be implemented in Phase 3")
    
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