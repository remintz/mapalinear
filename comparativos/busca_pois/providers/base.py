"""
Base abstract class for POI providers.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
import time


@dataclass
class POIResult:
    """Result from a POI search."""
    id: str
    name: str
    category: str
    latitude: float
    longitude: float
    address: Optional[str] = None
    phone: Optional[str] = None
    website: Optional[str] = None
    rating: Optional[float] = None
    raw_data: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "category": self.category,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "address": self.address,
            "phone": self.phone,
            "website": self.website,
            "rating": self.rating,
        }


class POIProvider(ABC):
    """Abstract base class for POI search providers."""
    
    def __init__(self, name: str):
        self.name = name
        self.total_requests = 0
        self.total_time = 0.0
        self.last_request_time = 0.0
    
    @abstractmethod
    async def search_pois(
        self,
        latitude: float,
        longitude: float,
        radius: int,
        categories: List[str],
    ) -> List[POIResult]:
        """
        Search for POIs near a location.
        
        Args:
            latitude: Latitude of search center
            longitude: Longitude of search center
            radius: Search radius in meters
            categories: List of POI categories to search for
            
        Returns:
            List of POI results
        """
        pass
    
    async def _make_request_with_timing(
        self,
        request_func,
        *args,
        **kwargs
    ) -> Any:
        """Execute a request and track timing."""
        self.total_requests += 1
        start_time = time.time()
        
        # Rate limiting
        elapsed = time.time() - self.last_request_time
        if elapsed < 1.0:
            time.sleep(1.0 - elapsed)
        
        result = await request_func(*args, **kwargs)
        
        self.total_time += time.time() - start_time
        self.last_request_time = time.time()
        
        return result
    
    def get_stats(self) -> Dict[str, Any]:
        """Get provider statistics."""
        avg_time = self.total_time / self.total_requests if self.total_requests > 0 else 0
        return {
            "provider": self.name,
            "total_requests": self.total_requests,
            "total_time_seconds": round(self.total_time, 2),
            "avg_time_per_request_seconds": round(avg_time, 3),
        }
    
    def reset_stats(self):
        """Reset provider statistics."""
        self.total_requests = 0
        self.total_time = 0.0
        self.last_request_time = 0.0
