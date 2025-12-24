"""
Repository for impersonation session operations.
"""
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy import and_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from api.database.models.impersonation_session import ImpersonationSession
from api.database.repositories.base import BaseRepository

logger = logging.getLogger(__name__)

# Default session duration: 1 hour
DEFAULT_SESSION_DURATION_HOURS = 1


class ImpersonationSessionRepository(BaseRepository[ImpersonationSession]):
    """Repository for managing impersonation sessions."""

    def __init__(self, session: AsyncSession):
        """Initialize repository with database session."""
        super().__init__(session, ImpersonationSession)

    async def get_active_session_for_admin(
        self, admin_id: UUID
    ) -> Optional[ImpersonationSession]:
        """
        Get the active impersonation session for an admin.

        An admin can only have one active session at a time.

        Args:
            admin_id: The admin user's UUID

        Returns:
            Active ImpersonationSession or None
        """
        now = datetime.now(timezone.utc)
        result = await self.session.execute(
            select(ImpersonationSession)
            .where(
                and_(
                    ImpersonationSession.admin_id == admin_id,
                    ImpersonationSession.is_active == True,  # noqa: E712
                    ImpersonationSession.expires_at > now,
                )
            )
            .order_by(ImpersonationSession.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def create_session(
        self,
        admin_id: UUID,
        target_user_id: UUID,
        duration_hours: int = DEFAULT_SESSION_DURATION_HOURS,
    ) -> ImpersonationSession:
        """
        Create a new impersonation session.

        Deactivates any existing active sessions for the admin first.

        Args:
            admin_id: The admin user's UUID
            target_user_id: The target user's UUID
            duration_hours: Session duration in hours (default: 1)

        Returns:
            Created ImpersonationSession
        """
        # Deactivate any existing sessions for this admin
        await self.deactivate_sessions_for_admin(admin_id)

        # Create new session
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(hours=duration_hours)

        session = ImpersonationSession(
            admin_id=admin_id,
            target_user_id=target_user_id,
            is_active=True,
            created_at=now,
            expires_at=expires_at,
        )

        self.session.add(session)
        await self.session.flush()
        await self.session.refresh(session)

        logger.info(
            f"Created impersonation session: admin={admin_id} -> target={target_user_id}, "
            f"expires_at={expires_at}"
        )

        return session

    async def deactivate_session(
        self, session_id: UUID
    ) -> Optional[ImpersonationSession]:
        """
        Deactivate a specific impersonation session.

        Args:
            session_id: The session UUID to deactivate

        Returns:
            Deactivated session or None if not found
        """
        imp_session = await self.get_by_id(session_id)
        if imp_session:
            imp_session.is_active = False
            await self.session.flush()
            await self.session.refresh(imp_session)
            logger.info(f"Deactivated impersonation session: {session_id}")
        return imp_session

    async def deactivate_sessions_for_admin(self, admin_id: UUID) -> int:
        """
        Deactivate all active sessions for an admin.

        Args:
            admin_id: The admin user's UUID

        Returns:
            Number of sessions deactivated
        """
        result = await self.session.execute(
            update(ImpersonationSession)
            .where(
                and_(
                    ImpersonationSession.admin_id == admin_id,
                    ImpersonationSession.is_active == True,  # noqa: E712
                )
            )
            .values(is_active=False)
        )
        count = result.rowcount
        if count > 0:
            logger.info(f"Deactivated {count} impersonation session(s) for admin={admin_id}")
        return count

    async def cleanup_expired_sessions(self) -> int:
        """
        Deactivate all expired sessions.

        Returns:
            Number of sessions cleaned up
        """
        now = datetime.now(timezone.utc)
        result = await self.session.execute(
            update(ImpersonationSession)
            .where(
                and_(
                    ImpersonationSession.is_active == True,  # noqa: E712
                    ImpersonationSession.expires_at <= now,
                )
            )
            .values(is_active=False)
        )
        count = result.rowcount
        if count > 0:
            logger.info(f"Cleaned up {count} expired impersonation session(s)")
        return count
