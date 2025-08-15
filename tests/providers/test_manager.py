"""
Tests for GeoProviderManager - TDD Implementation.

This module contains comprehensive tests for the provider management system,
including provider registration, instantiation, configuration, and statistics.
"""

import pytest
import os
from unittest.mock import patch, Mock, AsyncMock

from api.providers.manager import GeoProviderManager, get_manager, create_provider
from api.providers.base import GeoProvider, ProviderType
from api.providers.cache import UnifiedCache
from api.providers.models import GeoLocation, POICategory


class MockProvider(GeoProvider):
    """Mock provider for testing manager functionality."""
    
    def __init__(self, cache=None, **kwargs):
        self.cache = cache
        self.kwargs = kwargs
        self.call_history = []
    
    async def geocode(self, address: str):
        self.call_history.append(('geocode', address))
        return None
    
    async def reverse_geocode(self, latitude: float, longitude: float):
        self.call_history.append(('reverse_geocode', latitude, longitude))
        return None
    
    async def calculate_route(self, origin, destination, waypoints=None, avoid=None):
        self.call_history.append(('calculate_route', origin, destination))
        return None
    
    async def search_pois(self, location, radius, categories, limit=50):
        self.call_history.append(('search_pois', location, radius, categories))
        return []
    
    async def get_poi_details(self, poi_id: str):
        self.call_history.append(('get_poi_details', poi_id))
        return None
    
    @property
    def provider_type(self):
        return ProviderType.OSM
    
    @property
    def supports_offline_export(self):
        return True
    
    @property
    def rate_limit_per_second(self):
        return 5.0
    
    def get_stats(self):
        return {"calls": len(self.call_history)}


class AlternativeMockProvider(GeoProvider):
    """Alternative mock provider for testing different provider types."""
    
    def __init__(self, cache=None):
        self.cache = cache
    
    async def geocode(self, address: str):
        return GeoLocation(latitude=0, longitude=0, address=address)
    
    async def reverse_geocode(self, latitude: float, longitude: float):
        return GeoLocation(latitude=latitude, longitude=longitude)
    
    async def calculate_route(self, origin, destination, waypoints=None, avoid=None):
        return None
    
    async def search_pois(self, location, radius, categories, limit=50):
        return []
    
    async def get_poi_details(self, poi_id: str):
        return None
    
    @property
    def provider_type(self):
        return ProviderType.HERE
    
    @property
    def supports_offline_export(self):
        return False
    
    @property
    def rate_limit_per_second(self):
        return 10.0


class TestGeoProviderManagerInitialization:
    """Test suite for GeoProviderManager initialization."""
    
    def test_manager_initialization_default_cache(self):
        """It should initialize with default cache when none provided."""
        manager = GeoProviderManager()
        
        assert manager._cache is not None
        assert isinstance(manager._cache, UnifiedCache)
        assert manager._providers == {}
        assert manager._provider_classes == {}
    
    def test_manager_initialization_custom_cache(self, clean_cache):
        """It should use provided cache instance."""
        custom_cache = clean_cache
        manager = GeoProviderManager(cache=custom_cache)
        
        assert manager._cache is custom_cache
        assert manager.cache is custom_cache
    
    def test_manager_cache_property_access(self, clean_cache):
        """It should provide access to cache instance."""
        manager = GeoProviderManager(cache=clean_cache)
        
        assert manager.cache is clean_cache


class TestProviderRegistration:
    """Test suite for provider registration functionality."""
    
    def test_register_provider_class(self):
        """It should register provider classes correctly."""
        manager = GeoProviderManager()
        
        # Initially empty
        assert len(manager._provider_classes) == 0
        
        # Register provider
        manager.register_provider(ProviderType.OSM, MockProvider)
        
        assert ProviderType.OSM in manager._provider_classes
        assert manager._provider_classes[ProviderType.OSM] is MockProvider
    
    def test_register_multiple_providers(self):
        """It should register multiple provider classes."""
        manager = GeoProviderManager()
        
        manager.register_provider(ProviderType.OSM, MockProvider)
        manager.register_provider(ProviderType.HERE, AlternativeMockProvider)
        
        assert len(manager._provider_classes) == 2
        assert manager._provider_classes[ProviderType.OSM] is MockProvider
        assert manager._provider_classes[ProviderType.HERE] is AlternativeMockProvider
    
    def test_register_provider_overwrite(self):
        """It should allow overwriting registered providers."""
        manager = GeoProviderManager()
        
        # Register initial provider
        manager.register_provider(ProviderType.OSM, MockProvider)
        assert manager._provider_classes[ProviderType.OSM] is MockProvider
        
        # Overwrite with different provider
        manager.register_provider(ProviderType.OSM, AlternativeMockProvider)
        assert manager._provider_classes[ProviderType.OSM] is AlternativeMockProvider


class TestProviderInstantiation:
    """Test suite for provider instance creation and management."""
    
    def test_get_provider_unregistered_type(self):
        """It should raise ValueError for unregistered provider types."""
        manager = GeoProviderManager()
        
        with pytest.raises(ValueError, match="Provider type osm is not registered"):
            manager.get_provider(ProviderType.OSM)
    
    def test_get_provider_creates_instance(self):
        """It should create and return provider instances."""
        manager = GeoProviderManager()
        manager.register_provider(ProviderType.OSM, MockProvider)
        
        provider = manager.get_provider(ProviderType.OSM)
        
        assert isinstance(provider, MockProvider)
        assert provider.provider_type == ProviderType.OSM
        assert provider.cache is manager._cache
    
    def test_get_provider_caches_instances(self):
        """It should cache and reuse provider instances."""
        manager = GeoProviderManager()
        manager.register_provider(ProviderType.OSM, MockProvider)
        
        provider1 = manager.get_provider(ProviderType.OSM)
        provider2 = manager.get_provider(ProviderType.OSM)
        
        # Should return the same instance
        assert provider1 is provider2
        
        # Verify only one instance was created
        assert len(manager._providers) == 1
        assert ProviderType.OSM in manager._providers
    
    def test_get_provider_different_types(self):
        """It should create separate instances for different provider types."""
        manager = GeoProviderManager()
        manager.register_provider(ProviderType.OSM, MockProvider)
        manager.register_provider(ProviderType.HERE, AlternativeMockProvider)
        
        osm_provider = manager.get_provider(ProviderType.OSM)
        here_provider = manager.get_provider(ProviderType.HERE)
        
        assert osm_provider is not here_provider
        assert isinstance(osm_provider, MockProvider)
        assert isinstance(here_provider, AlternativeMockProvider)
        assert osm_provider.provider_type == ProviderType.OSM
        assert here_provider.provider_type == ProviderType.HERE


class TestDefaultProviderConfiguration:
    """Test suite for default provider selection from environment."""
    
    def test_get_default_provider_type_from_env(self):
        """It should read default provider from GEO_PRIMARY_PROVIDER env var."""
        from api.providers.settings import reset_settings
        
        manager = GeoProviderManager()
        
        with patch.dict(os.environ, {"GEO_PRIMARY_PROVIDER": "here"}):
            reset_settings()  # Force settings reload
            provider_type = manager._get_default_provider_type()
            assert provider_type == ProviderType.HERE
        
        with patch.dict(os.environ, {"GEO_PRIMARY_PROVIDER": "osm"}):
            reset_settings()  # Force settings reload
            provider_type = manager._get_default_provider_type()
            assert provider_type == ProviderType.OSM
    
    def test_get_default_provider_type_default_value(self):
        """It should default to OSM when env var is not set."""
        from api.providers.settings import reset_settings
        
        manager = GeoProviderManager()
        
        with patch.dict(os.environ, {}, clear=True):
            reset_settings()  # Force settings reload
            provider_type = manager._get_default_provider_type()
            assert provider_type == ProviderType.OSM
    
    def test_get_default_provider_type_invalid_value(self):
        """It should raise ValueError for invalid provider names."""
        from api.providers.settings import reset_settings
        
        manager = GeoProviderManager()
        
        with patch.dict(os.environ, {"GEO_PRIMARY_PROVIDER": "invalid_provider"}):
            reset_settings()  # Force settings reload
            with pytest.raises(ValueError, match="Invalid provider 'invalid_provider'"):
                manager._get_default_provider_type()
    
    def test_get_provider_uses_default_when_none_specified(self):
        """It should use default provider when none is specified."""
        from api.providers.settings import reset_settings
        
        manager = GeoProviderManager()
        manager.register_provider(ProviderType.OSM, MockProvider)
        manager.register_provider(ProviderType.HERE, AlternativeMockProvider)
        
        with patch.dict(os.environ, {"GEO_PRIMARY_PROVIDER": "here"}):
            reset_settings()  # Force settings reload
            provider = manager.get_provider()  # No provider_type specified
            assert isinstance(provider, AlternativeMockProvider)
            assert provider.provider_type == ProviderType.HERE


class TestProviderStatistics:
    """Test suite for provider statistics and monitoring."""
    
    def test_get_stats_initial_state(self):
        """It should return correct initial statistics."""
        manager = GeoProviderManager()
        stats = manager.get_stats()
        
        assert stats["active_providers"] == []
        assert stats["registered_providers"] == []
        assert "cache_stats" in stats
    
    def test_get_stats_after_registration(self):
        """It should show registered providers in statistics."""
        manager = GeoProviderManager()
        manager.register_provider(ProviderType.OSM, MockProvider)
        manager.register_provider(ProviderType.HERE, AlternativeMockProvider)
        
        stats = manager.get_stats()
        
        assert ProviderType.OSM in stats["registered_providers"]
        assert ProviderType.HERE in stats["registered_providers"]
        assert len(stats["registered_providers"]) == 2
        assert stats["active_providers"] == []  # No instances created yet
    
    def test_get_stats_after_instantiation(self):
        """It should show active providers in statistics."""
        manager = GeoProviderManager()
        manager.register_provider(ProviderType.OSM, MockProvider)
        
        # Create instance
        provider = manager.get_provider(ProviderType.OSM)
        
        stats = manager.get_stats()
        assert ProviderType.OSM in stats["active_providers"]
        assert len(stats["active_providers"]) == 1
    
    def test_get_stats_includes_provider_specific_stats(self):
        """It should include provider-specific statistics when available."""
        manager = GeoProviderManager()
        manager.register_provider(ProviderType.OSM, MockProvider)
        
        # Create and use provider
        provider = manager.get_provider(ProviderType.OSM)
        
        stats = manager.get_stats()
        # MockProvider has get_stats method
        assert "osm_stats" in stats
        assert stats["osm_stats"] == {"calls": 0}
    
    def test_get_stats_cache_metrics(self, clean_cache):
        """It should include cache statistics."""
        manager = GeoProviderManager(cache=clean_cache)
        stats = manager.get_stats()
        
        cache_stats = stats["cache_stats"]
        assert "backend" in cache_stats
        assert "total_entries" in cache_stats
        assert "hits" in cache_stats
        assert "misses" in cache_stats


class TestGlobalManagerFunctions:
    """Test suite for global manager singleton and factory functions."""
    
    def test_get_manager_returns_singleton(self):
        """It should return the same manager instance (singleton pattern)."""
        # Clear global manager to start fresh
        import api.providers.manager
        api.providers.manager._global_manager = None
        
        manager1 = get_manager()
        manager2 = get_manager()
        
        assert manager1 is manager2
        assert isinstance(manager1, GeoProviderManager)
    
    @patch('api.providers.manager._register_built_in_providers')
    def test_get_manager_registers_built_in_providers(self, mock_register):
        """It should register built-in providers on first call."""
        # Clear global manager
        import api.providers.manager
        api.providers.manager._global_manager = None
        
        manager = get_manager()
        
        mock_register.assert_called_once_with(manager)
    
    def test_create_provider_uses_global_manager(self):
        """It should use global manager for provider creation."""
        from api.providers.settings import reset_settings
        
        # Setup global manager with mock provider
        global_manager = get_manager()
        global_manager.register_provider(ProviderType.OSM, MockProvider)
        
        with patch.dict(os.environ, {"GEO_PRIMARY_PROVIDER": "osm"}):
            reset_settings()  # Force settings reload
            provider = create_provider()
            
            assert isinstance(provider, MockProvider)
            assert provider.provider_type == ProviderType.OSM
    
    def test_create_provider_with_specific_type(self):
        """It should create provider of specified type."""
        global_manager = get_manager()
        global_manager.register_provider(ProviderType.OSM, MockProvider)
        global_manager.register_provider(ProviderType.HERE, AlternativeMockProvider)
        
        # Request specific provider type
        osm_provider = create_provider(ProviderType.OSM)
        here_provider = create_provider(ProviderType.HERE)
        
        assert isinstance(osm_provider, MockProvider)
        assert isinstance(here_provider, AlternativeMockProvider)
        assert osm_provider is not here_provider
    
    def test_create_provider_respects_env_default(self):
        """It should respect GEO_PRIMARY_PROVIDER environment variable."""
        from api.providers.settings import reset_settings
        
        global_manager = get_manager()
        global_manager.register_provider(ProviderType.OSM, MockProvider)
        global_manager.register_provider(ProviderType.HERE, AlternativeMockProvider)
        
        with patch.dict(os.environ, {"GEO_PRIMARY_PROVIDER": "here"}):
            reset_settings()  # Force settings reload
            provider = create_provider()  # No explicit type
            assert isinstance(provider, AlternativeMockProvider)
        
        with patch.dict(os.environ, {"GEO_PRIMARY_PROVIDER": "osm"}):
            reset_settings()  # Force settings reload
            provider = create_provider()  # No explicit type
            assert isinstance(provider, MockProvider)


class TestProviderIntegration:
    """Test suite for end-to-end provider integration."""
    
    @pytest.mark.asyncio
    async def test_provider_integration_workflow(self):
        """It should support complete provider workflow."""
        manager = GeoProviderManager()
        manager.register_provider(ProviderType.OSM, MockProvider)
        
        # Get provider instance
        provider = manager.get_provider(ProviderType.OSM)
        
        # Use provider methods
        await provider.geocode("São Paulo, SP")
        await provider.reverse_geocode(-23.5505, -46.6333)
        
        # Verify calls were tracked
        assert len(provider.call_history) == 2
        assert provider.call_history[0] == ('geocode', 'São Paulo, SP')
        assert provider.call_history[1] == ('reverse_geocode', -23.5505, -46.6333)
    
    @pytest.mark.asyncio
    async def test_provider_cache_integration(self, clean_cache):
        """It should integrate with cache system."""
        manager = GeoProviderManager(cache=clean_cache)
        manager.register_provider(ProviderType.OSM, MockProvider)
        
        provider = manager.get_provider(ProviderType.OSM)
        
        # Provider should have access to cache
        assert provider.cache is clean_cache
        
        # Cache should be shared across provider instances
        another_provider = manager.get_provider(ProviderType.OSM)
        assert another_provider.cache is clean_cache
        assert another_provider is provider  # Same instance
    
    def test_error_handling_unregistered_provider(self):
        """It should handle errors gracefully for unregistered providers."""
        manager = GeoProviderManager()
        
        with pytest.raises(ValueError) as exc_info:
            manager.get_provider(ProviderType.TOMTOM)  # Not registered
        
        assert "Provider type tomtom is not registered" in str(exc_info.value)
    
    def test_error_handling_invalid_env_config(self):
        """It should handle invalid environment configuration."""
        from api.providers.settings import reset_settings
        
        manager = GeoProviderManager()
        
        with patch.dict(os.environ, {"GEO_PRIMARY_PROVIDER": "nonexistent"}):
            reset_settings()  # Force settings reload
            with pytest.raises(ValueError) as exc_info:
                manager.get_provider()  # Uses default from env
            
            assert "Invalid provider 'nonexistent'" in str(exc_info.value)


class TestBuiltInProviderRegistration:
    """Test suite for built-in provider registration logic."""
    
    @patch('api.providers.manager.logger')
    def test_register_built_in_providers_osm_success(self, mock_logger):
        """It should register OSM provider when import succeeds."""
        import sys
        import types
        
        manager = GeoProviderManager()
        
        # Create mock module structure
        mock_osm_provider = types.ModuleType('api.providers.osm.provider')
        mock_osm_provider.OSMProvider = MockProvider
        
        with patch.dict(sys.modules, {
            'api.providers.osm': types.ModuleType('api.providers.osm'),
            'api.providers.osm.provider': mock_osm_provider
        }):
            from api.providers.manager import _register_built_in_providers
            _register_built_in_providers(manager)
            
            assert ProviderType.OSM in manager._provider_classes
            mock_logger.info.assert_called_with("Finished registering built-in providers")
    
    @patch('api.providers.manager.logger')
    def test_register_built_in_providers_import_error(self, mock_logger):
        """It should handle import errors gracefully."""
        manager = GeoProviderManager()
        
        # Test that function handles import errors gracefully
        # The function should not crash even if provider modules don't exist
        from api.providers.manager import _register_built_in_providers
        
        # This should not raise an exception, even if providers can't be imported
        try:
            _register_built_in_providers(manager)
            # Test passes if no exception is raised
            assert True
        except Exception as e:
            pytest.fail(f"_register_built_in_providers should handle import errors gracefully but raised: {e}")
            
        # Verify manager is still in a valid state
        stats = manager.get_stats()
        assert isinstance(stats, dict)
        assert "registered_providers" in stats