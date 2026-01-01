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
    
    # Primary provider configuration (legacy - kept for backwards compatibility)
    geo_primary_provider: str = Field(
        default="osm",
        alias="GEO_PRIMARY_PROVIDER",
        description="Primary geographic data provider (osm, here, tomtom) - DEPRECATED, use POI_PROVIDER"
    )

    # POI provider configuration
    poi_provider: str = Field(
        default="osm",
        alias="POI_PROVIDER",
        description="Provider for POI search (osm, here). Route calculation always uses OSM."
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

    # Google Places settings (for restaurant/hotel ratings)
    google_places_api_key: Optional[str] = Field(
        default=None,
        alias="GOOGLE_PLACES_API_KEY",
        description="Google Places API key for fetching ratings"
    )
    google_places_cache_ttl: int = Field(
        default=2592000,  # 30 days (Google ToS requirement)
        alias="GOOGLE_PLACES_CACHE_TTL",
        description="Cache TTL for Google Places data in seconds (max 30 days per Google ToS)"
    )
    google_places_enabled: bool = Field(
        default=True,
        alias="GOOGLE_PLACES_ENABLED",
        description="Enable Google Places enrichment for restaurants and hotels"
    )

    # HERE Maps enrichment settings
    here_enrichment_enabled: bool = Field(
        default=False,
        alias="HERE_ENRICHMENT_ENABLED",
        description="Enable HERE Maps enrichment for OSM POIs (adds phone, website, hours). Only applies when POI_PROVIDER=osm."
    )

    # Map duplication detection settings
    duplicate_map_tolerance_km: float = Field(
        default=5.0,
        alias="DUPLICATE_MAP_TOLERANCE_KM",
        description="Maximum distance in km between origin/destination coordinates to consider maps as duplicates"
    )

    # POI junction calculation settings
    lookback_milestones_count: int = Field(
        default=10,
        alias="LOOKBACK_MILESTONES_COUNT",
        description="Number of milestones to look back when calculating junction for distant POIs. Uses actual milestone coordinates instead of interpolated points."
    )

    # Google OAuth settings
    google_client_id: Optional[str] = Field(
        default=None,
        alias="GOOGLE_CLIENT_ID",
        description="Google OAuth client ID for authentication"
    )
    google_client_secret: Optional[str] = Field(
        default=None,
        alias="GOOGLE_CLIENT_SECRET",
        description="Google OAuth client secret for authentication"
    )

    # JWT settings
    jwt_secret_key: str = Field(
        default="change-me-in-production-use-a-long-random-string",
        alias="JWT_SECRET_KEY",
        description="Secret key for JWT token signing"
    )
    jwt_algorithm: str = Field(
        default="HS256",
        alias="JWT_ALGORITHM",
        description="Algorithm for JWT token signing"
    )
    jwt_expire_hours: int = Field(
        default=24,
        alias="JWT_EXPIRE_HOURS",
        description="JWT token expiration time in hours"
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
    
    # PostgreSQL Cache configuration (always uses PostgreSQL)
    postgres_host: str = Field(
        default="localhost",
        alias="POSTGRES_HOST",
        description="PostgreSQL host"
    )
    postgres_port: int = Field(
        default=5432,
        alias="POSTGRES_PORT",
        description="PostgreSQL port"
    )
    postgres_database: str = Field(
        default="mapalinear",
        alias="POSTGRES_DATABASE",
        description="PostgreSQL database name"
    )
    postgres_user: str = Field(
        default="mapalinear",
        alias="POSTGRES_USER",
        description="PostgreSQL user"
    )
    postgres_password: str = Field(
        default="mapalinear",
        alias="POSTGRES_PASSWORD",
        description="PostgreSQL password"
    )
    postgres_pool_min_size: int = Field(
        default=0,
        alias="POSTGRES_POOL_MIN_SIZE",
        description="Minimum PostgreSQL connection pool size (0 to avoid race conditions)"
    )
    postgres_pool_max_size: int = Field(
        default=50,
        alias="POSTGRES_POOL_MAX_SIZE",
        description="Maximum PostgreSQL connection pool size"
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