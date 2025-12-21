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
    from api.database.models.user import User


class Map(Base):
    """
    Map model representing a linear map between two locations.

    Segments are stored as JSONB for simplicity (they are always accessed via the map).
    POIs are stored in a separate normalized table and linked via MapPOI.
    """

    __tablename__ = "maps"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    user_id: Mapped[Optional[UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True
    )
    origin: Mapped[str] = mapped_column(String(500))
    destination: Mapped[str] = mapped_column(String(500))
    total_length_km: Mapped[float] = mapped_column()
    road_id: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)

    # Segments stored as JSONB (list of LinearRoadSegment dicts)
    segments: Mapped[list] = mapped_column(JSONB, default=list)

    # Optional metadata
    metadata_: Mapped[dict] = mapped_column("metadata", JSONB, default=dict)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        default=func.now(), onupdate=func.now()
    )

    # Relationships
    user: Mapped[Optional["User"]] = relationship("User", back_populates="maps")
    map_pois: Mapped[List["MapPOI"]] = relationship(
        "MapPOI", back_populates="map", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Map(id={self.id}, origin='{self.origin}', destination='{self.destination}')>"
