"""
Configuration settings for the multi-provider system using Pydantic Settings.

This module centralizes all configuration for geographic data providers,
using Pydantic Settings for validation and type safety.
"""

from pydantic import Field
from pydantic_settings import BaseSettings
from typing import Optional, Dict, Any


class ProviderSettings(BaseSettings):
    """
    Settings for geographic data providers.
    
    Uses Pydantic Settings to load and validate configuration from
    environment variables with proper type checking and defaults.
    """
    
    # Primary provider configuration
    geo_primary_provider: str = Field(
        default="osm",
        alias="GEO_PRIMARY_PROVIDER",
        description="Primary geographic data provider (osm, here, tomtom)"
    )
    
    # OSM Provider settings
    osm_overpass_endpoint: str = Field(
        default="https://overpass-api.de/api/interpreter",
        alias="OSM_OVERPASS_ENDPOINT",
        description="OpenStreetMap Overpass API endpoint"
    )
    osm_nominatim_endpoint: str = Field(
        default="https://nominatim.openstreetmap.org",
        alias="OSM_NOMINATIM_ENDPOINT",
        description="OpenStreetMap Nominatim geocoding endpoint"
    )
    osm_user_agent: str = Field(
        default="mapalinear/1.0",
        alias="OSM_USER_AGENT",
        description="User agent for OSM API requests"
    )
    
    # HERE Maps settings
    here_api_key: Optional[str] = Field(
        default=None,
        alias="HERE_API_KEY",
        description="HERE Maps API key (required when using HERE provider)"
    )
    here_app_id: Optional[str] = Field(
        default=None,
        alias="HERE_APP_ID",
        description="HERE Maps App ID (optional for some endpoints)"
    )
    here_app_code: Optional[str] = Field(
        default=None,
        alias="HERE_APP_CODE",
        description="HERE Maps App Code (optional)"
    )
    
    # Cache configuration
    geo_cache_ttl_geocode: int = Field(
        default=604800,  # 7 days
        alias="GEO_CACHE_TTL_GEOCODE",
        description="Cache TTL for geocoding results in seconds"
    )
    geo_cache_ttl_route: int = Field(
        default=21600,   # 6 hours
        alias="GEO_CACHE_TTL_ROUTE",
        description="Cache TTL for routing results in seconds"
    )
    geo_cache_ttl_poi: int = Field(
        default=86400,   # 1 day
        alias="GEO_CACHE_TTL_POI",
        description="Cache TTL for POI search results in seconds"
    )
    geo_cache_ttl_poi_details: int = Field(
        default=43200,   # 12 hours
        alias="GEO_CACHE_TTL_POI_DETAILS",
        description="Cache TTL for POI details in seconds"
    )
    
    # Rate limiting configuration
    geo_rate_limit_here: float = Field(
        default=10.0,
        alias="GEO_RATE_LIMIT_HERE",
        description="HERE Maps rate limit (requests per second)"
    )
    geo_rate_limit_osm: float = Field(
        default=1.0,
        alias="GEO_RATE_LIMIT_OSM",
        description="OpenStreetMap rate limit (requests per second)"
    )
    geo_rate_limit_tomtom: float = Field(
        default=5.0,
        alias="GEO_RATE_LIMIT_TOMTOM",
        description="TomTom rate limit (requests per second)"
    )
    
    # API configuration
    mapalinear_api_url: str = Field(
        default="http://localhost:8001/api",
        alias="MAPALINEAR_API_URL",
        description="MapaLinear API base URL"
    )
    mapalinear_host: str = Field(
        default="0.0.0.0",
        alias="MAPALINEAR_HOST",
        description="API server host"
    )
    mapalinear_port: int = Field(
        default=8001,
        alias="MAPALINEAR_PORT",
        description="API server port"
    )
    
    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
        "env_prefix": "",
        "extra": "ignore",  # Allow extra fields from .env but ignore them
    }
    
    def get_provider_rate_limit(self, provider: str) -> float:
        """Get rate limit for specific provider."""
        rate_limits = {
            "osm": self.geo_rate_limit_osm,
            "here": self.geo_rate_limit_here,
            "tomtom": self.geo_rate_limit_tomtom,
        }
        return rate_limits.get(provider.lower(), 1.0)
    
    def get_cache_ttl(self, operation: str) -> int:
        """Get cache TTL for specific operation."""
        ttl_config = {
            "geocode": self.geo_cache_ttl_geocode,
            "reverse_geocode": self.geo_cache_ttl_geocode,
            "route": self.geo_cache_ttl_route,
            "poi_search": self.geo_cache_ttl_poi,
            "poi_details": self.geo_cache_ttl_poi_details,
        }
        return ttl_config.get(operation, 3600)  # Default 1 hour
    
    def validate_here_config(self) -> bool:
        """Validate HERE Maps configuration."""
        if self.geo_primary_provider.lower() == "here":
            return self.here_api_key is not None
        return True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert settings to dictionary."""
        return self.dict()


# Global settings instance
_settings: Optional[ProviderSettings] = None


def get_settings() -> ProviderSettings:
    """
    Get global settings instance (singleton pattern).
    
    Returns:
        Validated ProviderSettings instance
    """
    global _settings
    if _settings is None:
        _settings = ProviderSettings()
    return _settings


def reset_settings() -> None:
    """Reset global settings (useful for testing)."""
    global _settings
    _settings = None