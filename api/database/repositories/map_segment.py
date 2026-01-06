"""
MapSegment repository for database operations.
"""
from typing import List
from uuid import UUID

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from api.database.models.map_segment import MapSegment
from api.database.repositories.base import BaseRepository


class MapSegmentRepository(BaseRepository[MapSegment]):
    """Repository for MapSegment model operations."""

    def __init__(self, session: AsyncSession):
        """Initialize with session."""
        super().__init__(session, MapSegment)

    async def get_by_map(self, map_id: UUID) -> List[MapSegment]:
        """
        Get all segments for a map, ordered by sequence.

        Args:
            map_id: Map UUID

        Returns:
            List of MapSegment instances ordered by sequence_order
        """
        result = await self.session.execute(
            select(MapSegment)
            .where(MapSegment.map_id == map_id)
            .order_by(MapSegment.sequence_order)
        )
        return list(result.scalars().all())

    async def get_by_map_with_segments(self, map_id: UUID) -> List[MapSegment]:
        """
        Get all segments for a map with RouteSegment data eagerly loaded.

        Args:
            map_id: Map UUID

        Returns:
            List of MapSegment instances with segment relationship loaded
        """
        result = await self.session.execute(
            select(MapSegment)
            .where(MapSegment.map_id == map_id)
            .options(selectinload(MapSegment.segment))
            .order_by(MapSegment.sequence_order)
        )
        return list(result.scalars().all())

    async def get_by_map_with_full_data(self, map_id: UUID) -> List[MapSegment]:
        """
        Get all segments for a map with full RouteSegment and SegmentPOI data.

        Args:
            map_id: Map UUID

        Returns:
            List of MapSegment instances with segment and segment_pois loaded
        """
        from api.database.models.route_segment import RouteSegment

        result = await self.session.execute(
            select(MapSegment)
            .where(MapSegment.map_id == map_id)
            .options(
                selectinload(MapSegment.segment).selectinload(
                    RouteSegment.segment_pois
                )
            )
            .order_by(MapSegment.sequence_order)
        )
        return list(result.scalars().all())

    async def bulk_create(self, items: List[MapSegment]) -> List[MapSegment]:
        """
        Create multiple map-segment associations.

        Args:
            items: List of MapSegment instances to create

        Returns:
            List of created MapSegment instances
        """
        if not items:
            return []

        self.session.add_all(items)
        await self.session.flush()

        # Refresh all items to get generated IDs
        for item in items:
            await self.session.refresh(item)

        return items

    async def delete_by_map(self, map_id: UUID) -> int:
        """
        Delete all segment associations for a map.

        Args:
            map_id: Map UUID

        Returns:
            Number of deleted associations
        """
        result = await self.session.execute(
            delete(MapSegment).where(MapSegment.map_id == map_id)
        )
        await self.session.flush()
        return result.rowcount

    async def count_by_map(self, map_id: UUID) -> int:
        """
        Count segments for a map.

        Args:
            map_id: Map UUID

        Returns:
            Number of segments
        """
        from sqlalchemy import func

        result = await self.session.execute(
            select(func.count(MapSegment.id)).where(MapSegment.map_id == map_id)
        )
        return result.scalar() or 0

    async def get_segment_ids_for_map(self, map_id: UUID) -> List[UUID]:
        """
        Get segment IDs for a map.

        Args:
            map_id: Map UUID

        Returns:
            List of segment UUIDs in sequence order
        """
        result = await self.session.execute(
            select(MapSegment.segment_id)
            .where(MapSegment.map_id == map_id)
            .order_by(MapSegment.sequence_order)
        )
        return [row[0] for row in result.all()]

    async def get_total_distance_for_map(self, map_id: UUID) -> float:
        """
        Get the total distance for a map based on its segments.

        Args:
            map_id: Map UUID

        Returns:
            Total distance in km
        """
        from sqlalchemy import func
        from api.database.models.route_segment import RouteSegment

        result = await self.session.execute(
            select(func.sum(RouteSegment.length_km))
            .select_from(MapSegment)
            .join(RouteSegment)
            .where(MapSegment.map_id == map_id)
        )
        return float(result.scalar() or 0)

    async def get_maps_using_segment(self, segment_id: UUID) -> List[UUID]:
        """
        Get all map IDs that use a specific segment.

        Args:
            segment_id: Segment UUID

        Returns:
            List of map UUIDs
        """
        result = await self.session.execute(
            select(MapSegment.map_id)
            .where(MapSegment.segment_id == segment_id)
            .distinct()
        )
        return [row[0] for row in result.all()]
