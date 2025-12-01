"""
MapPOI (junction table) repository for database operations.
"""
from typing import List, Optional
from uuid import UUID

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from api.database.models.map_poi import MapPOI
from api.database.models.poi import POI
from api.database.repositories.base import BaseRepository


class MapPOIRepository(BaseRepository[MapPOI]):
    """Repository for MapPOI model operations."""

    def __init__(self, session: AsyncSession):
        """Initialize with session."""
        super().__init__(session, MapPOI)

    async def get_by_map_and_poi(
        self, map_id: UUID, poi_id: UUID
    ) -> Optional[MapPOI]:
        """
        Get a specific map-POI relationship.

        Args:
            map_id: Map UUID
            poi_id: POI UUID

        Returns:
            MapPOI instance or None if not found
        """
        result = await self.session.execute(
            select(MapPOI).where(
                MapPOI.map_id == map_id,
                MapPOI.poi_id == poi_id
            )
        )
        return result.scalar_one_or_none()

    async def get_pois_for_map(
        self, map_id: UUID, include_poi_details: bool = False
    ) -> List[MapPOI]:
        """
        Get all POI relationships for a map, ordered by distance.

        Args:
            map_id: Map UUID
            include_poi_details: Whether to eagerly load POI data

        Returns:
            List of MapPOI instances ordered by distance from origin
        """
        query = select(MapPOI).where(MapPOI.map_id == map_id)

        if include_poi_details:
            query = query.options(selectinload(MapPOI.poi))

        query = query.order_by(MapPOI.distance_from_origin_km)

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_maps_for_poi(self, poi_id: UUID) -> List[MapPOI]:
        """
        Get all map relationships for a POI.

        Args:
            poi_id: POI UUID

        Returns:
            List of MapPOI instances
        """
        result = await self.session.execute(
            select(MapPOI)
            .where(MapPOI.poi_id == poi_id)
            .options(selectinload(MapPOI.map))
        )
        return list(result.scalars().all())

    async def get_pois_by_type_for_map(
        self, map_id: UUID, poi_type: str
    ) -> List[MapPOI]:
        """
        Get POIs of a specific type for a map.

        Args:
            map_id: Map UUID
            poi_type: POI type to filter by

        Returns:
            List of MapPOI instances with matching POI type
        """
        result = await self.session.execute(
            select(MapPOI)
            .join(MapPOI.poi)
            .where(
                MapPOI.map_id == map_id,
                POI.type == poi_type
            )
            .options(selectinload(MapPOI.poi))
            .order_by(MapPOI.distance_from_origin_km)
        )
        return list(result.scalars().all())

    async def get_pois_by_side(
        self, map_id: UUID, side: str
    ) -> List[MapPOI]:
        """
        Get POIs on a specific side of the road.

        Args:
            map_id: Map UUID
            side: Side of road ("left", "right", "center")

        Returns:
            List of MapPOI instances on the specified side
        """
        result = await self.session.execute(
            select(MapPOI)
            .where(
                MapPOI.map_id == map_id,
                MapPOI.side == side
            )
            .options(selectinload(MapPOI.poi))
            .order_by(MapPOI.distance_from_origin_km)
        )
        return list(result.scalars().all())

    async def get_pois_in_segment(
        self, map_id: UUID, segment_index: int
    ) -> List[MapPOI]:
        """
        Get POIs in a specific road segment.

        Args:
            map_id: Map UUID
            segment_index: Segment index

        Returns:
            List of MapPOI instances in the segment
        """
        result = await self.session.execute(
            select(MapPOI)
            .where(
                MapPOI.map_id == map_id,
                MapPOI.segment_index == segment_index
            )
            .options(selectinload(MapPOI.poi))
            .order_by(MapPOI.distance_from_origin_km)
        )
        return list(result.scalars().all())

    async def get_pois_in_distance_range(
        self, map_id: UUID, start_km: float, end_km: float
    ) -> List[MapPOI]:
        """
        Get POIs within a distance range from origin.

        Args:
            map_id: Map UUID
            start_km: Start distance in kilometers
            end_km: End distance in kilometers

        Returns:
            List of MapPOI instances within the range
        """
        result = await self.session.execute(
            select(MapPOI)
            .where(
                MapPOI.map_id == map_id,
                MapPOI.distance_from_origin_km >= start_km,
                MapPOI.distance_from_origin_km <= end_km
            )
            .options(selectinload(MapPOI.poi))
            .order_by(MapPOI.distance_from_origin_km)
        )
        return list(result.scalars().all())

    async def delete_all_for_map(self, map_id: UUID) -> int:
        """
        Delete all POI relationships for a map.

        Args:
            map_id: Map UUID

        Returns:
            Number of deleted relationships
        """
        from sqlalchemy import delete
        result = await self.session.execute(
            delete(MapPOI).where(MapPOI.map_id == map_id)
        )
        return result.rowcount

    async def bulk_create(self, map_pois: List[MapPOI]) -> List[MapPOI]:
        """
        Create multiple MapPOI relationships at once.

        Args:
            map_pois: List of MapPOI instances to create

        Returns:
            List of created MapPOI instances
        """
        self.session.add_all(map_pois)
        await self.session.flush()
        return map_pois
