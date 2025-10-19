"""
Provider management and factory functions.

This module provides the main interface for creating and managing geographic
data providers. It handles provider selection based on configuration and
provides a factory function for easy provider instantiation.
"""

import logging
from typing import Optional, Dict, Type
from .base import GeoProvider, ProviderType
from .cache import UnifiedCache

logger = logging.getLogger(__name__)


class GeoProviderManager:
    """
    Manages geographic data provider instances and configuration.
    
    This class handles the lifecycle of provider instances, caching,
    and provider selection based on environment configuration.
    """
    
    def __init__(self, cache: Optional[UnifiedCache] = None):
        """
        Initialize the provider manager.

        Args:
            cache: Optional unified cache instance. If not provided, creates a new one.
        """
        if cache is None:
            # Import settings to determine cache backend
            from .settings import get_settings
            settings = get_settings()
            cache = UnifiedCache(backend=settings.cache_backend)

        self._cache = cache
        self._providers: Dict[ProviderType, GeoProvider] = {}
        self._provider_classes: Dict[ProviderType, Type[GeoProvider]] = {}
        
    def register_provider(self, provider_type: ProviderType, provider_class: Type[GeoProvider]):
        """
        Register a provider class for a given provider type.
        
        Args:
            provider_type: The provider type identifier
            provider_class: The provider class to register
        """
        self._provider_classes[provider_type] = provider_class
        logger.info(f"Registered provider class for {provider_type.value}")
    
    def get_provider(self, provider_type: Optional[ProviderType] = None) -> GeoProvider:
        """
        Get a provider instance for the specified type.
        
        Args:
            provider_type: Provider type to get. If None, uses configured default.
            
        Returns:
            Configured provider instance
            
        Raises:
            ValueError: If provider type is not supported or not configured
        """
        if provider_type is None:
            provider_type = self._get_default_provider_type()
        
        # Return cached instance if available
        if provider_type in self._providers:
            return self._providers[provider_type]
        
        # Create new provider instance
        if provider_type not in self._provider_classes:
            raise ValueError(f"Provider type {provider_type.value} is not registered")
        
        provider_class = self._provider_classes[provider_type]
        provider_instance = provider_class(cache=self._cache)
        
        # Cache the instance
        self._providers[provider_type] = provider_instance
        
        logger.info(f"Created new provider instance: {provider_type.value}")
        return provider_instance
    
    def _get_default_provider_type(self) -> ProviderType:
        """
        Get the default provider type from settings configuration.
        
        Returns:
            Default provider type
            
        Raises:
            ValueError: If no valid provider is configured
        """
        from .settings import get_settings
        settings = get_settings()
        provider_name = settings.geo_primary_provider.lower()
        
        try:
            return ProviderType(provider_name)
        except ValueError:
            available = [p.value for p in ProviderType]
            raise ValueError(
                f"Invalid provider '{provider_name}'. "
                f"Available providers: {', '.join(available)}"
            )
    
    @property
    def cache(self) -> UnifiedCache:
        """Get the unified cache instance."""
        return self._cache
    
    async def get_stats(self) -> Dict[str, any]:
        """
        Get statistics for all registered providers.

        Returns:
            Dictionary with provider statistics and cache metrics
        """
        stats = {
            "active_providers": list(self._providers.keys()),
            "registered_providers": list(self._provider_classes.keys()),
            "cache_stats": await self._cache.get_stats(),
        }

        # Add provider-specific stats if available
        for provider_type, provider in self._providers.items():
            if hasattr(provider, 'get_stats'):
                stats[f"{provider_type.value}_stats"] = provider.get_stats()

        return stats


# Global provider manager instance
_global_manager: Optional[GeoProviderManager] = None


def get_manager() -> GeoProviderManager:
    """
    Get the global provider manager instance.
    
    Returns:
        Global GeoProviderManager instance
    """
    global _global_manager
    if _global_manager is None:
        _global_manager = GeoProviderManager()
        _register_built_in_providers(_global_manager)
    return _global_manager


def create_provider(provider_type: Optional[ProviderType] = None) -> GeoProvider:
    """
    Factory function to create a geographic data provider.
    
    This is the main entry point for getting a provider instance.
    It uses the global manager and automatically selects the provider
    based on environment configuration.
    
    Args:
        provider_type: Specific provider type to create. If None, uses default.
        
    Returns:
        Configured provider instance ready for use
        
    Example:
        ```python
        # Use default provider (from GEO_PRIMARY_PROVIDER env var)
        provider = create_provider()
        
        # Use specific provider
        provider = create_provider(ProviderType.HERE)
        
        # Use the provider
        location = await provider.geocode("São Paulo, SP")
        ```
    """
    manager = get_manager()
    return manager.get_provider(provider_type)


def _register_built_in_providers(manager: GeoProviderManager):
    """
    Register all built-in provider classes.
    
    Args:
        manager: Manager instance to register providers with
    """
    # Import providers here to avoid circular imports
    try:
        from .osm.provider import OSMProvider
        manager.register_provider(ProviderType.OSM, OSMProvider)
    except ImportError as e:
        logger.warning(f"Could not register OSM provider: {e}")
    
    try:
        from .here.provider import HEREProvider
        manager.register_provider(ProviderType.HERE, HEREProvider)
    except ImportError as e:
        logger.warning(f"Could not register HERE provider: {e}")
    
    logger.info("Finished registering built-in providers")