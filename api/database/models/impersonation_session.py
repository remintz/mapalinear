"""
Impersonation session model for admin user impersonation.
"""

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.database.connection import Base

if TYPE_CHECKING:
    from api.database.models.user import User


class ImpersonationSession(Base):
    """
    Tracks active impersonation sessions.

    When an admin impersonates a user, a session is created.
    The middleware checks for active sessions and returns the target user
    instead of the admin when making API calls.
    """

    __tablename__ = "impersonation_sessions"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4
    )

    # The admin who is impersonating
    admin_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
    )

    # The user being impersonated
    target_user_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
    )

    # Session state
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=func.now()
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)

    # Relationships
    admin: Mapped["User"] = relationship(
        "User", foreign_keys=[admin_id], lazy="selectin"
    )
    target_user: Mapped["User"] = relationship(
        "User", foreign_keys=[target_user_id], lazy="selectin"
    )

    def __repr__(self) -> str:
        return (
            f"<ImpersonationSession(id={self.id}, "
            f"admin_id={self.admin_id}, "
            f"target_user_id={self.target_user_id}, "
            f"is_active={self.is_active})>"
        )

    @property
    def is_expired(self) -> bool:
        """Check if the session has expired."""
        return datetime.now(self.expires_at.tzinfo) > self.expires_at
