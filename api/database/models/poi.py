"""
POI (Point of Interest) SQLAlchemy model.
"""
from datetime import datetime
from typing import TYPE_CHECKING, List, Optional
from uuid import uuid4

from sqlalchemy import Index, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.database.connection import Base

if TYPE_CHECKING:
    from api.database.models.map_poi import MapPOI


class POI(Base):
    """
    Point of Interest model.

    Stores normalized POI data that can be reused across multiple maps.
    The osm_id serves as a unique identifier to avoid duplicates.
    """

    __tablename__ = "pois"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    osm_id: Mapped[Optional[str]] = mapped_column(
        String(100), unique=True, index=True, nullable=True
    )
    name: Mapped[str] = mapped_column(String(500), index=True)
    type: Mapped[str] = mapped_column(String(50), index=True)  # MilestoneType.value
    latitude: Mapped[float] = mapped_column()
    longitude: Mapped[float] = mapped_column()

    # Enriched metadata
    city: Mapped[Optional[str]] = mapped_column(String(200), index=True, nullable=True)
    operator: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    brand: Mapped[Optional[str]] = mapped_column(String(200), index=True, nullable=True)
    opening_hours: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    website: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    cuisine: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)

    # JSONB fields for flexible data
    amenities: Mapped[list] = mapped_column(JSONB, default=list)
    tags: Mapped[dict] = mapped_column(JSONB, default=dict)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        default=func.now(), onupdate=func.now()
    )

    # Relationships
    map_pois: Mapped[List["MapPOI"]] = relationship(
        "MapPOI", back_populates="poi", cascade="all, delete-orphan"
    )

    # Indexes
    __table_args__ = (
        Index("idx_pois_location", "latitude", "longitude"),
        Index("idx_pois_type_city", "type", "city"),
    )

    def __repr__(self) -> str:
        return f"<POI(id={self.id}, name='{self.name}', type='{self.type}')>"
