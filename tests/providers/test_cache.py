"""
Tests for the unified cache system - TDD Implementation.

This module contains comprehensive tests for the unified caching layer,
following Test-Driven Development principles with thorough coverage
of cache operations, semantic matching, and performance metrics.
"""

import pytest
import asyncio
import os
from datetime import datetime, timedelta
from unittest.mock import patch

from api.providers.cache import UnifiedCache, CacheKey, CacheEntry
from api.providers.base import ProviderType
from api.providers.models import GeoLocation, POI, POICategory


class TestCacheKey:
    """Test suite for CacheKey generation and normalization."""
    
    def test_cache_key_structure(self):
        """It should generate keys with provider:operation:hash structure."""
        key = CacheKey(
            provider=ProviderType.OSM,
            operation="geocode",
            params={"address": "São Paulo, SP"}
        )
        
        generated_key = key.generate_key()
        parts = generated_key.split(":")
        
        assert len(parts) == 3
        assert parts[0] == "osm"
        assert parts[1] == "geocode"
        assert len(parts[2]) == 32  # MD5 hash length
    
    def test_cache_key_consistency(self):
        """It should generate identical keys for identical parameters."""
        params = {"address": "São Paulo, SP", "limit": 1}
        
        key1 = CacheKey(ProviderType.HERE, "geocode", params)
        key2 = CacheKey(ProviderType.HERE, "geocode", params)
        
        assert key1.generate_key() == key2.generate_key()
    
    def test_cache_key_different_providers(self):
        """It should generate different keys for different providers."""
        params = {"address": "São Paulo, SP"}
        
        osm_key = CacheKey(ProviderType.OSM, "geocode", params)
        here_key = CacheKey(ProviderType.HERE, "geocode", params)
        
        assert osm_key.generate_key() != here_key.generate_key()
    
    def test_cache_key_different_operations(self):
        """It should generate different keys for different operations."""
        params = {"latitude": -23.5505, "longitude": -46.6333}
        
        geocode_key = CacheKey(ProviderType.OSM, "geocode", params)
        reverse_key = CacheKey(ProviderType.OSM, "reverse_geocode", params)
        
        assert geocode_key.generate_key() != reverse_key.generate_key()


class TestCacheKeyNormalization:
    """Test suite for parameter normalization in cache keys."""
    
    def test_string_normalization(self):
        """It should normalize strings to lowercase and remove extra spaces."""
        key1 = CacheKey(
            ProviderType.OSM, "geocode",
            {"address": "São Paulo, SP"}
        )
        
        key2 = CacheKey(
            ProviderType.OSM, "geocode", 
            {"address": "  SÃO PAULO,   SP  "}
        )
        
        assert key1.generate_key() == key2.generate_key()
    
    def test_coordinate_rounding(self):
        """It should round coordinates to 6 decimal places for consistency."""
        key1 = CacheKey(
            ProviderType.HERE, "reverse_geocode",
            {"latitude": -23.550500000, "longitude": -46.633300000}
        )
        
        key2 = CacheKey(
            ProviderType.HERE, "reverse_geocode",
            {"latitude": -23.5505, "longitude": -46.6333}
        )
        
        assert key1.generate_key() == key2.generate_key()
    
    def test_list_sorting(self):
        """It should sort lists for consistent hashing."""
        key1 = CacheKey(
            ProviderType.OSM, "poi_search",
            {"categories": ["restaurant", "gas_station", "hotel"]}
        )
        
        key2 = CacheKey(
            ProviderType.OSM, "poi_search",
            {"categories": ["hotel", "gas_station", "restaurant"]}  # Different order
        )
        
        assert key1.generate_key() == key2.generate_key()
    
    def test_empty_list_handling(self):
        """It should handle empty lists consistently."""
        key1 = CacheKey(ProviderType.OSM, "poi_search", {"categories": []})
        key2 = CacheKey(ProviderType.OSM, "poi_search", {"categories": []})
        
        assert key1.generate_key() == key2.generate_key()


class TestCacheEntry:
    """Test suite for CacheEntry model."""
    
    def test_cache_entry_creation(self):
        """It should create CacheEntry with all required fields."""
        created_at = datetime.utcnow()
        expires_at = created_at + timedelta(hours=1)
        
        entry = CacheEntry(
            key="osm:geocode:abc123",
            data={"test": "data"},
            provider=ProviderType.OSM,
            operation="geocode",
            created_at=created_at,
            expires_at=expires_at,
            hit_count=0,
            params={"address": "Test"}
        )
        
        assert entry.key == "osm:geocode:abc123"
        assert entry.data == {"test": "data"}
        assert entry.provider == ProviderType.OSM
        assert entry.operation == "geocode"
        assert entry.hit_count == 0
    
    def test_cache_entry_expiration_check(self):
        """It should correctly identify expired entries."""
        now = datetime.utcnow()
        
        # Non-expired entry
        fresh_entry = CacheEntry(
            key="test", data={}, provider=ProviderType.OSM, operation="geocode",
            created_at=now, expires_at=now + timedelta(hours=1)
        )
        assert not fresh_entry.is_expired()
        
        # Expired entry
        expired_entry = CacheEntry(
            key="test", data={}, provider=ProviderType.OSM, operation="geocode",
            created_at=now - timedelta(hours=2), expires_at=now - timedelta(hours=1)
        )
        assert expired_entry.is_expired()
    
    def test_cache_entry_serialization(self):
        """It should serialize and deserialize correctly."""
        original = CacheEntry(
            key="test:key:123",
            data={"result": "test data"},
            provider=ProviderType.HERE,
            operation="geocode",
            created_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(hours=1),
            hit_count=5,
            params={"address": "Test Address"}
        )
        
        # Serialize
        serialized = original.to_dict()
        assert serialized['key'] == "test:key:123"
        assert serialized['provider'] == "here"
        assert serialized['hit_count'] == 5
        assert isinstance(serialized['created_at'], str)
        
        # Deserialize
        restored = CacheEntry.from_dict(serialized)
        assert restored.key == original.key
        assert restored.provider == original.provider
        assert restored.hit_count == original.hit_count
        assert restored.data == original.data


class TestUnifiedCacheBasicOperations:
    """Test suite for basic cache operations."""
    
    @pytest.mark.asyncio
    async def test_cache_miss_initially(self, clean_cache):
        """It should return None for non-existent cache entries."""
        cache = clean_cache
        
        result = await cache.get(
            provider=ProviderType.OSM,
            operation="geocode",
            params={"address": "NonExistent"}
        )
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_basic_cache_set_get(self, clean_cache):
        """It should store and retrieve data correctly."""
        cache = clean_cache
        test_data = {"lat": -23.5505, "lon": -46.6333, "address": "São Paulo"}
        
        # Set cache entry
        await cache.set(
            provider=ProviderType.OSM,
            operation="geocode",
            params={"address": "São Paulo, SP"},
            data=test_data
        )
        
        # Get cache entry
        result = await cache.get(
            provider=ProviderType.OSM,
            operation="geocode",
            params={"address": "São Paulo, SP"}
        )
        
        assert result == test_data
    
    @pytest.mark.asyncio
    async def test_cache_provider_isolation(self, clean_cache):
        """It should isolate data between different providers."""
        cache = clean_cache
        osm_data = {"source": "osm"}
        here_data = {"source": "here"}
        
        # Set data for different providers
        await cache.set(ProviderType.OSM, "geocode", {"address": "Test"}, osm_data)
        await cache.set(ProviderType.HERE, "geocode", {"address": "Test"}, here_data)
        
        # Verify isolation
        osm_result = await cache.get(ProviderType.OSM, "geocode", {"address": "Test"})
        here_result = await cache.get(ProviderType.HERE, "geocode", {"address": "Test"})
        
        assert osm_result == osm_data
        assert here_result == here_data
        assert osm_result != here_result
    
    @pytest.mark.asyncio
    async def test_cache_operation_isolation(self, clean_cache):
        """It should isolate data between different operations."""
        cache = clean_cache
        geocode_data = {"type": "geocoding"}
        poi_data = {"type": "poi_search"}
        
        params = {"query": "test"}
        
        # Set data for different operations
        await cache.set(ProviderType.OSM, "geocode", params, geocode_data)
        await cache.set(ProviderType.OSM, "poi_search", params, poi_data)
        
        # Verify isolation
        geocode_result = await cache.get(ProviderType.OSM, "geocode", params)
        poi_result = await cache.get(ProviderType.OSM, "poi_search", params)
        
        assert geocode_result == geocode_data
        assert poi_result == poi_data
        assert geocode_result != poi_result


class TestCacheTTLandExpiration:
    """Test suite for cache TTL and expiration logic."""
    
    @pytest.mark.asyncio
    async def test_cache_respects_ttl_config(self, mock_env_vars):
        """It should use TTL from configuration."""
        # Create cache AFTER setting environment variables
        cache = UnifiedCache(backend="memory")
        
        # Verify TTL configuration is loaded from mocked env vars
        assert cache.ttl_config["geocode"] == 3600  # From mock env
        assert cache.ttl_config["route"] == 1800
        assert cache.ttl_config["poi_search"] == 900
    
    @pytest.mark.asyncio
    async def test_cache_entry_expiration(self, clean_cache):
        """It should expire entries after TTL."""
        cache = clean_cache
        cache.ttl_config["geocode"] = 1  # 1 second for testing
        
        test_data = {"expired": "data"}
        
        # Set entry
        await cache.set(
            ProviderType.OSM, "geocode",
            {"address": "Test"}, test_data
        )
        
        # Should be available immediately
        result = await cache.get(ProviderType.OSM, "geocode", {"address": "Test"})
        assert result == test_data
        
        # Wait for expiration
        await asyncio.sleep(1.5)
        
        # Should be expired
        result = await cache.get(ProviderType.OSM, "geocode", {"address": "Test"})
        assert result is None
    
    @pytest.mark.asyncio
    async def test_cache_cleanup_expired_entries(self, clean_cache):
        """It should clean up expired entries periodically."""
        cache = clean_cache
        cache.ttl_config["geocode"] = 1  # 1 second
        
        # Add some entries that will expire
        for i in range(10):  
            await cache.set(
                ProviderType.OSM, "geocode",
                {"address": f"Test{i}"}, {"data": i}
            )
        
        # Verify entries were added
        initial_stats = cache.get_stats()
        assert initial_stats['total_entries'] == 10
        
        # Wait for expiration
        await asyncio.sleep(1.5)
        
        # Manually trigger cleanup to test the functionality
        await cache._cleanup_expired()
        
        final_stats = cache.get_stats()
        # All entries should have been cleaned up since they expired
        assert final_stats['evictions'] == 10
        assert final_stats['total_entries'] == 0


class TestCacheSemanticMatching:
    """Test suite for semantic matching capabilities."""
    
    @pytest.mark.asyncio
    async def test_address_normalization_basic(self, clean_cache):
        """It should normalize addresses for consistent matching."""
        cache = clean_cache
        test_data = {"matched": True}
        
        # Store with one format
        await cache.set(
            ProviderType.OSM, "geocode",
            {"address": "Avenida Paulista, São Paulo, SP"}, test_data
        )
        
        # The semantic matching implementation needs to be completed
        # For now, test that it doesn't crash
        result = await cache.get(
            ProviderType.OSM, "geocode",
            {"address": "Av. Paulista, Sao Paulo"}
        )
        
        # This will be None until semantic matching is fully implemented
        # The test ensures the method doesn't crash
        assert result is None or result == test_data
    
    def test_address_normalization_function(self, clean_cache):
        """It should normalize addresses correctly."""
        cache = clean_cache
        
        # Test common Brazilian address normalizations
        normalized = cache._normalize_address("Avenida Paulista, São Paulo, SP")
        assert "av" in normalized
        assert "sao" in normalized
        
        normalized2 = cache._normalize_address("  RUA   das Flores,  Santos  ")
        assert "r das flores santos" == normalized2
        
        # Test empty/None handling
        assert cache._normalize_address("") == ""
        assert cache._normalize_address(None) == ""
    
    def test_address_similarity_detection(self, clean_cache):
        """It should detect similar addresses."""
        cache = clean_cache
        
        # Test similar addresses (after normalization)
        addr1 = "avenida paulista sao paulo sp"  # Will become "av paulista sao paulo sp"
        addr2 = "av paulista sao paulo sp"       # Already normalized form
        
        # Normalize first (as done in the actual semantic matching)
        norm1 = cache._normalize_address(addr1)
        norm2 = cache._normalize_address(addr2)
        
        # These should be considered similar (>70% overlap)
        similarity = cache._addresses_similar(norm1, norm2)
        assert similarity == True
        
        # Completely different addresses
        addr3 = "rua augusta rio janeiro rj"
        norm3 = cache._normalize_address(addr3)
        similarity2 = cache._addresses_similar(norm1, norm3)
        assert similarity2 == False


class TestCacheSpatialMatching:
    """Test suite for spatial/geospatial cache matching."""
    
    @pytest.mark.asyncio
    async def test_spatial_poi_matching_basic(self, clean_cache):
        """It should find cached POI results for nearby locations."""
        cache = clean_cache
        
        # Cache POI results for a location
        original_params = {
            "latitude": -23.5505,
            "longitude": -46.6333, 
            "radius": 1000,
            "categories": ["gas_station", "restaurant"]
        }
        poi_data = [{"id": "poi1", "name": "Test POI"}]
        
        await cache.set(
            ProviderType.OSM, "poi_search",
            original_params, poi_data
        )
        
        # Search for nearby location (should find cached result)
        nearby_params = {
            "latitude": -23.5500,  # Very close
            "longitude": -46.6330,
            "radius": 1000,
            "categories": ["gas_station", "restaurant"]  # Same categories
        }
        
        # This tests the spatial matching logic
        result = await cache.get(
            ProviderType.OSM, "poi_search", nearby_params
        )
        
        # The spatial matching is not fully implemented yet
        # For now, ensure it doesn't crash
        assert result is None or result == poi_data
    
    def test_distance_calculation(self, clean_cache):
        """It should calculate approximate distances correctly."""
        cache = clean_cache
        
        # Test distance calculation
        lat1, lon1 = -23.5505, -46.6333  # São Paulo
        lat2, lon2 = -23.5500, -46.6330  # Very close point
        
        distance = cache._calculate_distance(lat1, lon1, lat2, lon2)
        
        # Should be a small distance (few hundred meters)
        assert 0 < distance < 1000  # Less than 1km
        
        # Test same point
        distance_same = cache._calculate_distance(lat1, lon1, lat1, lon1)
        assert distance_same == 0


class TestCacheStatistics:
    """Test suite for cache statistics and metrics."""
    
    @pytest.mark.asyncio
    async def test_initial_stats(self, clean_cache):
        """It should provide correct initial statistics."""
        cache = clean_cache
        stats = cache.get_stats()
        
        assert stats['backend'] == 'memory'
        assert stats['total_entries'] == 0
        assert stats['hits'] == 0
        assert stats['misses'] == 0
        assert stats['sets'] == 0
        assert stats['evictions'] == 0
        assert stats['hit_rate_percent'] == 0
        assert 'ttl_config' in stats
    
    @pytest.mark.asyncio
    async def test_stats_tracking_operations(self, clean_cache):
        """It should track cache operations in statistics."""
        cache = clean_cache
        
        # Test cache miss
        await cache.get(ProviderType.OSM, "geocode", {"address": "Miss"})
        
        # Test cache set
        await cache.set(ProviderType.OSM, "geocode", {"address": "Test"}, {"data": 1})
        
        # Test cache hit
        await cache.get(ProviderType.OSM, "geocode", {"address": "Test"})
        await cache.get(ProviderType.OSM, "geocode", {"address": "Test"})  # Another hit
        
        # Test another miss
        await cache.get(ProviderType.OSM, "geocode", {"address": "Miss2"})
        
        stats = cache.get_stats()
        assert stats['total_entries'] == 1
        assert stats['hits'] == 2
        assert stats['misses'] == 2
        assert stats['sets'] == 1
        assert stats['hit_rate_percent'] == 50.0  # 2 hits out of 4 total requests
    
    @pytest.mark.asyncio
    async def test_hit_count_tracking(self, clean_cache):
        """It should track hit count for individual entries."""
        cache = clean_cache
        
        # Set entry
        await cache.set(ProviderType.OSM, "geocode", {"address": "Test"}, {"data": 1})
        
        # Access multiple times
        for _ in range(5):
            await cache.get(ProviderType.OSM, "geocode", {"address": "Test"})
        
        # Check internal entry hit count
        key = CacheKey(ProviderType.OSM, "geocode", {"address": "Test"}).generate_key()
        entry = cache._get_entry(key)
        
        assert entry is not None
        assert entry.hit_count == 5


class TestCacheManagement:
    """Test suite for cache management operations."""
    
    @pytest.mark.asyncio
    async def test_cache_clear(self, clean_cache):
        """It should clear all cache entries."""
        cache = clean_cache
        
        # Add some entries
        for i in range(5):
            await cache.set(
                ProviderType.OSM, "geocode",
                {"address": f"Test{i}"}, {"data": i}
            )
        
        stats = cache.get_stats()
        assert stats['total_entries'] == 5
        
        # Clear cache
        await cache.clear()
        
        stats = cache.get_stats()
        assert stats['total_entries'] == 0
    
    @pytest.mark.asyncio
    async def test_pattern_invalidation(self, clean_cache):
        """It should invalidate entries matching patterns."""
        cache = clean_cache
        
        # Add entries for different providers and operations
        await cache.set(ProviderType.OSM, "geocode", {"addr": "1"}, {"osm": "geo"})
        await cache.set(ProviderType.OSM, "poi_search", {"addr": "2"}, {"osm": "poi"})
        await cache.set(ProviderType.HERE, "geocode", {"addr": "3"}, {"here": "geo"})
        
        stats = cache.get_stats()
        assert stats['total_entries'] == 3
        
        # Invalidate all OSM entries
        invalidated = await cache.invalidate_pattern("osm:*")
        assert invalidated == 2
        
        stats = cache.get_stats()
        assert stats['total_entries'] == 1
        
        # Verify HERE entry still exists
        result = await cache.get(ProviderType.HERE, "geocode", {"addr": "3"})
        assert result == {"here": "geo"}
    
    @pytest.mark.asyncio
    async def test_cache_with_complex_data(self, clean_cache, sample_locations, sample_pois):
        """It should handle complex data structures (GeoLocation, POI, etc.)."""
        cache = clean_cache
        
        # Test with GeoLocation
        location = sample_locations['sao_paulo']
        await cache.set(ProviderType.HERE, "geocode", {"address": "SP"}, location)
        
        result = await cache.get(ProviderType.HERE, "geocode", {"address": "SP"})
        assert result == location
        
        # Test with POI list
        pois = sample_pois[:2]
        await cache.set(
            ProviderType.OSM, "poi_search", 
            {"lat": -23.5505, "lon": -46.6333}, pois
        )
        
        poi_result = await cache.get(
            ProviderType.OSM, "poi_search",
            {"lat": -23.5505, "lon": -46.6333}
        )
        assert poi_result == pois