"""
UserMap SQLAlchemy model - junction table for user-map associations.
"""

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import uuid4

from sqlalchemy import Boolean, ForeignKey, Index, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.database.connection import Base

if TYPE_CHECKING:
    from api.database.models.map import Map
    from api.database.models.user import User


class UserMap(Base):
    """
    Junction table for user-map associations.

    Allows multiple users to have access to the same map.
    Maps are now global/shared, and this table tracks which users
    have each map in their collection.
    """

    __tablename__ = "user_maps"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    user_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    map_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("maps.id", ondelete="CASCADE"),
        nullable=False,
    )
    added_at: Mapped[datetime] = mapped_column(default=func.now())
    is_creator: Mapped[bool] = mapped_column(Boolean, default=False)

    # Table constraints
    __table_args__ = (
        UniqueConstraint("user_id", "map_id", name="uq_user_map"),
        Index("idx_user_maps_user_id", "user_id"),
        Index("idx_user_maps_map_id", "map_id"),
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="user_maps")
    map: Mapped["Map"] = relationship("Map", back_populates="user_maps")

    def __repr__(self) -> str:
        return f"<UserMap(user_id={self.user_id}, map_id={self.map_id}, is_creator={self.is_creator})>"
