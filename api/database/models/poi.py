"""
POI (Point of Interest) SQLAlchemy model.

Supports multiple data providers (OSM, HERE, Google) with enrichment capabilities.
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
    Supports data from multiple providers (OSM, HERE, Google Places).

    Provider IDs:
    - osm_id: OpenStreetMap node/way ID
    - here_id: HERE Maps place ID

    The primary_provider field indicates which provider originally created this POI.
    Additional providers can enrich the data without creating duplicates.
    """

    __tablename__ = "pois"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4
    )

    # Provider identification
    primary_provider: Mapped[str] = mapped_column(
        String(20), index=True, default="osm"
    )  # osm, here, google
    osm_id: Mapped[Optional[str]] = mapped_column(
        String(100), unique=True, index=True, nullable=True
    )
    here_id: Mapped[Optional[str]] = mapped_column(
        String(100), unique=True, index=True, nullable=True
    )

    # Core POI data
    name: Mapped[str] = mapped_column(String(500), index=True)
    type: Mapped[str] = mapped_column(String(50), index=True)  # MilestoneType.value
    latitude: Mapped[float] = mapped_column()
    longitude: Mapped[float] = mapped_column()

    # Enriched metadata (can come from any provider)
    city: Mapped[Optional[str]] = mapped_column(String(200), index=True, nullable=True)
    operator: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    brand: Mapped[Optional[str]] = mapped_column(String(200), index=True, nullable=True)
    opening_hours: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    website: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    cuisine: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)

    # Google Places ratings (for restaurants and hotels)
    rating: Mapped[Optional[float]] = mapped_column(nullable=True)  # 1.0 to 5.0
    rating_count: Mapped[Optional[int]] = mapped_column(nullable=True)  # Number of reviews
    google_maps_uri: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # HERE Maps specific data (structured address, references, etc.)
    here_data: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    # Example here_data structure:
    # {
    #     "address": {
    #         "street": "Rua dos Paulistas",
    #         "houseNumber": "43",
    #         "district": "Centro",
    #         "postalCode": "35400-030"
    #     },
    #     "references": {
    #         "tripadvisor": "2402590",
    #         "yelp": "Nv_URBAb-MwPzUO0qwxrNQ"
    #     },
    #     "categories": [{"id": "500-5000-0053", "name": "Hotel"}]
    # }

    # JSONB fields for flexible data
    amenities: Mapped[list] = mapped_column(JSONB, default=list)
    tags: Mapped[dict] = mapped_column(JSONB, default=dict)

    # Enrichment tracking
    enriched_by: Mapped[list] = mapped_column(JSONB, default=list)
    # Example: ["google_places", "here_maps"]
    last_enriched_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)

    # Reference tracking - indicates if this POI is used in any map
    # POIs with is_referenced=False don't need enrichment
    is_referenced: Mapped[bool] = mapped_column(default=False, index=True)

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
        Index("idx_pois_provider", "primary_provider"),
    )

    def __repr__(self) -> str:
        return f"<POI(id={self.id}, name='{self.name}', type='{self.type}', provider='{self.primary_provider}')>"

    def is_enriched_by(self, provider: str) -> bool:
        """Check if this POI has been enriched by a specific provider."""
        return provider in (self.enriched_by or [])

    def add_enrichment(self, provider: str) -> None:
        """Mark this POI as enriched by a provider."""
        if self.enriched_by is None:
            self.enriched_by = []
        if provider not in self.enriched_by:
            self.enriched_by.append(provider)
            self.last_enriched_at = datetime.utcnow()
