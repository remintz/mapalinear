"""
Multi-provider geographic data abstraction layer.

This module provides a unified interface for working with different geographic data providers
such as OpenStreetMap (OSM), HERE Maps, TomTom, and others.

The architecture follows the Strategy pattern, allowing the application to switch between
different providers based on configuration, while maintaining a consistent interface
for the business logic.
"""

from .base import GeoProvider, ProviderType
from .models import GeoLocation, Route, RouteSegment, POI, POICategory
from .manager import GeoProviderManager, create_provider

__all__ = [
    'GeoProvider',
    'ProviderType',
    'GeoLocation',
    'Route',
    'RouteSegment', 
    'POI',
    'POICategory',
    'GeoProviderManager',
    'create_provider'
]