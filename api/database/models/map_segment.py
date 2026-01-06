"""
MapSegment SQLAlchemy model.

Links Maps to RouteSegments with order and distance information.
"""
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import UUID as PyUUID
from uuid import uuid4

from sqlalchemy import ForeignKey, Index, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.database.connection import Base

if TYPE_CHECKING:
    from api.database.models.map import Map
    from api.database.models.route_segment import RouteSegment


class MapSegment(Base):
    """
    Junction table linking Maps to RouteSegments.

    Stores the order of segments within a map and the cumulative
    distance from the origin to the start of each segment.
    """

    __tablename__ = "map_segments"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4
    )

    # Foreign keys
    map_id: Mapped[PyUUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("maps.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    segment_id: Mapped[PyUUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("route_segments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Order within the map (0, 1, 2, ...)
    sequence_order: Mapped[int] = mapped_column(nullable=False)

    # Cumulative distance from map origin to start of this segment
    distance_from_origin_km: Mapped[Decimal] = mapped_column(nullable=False)

    # Timestamp
    created_at: Mapped[datetime] = mapped_column(default=func.now())

    # Relationships
    map: Mapped["Map"] = relationship("Map", back_populates="map_segments")
    segment: Mapped["RouteSegment"] = relationship(
        "RouteSegment", back_populates="map_segments"
    )

    # Indexes and constraints
    __table_args__ = (
        Index("idx_map_segments_map_order", "map_id", "sequence_order"),
        Index(
            "idx_map_segments_map_segment",
            "map_id",
            "segment_id",
            unique=True,
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<MapSegment(map_id={self.map_id}, segment_id={self.segment_id}, "
            f"order={self.sequence_order}, distance={self.distance_from_origin_km}km)>"
        )
