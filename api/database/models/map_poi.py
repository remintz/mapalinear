"""
MapPOI (junction table) SQLAlchemy model.
"""
from typing import TYPE_CHECKING, Optional
from uuid import UUID as PyUUID
from uuid import uuid4

from sqlalchemy import ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.database.connection import Base

if TYPE_CHECKING:
    from api.database.models.map import Map
    from api.database.models.poi import POI


class MapPOI(Base):
    """
    Junction table linking Maps to POIs with position-specific data.

    This table stores the relationship between a map and its POIs,
    including position data that is specific to how the POI appears
    on that particular map (distance from origin, side of road, etc).
    """

    __tablename__ = "map_pois"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    map_id: Mapped[PyUUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("maps.id", ondelete="CASCADE"),
        index=True,
    )
    poi_id: Mapped[PyUUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("pois.id", ondelete="CASCADE"),
        index=True,
    )

    # Position data specific to this map
    segment_index: Mapped[Optional[int]] = mapped_column(nullable=True)
    distance_from_origin_km: Mapped[float] = mapped_column()
    distance_from_road_meters: Mapped[float] = mapped_column()
    side: Mapped[str] = mapped_column(String(20))  # "left", "right", "center"

    # Junction/detour information
    junction_distance_km: Mapped[Optional[float]] = mapped_column(nullable=True)
    junction_lat: Mapped[Optional[float]] = mapped_column(nullable=True)
    junction_lon: Mapped[Optional[float]] = mapped_column(nullable=True)
    requires_detour: Mapped[bool] = mapped_column(default=False)

    # Quality score for this POI on this map
    quality_score: Mapped[Optional[float]] = mapped_column(nullable=True)

    # Relationships
    map: Mapped["Map"] = relationship("Map", back_populates="map_pois")
    poi: Mapped["POI"] = relationship("POI", back_populates="map_pois")

    # Indexes for efficient queries
    __table_args__ = (
        Index("idx_map_pois_map_distance", "map_id", "distance_from_origin_km"),
        Index("idx_map_pois_map_poi", "map_id", "poi_id", unique=True),
    )

    def __repr__(self) -> str:
        return f"<MapPOI(map_id={self.map_id}, poi_id={self.poi_id}, distance={self.distance_from_origin_km}km)>"
