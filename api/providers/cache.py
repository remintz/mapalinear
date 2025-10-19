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

        for key, value in params.items():
            if isinstance(value, str):
                # Normalize strings: lowercase, remove extra spaces
                normalized[key] = ' '.join(value.lower().split())
            elif isinstance(value, (int, float)):
                # Round coordinates to 3 decimal places (~111m precision)
                # This allows POIs within ~100m to share the same cache
                if key in ('latitude', 'longitude', 'lat', 'lon'):
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
            return data.model_dump()
        elif hasattr(data, 'dict'):
            return data.dict()
        
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
    Unified cache system for geographic data.
    
    Features:
    1. Provider-aware caching with namespaced keys
    2. Semantic matching for geocoding (handles similar addresses)
    3. Configurable TTL per operation type
    4. In-memory storage with optional persistence
    5. Statistics tracking for monitoring
    """
    
    def __init__(self, backend: str = "memory"):
        """
        Initialize the unified cache.
        
        Args:
            backend: Cache backend type ("memory" or "redis" in future)
        """
        self.backend = backend
        self._cache: Dict[str, CacheEntry] = {}
        self._stats = {
            'hits': 0,
            'misses': 0,
            'sets': 0,
            'evictions': 0
        }
        
        # Import settings here to avoid circular imports
        from .settings import get_settings
        settings = get_settings()
        
        # TTL configuration from Pydantic Settings
        self.ttl_config = {
            "geocode": settings.geo_cache_ttl_geocode,
            "reverse_geocode": settings.geo_cache_ttl_geocode,
            "route": settings.geo_cache_ttl_route,
            "poi_search": settings.geo_cache_ttl_poi,
            "poi_details": settings.geo_cache_ttl_poi_details
        }
        
        logger.info(f"Initialized unified cache with backend: {backend}")

        
        # Persistent cache configuration
        self.cache_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'cache')
        self.cache_file = os.path.join(self.cache_dir, 'unified_cache.json')
        
        # Ensure cache directory exists
        os.makedirs(self.cache_dir, exist_ok=True)
        
        # Load existing cache from disk if available
        self._load_from_file()
    
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
        
        # Try exact match first
        entry = self._get_entry(primary_key)
        if entry and not entry.is_expired():
            entry.hit_count += 1
            self._stats['hits'] += 1
            logger.debug(f"Cache hit for {operation} with provider {provider.value}")
            # Reconstruct Pydantic models if data came from disk
            return self._reconstruct_data(entry.data, operation)
        
        # Special logging for reverse_geocode when cache miss
        if operation == "reverse_geocode":
            poi_name = params.get("poi_name")
            logger.info(f"🔍 Cache MISS for reverse_geocode")
            logger.info(f"🔍 Original params: {params}")
            logger.info(f"🔍 Normalized params: {normalized_params}")
            logger.info(f"🔍 Generated key: {primary_key}")
            
            # Find all reverse_geocode entries with same poi_name
            if poi_name:
                matching_entries = []
                for key, entry in self._cache.items():
                    if entry.operation == "reverse_geocode" and entry.params.get("poi_name") == poi_name:
                        matching_entries.append({
                            "key": key,
                            "params": entry.params,
                            "is_expired": entry.is_expired(),
                            "created_at": entry.created_at.isoformat()
                        })
                
                if matching_entries:
                    logger.info(f"🔍 Found {len(matching_entries)} cache entries with same POI name '{poi_name}':")
                    for i, match in enumerate(matching_entries, 1):
                        logger.info(f"🔍   Entry {i}:")
                        logger.info(f"🔍     Key: {match['key']}")
                        logger.info(f"🔍     Params: {match['params']}")
                        logger.info(f"🔍     Expired: {match['is_expired']}")
                        logger.info(f"🔍     Created: {match['created_at']}")
                else:
                    logger.info(f"🔍 No cache entries found with POI name '{poi_name}'")
        
        # For geocoding, try semantic matching
        if operation == "geocode" and "address" in params:
            similar_entry = await self._find_similar_geocode(params["address"])
            if similar_entry and not similar_entry.is_expired():
                similar_entry.hit_count += 1
                self._stats['hits'] += 1
                logger.debug(f"Cache hit via semantic matching for geocode: {params['address']}")
                return self._reconstruct_data(similar_entry.data, operation)
        
        # For POI searches, try spatial matching
        elif operation == "poi_search" and all(k in params for k in ['latitude', 'longitude', 'radius']):
            spatial_entry = await self._find_spatial_poi_match(params)
            if spatial_entry and not spatial_entry.is_expired():
                spatial_entry.hit_count += 1
                self._stats['hits'] += 1
                logger.debug(f"Cache hit via spatial matching for POI search")
                return self._reconstruct_data(spatial_entry.data, operation)
        
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
        expires_at = datetime.utcnow() + timedelta(seconds=ttl)
        
        # Special logging for reverse_geocode
        if operation == "reverse_geocode":
            logger.info(f"💾 Storing reverse_geocode in cache")
            logger.info(f"💾 Original params: {params}")
            logger.info(f"💾 Normalized params: {normalized_params}")
            logger.info(f"💾 Generated key: {key}")
            logger.info(f"💾 TTL: {ttl}s, expires: {expires_at.isoformat()}")
        
        entry = CacheEntry(
            key=key,
            data=data,
            provider=provider,
            operation=operation,
            created_at=datetime.utcnow(),
            expires_at=expires_at,
            hit_count=0,
            params=params
        )
        
        self._cache[key] = entry
        self._stats['sets'] += 1
        
        logger.debug(f"Cached {operation} data for provider {provider.value}, expires at {expires_at}")
        
        # Clean up expired entries periodically
        if len(self._cache) % 100 == 0:  # Every 100 sets
            await self._cleanup_expired()
    
    def _get_entry(self, key: str) -> Optional[CacheEntry]:
        """Get cache entry by key."""
        return self._cache.get(key)
    
    async def _find_similar_geocode(self, address: str) -> Optional[CacheEntry]:
        """
        Find similar geocoding entries using semantic matching.
        
        This method normalizes addresses and looks for similar cached results.
        For example, "Av. Paulista, São Paulo" should match "Avenida Paulista, SP".
        """
        normalized_address = self._normalize_address(address)
        
        # Look through geocoding entries for similar addresses
        for entry in self._cache.values():
            if entry.operation != "geocode" or entry.is_expired():
                continue
            
            if "address" not in entry.params:
                continue
            
            cached_address = self._normalize_address(entry.params["address"])
            if self._addresses_similar(normalized_address, cached_address):
                logger.debug(f"Found similar address: '{address}' ~ '{entry.params['address']}'")
                return entry
        
        return None
    
    async def _find_spatial_poi_match(self, params: Dict[str, Any]) -> Optional[CacheEntry]:
        """
        Find POI search results for nearby locations.
        
        If we have cached POI results for a nearby location with similar search criteria,
        we can reuse those results.
        """
        target_lat = params['latitude']
        target_lon = params['longitude']
        target_radius = params['radius']
        target_categories = set(params.get('categories', []))
        
        # Search for nearby POI cache entries
        for entry in self._cache.values():
            if entry.operation != "poi_search" or entry.is_expired():
                continue
            
            if not all(k in entry.params for k in ['latitude', 'longitude', 'radius']):
                continue
            
            cached_lat = entry.params['latitude']
            cached_lon = entry.params['longitude']
            cached_radius = entry.params['radius']
            cached_categories = set(entry.params.get('categories', []))
            
            # Check if locations are close enough
            distance = self._calculate_distance(target_lat, target_lon, cached_lat, cached_lon)
            
            # If search areas overlap significantly and categories match
            if (distance < (target_radius + cached_radius) / 2 and 
                target_categories == cached_categories):
                logger.debug(f"Found spatial POI match at distance {distance}m")
                return entry
        
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
        before_count = len(self._cache)
        current_time = datetime.utcnow()
        
        expired_keys = [
            key for key, entry in self._cache.items()
            if entry.expires_at < current_time
        ]
        
        for key in expired_keys:
            del self._cache[key]
            self._stats['evictions'] += 1
        
        if expired_keys:
            logger.debug(f"Cleaned up {len(expired_keys)} expired cache entries")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total_requests = self._stats['hits'] + self._stats['misses']
        hit_rate = (self._stats['hits'] / total_requests * 100) if total_requests > 0 else 0
        
        return {
            'backend': self.backend,
            'total_entries': len(self._cache),
            'hits': self._stats['hits'],
            'misses': self._stats['misses'],
            'sets': self._stats['sets'],
            'evictions': self._stats['evictions'],
            'hit_rate_percent': round(hit_rate, 2),
            'ttl_config': self.ttl_config
        }
    
    async def clear(self) -> None:
        """Clear all cache entries."""
        self._cache.clear()
        logger.info("Cache cleared")
    
    async def invalidate_pattern(self, pattern: str) -> int:
        """
        Invalidate cache entries matching a pattern.
        
        Args:
            pattern: Pattern to match (supports provider:operation:* syntax)
            
        Returns:
            Number of entries invalidated
        """
        import fnmatch
        
        matching_keys = [
            key for key in self._cache.keys()
            if fnmatch.fnmatch(key, pattern)
        ]
        
        for key in matching_keys:
            del self._cache[key]
        
        logger.info(f"Invalidated {len(matching_keys)} cache entries matching pattern: {pattern}")
        return len(matching_keys)

    
    def _load_from_file(self) -> None:
        """Load cache from persistent storage on disk."""
        if not os.path.exists(self.cache_file):
            logger.info("No persistent cache file found, starting with empty cache")
            return
        
        try:
            with open(self.cache_file, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)
            
            # Reconstruct cache entries from stored data
            loaded_count = 0
            expired_count = 0
            
            for entry_dict in cache_data.get('entries', []):
                try:
                    entry = CacheEntry.from_dict(entry_dict)
                    
                    # Skip expired entries
                    if entry.is_expired():
                        expired_count += 1
                        continue
                    
                    self._cache[entry.key] = entry
                    loaded_count += 1
                    
                except Exception as e:
                    logger.warning(f"Failed to load cache entry: {e}")
                    continue
            
            # Load stats if available
            if 'stats' in cache_data:
                self._stats = cache_data['stats']
            
            logger.info(f"Loaded {loaded_count} cache entries from disk ({expired_count} expired entries skipped)")
            
        except Exception as e:
            logger.error(f"Error loading cache from file: {e}")
            logger.info("Starting with empty cache")
    
    def save_to_file(self) -> None:
        """Save cache to persistent storage on disk."""
        try:
            # Clean up expired entries before saving
            current_time = datetime.utcnow()
            valid_entries = [
                entry.to_dict()
                for entry in self._cache.values()
                if not entry.is_expired()
            ]
            
            cache_data = {
                'version': '1.0',
                'saved_at': datetime.utcnow().isoformat(),
                'backend': self.backend,
                'stats': self._stats,
                'entries': valid_entries
            }
            
            # Write to temporary file first, then rename (atomic operation)
            temp_file = self.cache_file + '.tmp'
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, indent=2, ensure_ascii=False)
            
            # Atomic rename
            os.replace(temp_file, self.cache_file)
            
            logger.info(f"Saved {len(valid_entries)} cache entries to disk at {self.cache_file}")
            
        except Exception as e:
            logger.error(f"Error saving cache to file: {e}")


# Import math for distance calculation
import math