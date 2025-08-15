"""
Unified data models for geographic data across all providers.

These models provide a consistent interface for geographic data regardless of the
underlying provider (OSM, HERE Maps, TomTom, etc.). All provider-specific data
is normalized to these unified models.
"""

from enum import Enum
from typing import List, Dict, Optional, Tuple, Any
from pydantic import BaseModel, Field


class POICategory(Enum):
    """Standardized POI categories across all providers."""
    GAS_STATION = "gas_station"
    RESTAURANT = "restaurant"
    HOTEL = "hotel" 
    HOSPITAL = "hospital"
    PHARMACY = "pharmacy"
    BANK = "bank"
    ATM = "atm"
    SHOPPING = "shopping"
    TOURIST_ATTRACTION = "tourist_attraction"
    REST_AREA = "rest_area"
    PARKING = "parking"
    FUEL = "fuel"
    FOOD = "food"
    LODGING = "lodging"
    SERVICES = "services"


class GeoLocation(BaseModel):
    """
    Unified geographic location representation.
    
    Normalizes location data from different providers into a consistent format.
    """
    latitude: float = Field(..., ge=-90, le=90, description="Latitude coordinate")
    longitude: float = Field(..., ge=-180, le=180, description="Longitude coordinate")
    address: Optional[str] = Field(None, description="Full formatted address")
    city: Optional[str] = Field(None, description="City name")
    state: Optional[str] = Field(None, description="State or region")
    country: Optional[str] = Field(default="Brasil", description="Country name")
    postal_code: Optional[str] = Field(None, description="Postal/ZIP code")
    
    class Config:
        """Pydantic configuration."""
        frozen = True  # Make immutable


class RouteSegment(BaseModel):
    """
    A segment of a route between two points.
    
    Routes are composed of multiple segments, each representing a portion
    of the journey with specific characteristics.
    """
    start_location: GeoLocation = Field(..., description="Starting point of this segment")
    end_location: GeoLocation = Field(..., description="Ending point of this segment")
    distance: float = Field(..., ge=0, description="Segment distance in kilometers")
    duration: float = Field(..., ge=0, description="Estimated travel time in minutes")
    road_name: Optional[str] = Field(None, description="Name of the road/highway")
    road_type: Optional[str] = Field(None, description="Type of road (highway, arterial, etc.)")
    geometry: List[Tuple[float, float]] = Field(
        default_factory=list, 
        description="Detailed geometry as [(lat, lon), ...] coordinates"
    )
    instructions: Optional[str] = Field(None, description="Navigation instructions")
    
    @property
    def midpoint(self) -> GeoLocation:
        """Calculate the midpoint of this segment."""
        mid_lat = (self.start_location.latitude + self.end_location.latitude) / 2
        mid_lon = (self.start_location.longitude + self.end_location.longitude) / 2
        return GeoLocation(latitude=mid_lat, longitude=mid_lon)


class Route(BaseModel):
    """
    Unified route representation across all providers.
    
    Contains the complete route information including geometry, segments,
    and metadata for travel between origin and destination.
    """
    origin: GeoLocation = Field(..., description="Starting location")
    destination: GeoLocation = Field(..., description="Ending location")
    total_distance: float = Field(..., ge=0, description="Total distance in kilometers")
    total_duration: float = Field(..., ge=0, description="Total estimated time in minutes")
    geometry: List[Tuple[float, float]] = Field(
        ..., 
        min_items=2, 
        description="Complete route geometry as [(lat, lon), ...] coordinates"
    )
    segments: List[RouteSegment] = Field(
        default_factory=list, 
        description="Route broken down into segments"
    )
    waypoints: List[GeoLocation] = Field(
        default_factory=list, 
        description="Intermediate waypoints if any"
    )
    road_names: List[str] = Field(
        default_factory=list, 
        description="Names of roads/highways used in this route"
    )
    
    class Config:
        """Pydantic configuration."""
        validate_assignment = True


class POI(BaseModel):
    """
    Unified Point of Interest representation.
    
    Normalizes POI data from different providers, including location,
    category information, and amenities.
    """
    id: str = Field(..., description="Unique identifier for this POI")
    name: str = Field(..., description="Display name of the POI")
    location: GeoLocation = Field(..., description="Geographic location")
    category: POICategory = Field(..., description="Primary category")
    subcategory: Optional[str] = Field(None, description="More specific category")
    description: Optional[str] = Field(None, description="Description or additional details")
    
    # Amenities and features
    amenities: List[str] = Field(
        default_factory=list, 
        description="Available amenities (WiFi, parking, etc.)"
    )
    services: List[str] = Field(
        default_factory=list, 
        description="Services offered"
    )
    
    # Quality and rating information
    rating: Optional[float] = Field(None, ge=0, le=5, description="Average rating (0-5)")
    review_count: Optional[int] = Field(None, ge=0, description="Number of reviews")
    is_open: Optional[bool] = Field(None, description="Currently open status")
    
    # Contact and operational information
    phone: Optional[str] = Field(None, description="Phone number")
    website: Optional[str] = Field(None, description="Website URL")
    opening_hours: Optional[Dict[str, str]] = Field(
        None, 
        description="Opening hours by day of week"
    )
    
    # Provider-specific data (preserved for compatibility)
    provider_data: Dict[str, Any] = Field(
        default_factory=dict, 
        description="Original provider-specific data"
    )
    
    class Config:
        """Pydantic configuration."""
        validate_assignment = True


class ProviderStats(BaseModel):
    """
    Statistics and metrics for a geographic data provider.
    
    Tracks usage, performance, and cost metrics for monitoring
    and optimization purposes.
    """
    provider_type: str = Field(..., description="Provider identifier")
    total_requests: int = Field(default=0, description="Total API requests made")
    successful_requests: int = Field(default=0, description="Successful requests")
    failed_requests: int = Field(default=0, description="Failed requests")
    cache_hits: int = Field(default=0, description="Cache hits")
    cache_misses: int = Field(default=0, description="Cache misses")
    avg_response_time: float = Field(default=0.0, description="Average response time in ms")
    last_request_time: Optional[str] = Field(None, description="ISO timestamp of last request")
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate percentage."""
        if self.total_requests == 0:
            return 0.0
        return (self.successful_requests / self.total_requests) * 100
    
    @property
    def cache_hit_rate(self) -> float:
        """Calculate cache hit rate percentage."""
        total_cache_attempts = self.cache_hits + self.cache_misses
        if total_cache_attempts == 0:
            return 0.0
        return (self.cache_hits / total_cache_attempts) * 100