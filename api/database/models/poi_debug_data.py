"""
POI Debug Data SQLAlchemy model.

Stores detailed calculation data for POI side determination and access route calculation.
This data is used to visualize and debug how each POI's position was determined.
"""
from datetime import datetime
from typing import TYPE_CHECKING, Optional, List, Dict, Any
from uuid import UUID as PyUUID
from uuid import uuid4

from sqlalchemy import ForeignKey, Index, String, Float, Boolean, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.database.connection import Base

if TYPE_CHECKING:
    from api.database.models.map import Map
    from api.database.models.map_poi import MapPOI


class POIDebugData(Base):
    """
    Debug data for POI calculation visualization.

    Stores all geometric and calculation data needed to visualize
    and debug POI side determination and access route calculation.

    Key data stored:
    - main_route_segment: The portion of the main route near the POI
    - access_route_geometry: The calculated route from junction to POI
    - side_calculation: Vectors and cross product used to determine left/right
    - lookback_data: Parameters used for distant POI junction calculation
    - recalculation_history: History of junction optimization attempts
    """

    __tablename__ = "poi_debug_data"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    map_id: Mapped[PyUUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("maps.id", ondelete="CASCADE"),
        index=True,
    )
    map_poi_id: Mapped[PyUUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("map_pois.id", ondelete="CASCADE"),
        index=True,
    )

    # POI identification
    poi_name: Mapped[str] = mapped_column(String(500))
    poi_type: Mapped[str] = mapped_column(String(50))

    # POI location
    poi_lat: Mapped[float] = mapped_column(Float)
    poi_lon: Mapped[float] = mapped_column(Float)

    # Main route segment near POI (list of [lat, lon] points)
    # Stores approximately ±50 points around the POI location
    main_route_segment: Mapped[Optional[List[List[float]]]] = mapped_column(
        JSONB, nullable=True, default=list
    )
    # Start/end indices of segment in full route geometry
    segment_start_idx: Mapped[Optional[int]] = mapped_column(nullable=True)
    segment_end_idx: Mapped[Optional[int]] = mapped_column(nullable=True)

    # Junction/exit point on main route
    junction_lat: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    junction_lon: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    junction_distance_km: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Access route geometry (from junction to POI)
    # List of [lat, lon] points representing the route to reach the POI
    access_route_geometry: Mapped[Optional[List[List[float]]]] = mapped_column(
        JSONB, nullable=True
    )
    access_route_distance_km: Mapped[Optional[float]] = mapped_column(
        Float, nullable=True
    )

    # Side calculation details
    # Structure:
    # {
    #     "road_vector": {"dx": float, "dy": float},
    #     "poi_vector": {"dx": float, "dy": float},
    #     "cross_product": float,
    #     "resulting_side": "left" | "right",
    #     "segment_start": {"lat": float, "lon": float},
    #     "segment_end": {"lat": float, "lon": float},
    #     "segment_idx": int
    # }
    side_calculation: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB, nullable=True, default=dict
    )

    # Lookback calculation for distant POIs
    # Structure:
    # {
    #     "poi_distance_from_road_m": float,
    #     "lookback_km": float,
    #     "lookback_distance_km": float,
    #     "lookback_point": {"lat": float, "lon": float},
    #     "search_point": {"lat": float, "lon": float},
    #     "search_point_distance_km": float
    # }
    lookback_data: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB, nullable=True
    )

    # Recalculation attempts (for debugging optimization)
    # List of:
    # {
    #     "attempt": int,
    #     "search_point": {"lat": float, "lon": float},
    #     "search_point_distance_km": float,
    #     "junction_found": bool,
    #     "junction_distance_km": float | null,
    #     "access_route_distance_km": float | null,
    #     "improvement": bool,
    #     "reason": str | null  # Why skipped or failed
    # }
    recalculation_history: Mapped[Optional[List[Dict[str, Any]]]] = mapped_column(
        JSONB, nullable=True
    )

    # Final result
    final_side: Mapped[str] = mapped_column(String(20))  # "left", "right", "center"
    requires_detour: Mapped[bool] = mapped_column(Boolean, default=False)
    distance_from_road_m: Mapped[float] = mapped_column(Float)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(default=func.now())

    # Relationships
    map: Mapped["Map"] = relationship("Map")
    map_poi: Mapped["MapPOI"] = relationship("MapPOI")

    # Indexes for efficient queries
    __table_args__ = (
        Index("idx_poi_debug_map", "map_id"),
        Index("idx_poi_debug_map_poi", "map_poi_id"),
    )

    def __repr__(self) -> str:
        return (
            f"<POIDebugData(map_id={self.map_id}, "
            f"poi_name='{self.poi_name}', side='{self.final_side}')>"
        )
