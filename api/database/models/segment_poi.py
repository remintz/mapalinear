"""
SegmentPOI SQLAlchemy model.

Links POIs to route segments with basic discovery data.
Junction and side calculations are done at map assembly time (see MapPOI).
"""
from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID as PyUUID
from uuid import uuid4

from sqlalchemy import ForeignKey, Index, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.database.connection import Base

if TYPE_CHECKING:
    from api.database.models.poi import POI
    from api.database.models.route_segment import RouteSegment


class SegmentPOI(Base):
    """
    Junction table linking RouteSegments to POIs.

    This table stores REUSABLE data about POIs found during segment processing:
    - Which search point discovered the POI
    - Approximate straight-line distance

    IMPORTANT: Junction coordinates, side (left/right), and actual distances
    are calculated at map assembly time and stored in MapPOI, because they
    depend on the full route context (lookback of 10km for junction calculation).
    """

    __tablename__ = "segment_pois"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4
    )

    # Foreign keys
    segment_id: Mapped[PyUUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("route_segments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    poi_id: Mapped[PyUUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("pois.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Discovery data (reusable across maps)
    # Index of the search point that found this POI
    search_point_index: Mapped[int] = mapped_column(nullable=False)

    # Straight-line distance from search point to POI (approximate, for filtering)
    straight_line_distance_m: Mapped[int] = mapped_column(nullable=False)

    # Timestamp
    created_at: Mapped[datetime] = mapped_column(default=func.now())

    # Relationships
    segment: Mapped["RouteSegment"] = relationship(
        "RouteSegment", back_populates="segment_pois"
    )
    poi: Mapped["POI"] = relationship("POI", back_populates="segment_pois")

    # Indexes and constraints
    __table_args__ = (
        Index(
            "idx_segment_pois_segment_poi",
            "segment_id",
            "poi_id",
            unique=True,
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<SegmentPOI(segment_id={self.segment_id}, poi_id={self.poi_id}, "
            f"sp_index={self.search_point_index}, distance={self.straight_line_distance_m}m)>"
        )
