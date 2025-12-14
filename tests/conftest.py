"""
Pytest configuration and shared fixtures.

This module provides common fixtures and configuration for all tests
in the MapaLinear project, following TDD best practices.
"""

import pytest
import os
import asyncio
from typing import AsyncGenerator, Generator
from unittest.mock import Mock, AsyncMock

# Add the project root to Python path
import sys
from pathlib import Path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from api.providers.base import GeoProvider, ProviderType
from api.providers.models import GeoLocation, Route, POI, POICategory
from api.providers.cache import UnifiedCache
from api.providers.manager import GeoProviderManager


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def sample_locations():
    """Provide sample locations for testing."""
    return {
        'sao_paulo': GeoLocation(
            latitude=-23.5505,
            longitude=-46.6333,
            address="São Paulo, SP, Brasil",
            city="São Paulo",
            state="SP",
            country="Brasil"
        ),
        'rio_janeiro': GeoLocation(
            latitude=-22.9068,
            longitude=-43.1729,
            address="Rio de Janeiro, RJ, Brasil", 
            city="Rio de Janeiro",
            state="RJ",
            country="Brasil"
        ),
        'belo_horizonte': GeoLocation(
            latitude=-19.9191,
            longitude=-43.9386,
            address="Belo Horizonte, MG, Brasil",
            city="Belo Horizonte", 
            state="MG",
            country="Brasil"
        )
    }


@pytest.fixture
def sample_pois():
    """Provide sample POIs for testing."""
    location_sp = GeoLocation(latitude=-23.5505, longitude=-46.6333)
    
    return [
        POI(
            id="poi_gas_1",
            name="Posto Shell Centro",
            location=location_sp,
            category=POICategory.GAS_STATION,
            amenities=["24h", "Loja de conveniência", "WiFi"],
            rating=4.2,
            is_open=True,
            phone="+55 11 1234-5678"
        ),
        POI(
            id="poi_restaurant_1", 
            name="Restaurante Família",
            location=location_sp,
            category=POICategory.RESTAURANT,
            subcategory="brasileira",
            amenities=["Estacionamento", "WiFi", "Cartão"],
            rating=4.5,
            is_open=True,
            opening_hours={"mon": "11:00-22:00", "tue": "11:00-22:00"}
        ),
        POI(
            id="poi_hotel_1",
            name="Hotel Central",
            location=location_sp,
            category=POICategory.HOTEL,
            amenities=["WiFi", "Café da manhã", "Estacionamento"],
            rating=3.8,
            is_open=True
        )
    ]


@pytest.fixture
def sample_route(sample_locations):
    """Provide a sample route for testing."""
    origin = sample_locations['sao_paulo']
    destination = sample_locations['rio_janeiro']
    
    return Route(
        origin=origin,
        destination=destination,
        total_distance=430.5,
        total_duration=300.0,  # 5 hours in minutes
        geometry=[
            (-23.5505, -46.6333),  # São Paulo
            (-23.0000, -45.0000),  # Intermediate point
            (-22.9068, -43.1729)   # Rio de Janeiro
        ],
        road_names=["BR-116", "Via Dutra"]
    )


@pytest.fixture
def clean_cache():
    """Provide a cache instance for testing.

    Note: The cache always uses PostgreSQL. Tests should use unique
    parameters (e.g., random coordinates) to avoid cache collisions.
    """
    return UnifiedCache()


@pytest.fixture
def mock_provider():
    """Create a mock provider for testing."""
    
    class MockGeoProvider(GeoProvider):
        """Mock provider for testing purposes."""
        
        def __init__(self):
            self.call_count = 0
            self.geocode_results = {}
            self.route_results = {}
            self.poi_results = {}
            
        async def geocode(self, address: str):
            self.call_count += 1
            return self.geocode_results.get(address)
        
        async def reverse_geocode(self, latitude: float, longitude: float):
            self.call_count += 1
            key = f"{latitude},{longitude}"
            return self.geocode_results.get(key)
        
        async def calculate_route(self, origin, destination, waypoints=None, avoid=None):
            self.call_count += 1
            key = f"{origin.latitude},{origin.longitude}-{destination.latitude},{destination.longitude}"
            return self.route_results.get(key)
        
        async def search_pois(self, location, radius, categories, limit=50):
            self.call_count += 1
            key = f"{location.latitude},{location.longitude}"
            return self.poi_results.get(key, [])
        
        async def get_poi_details(self, poi_id: str):
            self.call_count += 1
            return self.poi_results.get(poi_id)
        
        @property
        def provider_type(self):
            return ProviderType.OSM
        
        @property  
        def supports_offline_export(self):
            return True
        
        @property
        def rate_limit_per_second(self):
            return 10.0
    
    return MockGeoProvider()


@pytest.fixture
def provider_manager(clean_cache):
    """Provide a clean provider manager for testing."""
    manager = GeoProviderManager(cache=clean_cache)
    return manager


@pytest.fixture
def mock_env_vars():
    """Mock environment variables for testing."""
    from api.providers.settings import reset_settings

    original_values = {}
    test_values = {
        'GEO_PRIMARY_PROVIDER': 'osm',
        'POI_PROVIDER': 'osm',
        'HERE_ENRICHMENT_ENABLED': 'false',
        'GEO_CACHE_TTL_GEOCODE': '3600',
        'GEO_CACHE_TTL_ROUTE': '1800',
        'GEO_CACHE_TTL_POI': '900',
        'HERE_API_KEY': 'test_api_key_12345',
        'GOOGLE_PLACES_ENABLED': 'true',
    }

    # Store original values and set test values
    for key, value in test_values.items():
        original_values[key] = os.getenv(key)
        os.environ[key] = value

    # Reset settings to pick up new env vars
    reset_settings()

    yield test_values

    # Restore original values
    for key, original_value in original_values.items():
        if original_value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = original_value

    # Reset settings again after restore
    reset_settings()


@pytest.fixture
def mock_env_vars_here_provider():
    """Mock environment variables with HERE as POI provider."""
    from api.providers.settings import reset_settings

    original_values = {}
    test_values = {
        'GEO_PRIMARY_PROVIDER': 'osm',
        'POI_PROVIDER': 'here',
        'HERE_ENRICHMENT_ENABLED': 'false',
        'HERE_API_KEY': 'test_api_key_12345',
        'GOOGLE_PLACES_ENABLED': 'true',
    }

    for key, value in test_values.items():
        original_values[key] = os.getenv(key)
        os.environ[key] = value

    reset_settings()
    yield test_values

    for key, original_value in original_values.items():
        if original_value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = original_value

    reset_settings()


@pytest.fixture
def mock_env_vars_here_enrichment():
    """Mock environment variables with HERE enrichment enabled."""
    from api.providers.settings import reset_settings

    original_values = {}
    test_values = {
        'GEO_PRIMARY_PROVIDER': 'osm',
        'POI_PROVIDER': 'osm',
        'HERE_ENRICHMENT_ENABLED': 'true',
        'HERE_API_KEY': 'test_api_key_12345',
        'GOOGLE_PLACES_ENABLED': 'true',
    }

    for key, value in test_values.items():
        original_values[key] = os.getenv(key)
        os.environ[key] = value

    reset_settings()
    yield test_values

    for key, original_value in original_values.items():
        if original_value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = original_value

    reset_settings()


class AsyncContextManagerMock:
    """Helper for mocking async context managers."""
    
    def __init__(self, mock_obj):
        self.mock_obj = mock_obj
    
    async def __aenter__(self):
        return self.mock_obj
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass


@pytest.fixture
def mock_http_client():
    """Mock HTTP client for testing external API calls."""
    mock_client = AsyncMock()
    
    # Mock successful response
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.raise_for_status = Mock()
    mock_response.json = Mock(return_value={
        'items': [{
            'position': {'lat': -23.5505, 'lng': -46.6333},
            'title': 'São Paulo, SP, Brasil',
            'address': {
                'city': 'São Paulo',
                'state': 'SP', 
                'countryName': 'Brasil'
            }
        }]
    })
    
    mock_client.get = AsyncMock(return_value=mock_response)
    mock_client.post = AsyncMock(return_value=mock_response)
    mock_client.aclose = AsyncMock()
    
    return mock_client


# TDD helper functions for test organization
def describe(description):
    """Decorator for test organization - TDD style describes."""
    def decorator(test_class):
        test_class.__doc__ = f"Describe: {description}"
        return test_class
    return decorator


def it(description):
    """Decorator for individual test cases - TDD style."""
    def decorator(test_func):
        test_func.__doc__ = f"It {description}"
        return test_func
    return decorator


def context(description):
    """Decorator for test contexts - TDD style."""
    def decorator(test_class):
        test_class.__doc__ = f"Context: {description}"
        return test_class
    return decorator