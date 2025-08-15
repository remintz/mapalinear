"""
OpenStreetMap (OSM) provider implementation.

This module provides access to OpenStreetMap data through the Overpass API,
Nominatim geocoding service, and OSMnx for routing calculations.
"""

from .provider import OSMProvider

__all__ = ['OSMProvider']