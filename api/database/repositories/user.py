"""
User repository for authentication and admin operations.
"""
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from api.database.models.map import Map
from api.database.models.user import User
from api.database.repositories.base import BaseRepository

# Default admin users by name
DEFAULT_ADMIN_NAMES = ["Renato Mintz"]


class UserRepository(BaseRepository[User]):
    """Repository for User model with authentication-specific methods."""

    def __init__(self, session: AsyncSession):
        """Initialize repository with session."""
        super().__init__(session, User)

    async def get_by_google_id(self, google_id: str) -> Optional[User]:
        """
        Get user by Google OAuth ID.

        Args:
            google_id: Google's unique user identifier

        Returns:
            User instance or None if not found
        """
        result = await self.session.execute(
            select(User).where(User.google_id == google_id)
        )
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> Optional[User]:
        """
        Get user by email address.

        Args:
            email: User's email address

        Returns:
            User instance or None if not found
        """
        result = await self.session.execute(
            select(User).where(User.email == email)
        )
        return result.scalar_one_or_none()

    async def get_by_id(self, user_id: UUID) -> Optional[User]:
        """
        Get user by UUID.

        Args:
            user_id: User's UUID

        Returns:
            User instance or None if not found
        """
        result = await self.session.execute(
            select(User).where(User.id == user_id)
        )
        return result.scalar_one_or_none()

    async def create_or_update_from_google(
        self,
        google_id: str,
        email: str,
        name: str,
        avatar_url: Optional[str] = None,
    ) -> User:
        """
        Create a new user or update existing from Google OAuth data.

        Also updates last_login_at timestamp.
        New users with names in DEFAULT_ADMIN_NAMES are automatically set as admin.

        Args:
            google_id: Google's unique user identifier
            email: User's email from Google
            name: User's display name from Google
            avatar_url: URL to user's Google profile picture

        Returns:
            Created or updated User instance
        """
        user = await self.get_by_google_id(google_id)

        if user:
            # Update existing user with latest Google data
            user.email = email
            user.name = name
            user.avatar_url = avatar_url
            user.last_login_at = datetime.utcnow()
            return await self.update(user)

        # Create new user
        # Check if user should be admin by default
        is_admin = name in DEFAULT_ADMIN_NAMES

        user = User(
            google_id=google_id,
            email=email,
            name=name,
            avatar_url=avatar_url,
            is_admin=is_admin,
            last_login_at=datetime.utcnow(),
        )
        return await self.create(user)

    async def get_all_users(self) -> List[User]:
        """
        Get all users ordered by name.

        Returns:
            List of all User instances
        """
        result = await self.session.execute(
            select(User).order_by(User.name)
        )
        return list(result.scalars().all())

    async def get_user_with_map_count(self, user_id: UUID) -> Optional[dict]:
        """
        Get user with their map count.

        Args:
            user_id: User's UUID

        Returns:
            Dictionary with user and map_count, or None
        """
        user = await self.get_by_id(user_id)
        if not user:
            return None

        # Get map count
        result = await self.session.execute(
            select(func.count(Map.id)).where(Map.user_id == user_id)
        )
        map_count = result.scalar() or 0

        return {
            "user": user,
            "map_count": map_count,
        }

    async def get_all_users_with_stats(self) -> List[dict]:
        """
        Get all users with their map counts.

        Returns:
            List of dictionaries with user data and stats
        """
        # Get all users
        users = await self.get_all_users()

        # Get map counts for all users
        result = await self.session.execute(
            select(Map.user_id, func.count(Map.id).label("count"))
            .group_by(Map.user_id)
        )
        map_counts = {row.user_id: row.count for row in result.all()}

        return [
            {
                "user": user,
                "map_count": map_counts.get(user.id, 0),
            }
            for user in users
        ]

    async def set_admin(self, user: User, is_admin: bool) -> User:
        """
        Set or remove admin status for a user.

        Args:
            user: User instance
            is_admin: Whether user should be admin

        Returns:
            Updated User instance
        """
        user.is_admin = is_admin
        return await self.update(user)

    async def deactivate(self, user: User) -> User:
        """
        Deactivate a user account.

        Args:
            user: User instance to deactivate

        Returns:
            Updated User instance
        """
        user.is_active = False
        return await self.update(user)

    async def activate(self, user: User) -> User:
        """
        Activate a user account.

        Args:
            user: User instance to activate

        Returns:
            Updated User instance
        """
        user.is_active = True
        return await self.update(user)
