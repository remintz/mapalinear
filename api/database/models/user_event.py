"""
Model for tracking user events for analytics and usage statistics.
"""

from datetime import datetime
from typing import Optional
from uuid import uuid4

from sqlalchemy import Float, Index, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from api.database.connection import Base


class UserEvent(Base):
    """
    Log entry for user events and interactions.

    Tracks user behavior, feature usage, errors, and performance metrics
    for analytics and product improvement purposes.
    """

    __tablename__ = "user_events"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )

    # User identification (nullable for anonymous users)
    user_id: Mapped[Optional[str]] = mapped_column(
        UUID(as_uuid=False), nullable=True, index=True
    )

    # Event classification
    event_type: Mapped[str] = mapped_column(String(100), index=True)
    # e.g., "login", "page_view", "map_create", "poi_click", "api_error"

    event_category: Mapped[str] = mapped_column(String(50), index=True)
    # e.g., "auth", "navigation", "map_management", "error", "performance"

    # Flexible event data
    event_data: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    # Device information
    device_type: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    # "mobile", "tablet", "desktop"

    os: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    # e.g., "iOS 17", "Android 14", "Windows 11", "macOS 14"

    browser: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    # e.g., "Chrome 120", "Safari 17", "Firefox 121"

    screen_width: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    screen_height: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Session and navigation
    session_id: Mapped[str] = mapped_column(String(36), index=True)

    page_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    # e.g., "/map", "/search", "/maps"

    referrer: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Location (optional, for geographic analysis)
    latitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    longitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Performance metrics (for performance events)
    duration_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Error information (for error events)
    error_message: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)

    # Timestamp
    created_at: Mapped[datetime] = mapped_column(default=func.now(), index=True)

    # Composite indexes for efficient analytical queries
    __table_args__ = (
        Index("idx_user_event_type_created", "event_type", "created_at"),
        Index("idx_user_event_category_created", "event_category", "created_at"),
        Index("idx_user_event_session_created", "session_id", "created_at"),
        Index("idx_user_event_user_created", "user_id", "created_at"),
        Index("idx_user_event_device_created", "device_type", "created_at"),
        Index("idx_user_event_category_type", "event_category", "event_type"),
    )

    def __repr__(self) -> str:
        return (
            f"<UserEvent(id='{self.id[:8]}...', type='{self.event_type}', "
            f"category='{self.event_category}', user='{self.user_id or 'anon'}')>"
        )
