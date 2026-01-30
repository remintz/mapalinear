"""
Map repository for database operations.
"""

from typing import List, Optional, Tuple
from uuid import UUID
import math

from sqlalchemy import select, func, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from api.database.models.map import Map
from api.database.models.map_poi import MapPOI
from api.database.models.map_segment import MapSegment
from api.database.models.route_segment import RouteSegment
from api.database.models.user_map import UserMap
from api.database.repositories.base import BaseRepository


class MapRepository(BaseRepository[Map]):
    """Repository for Map model operations."""

    def __init__(self, session: AsyncSession):
        """Initialize with session."""
        super().__init__(session, Map)

    async def get_by_id_with_pois(self, id: UUID) -> Optional[Map]:
        """
        Get a map by ID with all related POIs loaded.

        Args:
            id: Map UUID

        Returns:
            Map instance with POIs or None if not found
        """
        result = await self.session.execute(
            select(Map).where(Map.id == id).options(
                selectinload(Map.map_pois).selectinload(MapPOI.poi)
            )
        )
        return result.scalar_one_or_none()

    async def get_all_maps(self, skip: int = 0, limit: int = 100) -> List[Map]:
        """
        Get all available maps (for browsing).

        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of maps ordered by creation date
        """
        result = await self.session.execute(
            select(Map).order_by(Map.created_at.desc()).offset(skip).limit(limit)
        )
        return list(result.scalars().all())

    async def find_by_origin_destination(
        self, origin: str, destination: str
    ) -> List[Map]:
        """
        Find maps by origin and destination.

        Args:
            origin: Origin location string
            destination: Destination location string

        Returns:
            List of matching maps
        """
        result = await self.session.execute(
            select(Map).where(Map.origin == origin, Map.destination == destination)
        )
        return list(result.scalars().all())

    async def find_by_road_id(self, road_id: str) -> List[Map]:
        """
        Find all maps for a specific road.

        Args:
            road_id: Road identifier

        Returns:
            List of maps on that road
        """
        result = await self.session.execute(select(Map).where(Map.road_id == road_id))
        return list(result.scalars().all())

    async def get_recent(self, limit: int = 10) -> List[Map]:
        """
        Get most recently created maps.

        Args:
            limit: Maximum number of maps to return

        Returns:
            List of recent maps ordered by creation date
        """
        result = await self.session.execute(
            select(Map).order_by(Map.created_at.desc()).limit(limit)
        )
        return list(result.scalars().all())

    async def search_by_location(self, location: str, limit: int = 10) -> List[Map]:
        """
        Search maps by origin or destination containing location string.

        Args:
            location: Location string to search for
            limit: Maximum number of results

        Returns:
            List of matching maps
        """
        search_pattern = f"%{location}%"
        result = await self.session.execute(
            select(Map)
            .where(
                (Map.origin.ilike(search_pattern))
                | (Map.destination.ilike(search_pattern))
            )
            .limit(limit)
        )
        return list(result.scalars().all())

    async def find_by_coordinates_proximity(
        self,
        origin_lat: float,
        origin_lon: float,
        dest_lat: float,
        dest_lon: float,
        tolerance_km: float = 5.0,
    ) -> Optional[Map]:
        """
        Find a map with origin and destination within tolerance of given coordinates.

        Uses Haversine formula to calculate distance between coordinates.
        Coordinates are obtained from MapSegment -> RouteSegment relationships.

        Args:
            origin_lat: Origin latitude
            origin_lon: Origin longitude
            dest_lat: Destination latitude
            dest_lon: Destination longitude
            tolerance_km: Maximum distance in km to consider a match

        Returns:
            First matching map or None
        """
        # Get all maps with their segments loaded
        result = await self.session.execute(
            select(Map).options(
                selectinload(Map.map_segments).selectinload(MapSegment.segment)
            )
        )

        maps = result.scalars().all()

        for map_obj in maps:
            try:
                if not map_obj.map_segments:
                    continue

                # Sort segments by sequence_order
                sorted_segments = sorted(
                    map_obj.map_segments, key=lambda s: s.sequence_order
                )

                if not sorted_segments:
                    continue

                # Get first segment for origin coordinates
                first_map_segment = sorted_segments[0]
                if not first_map_segment.segment:
                    continue

                map_origin_lat = float(first_map_segment.segment.start_lat)
                map_origin_lon = float(first_map_segment.segment.start_lon)

                # Get last segment for destination coordinates
                last_map_segment = sorted_segments[-1]
                if not last_map_segment.segment:
                    continue

                map_dest_lat = float(last_map_segment.segment.end_lat)
                map_dest_lon = float(last_map_segment.segment.end_lon)

                # Calculate distances using Haversine formula
                origin_distance = self._haversine_distance(
                    origin_lat, origin_lon, map_origin_lat, map_origin_lon
                )
                dest_distance = self._haversine_distance(
                    dest_lat, dest_lon, map_dest_lat, map_dest_lon
                )

                # Check if both origin and destination are within tolerance
                if origin_distance <= tolerance_km and dest_distance <= tolerance_km:
                    return map_obj

            except (ValueError, TypeError, AttributeError):
                continue

        return None

    @staticmethod
    def _haversine_distance(
        lat1: float, lon1: float, lat2: float, lon2: float
    ) -> float:
        """
        Calculate the great-circle distance between two points on Earth.

        Args:
            lat1, lon1: First point coordinates
            lat2, lon2: Second point coordinates

        Returns:
            Distance in kilometers
        """
        R = 6371  # Earth's radius in kilometers

        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        delta_lat = math.radians(lat2 - lat1)
        delta_lon = math.radians(lon2 - lon1)

        a = (
            math.sin(delta_lat / 2) ** 2
            + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon / 2) ** 2
        )
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

        return R * c

    async def get_all_maps_with_user_count(
        self, skip: int = 0, limit: int = 100
    ) -> List[dict]:
        """
        Get all maps with their user count for admin view.

        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of dicts with map and user_count
        """
        result = await self.session.execute(
            select(Map, func.count(UserMap.id).label("user_count"))
            .outerjoin(UserMap, Map.id == UserMap.map_id)
            .group_by(Map.id)
            .order_by(Map.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        rows = result.all()
        return [{"map": row[0], "user_count": row[1]} for row in rows]

    async def count_all_maps(self) -> int:
        """
        Count total number of maps.

        Returns:
            Total number of maps
        """
        result = await self.session.execute(select(func.count()).select_from(Map))
        return result.scalar_one()
