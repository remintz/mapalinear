"""
Model for GPS debug logs for admin testing.

This model stores GPS position data and POI distance calculations
reported by admin users for debugging distance calculation issues.
"""

from datetime import datetime
from typing import Optional
from uuid import uuid4

from sqlalchemy import Float, Index, String, func
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP, UUID
from sqlalchemy.orm import Mapped, mapped_column

from api.database.connection import Base


class GPSDebugLog(Base):
    """
    Log entry for GPS debug data from admin users.

    Stores GPS coordinates, calculated distances, and nearby POI
    information for debugging distance calculation issues during
    real-world testing.
    """

    __tablename__ = "gps_debug_logs"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )

    # Timestamp when the log was created (with timezone)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), default=func.now(), index=True
    )

    # User who created the log (admin)
    user_id: Mapped[str] = mapped_column(UUID(as_uuid=False), index=True)
    user_email: Mapped[str] = mapped_column(String(320), index=True)

    # Map being viewed
    map_id: Mapped[str] = mapped_column(UUID(as_uuid=False), index=True)
    map_origin: Mapped[str] = mapped_column(String(500))
    map_destination: Mapped[str] = mapped_column(String(500))

    # GPS coordinates
    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)
    gps_accuracy: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Calculated position on route
    distance_from_origin_km: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    is_on_route: Mapped[bool] = mapped_column(default=False)
    distance_to_route_m: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # POIs data (2 previous + 5 next)
    # Structure: [{"id": "...", "name": "...", "type": "...", "distance_from_origin_km": ..., "relative_distance_km": ...}]
    previous_pois: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)
    next_pois: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)

    # Session info
    session_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True, index=True)
    user_agent: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Indexes for efficient queries
    __table_args__ = (
        Index("idx_gps_debug_user_created", "user_id", "created_at"),
        Index("idx_gps_debug_map_created", "map_id", "created_at"),
        Index("idx_gps_debug_coords", "latitude", "longitude"),
    )

    def __repr__(self) -> str:
        return (
            f"<GPSDebugLog(id='{self.id[:8]}...', user='{self.user_email}', "
            f"map='{self.map_id[:8]}...', lat={self.latitude:.5f}, lon={self.longitude:.5f})>"
        )
