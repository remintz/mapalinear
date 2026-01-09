"""
RouteSegment repository for database operations.
"""
from typing import Dict, List, Optional
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from api.database.models.route_segment import RouteSegment
from api.database.repositories.base import BaseRepository


class RouteSegmentRepository(BaseRepository[RouteSegment]):
    """Repository for RouteSegment model operations."""

    def __init__(self, session: AsyncSession):
        """Initialize with session."""
        super().__init__(session, RouteSegment)

    async def get_by_hash(self, segment_hash: str) -> Optional[RouteSegment]:
        """
        Get a segment by its hash.

        Args:
            segment_hash: MD5 hash of segment start/end coordinates

        Returns:
            RouteSegment instance or None if not found
        """
        result = await self.session.execute(
            select(RouteSegment).where(RouteSegment.segment_hash == segment_hash)
        )
        return result.scalar_one_or_none()

    async def bulk_get_by_hashes(
        self, hashes: List[str]
    ) -> Dict[str, RouteSegment]:
        """
        Get multiple segments by their hashes.

        Args:
            hashes: List of segment hashes

        Returns:
            Dictionary mapping hash -> RouteSegment
        """
        if not hashes:
            return {}

        result = await self.session.execute(
            select(RouteSegment).where(RouteSegment.segment_hash.in_(hashes))
        )
        segments = result.scalars().all()
        return {s.segment_hash: s for s in segments}

    async def get_with_pois(self, segment_id: UUID) -> Optional[RouteSegment]:
        """
        Get a segment with its POIs eagerly loaded.

        Args:
            segment_id: Segment UUID

        Returns:
            RouteSegment with segment_pois relationship loaded
        """
        result = await self.session.execute(
            select(RouteSegment)
            .where(RouteSegment.id == segment_id)
            .options(selectinload(RouteSegment.segment_pois))
        )
        return result.scalar_one_or_none()

    async def increment_usage_count(self, segment_id: UUID) -> None:
        """
        Increment the usage count for a segment.

        Args:
            segment_id: Segment UUID
        """
        await self.session.execute(
            update(RouteSegment)
            .where(RouteSegment.id == segment_id)
            .values(usage_count=RouteSegment.usage_count + 1)
        )
        await self.session.flush()

    async def bulk_increment_usage(self, segment_ids: List[UUID]) -> None:
        """
        Increment usage count for multiple segments.

        Args:
            segment_ids: List of segment UUIDs
        """
        if not segment_ids:
            return

        await self.session.execute(
            update(RouteSegment)
            .where(RouteSegment.id.in_(segment_ids))
            .values(usage_count=RouteSegment.usage_count + 1)
        )
        await self.session.flush()

    async def find_by_road_name(
        self, road_name: str, limit: int = 100
    ) -> List[RouteSegment]:
        """
        Find segments by road name.

        Args:
            road_name: Name of the road
            limit: Maximum number of results

        Returns:
            List of matching segments
        """
        result = await self.session.execute(
            select(RouteSegment)
            .where(RouteSegment.road_name == road_name)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_segments_needing_poi_search(
        self, limit: int = 100
    ) -> List[RouteSegment]:
        """
        Get segments that need POI search (pois_fetched_at is None).

        Args:
            limit: Maximum number of results

        Returns:
            List of segments needing POI search
        """
        result = await self.session.execute(
            select(RouteSegment)
            .where(RouteSegment.pois_fetched_at.is_(None))
            .limit(limit)
        )
        return list(result.scalars().all())

    async def mark_pois_fetched(self, segment_id: UUID) -> None:
        """
        Mark a segment as having its POIs fetched.

        Args:
            segment_id: Segment UUID
        """
        from datetime import datetime

        await self.session.execute(
            update(RouteSegment)
            .where(RouteSegment.id == segment_id)
            .values(pois_fetched_at=datetime.utcnow())
        )
        await self.session.flush()

    async def decrement_usage_count(self, segment_id: UUID) -> None:
        """
        Decrement the usage count for a segment.

        Args:
            segment_id: Segment UUID
        """
        await self.session.execute(
            update(RouteSegment)
            .where(RouteSegment.id == segment_id)
            .where(RouteSegment.usage_count > 0)  # Prevent negative counts
            .values(usage_count=RouteSegment.usage_count - 1)
        )
        await self.session.flush()

    async def bulk_decrement_usage(self, segment_ids: List[UUID]) -> None:
        """
        Decrement usage count for multiple segments.

        Args:
            segment_ids: List of segment UUIDs
        """
        if not segment_ids:
            return

        await self.session.execute(
            update(RouteSegment)
            .where(RouteSegment.id.in_(segment_ids))
            .where(RouteSegment.usage_count > 0)  # Prevent negative counts
            .values(usage_count=RouteSegment.usage_count - 1)
        )
        await self.session.flush()

    async def find_orphan_segment_ids(self) -> List[UUID]:
        """
        Find segment IDs that are not referenced by any MapSegment.

        Returns:
            List of orphan segment UUIDs
        """
        from sqlalchemy import func
        from api.database.models.map_segment import MapSegment

        # Subquery to get all segment IDs that have at least one MapSegment
        referenced_subquery = select(MapSegment.segment_id).distinct()

        # Find segments not in the referenced set
        result = await self.session.execute(
            select(RouteSegment.id).where(~RouteSegment.id.in_(referenced_subquery))
        )
        return list(result.scalars().all())

    async def count_orphan_segments(self) -> int:
        """
        Count segments that are not referenced by any MapSegment.

        Returns:
            Number of orphan segments
        """
        from sqlalchemy import func
        from api.database.models.map_segment import MapSegment

        referenced_subquery = select(MapSegment.segment_id).distinct()

        result = await self.session.execute(
            select(func.count(RouteSegment.id))
            .where(~RouteSegment.id.in_(referenced_subquery))
        )
        return result.scalar() or 0

    async def delete_orphan_segments(self) -> int:
        """
        Delete segments that are not referenced by any MapSegment.

        This will also cascade delete associated SegmentPOIs.

        Returns:
            Number of segments deleted
        """
        from sqlalchemy import delete
        from api.database.models.map_segment import MapSegment

        # Get orphan IDs first
        orphan_ids = await self.find_orphan_segment_ids()

        if not orphan_ids:
            return 0

        # Delete orphan segments (SegmentPOIs will cascade delete)
        result = await self.session.execute(
            delete(RouteSegment).where(RouteSegment.id.in_(orphan_ids))
        )

        return result.rowcount

    async def get_statistics(self) -> dict:
        """
        Get statistics about route segments.

        Returns:
            Dictionary with statistics
        """
        from sqlalchemy import func

        # Total count
        total_result = await self.session.execute(
            select(func.count(RouteSegment.id))
        )
        total = total_result.scalar() or 0

        # Segments with POIs fetched
        with_pois_result = await self.session.execute(
            select(func.count(RouteSegment.id))
            .where(RouteSegment.pois_fetched_at.isnot(None))
        )
        with_pois = with_pois_result.scalar() or 0

        # Total usage count
        usage_result = await self.session.execute(
            select(func.sum(RouteSegment.usage_count))
        )
        total_usage = usage_result.scalar() or 0

        # Total length
        length_result = await self.session.execute(
            select(func.sum(RouteSegment.length_km))
        )
        total_length_km = float(length_result.scalar() or 0)

        # Orphan segments count
        orphan_count = await self.count_orphan_segments()

        return {
            "total_segments": total,
            "segments_with_pois": with_pois,
            "total_usage": total_usage,
            "total_length_km": total_length_km,
            "orphan_segments": orphan_count,
        }
