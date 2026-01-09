"""
RouteSegment SQLAlchemy model.

Represents a reusable route segment based on OSRM steps.
Segments are identified by a hash of their start/end coordinates.
"""
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, List, Optional
from uuid import uuid4

from sqlalchemy import Index, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.database.connection import Base

if TYPE_CHECKING:
    from api.database.models.map_segment import MapSegment
    from api.database.models.segment_poi import SegmentPOI


class RouteSegment(Base):
    """
    Route segment model representing a reusable portion of a route.

    Each segment corresponds to a step from OSRM routing and is identified
    by a unique hash of its start and end coordinates (rounded to 4 decimals).

    Segments can be reused across multiple maps, avoiding redundant POI searches.
    """

    __tablename__ = "route_segments"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4
    )

    # Unique identifier based on start/end coordinates
    segment_hash: Mapped[str] = mapped_column(
        String(32), unique=True, index=True, nullable=False
    )

    # Start coordinates
    start_lat: Mapped[Decimal] = mapped_column(nullable=False)
    start_lon: Mapped[Decimal] = mapped_column(nullable=False)

    # End coordinates
    end_lat: Mapped[Decimal] = mapped_column(nullable=False)
    end_lon: Mapped[Decimal] = mapped_column(nullable=False)

    # Segment metadata
    road_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    length_km: Mapped[Decimal] = mapped_column(nullable=False)

    # Full geometry as list of [lat, lon] coordinates
    geometry: Mapped[list] = mapped_column(JSONB, nullable=False)

    # Pre-calculated search points for POI searching
    # Structure: [{"index": 0, "lat": -19.9167, "lon": -43.9345, "distance_from_segment_start_km": 0.0}, ...]
    search_points: Mapped[list] = mapped_column(JSONB, default=list)

    # OSRM maneuver information
    osrm_instruction: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    osrm_maneuver_type: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True
    )

    # Usage tracking
    usage_count: Mapped[int] = mapped_column(default=0)
    pois_fetched_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        default=func.now(), onupdate=func.now()
    )

    # Relationships
    segment_pois: Mapped[List["SegmentPOI"]] = relationship(
        "SegmentPOI", back_populates="segment", cascade="all, delete-orphan"
    )
    map_segments: Mapped[List["MapSegment"]] = relationship(
        "MapSegment", back_populates="segment", cascade="all, delete-orphan"
    )

    # Indexes
    __table_args__ = (
        Index("idx_route_segments_start_coords", "start_lat", "start_lon"),
        Index("idx_route_segments_road_name", "road_name"),
    )

    def __repr__(self) -> str:
        return (
            f"<RouteSegment(id={self.id}, road='{self.road_name}', "
            f"length={self.length_km}km, usage={self.usage_count})>"
        )

    def increment_usage(self) -> None:
        """Increment the usage count for this segment."""
        self.usage_count = (self.usage_count or 0) + 1
