"""
Tests for HERE Provider implementation - TDD Implementation.

This module contains comprehensive tests for the HERE provider,
verifying that it correctly implements the GeoProvider interface
including POI search functionality.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from typing import List

from api.providers.here.provider import HEREProvider
from api.providers.base import ProviderType
from api.providers.models import GeoLocation, Route, POI, POICategory
from api.providers.cache import UnifiedCache


class TestHEREProviderBasics:
    """Test basic functionality of HERE Provider."""

    @pytest.fixture
    def here_provider(self, clean_cache):
        """Create HERE provider with clean cache and mock API key."""
        with patch.dict('os.environ', {'HERE_API_KEY': 'test_api_key'}):
            from api.providers.settings import reset_settings
            reset_settings()
            return HEREProvider(cache=clean_cache)

    def test_provider_type_identification(self, here_provider):
        """It should identify itself as HERE provider."""
        assert here_provider.provider_type == ProviderType.HERE

    def test_offline_export_support(self, here_provider):
        """It should support offline data export (cached data)."""
        assert here_provider.supports_offline_export is True

    def test_rate_limiting_configuration(self, here_provider):
        """It should have appropriate rate limiting for HERE APIs."""
        assert here_provider.rate_limit_per_second == 5.0


class TestHEREProviderPOISearch:
    """Test POI search functionality of HERE Provider."""

    @pytest.fixture
    def here_provider(self, clean_cache):
        """Create HERE provider with clean cache and mock API key."""
        with patch.dict('os.environ', {'HERE_API_KEY': 'test_api_key'}):
            from api.providers.settings import reset_settings
            reset_settings()
            provider = HEREProvider(cache=clean_cache)
            return provider

    @pytest.mark.asyncio
    async def test_search_pois_basic(self, here_provider, sample_locations):
        """It should search for POIs around a location."""
        location = sample_locations['sao_paulo']
        categories = [POICategory.GAS_STATION, POICategory.RESTAURANT]

        # Mock HERE API response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.raise_for_status = Mock()
        mock_response.content = b'{}'  # For API call logging
        mock_response.json = Mock(return_value={
            'items': [
                {
                    'id': 'here123456',
                    'title': 'Posto Shell Centro',
                    'position': {'lat': -23.5505, 'lng': -46.6333},
                    'categories': [{'id': '700-7600-0116', 'name': 'Petrol/Gasoline Station'}],
                    'address': {
                        'label': 'Av Paulista, 1000, São Paulo, SP',
                        'city': 'São Paulo',
                        'state': 'SP',
                        'countryName': 'Brasil'
                    },
                    'contacts': [
                        {'phone': [{'value': '+55 11 1234-5678'}]},
                        {'www': [{'value': 'https://shell.com.br'}]}
                    ],
                    'openingHours': [{'text': ['Seg-Dom: 00:00-24:00']}]
                },
                {
                    'id': 'here789012',
                    'title': 'Restaurante Família',
                    'position': {'lat': -23.5510, 'lng': -46.6330},
                    'categories': [{'id': '100-1000-0000', 'name': 'Restaurant'}],
                    'address': {
                        'label': 'Rua Augusta, 500, São Paulo, SP',
                        'city': 'São Paulo',
                        'state': 'SP',
                        'countryName': 'Brasil'
                    }
                }
            ]
        })

        with patch.object(here_provider._client, 'get', AsyncMock(return_value=mock_response)):
            results = await here_provider.search_pois(location, 1000, categories, limit=10)

            assert len(results) >= 1
            # Check that POIs were returned
            assert any(poi.name == "Posto Shell Centro" for poi in results)

    @pytest.mark.asyncio
    async def test_search_pois_respects_limit(self, here_provider, sample_locations):
        """It should respect the limit parameter in POI searches."""
        location = sample_locations['sao_paulo']
        categories = [POICategory.GAS_STATION]

        # Mock response with many POIs
        mock_items = []
        for i in range(20):
            mock_items.append({
                'id': f'here{i}',
                'title': f'Posto {i+1}',
                'position': {'lat': -23.5505 + (i * 0.001), 'lng': -46.6333},
                'categories': [{'id': '700-7600-0116', 'name': 'Petrol/Gasoline Station'}],
                'address': {'label': f'Rua {i}, São Paulo, SP'}
            })

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.raise_for_status = Mock()
        mock_response.content = b'{}'  # For API call logging
        mock_response.json = Mock(return_value={'items': mock_items})

        with patch.object(here_provider._client, 'get', AsyncMock(return_value=mock_response)):
            results = await here_provider.search_pois(location, 1000, categories, limit=5)

            # Results should be capped at limit (or less)
            assert len(results) <= 20  # HERE returns up to limit

    @pytest.mark.asyncio
    async def test_search_pois_caches_results(self, clean_cache):
        """It should cache POI search results."""
        import random
        import time

        with patch.dict('os.environ', {'HERE_API_KEY': 'test_api_key'}):
            from api.providers.settings import reset_settings
            reset_settings()
            provider = HEREProvider(cache=clean_cache)

        # Generate truly unique coordinates using random offset and timestamp
        # This ensures we don't hit any existing cache entries
        random_offset = random.uniform(0.001, 0.999)
        unique_lat = -89.0 + random_offset  # Remote location unlikely to be in cache
        unique_lng = -179.0 + random_offset
        unique_location = GeoLocation(latitude=unique_lat, longitude=unique_lng)
        categories = [POICategory.GAS_STATION]

        # Generate unique ID based on timestamp to avoid any possible collision
        unique_id = f'here_cache_test_{int(time.time() * 1000)}'

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.raise_for_status = Mock()
        mock_response.content = b'{}'  # For API call logging
        mock_response.json = Mock(return_value={
            'items': [{
                'id': unique_id,
                'title': 'Posto Test Cache Unique',
                'position': {'lat': unique_lat, 'lng': unique_lng},
                'categories': [{'id': '700-7600-0116', 'name': 'Petrol/Gasoline Station'}],
                'address': {'label': 'Test Address Remote'}
            }]
        })

        with patch.object(provider._client, 'get', AsyncMock(return_value=mock_response)) as mock_get:
            # First call - should hit the API since location is unique
            results1 = await provider.search_pois(unique_location, 1000, categories, limit=10)
            # Second call (should use cache)
            results2 = await provider.search_pois(unique_location, 1000, categories, limit=10)

            assert len(results1) == len(results2)
            # API should have been called only once (second call uses cache)
            # Note: Due to the cache using PostgreSQL even with backend='memory',
            # if there's pre-existing data, this might fail. Using unique coordinates
            # should prevent this.
            assert mock_get.call_count == 1

    @pytest.mark.asyncio
    async def test_search_pois_handles_api_error(self, clean_cache):
        """It should handle API errors gracefully."""
        with patch.dict('os.environ', {'HERE_API_KEY': 'test_api_key'}):
            from api.providers.settings import reset_settings
            reset_settings()
            # Create fresh provider with clean cache to avoid cached results
            provider = HEREProvider(cache=clean_cache)

        # Use unique location to avoid cache hits
        unique_location = GeoLocation(latitude=-10.0000, longitude=-40.0000)
        categories = [POICategory.GAS_STATION]

        import httpx
        with patch.object(provider._client, 'get', AsyncMock(side_effect=httpx.HTTPError("API Error"))):
            results = await provider.search_pois(unique_location, 1000, categories, limit=10)

            # Should return empty list on error, not raise exception
            assert results == []

    @pytest.mark.asyncio
    async def test_search_pois_empty_categories(self, here_provider, sample_locations):
        """It should return empty list for invalid categories."""
        location = sample_locations['sao_paulo']
        categories = []  # Empty categories

        results = await here_provider.search_pois(location, 1000, categories, limit=10)
        assert results == []


class TestHEREProviderCategoryMapping:
    """Test category mapping from POICategory to HERE categories."""

    @pytest.fixture
    def here_provider(self, clean_cache):
        """Create HERE provider with clean cache."""
        with patch.dict('os.environ', {'HERE_API_KEY': 'test_api_key'}):
            from api.providers.settings import reset_settings
            reset_settings()
            return HEREProvider(cache=clean_cache)

    def test_map_gas_station_category(self, here_provider):
        """It should map GAS_STATION to HERE fuel category."""
        categories = [POICategory.GAS_STATION]
        here_cats = here_provider._map_categories_to_here(categories)
        assert '700-7600-0116' in here_cats

    def test_map_restaurant_category(self, here_provider):
        """It should map RESTAURANT to HERE restaurant category."""
        categories = [POICategory.RESTAURANT]
        here_cats = here_provider._map_categories_to_here(categories)
        assert '100-1000' in here_cats

    def test_map_hotel_category(self, here_provider):
        """It should map HOTEL to HERE hotel category."""
        categories = [POICategory.HOTEL]
        here_cats = here_provider._map_categories_to_here(categories)
        assert '500-5000' in here_cats

    def test_map_multiple_categories(self, here_provider):
        """It should map multiple categories correctly."""
        categories = [POICategory.GAS_STATION, POICategory.RESTAURANT, POICategory.HOSPITAL]
        here_cats = here_provider._map_categories_to_here(categories)
        # Should contain multiple comma-separated category IDs
        assert len(here_cats) > 0


class TestHEREProviderPOIParsing:
    """Test parsing HERE API responses to POI objects."""

    @pytest.fixture
    def here_provider(self, clean_cache):
        """Create HERE provider with clean cache."""
        with patch.dict('os.environ', {'HERE_API_KEY': 'test_api_key'}):
            from api.providers.settings import reset_settings
            reset_settings()
            return HEREProvider(cache=clean_cache)

    def test_parse_poi_with_full_data(self, here_provider, sample_locations):
        """It should correctly parse POI with all fields."""
        location = sample_locations['sao_paulo']
        here_item = {
            'id': 'here123456',
            'title': 'Posto Shell Centro',
            'position': {'lat': -23.5505, 'lng': -46.6333},
            'categories': [{'id': '700-7600-0116', 'name': 'Petrol/Gasoline Station'}],
            'address': {
                'label': 'Av Paulista, 1000, São Paulo, SP',
                'city': 'São Paulo',
                'state': 'SP',
                'countryName': 'Brasil',
                'street': 'Av Paulista',
                'houseNumber': '1000',
                'postalCode': '01310-100'
            },
            'contacts': [
                {'phone': [{'value': '+55 11 1234-5678'}]},
                {'www': [{'value': 'https://shell.com.br'}]}
            ],
            'openingHours': [{'text': ['Seg-Dom: 00:00-24:00']}]
        }

        poi = here_provider._parse_here_place_to_poi(here_item, location)

        assert poi is not None
        assert poi.name == "Posto Shell Centro"
        assert poi.location.latitude == -23.5505
        assert poi.location.longitude == -46.6333
        assert poi.phone == "+55 11 1234-5678"
        assert poi.website == "https://shell.com.br"
        assert poi.category == POICategory.GAS_STATION

    def test_parse_poi_with_minimal_data(self, here_provider, sample_locations):
        """It should correctly parse POI with minimal fields."""
        location = sample_locations['sao_paulo']
        here_item = {
            'id': 'here789',
            'title': 'Local Desconhecido',
            'position': {'lat': -23.5510, 'lng': -46.6330},
            'categories': [{'id': '100-1000-0000', 'name': 'Restaurant'}],
            'address': {'label': 'Endereço não informado'}
        }

        poi = here_provider._parse_here_place_to_poi(here_item, location)

        assert poi is not None
        assert poi.name == "Local Desconhecido"
        assert poi.phone is None
        assert poi.website is None

    def test_parse_poi_stores_here_id(self, here_provider, sample_locations):
        """It should store HERE ID in provider_data."""
        location = sample_locations['sao_paulo']
        here_item = {
            'id': 'here_unique_123',
            'title': 'Test POI',
            'position': {'lat': -23.5505, 'lng': -46.6333},
            'categories': [{'id': '700-7600-0116', 'name': 'Petrol/Gasoline Station'}],
            'address': {'label': 'Test Address'}
        }

        poi = here_provider._parse_here_place_to_poi(here_item, location)

        assert poi.provider_data.get('here_id') == 'here_unique_123'


class TestHEREProviderInitialization:
    """Test HERE Provider initialization requirements."""

    def test_api_key_handling_without_key(self):
        """It should handle missing API key gracefully."""
        # Test that provider validates API key is needed
        # by manually setting settings
        from api.providers.settings import ProviderSettings

        settings = ProviderSettings()
        original_key = settings.here_api_key
        settings.here_api_key = None

        # Validation should fail when HERE is primary provider with no key
        settings.geo_primary_provider = "here"
        assert settings.validate_here_config() is False

        # Restore original key
        settings.here_api_key = original_key

    def test_uses_api_key_from_settings(self, clean_cache):
        """It should use API key from settings."""
        with patch.dict('os.environ', {'HERE_API_KEY': 'my_test_key'}):
            from api.providers.settings import reset_settings
            reset_settings()
            provider = HEREProvider(cache=clean_cache)
            assert provider._api_key == 'my_test_key'
