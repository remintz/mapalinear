"""
UserMap repository for database operations.
"""

from typing import List, Optional
from uuid import UUID

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from api.database.models.user_map import UserMap
from api.database.models.map import Map
from api.database.repositories.base import BaseRepository


class UserMapRepository(BaseRepository[UserMap]):
    """Repository for UserMap model operations (user-map associations)."""

    def __init__(self, session: AsyncSession):
        """Initialize with session."""
        super().__init__(session, UserMap)

    async def get_user_maps(
        self, user_id: UUID, skip: int = 0, limit: int = 100
    ) -> List[UserMap]:
        """
        Get all map associations for a user.

        Args:
            user_id: User UUID
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of user's map associations ordered by added_at
        """
        result = await self.session.execute(
            select(UserMap)
            .where(UserMap.user_id == user_id)
            .options(selectinload(UserMap.map).selectinload(Map.map_pois))
            .order_by(UserMap.added_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_map_users(self, map_id: UUID) -> List[UserMap]:
        """
        Get all user associations for a map.

        Args:
            map_id: Map UUID

        Returns:
            List of user associations for the map
        """
        result = await self.session.execute(
            select(UserMap)
            .where(UserMap.map_id == map_id)
            .order_by(UserMap.added_at.asc())
        )
        return list(result.scalars().all())

    async def user_has_map(self, user_id: UUID, map_id: UUID) -> bool:
        """
        Check if user has access to a map.

        Args:
            user_id: User UUID
            map_id: Map UUID

        Returns:
            True if user has the map in their collection
        """
        result = await self.session.execute(
            select(UserMap.id).where(
                UserMap.user_id == user_id, UserMap.map_id == map_id
            )
        )
        return result.scalar_one_or_none() is not None

    async def add_map_to_user(
        self, user_id: UUID, map_id: UUID, is_creator: bool = False
    ) -> UserMap:
        """
        Add a map to user's collection.

        Args:
            user_id: User UUID
            map_id: Map UUID
            is_creator: Whether the user is the creator of the map

        Returns:
            Created UserMap association
        """
        user_map = UserMap(user_id=user_id, map_id=map_id, is_creator=is_creator)
        return await self.create(user_map)

    async def remove_map_from_user(self, user_id: UUID, map_id: UUID) -> bool:
        """
        Remove map from user's collection (unlink).

        Args:
            user_id: User UUID
            map_id: Map UUID

        Returns:
            True if removed, False if not found
        """
        result = await self.session.execute(
            select(UserMap).where(UserMap.user_id == user_id, UserMap.map_id == map_id)
        )
        user_map = result.scalar_one_or_none()
        if user_map:
            await self.delete(user_map)
            return True
        return False

    async def get_map_user_count(self, map_id: UUID) -> int:
        """
        Count how many users have this map.

        Args:
            map_id: Map UUID

        Returns:
            Number of users with this map
        """
        result = await self.session.execute(
            select(func.count()).select_from(UserMap).where(UserMap.map_id == map_id)
        )
        return result.scalar_one()

    async def get_user_map_with_details(
        self, user_id: UUID, map_id: UUID
    ) -> Optional[UserMap]:
        """
        Get a specific user-map association with map details loaded.

        Args:
            user_id: User UUID
            map_id: Map UUID

        Returns:
            UserMap with map details or None if not found
        """
        result = await self.session.execute(
            select(UserMap)
            .where(UserMap.user_id == user_id, UserMap.map_id == map_id)
            .options(selectinload(UserMap.map).selectinload(Map.map_pois))
        )
        return result.scalar_one_or_none()

    async def get_by_user_and_map(
        self, user_id: UUID, map_id: UUID
    ) -> Optional[UserMap]:
        """
        Get a specific user-map association.

        Args:
            user_id: User UUID
            map_id: Map UUID

        Returns:
            UserMap or None if not found
        """
        result = await self.session.execute(
            select(UserMap).where(UserMap.user_id == user_id, UserMap.map_id == map_id)
        )
        return result.scalar_one_or_none()
