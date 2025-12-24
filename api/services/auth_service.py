"""
Authentication service for Google OAuth and JWT handling.
"""

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional
from uuid import UUID

from google.auth.transport import requests as google_requests
from google.oauth2 import id_token
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession

from api.database.models.user import User
from api.database.repositories.user import UserRepository
from api.providers.settings import get_settings

logger = logging.getLogger(__name__)


class AuthError(Exception):
    """Authentication error."""

    def __init__(self, message: str, status_code: int = 401):
        self.message = message
        self.status_code = status_code
        super().__init__(message)


@dataclass
class VerifyResult:
    """Result of JWT verification."""

    user: User


class AuthService:
    """Service for authentication operations."""

    def __init__(self, session: AsyncSession):
        """
        Initialize auth service.

        Args:
            session: SQLAlchemy async session
        """
        self.session = session
        self.user_repo = UserRepository(session)
        self.settings = get_settings()

    async def verify_google_token(self, token: str) -> Dict[str, Any]:
        """
        Verify a Google OAuth ID token.

        Args:
            token: Google ID token from frontend

        Returns:
            Dict with user info from Google (sub, email, name, picture)

        Raises:
            AuthError: If token is invalid or expired
        """
        try:
            # Verify the token with Google
            idinfo = id_token.verify_oauth2_token(
                token,
                google_requests.Request(),
                self.settings.google_client_id,
            )

            # Verify issuer
            if idinfo["iss"] not in [
                "accounts.google.com",
                "https://accounts.google.com",
            ]:
                raise AuthError("Invalid token issuer")

            return {
                "google_id": idinfo["sub"],
                "email": idinfo["email"],
                "name": idinfo.get("name", idinfo["email"].split("@")[0]),
                "avatar_url": idinfo.get("picture"),
            }

        except ValueError as e:
            logger.warning(f"Invalid Google token: {e}")
            raise AuthError("Invalid Google token")

    async def authenticate_with_google(self, google_token: str) -> tuple[User, str]:
        """
        Authenticate user with Google OAuth token.

        Creates or updates user in database and returns JWT.

        Args:
            google_token: Google ID token from frontend

        Returns:
            Tuple of (User, JWT token)

        Raises:
            AuthError: If authentication fails
        """
        # Verify Google token and get user info
        google_data = await self.verify_google_token(google_token)

        # Create or update user in database
        user = await self.user_repo.create_or_update_from_google(
            google_id=google_data["google_id"],
            email=google_data["email"],
            name=google_data["name"],
            avatar_url=google_data.get("avatar_url"),
        )

        if not user.is_active:
            raise AuthError("User account is deactivated", status_code=403)

        # Generate JWT
        jwt_token = self.create_jwt(user)

        await self.session.commit()

        logger.info(f"User authenticated: {user.email}")
        return user, jwt_token

    def create_jwt(self, user: User) -> str:
        """
        Create a JWT token for a user.

        Args:
            user: User instance

        Returns:
            JWT token string
        """
        expire = datetime.now(timezone.utc) + timedelta(
            hours=self.settings.jwt_expire_hours
        )

        payload = {
            "sub": str(user.id),
            "email": user.email,
            "name": user.name,
            "exp": expire,
            "iat": datetime.now(timezone.utc),
        }

        token = jwt.encode(
            payload,
            self.settings.jwt_secret_key,
            algorithm=self.settings.jwt_algorithm,
        )

        return token

    async def verify_jwt(self, token: str) -> VerifyResult:
        """
        Verify a JWT token and return the user.

        Args:
            token: JWT token string

        Returns:
            VerifyResult with user

        Raises:
            AuthError: If token is invalid or user not found
        """
        try:
            payload = jwt.decode(
                token,
                self.settings.jwt_secret_key,
                algorithms=[self.settings.jwt_algorithm],
            )

            user_id = payload.get("sub")
            if not user_id:
                raise AuthError("Invalid token: missing user ID")

            user = await self.user_repo.get_by_id(UUID(user_id))

            if not user:
                raise AuthError("User not found")

            if not user.is_active:
                raise AuthError("User account is deactivated", status_code=403)

            return VerifyResult(user=user)

        except JWTError as e:
            logger.warning(f"JWT verification failed: {e}")
            raise AuthError("Invalid or expired token")

    async def get_user_by_id(self, user_id: UUID) -> Optional[User]:
        """
        Get user by ID.

        Args:
            user_id: User UUID

        Returns:
            User instance or None
        """
        return await self.user_repo.get_by_id(user_id)
