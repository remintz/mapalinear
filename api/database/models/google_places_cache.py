"""
Google Places Cache SQLAlchemy model.

Caches Google Places API responses to minimize API calls and costs.
"""
from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import CheckConstraint, Index, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import TIMESTAMP
from sqlalchemy.orm import Mapped, mapped_column

from api.database.connection import Base


class GooglePlacesCache(Base):
    """
    Cache for Google Places API responses.

    Stores rating and review data for POIs (restaurants, hotels) to avoid
    repeated API calls. Data is keyed by OSM POI ID.
    """

    __tablename__ = "google_places_cache"

    # Primary key - OSM POI identifier
    osm_poi_id: Mapped[str] = mapped_column(
        String(100), primary_key=True
    )

    # Google Place data
    google_place_id: Mapped[str] = mapped_column(
        String(200), nullable=False, index=True
    )
    rating: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(2, 1), nullable=True
    )  # 1.0 to 5.0
    user_rating_count: Mapped[Optional[int]] = mapped_column(nullable=True)
    google_maps_uri: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Match metadata
    matched_name: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    match_distance_meters: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(10, 2), nullable=True
    )

    # Search parameters (for debugging/auditing)
    search_latitude: Mapped[Decimal] = mapped_column(
        Numeric(10, 7), nullable=False
    )
    search_longitude: Mapped[Decimal] = mapped_column(
        Numeric(10, 7), nullable=False
    )
    search_name: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now()
    )
    expires_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False
    )

    # Constraints and indexes
    __table_args__ = (
        CheckConstraint(
            "rating IS NULL OR (rating >= 1.0 AND rating <= 5.0)",
            name="valid_rating"
        ),
        CheckConstraint(
            "user_rating_count IS NULL OR user_rating_count >= 0",
            name="valid_review_count"
        ),
        Index("idx_google_places_expires", "expires_at"),
        Index("idx_google_places_google_id", "google_place_id"),
    )

    def __repr__(self) -> str:
        return (
            f"<GooglePlacesCache(osm_poi_id='{self.osm_poi_id}', "
            f"rating={self.rating}, reviews={self.user_rating_count})>"
        )

    def is_expired(self) -> bool:
        """Check if the cache entry has expired."""
        return datetime.now(self.expires_at.tzinfo) > self.expires_at
