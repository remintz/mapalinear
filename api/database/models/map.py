"""
Map SQLAlchemy model.
"""

from datetime import datetime
from typing import TYPE_CHECKING, List, Optional
from uuid import uuid4

from sqlalchemy import ForeignKey, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.database.connection import Base

if TYPE_CHECKING:
    from api.database.models.map_poi import MapPOI
    from api.database.models.map_segment import MapSegment
    from api.database.models.user import User
    from api.database.models.user_map import UserMap


class Map(Base):
    """
    Map model representing a linear map between two locations.

    Segments are stored in the map_segments table (via MapSegment -> RouteSegment).
    POIs are stored in a separate normalized table and linked via MapPOI.
    """

    __tablename__ = "maps"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    origin: Mapped[str] = mapped_column(String(500))
    destination: Mapped[str] = mapped_column(String(500))
    total_length_km: Mapped[float] = mapped_column()
    road_id: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)

    # Optional metadata
    metadata_: Mapped[dict] = mapped_column("metadata", JSONB, default=dict)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        default=func.now(), onupdate=func.now()
    )

    # Creator reference (for audit purposes, not ownership)
    created_by_user_id: Mapped[Optional[UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Relationships
    # User-map associations (for shared maps)
    user_maps: Mapped[List["UserMap"]] = relationship(
        "UserMap", back_populates="map", cascade="all, delete-orphan"
    )
    # Creator reference (for audit purposes)
    created_by: Mapped[Optional["User"]] = relationship(
        "User", foreign_keys=[created_by_user_id]
    )
    map_pois: Mapped[List["MapPOI"]] = relationship(
        "MapPOI", back_populates="map", cascade="all, delete-orphan"
    )
    map_segments: Mapped[List["MapSegment"]] = relationship(
        "MapSegment", back_populates="map", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Map(id={self.id}, origin='{self.origin}', destination='{self.destination}')>"
