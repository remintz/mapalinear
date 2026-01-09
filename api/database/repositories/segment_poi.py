"""
SegmentPOI repository for database operations.
"""
from typing import List, Optional
from uuid import UUID

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from api.database.models.segment_poi import SegmentPOI
from api.database.repositories.base import BaseRepository


class SegmentPOIRepository(BaseRepository[SegmentPOI]):
    """Repository for SegmentPOI model operations."""

    def __init__(self, session: AsyncSession):
        """Initialize with session."""
        super().__init__(session, SegmentPOI)

    async def get_by_segment(self, segment_id: UUID) -> List[SegmentPOI]:
        """
        Get all POI associations for a segment.

        Args:
            segment_id: Segment UUID

        Returns:
            List of SegmentPOI instances
        """
        result = await self.session.execute(
            select(SegmentPOI)
            .where(SegmentPOI.segment_id == segment_id)
            .order_by(SegmentPOI.search_point_index)
        )
        return list(result.scalars().all())

    async def get_by_segment_with_pois(
        self, segment_id: UUID
    ) -> List[SegmentPOI]:
        """
        Get all POI associations for a segment with POI data eagerly loaded.

        Args:
            segment_id: Segment UUID

        Returns:
            List of SegmentPOI instances with poi relationship loaded
        """
        result = await self.session.execute(
            select(SegmentPOI)
            .where(SegmentPOI.segment_id == segment_id)
            .options(selectinload(SegmentPOI.poi))
            .order_by(SegmentPOI.search_point_index)
        )
        return list(result.scalars().all())

    async def get_by_poi(self, poi_id: UUID) -> List[SegmentPOI]:
        """
        Get all segment associations for a POI.

        Args:
            poi_id: POI UUID

        Returns:
            List of SegmentPOI instances
        """
        result = await self.session.execute(
            select(SegmentPOI).where(SegmentPOI.poi_id == poi_id)
        )
        return list(result.scalars().all())

    async def exists_for_segment_poi(
        self, segment_id: UUID, poi_id: UUID
    ) -> bool:
        """
        Check if a segment-POI association exists.

        Args:
            segment_id: Segment UUID
            poi_id: POI UUID

        Returns:
            True if association exists, False otherwise
        """
        result = await self.session.execute(
            select(SegmentPOI.id).where(
                and_(
                    SegmentPOI.segment_id == segment_id,
                    SegmentPOI.poi_id == poi_id,
                )
            )
        )
        return result.scalar_one_or_none() is not None

    async def get_by_segment_and_poi(
        self, segment_id: UUID, poi_id: UUID
    ) -> Optional[SegmentPOI]:
        """
        Get a specific segment-POI association.

        Args:
            segment_id: Segment UUID
            poi_id: POI UUID

        Returns:
            SegmentPOI instance or None if not found
        """
        result = await self.session.execute(
            select(SegmentPOI).where(
                and_(
                    SegmentPOI.segment_id == segment_id,
                    SegmentPOI.poi_id == poi_id,
                )
            )
        )
        return result.scalar_one_or_none()

    async def bulk_create(self, items: List[SegmentPOI]) -> List[SegmentPOI]:
        """
        Create multiple segment-POI associations.

        Args:
            items: List of SegmentPOI instances to create

        Returns:
            List of created SegmentPOI instances
        """
        if not items:
            return []

        self.session.add_all(items)
        await self.session.flush()

        # Refresh all items to get generated IDs
        for item in items:
            await self.session.refresh(item)

        return items

    async def delete_by_segment(self, segment_id: UUID) -> int:
        """
        Delete all POI associations for a segment.

        Args:
            segment_id: Segment UUID

        Returns:
            Number of deleted associations
        """
        from sqlalchemy import delete

        result = await self.session.execute(
            delete(SegmentPOI).where(SegmentPOI.segment_id == segment_id)
        )
        await self.session.flush()
        return result.rowcount

    async def count_by_segment(self, segment_id: UUID) -> int:
        """
        Count POI associations for a segment.

        Args:
            segment_id: Segment UUID

        Returns:
            Number of POI associations
        """
        from sqlalchemy import func

        result = await self.session.execute(
            select(func.count(SegmentPOI.id))
            .where(SegmentPOI.segment_id == segment_id)
        )
        return result.scalar() or 0

    async def get_unique_poi_ids_for_segments(
        self, segment_ids: List[UUID]
    ) -> List[UUID]:
        """
        Get unique POI IDs associated with multiple segments.

        Args:
            segment_ids: List of segment UUIDs

        Returns:
            List of unique POI UUIDs
        """
        if not segment_ids:
            return []

        result = await self.session.execute(
            select(SegmentPOI.poi_id)
            .where(SegmentPOI.segment_id.in_(segment_ids))
            .distinct()
        )
        return [row[0] for row in result.all()]
