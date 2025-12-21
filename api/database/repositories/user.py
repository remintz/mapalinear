"""
User repository for authentication operations.
"""
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.database.models.user import User
from api.database.repositories.base import BaseRepository


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

    async def create_or_update_from_google(
        self,
        google_id: str,
        email: str,
        name: str,
        avatar_url: Optional[str] = None,
    ) -> User:
        """
        Create a new user or update existing from Google OAuth data.

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
            return await self.update(user)

        # Create new user
        user = User(
            google_id=google_id,
            email=email,
            name=name,
            avatar_url=avatar_url,
        )
        return await self.create(user)

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
