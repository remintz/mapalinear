"""
Map repository for database operations.
"""
from typing import List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from api.database.models.map import Map
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
            select(Map)
            .where(Map.id == id)
            .options(selectinload(Map.map_pois))
        )
        return result.scalar_one_or_none()

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
            select(Map).where(
                Map.origin == origin,
                Map.destination == destination
            )
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
        result = await self.session.execute(
            select(Map).where(Map.road_id == road_id)
        )
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
            select(Map)
            .order_by(Map.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def search_by_location(
        self, location: str, limit: int = 10
    ) -> List[Map]:
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
                (Map.origin.ilike(search_pattern)) |
                (Map.destination.ilike(search_pattern))
            )
            .limit(limit)
        )
        return list(result.scalars().all())
