"""
Base interfaces and abstract classes for geographic data providers.

This module defines the core contracts that all geographic data providers must implement,
ensuring a consistent API across different provider implementations.
"""

from abc import ABC, abstractmethod
from enum import Enum
from typing import List, Dict, Optional
from .models import GeoLocation, Route, POI, POICategory


class ProviderType(Enum):
    """Supported geographic data providers."""
    OSM = "osm"
    HERE = "here"
    TOMTOM = "tomtom"


class GeoProvider(ABC):
    """
    Abstract base class for geographic data providers.
    
    All geographic data providers must implement this interface to ensure
    compatibility with the MapaLinear platform. The interface provides
    methods for geocoding, routing, and POI search operations.
    """
    
    @abstractmethod
    async def geocode(self, address: str) -> Optional[GeoLocation]:
        """
        Convert address to geographic coordinates.
        
        Args:
            address: Address string to geocode (e.g., "São Paulo, SP")
            
        Returns:
            GeoLocation object with coordinates and address details, or None if not found
        """
        pass
    
    @abstractmethod
    async def reverse_geocode(self, latitude: float, longitude: float) -> Optional[GeoLocation]:
        """
        Convert geographic coordinates to address.
        
        Args:
            latitude: Latitude coordinate (-90 to 90)
            longitude: Longitude coordinate (-180 to 180)
            
        Returns:
            GeoLocation object with address details, or None if not found
        """
        pass
    
    @abstractmethod
    async def calculate_route(
        self, 
        origin: GeoLocation, 
        destination: GeoLocation,
        waypoints: Optional[List[GeoLocation]] = None,
        avoid: Optional[List[str]] = None
    ) -> Optional[Route]:
        """
        Calculate route between two points.
        
        Args:
            origin: Starting location
            destination: Ending location
            waypoints: Optional intermediate points to route through
            avoid: Optional list of things to avoid (e.g., "tolls", "highways", "ferries")
            
        Returns:
            Route object with geometry and metadata, or None if no route found
        """
        pass
    
    @abstractmethod
    async def search_pois(
        self,
        location: GeoLocation,
        radius: float,
        categories: List[POICategory],
        limit: int = 50
    ) -> List[POI]:
        """
        Search for Points of Interest around a location.
        
        Args:
            location: Center point for the search
            radius: Search radius in meters
            categories: List of POI categories to search for
            limit: Maximum number of results to return
            
        Returns:
            List of POI objects found within the search area
        """
        pass
    
    @abstractmethod
    async def get_poi_details(self, poi_id: str) -> Optional[POI]:
        """
        Get detailed information about a specific POI.
        
        Args:
            poi_id: Unique identifier for the POI
            
        Returns:
            Detailed POI object, or None if not found
        """
        pass
    
    @property
    @abstractmethod
    def provider_type(self) -> ProviderType:
        """Return the provider type identifier."""
        pass
    
    @property
    @abstractmethod
    def supports_offline_export(self) -> bool:
        """
        Whether this provider's data can be exported for offline use.
        
        Returns:
            True if data can be cached and used offline, False otherwise
        """
        pass
    
    @property
    @abstractmethod
    def rate_limit_per_second(self) -> float:
        """
        Maximum requests per second for this provider.
        
        Returns:
            Number of requests per second that can be safely made
        """
        pass