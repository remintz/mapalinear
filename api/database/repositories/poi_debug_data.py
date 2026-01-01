"""
POI Debug Data repository for database operations.
"""
from typing import List, Optional, Dict, Any
from uuid import UUID

from sqlalchemy import select, delete, func, Integer, cast
from sqlalchemy.ext.asyncio import AsyncSession

from api.database.models.poi_debug_data import POIDebugData
from api.database.repositories.base import BaseRepository


class POIDebugDataRepository(BaseRepository[POIDebugData]):
    """Repository for POIDebugData model operations."""

    def __init__(self, session: AsyncSession):
        """Initialize with session."""
        super().__init__(session, POIDebugData)

    async def get_by_map(self, map_id: UUID) -> List[POIDebugData]:
        """
        Get all debug data for a map, ordered by junction distance.

        Args:
            map_id: Map UUID

        Returns:
            List of POIDebugData instances ordered by junction_distance_km
        """
        result = await self.session.execute(
            select(POIDebugData)
            .where(POIDebugData.map_id == map_id)
            .order_by(POIDebugData.junction_distance_km.nulls_last())
        )
        return list(result.scalars().all())

    async def get_by_map_poi(self, map_poi_id: UUID) -> Optional[POIDebugData]:
        """
        Get debug data for a specific map-POI relationship.

        Args:
            map_poi_id: MapPOI UUID

        Returns:
            POIDebugData instance or None if not found
        """
        result = await self.session.execute(
            select(POIDebugData).where(POIDebugData.map_poi_id == map_poi_id)
        )
        return result.scalar_one_or_none()

    async def delete_by_map(self, map_id: UUID) -> int:
        """
        Delete all debug data for a map.

        This is called when a map is regenerated to clear old debug data.

        Args:
            map_id: Map UUID

        Returns:
            Number of deleted entries
        """
        result = await self.session.execute(
            delete(POIDebugData).where(POIDebugData.map_id == map_id)
        )
        return result.rowcount

    async def bulk_create(self, debug_entries: List[POIDebugData]) -> List[POIDebugData]:
        """
        Create multiple debug entries at once.

        Args:
            debug_entries: List of POIDebugData instances to create

        Returns:
            List of created POIDebugData instances
        """
        if not debug_entries:
            return []
        self.session.add_all(debug_entries)
        await self.session.flush()
        return debug_entries

    async def get_summary_by_map(self, map_id: UUID) -> Dict[str, int]:
        """
        Get summary statistics for debug data of a map.

        Args:
            map_id: Map UUID

        Returns:
            Dictionary with counts: total, detour_count, left_count, right_count, center_count
        """
        # Total count
        total_result = await self.session.execute(
            select(func.count(POIDebugData.id))
            .where(POIDebugData.map_id == map_id)
        )
        total = total_result.scalar() or 0

        # Detour count
        detour_result = await self.session.execute(
            select(func.count(POIDebugData.id))
            .where(
                POIDebugData.map_id == map_id,
                POIDebugData.requires_detour == True
            )
        )
        detour_count = detour_result.scalar() or 0

        # Left count
        left_result = await self.session.execute(
            select(func.count(POIDebugData.id))
            .where(
                POIDebugData.map_id == map_id,
                POIDebugData.final_side == "left"
            )
        )
        left_count = left_result.scalar() or 0

        # Right count
        right_result = await self.session.execute(
            select(func.count(POIDebugData.id))
            .where(
                POIDebugData.map_id == map_id,
                POIDebugData.final_side == "right"
            )
        )
        right_count = right_result.scalar() or 0

        # Center count
        center_result = await self.session.execute(
            select(func.count(POIDebugData.id))
            .where(
                POIDebugData.map_id == map_id,
                POIDebugData.final_side == "center"
            )
        )
        center_count = center_result.scalar() or 0

        return {
            "total": total,
            "detour_count": detour_count,
            "left_count": left_count,
            "right_count": right_count,
            "center_count": center_count,
        }

    async def get_by_poi_type(
        self, map_id: UUID, poi_type: str
    ) -> List[POIDebugData]:
        """
        Get debug data for POIs of a specific type.

        Args:
            map_id: Map UUID
            poi_type: POI type to filter by

        Returns:
            List of POIDebugData instances matching the type
        """
        result = await self.session.execute(
            select(POIDebugData)
            .where(
                POIDebugData.map_id == map_id,
                POIDebugData.poi_type == poi_type
            )
            .order_by(POIDebugData.junction_distance_km.nulls_last())
        )
        return list(result.scalars().all())

    async def get_by_side(
        self, map_id: UUID, side: str
    ) -> List[POIDebugData]:
        """
        Get debug data for POIs on a specific side.

        Args:
            map_id: Map UUID
            side: Side to filter by ("left", "right", "center")

        Returns:
            List of POIDebugData instances on the specified side
        """
        result = await self.session.execute(
            select(POIDebugData)
            .where(
                POIDebugData.map_id == map_id,
                POIDebugData.final_side == side
            )
            .order_by(POIDebugData.junction_distance_km.nulls_last())
        )
        return list(result.scalars().all())

    async def get_requiring_detour(self, map_id: UUID) -> List[POIDebugData]:
        """
        Get debug data for POIs that require a detour.

        Args:
            map_id: Map UUID

        Returns:
            List of POIDebugData instances requiring detour
        """
        result = await self.session.execute(
            select(POIDebugData)
            .where(
                POIDebugData.map_id == map_id,
                POIDebugData.requires_detour == True
            )
            .order_by(POIDebugData.junction_distance_km.nulls_last())
        )
        return list(result.scalars().all())

    async def has_debug_data(self, map_id: UUID) -> bool:
        """
        Check if a map has any debug data.

        Args:
            map_id: Map UUID

        Returns:
            True if the map has debug data, False otherwise
        """
        result = await self.session.execute(
            select(func.count(POIDebugData.id))
            .where(POIDebugData.map_id == map_id)
            .limit(1)
        )
        count = result.scalar() or 0
        return count > 0
