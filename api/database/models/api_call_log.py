"""
Model for tracking external API calls for cost monitoring.
"""

from datetime import datetime
from typing import Optional
from uuid import uuid4

from sqlalchemy import Index, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from api.database.connection import Base


class ApiCallLog(Base):
    """
    Log entry for external API calls.

    Tracks all calls to external APIs (OSM, HERE, Google Places) for
    cost monitoring and analysis purposes.
    """

    __tablename__ = "api_call_logs"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )

    # Provider identification
    provider: Mapped[str] = mapped_column(String(50), index=True)
    # e.g., "osm", "here", "google_places"

    # Operation type
    operation: Mapped[str] = mapped_column(String(100), index=True)
    # e.g., "geocode", "reverse_geocode", "poi_search", "route", "nearby_search"

    # API endpoint called
    endpoint: Mapped[str] = mapped_column(String(500))

    # HTTP method
    http_method: Mapped[str] = mapped_column(String(10), default="GET")

    # Request parameters (sanitized - no API keys)
    request_params: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    # Response information
    response_status: Mapped[int] = mapped_column()
    response_size_bytes: Mapped[Optional[int]] = mapped_column(nullable=True)

    # Timing
    duration_ms: Mapped[int] = mapped_column()

    # Cache information
    cache_hit: Mapped[bool] = mapped_column(default=False)

    # Result count (for searches)
    result_count: Mapped[Optional[int]] = mapped_column(nullable=True)

    # Error information (if any)
    error_message: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)

    # Timestamp
    created_at: Mapped[datetime] = mapped_column(default=func.now(), index=True)

    # Indexes for efficient queries and cost analysis
    __table_args__ = (
        Index("idx_api_call_provider_created", "provider", "created_at"),
        Index("idx_api_call_operation_created", "operation", "created_at"),
        Index("idx_api_call_provider_operation", "provider", "operation"),
    )

    def __repr__(self) -> str:
        return (
            f"<ApiCallLog(id='{self.id[:8]}...', provider='{self.provider}', "
            f"operation='{self.operation}', status={self.response_status})>"
        )
