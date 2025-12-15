"""
Unified cache system for geographic data providers.

This module provides a provider-agnostic caching layer that intelligently
stores and retrieves geographic data regardless of the source provider.
It includes features like semantic matching for geocoding, geospatial
indexing for POI searches, and configurable TTL policies.
"""

import hashlib
import json
import os
import re
import logging
import math
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Union
from dataclasses import dataclass, field
from .base import ProviderType

logger = logging.getLogger(__name__)


@dataclass
class CacheKey:
    """Structure for generating consistent cache keys."""
    provider: ProviderType
    operation: str  # geocode, route, poi_search, poi_details
    params: Dict[str, Any]
    
    def generate_key(self) -> str:
        """Generate a unique key based on provider, operation and parameters."""
        # Normalize parameters to ensure consistency
        normalized_params = self._normalize_params(self.params)
        params_json = json.dumps(normalized_params, sort_keys=True, ensure_ascii=False)
        param_hash = hashlib.md5(params_json.encode('utf-8')).hexdigest()
        
        return f"{self.provider.value}:{self.operation}:{param_hash}"
    
    def _normalize_params(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize parameters for consistent hashing."""
        normalized = {}
        
        # Keys that contain coordinates and should be rounded
        coordinate_keys = {
            'latitude', 'longitude', 'lat', 'lon',
            'origin_lat', 'origin_lon', 'dest_lat', 'dest_lon'
        }

        for key, value in params.items():
            if isinstance(value, str):
                # Normalize strings: lowercase, remove extra spaces
                normalized[key] = ' '.join(value.lower().split())
            elif isinstance(value, (int, float)):
                # Round coordinates to 3 decimal places (~111m precision)
                # This allows POIs within ~100m to share the same cache
                if key in coordinate_keys:
                    normalized[key] = round(float(value), 3)
                else:
                    normalized[key] = value
            elif isinstance(value, list):
                # Sort lists for consistency
                normalized[key] = sorted(value) if value else []
            else:
                normalized[key] = value

        return normalized


@dataclass
class CacheEntry:
    """Cache entry with metadata and expiration info."""
    key: str
    data: Any
    provider: ProviderType
    operation: str
    created_at: datetime
    expires_at: datetime
    hit_count: int = 0
    params: Dict[str, Any] = field(default_factory=dict)
    
    def is_expired(self) -> bool:
        """Check if this cache entry has expired."""
        return datetime.utcnow() > self.expires_at
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        # Convert data to JSON-serializable format
        data_serialized = self._serialize_data(self.data)
        
        return {
            'key': self.key,
            'data': data_serialized,
            'provider': self.provider.value,
            'operation': self.operation,
            'created_at': self.created_at.isoformat(),
            'expires_at': self.expires_at.isoformat(),
            'hit_count': self.hit_count,
            'params': self.params
        }
    
    def _serialize_data(self, data: Any) -> Any:
        """Convert data to JSON-serializable format."""
        if data is None:
            return None

        # Check if it's a Pydantic model (has model_dump or dict method)
        if hasattr(data, 'model_dump'):
            # Use mode='json' to ensure Enums and other types are properly serialized
            serialized = data.model_dump(mode='json')
            # Recursively serialize nested structures
            return self._serialize_data(serialized)
        elif hasattr(data, 'dict'):
            serialized = data.dict()
            return self._serialize_data(serialized)
        
        # Handle Enums (like POICategory)
        elif hasattr(data, 'value'):
            return data.value
        
        # Handle tuples (convert to lists for JSON)
        elif isinstance(data, tuple):
            return [self._serialize_data(item) for item in data]
        
        # Handle sets (convert to lists for JSON)
        elif isinstance(data, set):
            return [self._serialize_data(item) for item in sorted(data)]
        
        # Handle lists
        elif isinstance(data, list):
            return [self._serialize_data(item) for item in data]
        
        # Handle dicts
        elif isinstance(data, dict):
            return {k: self._serialize_data(v) for k, v in data.items()}
        
        # Handle bytes (convert to base64 string)
        elif isinstance(data, bytes):
            import base64
            return base64.b64encode(data).decode('utf-8')
        
        # Handle primitives (str, int, float, bool)
        elif isinstance(data, (str, int, float, bool)):
            return data
        
        # Unknown type - log warning and convert to string
        else:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Cache serialization: unknown type {type(data)}, converting to string")
            return str(data)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CacheEntry':
        """Create cache entry from dictionary."""
        # Note: data will be stored as dictionaries and reconstructed on-demand
        # by the provider when retrieved from cache
        return cls(
            key=data['key'],
            data=data['data'],  # Keep as dict, will be reconstructed by provider
            provider=ProviderType(data['provider']),
            operation=data['operation'],
            created_at=datetime.fromisoformat(data['created_at']),
            expires_at=datetime.fromisoformat(data['expires_at']),
            hit_count=data.get('hit_count', 0),
            params=data.get('params', {})
        )


class UnifiedCache:
    """
    Unified cache system for geographic data backed by PostgreSQL.
    
    Features:
    1. Provider-aware caching with namespaced keys
    2. Semantic matching for geocoding (handles similar addresses)
    3. Configurable TTL per operation type
    4. PostgreSQL storage with connection pooling
    5. Statistics tracking for monitoring
    """
    
    def __init__(self):
        """
        Initialize cache with PostgreSQL backend.

        The cache always uses PostgreSQL for persistence and reliability.
        Connection pooling is managed per event loop for async compatibility.
        """
        from .settings import get_settings

        self._pools = {}  # Event loop ID -> pool mapping
        self._pool_locks = {}  # Event loop ID -> lock mapping
        self._stats = {'hits': 0, 'misses': 0, 'sets': 0, 'evictions': 0}

        self.settings = get_settings()
        
        # TTL configuration (in seconds)
        self.ttl_config = {
            'geocode': self.settings.geo_cache_ttl_geocode,
            'reverse_geocode': self.settings.geo_cache_ttl_geocode,
            'route': self.settings.geo_cache_ttl_route,
            'poi_search': self.settings.geo_cache_ttl_poi,
            'poi_details': self.settings.geo_cache_ttl_poi_details,
        }
    
    async def _get_pool(self):
        """Get or create PostgreSQL connection pool for current event loop."""
        import asyncio
        
        try:
            # Get current event loop
            loop = asyncio.get_running_loop()
        except RuntimeError:
            # No running loop - should not happen in async context
            logger.error("No running event loop found!")
            raise
        
        # Use loop ID as key (each loop is unique per thread execution)
        loop_id = id(loop)
        
        # Check if pool exists and if its loop is still valid
        if loop_id in self._pools:
            pool = self._pools[loop_id]
            # Verify the loop is still running and not closed
            if not loop.is_closed():
                return pool
            else:
                # Loop was closed, remove stale pool
                logger.warning(f"⚠️ Loop {loop_id} was closed, removing stale pool")
                try:
                    await pool.close()
                except:
                    pass
                del self._pools[loop_id]
                if loop_id in self._pool_locks:
                    del self._pool_locks[loop_id]
        
        # Initialize lock for this loop if not exists
        if loop_id not in self._pool_locks:
            self._pool_locks[loop_id] = asyncio.Lock()
        
        # Use lock to prevent multiple initializations
        async with self._pool_locks[loop_id]:
            # Double-check after acquiring lock
            if loop_id in self._pools and not loop.is_closed():
                return self._pools[loop_id]
            
            import asyncpg
            
            logger.info(f"🔵 Creating PostgreSQL connection pool for loop {loop_id}...")
            
            self._pools[loop_id] = await asyncpg.create_pool(
                host=self.settings.postgres_host,
                port=self.settings.postgres_port,
                database=self.settings.postgres_database,
                user=self.settings.postgres_user,
                password=self.settings.postgres_password,
                min_size=self.settings.postgres_pool_min_size,
                max_size=self.settings.postgres_pool_max_size,
                command_timeout=60
            )
            
            logger.info(f"✅ PostgreSQL connection pool created for loop {loop_id}: {self.settings.postgres_host}:{self.settings.postgres_port}/{self.settings.postgres_database}")

        return self._pools[loop_id]

    async def get(self, provider: ProviderType, operation: str, params: Dict[str, Any]) -> Optional[Any]:
        """
        Retrieve data from cache with fallback to similar entries.
        
        Args:
            provider: Provider that would generate this data
            operation: Operation type (geocode, route, etc.)
            params: Operation parameters
            
        Returns:
            Cached data if found, None otherwise
        """
        # Generate primary key
        cache_key = CacheKey(provider=provider, operation=operation, params=params)
        normalized_params = cache_key._normalize_params(params)
        primary_key = cache_key.generate_key()
        
        pool = await self._get_pool()
        
        # Try exact match first - simple read
        row = None
        
        try:
            # Use timeout to acquire connection
            async with pool.acquire(timeout=10) as conn:
                row = await conn.fetchrow(
                    """
                    SELECT data, params
                    FROM cache_entries
                    WHERE key = $1 AND expires_at > NOW()
                    """,
                    primary_key
                )
        except Exception as e:
            logger.error(f"❌ get({operation}): Error during cache read: {e}", exc_info=True)
            # Return None on cache error, don't fail the operation
            return None
        
        if row:
            self._stats['hits'] += 1
            logger.debug(f"Cache hit for {operation} with provider {provider.value}")
            
            # Parse JSONB data
            data = row['data']
            if isinstance(data, str):
                data = json.loads(data)
            
            # Reconstruct Pydantic models
            return self._reconstruct_data(data, operation)
        
        # For geocoding, try semantic matching
        if operation == "geocode" and "address" in params:
            similar_entry = await self._find_similar_geocode(params["address"])
            if similar_entry:
                self._stats['hits'] += 1
                logger.debug(f"Cache hit via semantic matching for geocode: {params['address']}")
                data = similar_entry['data']
                if isinstance(data, str):
                    data = json.loads(data)
                return self._reconstruct_data(data, operation)
        
        # For POI searches, try spatial matching
        elif operation == "poi_search" and all(k in params for k in ['latitude', 'longitude', 'radius']):
            spatial_entry = await self._find_spatial_poi_match(params)
            if spatial_entry:
                self._stats['hits'] += 1
                logger.debug(f"Cache hit via spatial matching for POI search")
                data = spatial_entry['data']
                if isinstance(data, str):
                    data = json.loads(data)
                return self._reconstruct_data(data, operation)
        
        self._stats['misses'] += 1
        logger.debug(f"Cache miss for {operation} with provider {provider.value}")
        return None

    def _reconstruct_data(self, data: Any, operation: str) -> Any:
        """Reconstruct Pydantic models from dictionaries loaded from cache."""
        if data is None:
            return None
        
        # Import models here to avoid circular imports
        from .models import GeoLocation, Route, POI
        
        # For reverse_geocode and geocode operations, reconstruct GeoLocation
        if operation in ["reverse_geocode", "geocode"]:
            if isinstance(data, dict):
                return GeoLocation(**data)
            return data
        
        # For route operations, reconstruct Route
        elif operation == "route":
            if isinstance(data, dict):
                return Route(**data)
            return data
        
        # For poi_search, reconstruct list of POIs
        elif operation == "poi_search":
            if isinstance(data, list):
                return [POI(**item) if isinstance(item, dict) else item for item in data]
            return data
        
        # For poi_details, reconstruct POI
        elif operation == "poi_details":
            if isinstance(data, dict):
                return POI(**data)
            return data
        
        # Return as-is for unknown operations
        return data
    
    async def set(self, provider: ProviderType, operation: str, params: Dict[str, Any], data: Any) -> None:
        """
        Store data in cache with appropriate TTL.
        
        Args:
            provider: Provider that generated this data
            operation: Operation type
            params: Operation parameters
            data: Data to cache
        """
        cache_key = CacheKey(provider=provider, operation=operation, params=params)
        normalized_params = cache_key._normalize_params(params)
        key = cache_key.generate_key()
        
        ttl = self.ttl_config.get(operation, 3600)  # Default 1 hour
        
        # Serialize data
        entry = CacheEntry(
            key=key,
            data=data,
            provider=provider,
            operation=operation,
            created_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(seconds=ttl),
            hit_count=0,
            params=normalized_params  # Use normalized params for consistency
        )
        
        data_serialized = entry._serialize_data(data)
        
        pool = await self._get_pool()
        
        # Use a single transaction to avoid concurrency issues
        try:
            async with pool.acquire() as conn:
                async with conn.transaction():
                    # Convert to JSON strings for JSONB columns
                    await conn.execute(
                        """
                        INSERT INTO cache_entries (key, data, provider, operation, created_at, expires_at, hit_count, params)
                        VALUES ($1, $2::jsonb, $3, $4, $5, $6, $7, $8::jsonb)
                        ON CONFLICT (key) DO UPDATE SET
                            data = EXCLUDED.data,
                            expires_at = EXCLUDED.expires_at,
                            hit_count = 0
                        """,
                        key,
                        json.dumps(data_serialized),
                        provider.value,
                        operation,
                        entry.created_at,
                        entry.expires_at,
                        0,
                        json.dumps(normalized_params)  # Store normalized params
                    )
            
            self._stats['sets'] += 1
            logger.debug(f"Cached {operation} data for provider {provider.value}, expires at {entry.expires_at}")
            
        except Exception as e:
            logger.error(f"❌ set({operation}): Error caching data: {e}", exc_info=True)
            # Don't fail the operation if cache fails
            return
        
        # Clean up expired entries periodically
        if self._stats['sets'] % 100 == 0:  # Every 100 sets
            # Run cleanup in background to avoid blocking
            import asyncio
            asyncio.create_task(self._cleanup_expired())
    
    async def _find_similar_geocode(self, address: str) -> Optional[Dict[str, Any]]:
        """
        Find similar geocoding entries using semantic matching.
        
        This method normalizes addresses and looks for similar cached results.
        For example, "Av. Paulista, São Paulo" should match "Avenida Paulista, SP".
        """
        normalized_address = self._normalize_address(address)
        
        pool = await self._get_pool()
        
        # Look through geocoding entries for similar addresses - simple read
        rows = None
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT key, data, params
                FROM cache_entries
                WHERE operation = 'geocode'
                AND expires_at > NOW()
                AND params->>'address' IS NOT NULL
                """
            )
        
        for row in rows:
            # Parse params if needed
            params_data = row['params']
            if isinstance(params_data, str):
                params_data = json.loads(params_data)
            
            cached_address = self._normalize_address(params_data.get('address', ''))
            if self._addresses_similar(normalized_address, cached_address):
                return dict(row)
        
        return None
    
    async def _find_spatial_poi_match(self, params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Find POI search results for nearby locations.
        
        If we have cached POI results for a nearby location with similar search criteria,
        we can reuse those results.
        """
        target_lat = params['latitude']
        target_lon = params['longitude']
        target_radius = params['radius']
        target_categories = set(params.get('categories', []))
        
        pool = await self._get_pool()
        
        # Search for nearby POI cache entries - simple read
        rows = None
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT key, data, params
                FROM cache_entries
                WHERE operation = 'poi_search'
                AND expires_at > NOW()
                AND params->>'latitude' IS NOT NULL
                AND params->>'longitude' IS NOT NULL
                AND params->>'radius' IS NOT NULL
                """
            )
        
        for row in rows:
            try:
                # Parse params if needed
                params_data = row['params']
                if isinstance(params_data, str):
                    params_data = json.loads(params_data)
                
                cached_lat = float(params_data.get('latitude', 0))
                cached_lon = float(params_data.get('longitude', 0))
                cached_radius = float(params_data.get('radius', 0))
                cached_categories = set(params_data.get('categories', []))
                
                # Check if locations are close enough
                distance = self._calculate_distance(target_lat, target_lon, cached_lat, cached_lon)
                
                # If search areas overlap significantly and categories match
                if (distance < (target_radius + cached_radius) / 2 and
                    target_categories == cached_categories):
                    return dict(row)
            except (ValueError, KeyError):
                continue
        
        return None
    
    def _normalize_address(self, address: str) -> str:
        """Normalize address for comparison."""
        if not address:
            return ""
        
        # Common Brazilian address normalizations
        replacements = {
            r'\bavenida\b': 'av',
            r'\brua\b': 'r',
            r'\spraça\b': 'pca',
            r'\bsão\b': 'sao',
            r'\bsanta\b': 'santa',
            r'\bsanto\b': 'santo',
            r'\bestrada\b': 'estr',
            r'\brodovia\b': 'rod',
            r'\balameda\b': 'al',
        }
        
        normalized = address.lower().strip()
        
        # Apply replacements
        for pattern, replacement in replacements.items():
            normalized = re.sub(pattern, replacement, normalized)
        
        # Remove extra spaces and punctuation
        normalized = re.sub(r'[^\w\s]', ' ', normalized)
        normalized = ' '.join(normalized.split())
        
        return normalized
    
    def _addresses_similar(self, addr1: str, addr2: str) -> bool:
        """Check if two normalized addresses are similar."""
        if not addr1 or not addr2:
            return False
        
        # Simple similarity check: common words
        words1 = set(addr1.split())
        words2 = set(addr2.split())
        
        if not words1 or not words2:
            return False
        
        # Calculate Jaccard similarity
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        
        similarity = len(intersection) / len(union) if union else 0
        
        # Consider similar if > 70% overlap
        return similarity > 0.7
    
    def _calculate_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate approximate distance between two points in meters."""
        import math
        
        # Simplified distance calculation for cache matching
        # This is good enough for determining if POI search areas overlap
        lat_diff = abs(lat1 - lat2)
        lon_diff = abs(lon1 - lon2)
        
        # Rough conversion: 1 degree ≈ 111km at equator
        lat_meters = lat_diff * 111000
        lon_meters = lon_diff * 111000 * abs(math.cos(math.radians(lat1)))
        
        return (lat_meters ** 2 + lon_meters ** 2) ** 0.5
    
    async def _cleanup_expired(self) -> None:
        """Remove expired entries from cache."""
        pool = await self._get_pool()
        
        async with pool.acquire() as conn:
            # Use transaction for DELETE operation
            async with conn.transaction():
                result = await conn.execute(
                    "DELETE FROM cache_entries WHERE expires_at < NOW()"
                )
            
            # Extract number of deleted rows
            deleted_count = int(result.split()[-1]) if result else 0
            
            if deleted_count > 0:
                self._stats['evictions'] += deleted_count
                logger.debug(f"Cleaned up {deleted_count} expired cache entries")
    async def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        pool = await self._get_pool()
        
        async with pool.acquire() as conn:
            total_entries = await conn.fetchval(
                "SELECT COUNT(*) FROM cache_entries WHERE expires_at > NOW()"
            )
        
        total_requests = self._stats['hits'] + self._stats['misses']
        hit_rate = (self._stats['hits'] / total_requests * 100) if total_requests > 0 else 0
        
        return {
            'backend': 'postgres',
            'total_entries': total_entries,
            'hits': self._stats['hits'],
            'misses': self._stats['misses'],
            'sets': self._stats['sets'],
            'evictions': self._stats['evictions'],
            'hit_rate_percent': round(hit_rate, 2),
            'ttl_config': self.ttl_config
        }
    
    async def clear(self) -> None:
        """Clear all cache entries."""
        pool = await self._get_pool()
        
        async with pool.acquire() as conn:
            await conn.execute("DELETE FROM cache_entries")
        
        logger.info("Cache cleared")
    
    async def invalidate_pattern(self, pattern: str) -> int:
        """
        Invalidate cache entries matching a pattern.
        
        Args:
            pattern: Pattern to match (supports provider:operation:* syntax)
            
        Returns:
            Number of entries invalidated
        """
        pool = await self._get_pool()
        
        # Convert fnmatch pattern to SQL LIKE pattern
        sql_pattern = pattern.replace('*', '%').replace('?', '_')
        
        async with pool.acquire() as conn:
            result = await conn.execute(
                "DELETE FROM cache_entries WHERE key LIKE $1",
                sql_pattern
            )
            
            deleted_count = int(result.split()[-1]) if result else 0
        
        logger.info(f"Invalidated {deleted_count} cache entries matching pattern: {pattern}")
        return deleted_count
    
    async def close(self) -> None:
        """Close all database connection pools from all threads."""
        import threading
        
        for thread_id, pool in list(self._pools.items()):
            try:
                await pool.close()
                logger.info(f"PostgreSQL connection pool closed for thread {thread_id}")
            except Exception as e:
                logger.error(f"Error closing pool for thread {thread_id}: {e}")
        
        self._pools.clear()
        self._pool_locks.clear()
        logger.info("All PostgreSQL connection pools closed")


# Import math for distance calculation
import math