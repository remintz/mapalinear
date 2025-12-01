"""
Cache repository for database operations.
"""
from datetime import datetime
from typing import Dict, List, Optional

from sqlalchemy import delete, select, update, func
from sqlalchemy.ext.asyncio import AsyncSession

from api.database.models.cache import CacheEntry


class CacheRepository:
    """
    Repository for CacheEntry model operations.

    Unlike other repositories, CacheEntry uses a string key as primary key
    rather than UUID, so this doesn't extend BaseRepository.
    """

    def __init__(self, session: AsyncSession):
        """Initialize with session."""
        self.session = session

    async def get_by_key(self, key: str) -> Optional[CacheEntry]:
        """
        Get a cache entry by key.

        Args:
            key: Cache key

        Returns:
            CacheEntry instance or None if not found
        """
        result = await self.session.execute(
            select(CacheEntry).where(CacheEntry.key == key)
        )
        return result.scalar_one_or_none()

    async def get_valid_by_key(self, key: str) -> Optional[CacheEntry]:
        """
        Get a non-expired cache entry by key.

        Args:
            key: Cache key

        Returns:
            CacheEntry instance or None if not found or expired
        """
        now = datetime.now()
        result = await self.session.execute(
            select(CacheEntry).where(
                CacheEntry.key == key,
                CacheEntry.expires_at > now
            )
        )
        return result.scalar_one_or_none()

    async def set(self, entry: CacheEntry) -> CacheEntry:
        """
        Create or update a cache entry.

        Args:
            entry: CacheEntry instance

        Returns:
            Created/updated CacheEntry instance
        """
        # Use merge for upsert behavior
        merged = await self.session.merge(entry)
        await self.session.flush()
        return merged

    async def delete_by_key(self, key: str) -> bool:
        """
        Delete a cache entry by key.

        Args:
            key: Cache key

        Returns:
            True if deleted, False if not found
        """
        result = await self.session.execute(
            delete(CacheEntry).where(CacheEntry.key == key)
        )
        return result.rowcount > 0

    async def increment_hit_count(self, key: str) -> None:
        """
        Increment the hit count for a cache entry.

        Args:
            key: Cache key
        """
        await self.session.execute(
            update(CacheEntry)
            .where(CacheEntry.key == key)
            .values(hit_count=CacheEntry.hit_count + 1)
        )

    async def delete_expired(self) -> int:
        """
        Delete all expired cache entries.

        Returns:
            Number of deleted entries
        """
        now = datetime.now()
        result = await self.session.execute(
            delete(CacheEntry).where(CacheEntry.expires_at < now)
        )
        return result.rowcount

    async def delete_by_operation(self, operation: str) -> int:
        """
        Delete all cache entries for a specific operation.

        Args:
            operation: Operation type (e.g., 'geocode', 'route')

        Returns:
            Number of deleted entries
        """
        result = await self.session.execute(
            delete(CacheEntry).where(CacheEntry.operation == operation)
        )
        return result.rowcount

    async def delete_by_provider(self, provider: str) -> int:
        """
        Delete all cache entries for a specific provider.

        Args:
            provider: Provider name (e.g., 'osm', 'here')

        Returns:
            Number of deleted entries
        """
        result = await self.session.execute(
            delete(CacheEntry).where(CacheEntry.provider == provider)
        )
        return result.rowcount

    async def delete_all(self) -> int:
        """
        Delete all cache entries.

        Returns:
            Number of deleted entries
        """
        result = await self.session.execute(delete(CacheEntry))
        return result.rowcount

    async def find_by_operation(
        self, operation: str, limit: int = 100
    ) -> List[CacheEntry]:
        """
        Find cache entries by operation type.

        Args:
            operation: Operation type
            limit: Maximum number of results

        Returns:
            List of cache entries
        """
        now = datetime.now()
        result = await self.session.execute(
            select(CacheEntry)
            .where(
                CacheEntry.operation == operation,
                CacheEntry.expires_at > now
            )
            .limit(limit)
        )
        return list(result.scalars().all())

    async def find_by_provider(
        self, provider: str, limit: int = 100
    ) -> List[CacheEntry]:
        """
        Find cache entries by provider.

        Args:
            provider: Provider name
            limit: Maximum number of results

        Returns:
            List of cache entries
        """
        now = datetime.now()
        result = await self.session.execute(
            select(CacheEntry)
            .where(
                CacheEntry.provider == provider,
                CacheEntry.expires_at > now
            )
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_stats(self) -> Dict[str, any]:
        """
        Get cache statistics.

        Returns:
            Dictionary with cache statistics
        """
        now = datetime.now()

        # Total entries
        total_result = await self.session.execute(
            select(func.count()).select_from(CacheEntry)
        )
        total_entries = total_result.scalar_one()

        # Valid (non-expired) entries
        valid_result = await self.session.execute(
            select(func.count())
            .select_from(CacheEntry)
            .where(CacheEntry.expires_at > now)
        )
        valid_entries = valid_result.scalar_one()

        # Expired entries
        expired_entries = total_entries - valid_entries

        # Entries by operation
        by_operation_result = await self.session.execute(
            select(CacheEntry.operation, func.count())
            .group_by(CacheEntry.operation)
        )
        by_operation = dict(by_operation_result.all())

        # Entries by provider
        by_provider_result = await self.session.execute(
            select(CacheEntry.provider, func.count())
            .group_by(CacheEntry.provider)
        )
        by_provider = dict(by_provider_result.all())

        # Total hits
        hits_result = await self.session.execute(
            select(func.sum(CacheEntry.hit_count))
        )
        total_hits = hits_result.scalar_one() or 0

        return {
            "total_entries": total_entries,
            "valid_entries": valid_entries,
            "expired_entries": expired_entries,
            "total_hits": total_hits,
            "by_operation": by_operation,
            "by_provider": by_provider,
        }

    async def count(self) -> int:
        """
        Count all cache entries.

        Returns:
            Total number of entries
        """
        result = await self.session.execute(
            select(func.count()).select_from(CacheEntry)
        )
        return result.scalar_one()

    async def count_valid(self) -> int:
        """
        Count non-expired cache entries.

        Returns:
            Number of valid entries
        """
        now = datetime.now()
        result = await self.session.execute(
            select(func.count())
            .select_from(CacheEntry)
            .where(CacheEntry.expires_at > now)
        )
        return result.scalar_one()
