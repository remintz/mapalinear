"""
Integration tests for the refactored provider system.

This module tests the integration between the new provider system
and the existing business logic to ensure backward compatibility.
"""

import pytest
from unittest.mock import Mock, patch
from api.services.road_service import RoadService
from api.providers import create_provider
from api.providers.base import ProviderType
from api.providers.models import GeoLocation, POICategory


class TestProviderSystemIntegration:
    """Integration tests for the refactored provider system."""
    
    def test_road_service_can_be_instantiated_with_default_provider(self):
        """It should create RoadService with default provider."""
        road_service = RoadService()
        
        # Should have the new provider system
        assert hasattr(road_service, 'geo_provider')
        assert road_service.geo_provider is not None
        assert road_service.geo_provider.provider_type == ProviderType.OSM
    
    def test_road_service_can_be_instantiated_with_custom_provider(self):
        """It should create RoadService with custom provider."""
        custom_provider = create_provider(ProviderType.OSM)
        road_service = RoadService(geo_provider=custom_provider)
        
        assert road_service.geo_provider is custom_provider
        assert road_service.geo_provider.provider_type == ProviderType.OSM
    
    @pytest.mark.asyncio
    async def test_geocode_location_async_works(self):
        """It should geocode locations using the new provider system."""
        road_service = RoadService()
        
        # Mock the geocoding response
        mock_location = GeoLocation(
            latitude=-23.5505,
            longitude=-46.6333,
            address="São Paulo, SP, Brasil",
            city="São Paulo",
            state="SP",
            country="Brasil"
        )
        
        with patch.object(road_service.geo_provider, 'geocode') as mock_geocode:
            mock_geocode.return_value = mock_location
            
            result = await road_service.geocode_location_async("São Paulo, SP")
            
            assert result is not None
            assert result == (-23.5505, -46.6333)
            mock_geocode.assert_called_once_with("São Paulo, SP")
    
    @pytest.mark.asyncio
    async def test_search_pois_async_works(self):
        """It should search POIs using the new provider system."""
        road_service = RoadService()
        
        # Mock POI search response
        from api.providers.models import POI
        mock_poi = POI(
            id="node/123456",
            name="Posto Shell",
            location=GeoLocation(latitude=-23.5505, longitude=-46.6333),
            category=POICategory.GAS_STATION,
            amenities=["24h", "Loja"],
            rating=4.2,
            phone="+55 11 1234-5678",
            provider_data={'tags': {'amenity': 'fuel', 'brand': 'Shell'}}
        )
        
        with patch.object(road_service.geo_provider, 'search_pois') as mock_search:
            mock_search.return_value = [mock_poi]
            
            result = await road_service.search_pois_async(
                location=(-23.5505, -46.6333),
                radius=1000,
                categories=['gas_station']
            )
            
            assert len(result) == 1
            poi_dict = result[0]
            assert poi_dict['name'] == "Posto Shell"
            assert poi_dict['category'] == 'gas_station'
            assert poi_dict['rating'] == 4.2
            assert poi_dict['phone'] == "+55 11 1234-5678"
            assert poi_dict['tags'] == {'amenity': 'fuel', 'brand': 'Shell'}
    
    @pytest.mark.asyncio 
    async def test_geocoding_error_handling(self):
        """It should handle geocoding errors gracefully."""
        road_service = RoadService()
        
        with patch.object(road_service.geo_provider, 'geocode') as mock_geocode:
            mock_geocode.side_effect = Exception("Network error")
            
            result = await road_service.geocode_location_async("Invalid Address")
            assert result is None
    
    @pytest.mark.asyncio
    async def test_poi_search_error_handling(self):
        """It should handle POI search errors gracefully."""
        road_service = RoadService()
        
        with patch.object(road_service.geo_provider, 'search_pois') as mock_search:
            mock_search.side_effect = Exception("Network error")
            
            result = await road_service.search_pois_async(
                location=(0, 0),
                radius=1000, 
                categories=['gas_station']
            )
            assert result == []
    
    @pytest.mark.asyncio
    async def test_poi_category_conversion_handles_unknowns(self):
        """It should handle unknown POI categories gracefully."""
        road_service = RoadService()
        
        with patch.object(road_service.geo_provider, 'search_pois') as mock_search:
            mock_search.return_value = []
            
            # Test with unknown categories - should not crash
            result = await road_service.search_pois_async(
                location=(0, 0),
                radius=1000,
                categories=['unknown_category', 'gas_station']
            )
            
            # Should have made a call with only the valid category
            assert mock_search.called
            call_args = mock_search.call_args
            categories = call_args.kwargs['categories']
            assert POICategory.GAS_STATION in categories
            assert len(categories) == 1  # Unknown category filtered out


class TestProviderCompatibility:
    """Test backward compatibility with existing code."""
    
    
    def test_provider_manager_creates_correct_provider(self):
        """It should create the correct provider type."""
        provider = create_provider()
        
        assert provider.provider_type == ProviderType.OSM
        assert provider.supports_offline_export == True
        assert provider.rate_limit_per_second == 1.0
    
    def test_provider_manager_with_explicit_type(self):
        """It should create provider with explicitly specified type."""
        osm_provider = create_provider(ProviderType.OSM)
        
        assert osm_provider.provider_type == ProviderType.OSM
        assert osm_provider.supports_offline_export == True


class TestCacheIntegration:
    """Test cache integration with the new provider system."""
    
    @pytest.mark.asyncio
    async def test_providers_use_unified_cache(self):
        """It should use the unified cache system."""
        provider = create_provider()
        
        # Provider should have cache
        assert hasattr(provider, '_cache')
        
        # Cache should be the unified cache type
        if provider._cache:
            from api.providers.cache import UnifiedCache
            assert isinstance(provider._cache, UnifiedCache)


class TestEnvironmentConfiguration:
    """Test environment-based provider configuration."""
    
    @pytest.mark.asyncio 
    async def test_provider_selection_via_environment(self, monkeypatch):
        """It should select provider based on environment variable."""
        # Test with OSM provider (default)
        monkeypatch.setenv("GEO_PRIMARY_PROVIDER", "osm")
        
        provider = create_provider()
        assert provider.provider_type == ProviderType.OSM
    
    @pytest.mark.asyncio
    async def test_invalid_provider_falls_back_to_default(self, monkeypatch):
        """It should fall back to default provider for invalid configuration."""
        monkeypatch.setenv("GEO_PRIMARY_PROVIDER", "invalid_provider")
        
        # Should still create a provider (falling back to default)
        provider = create_provider()
        assert provider.provider_type == ProviderType.OSM  # Default fallback