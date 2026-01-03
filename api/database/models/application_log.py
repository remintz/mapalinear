"""
Model for storing application logs in the database.

This model captures logs from the Python logging system for
monitoring and debugging through the admin interface.
"""

from datetime import datetime
from typing import Optional
from uuid import uuid4

from sqlalchemy import Index, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from api.database.connection import Base


class ApplicationLog(Base):
    """
    Log entry from the application logging system.

    Stores logs from Python's logging module with context information
    (request_id, session_id, user_id) for correlation and filtering.
    """

    __tablename__ = "application_logs"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )

    # Timestamp when the log was created
    timestamp: Mapped[datetime] = mapped_column(default=func.now(), index=True)

    # Log level as string (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    level: Mapped[str] = mapped_column(String(20), index=True)

    # Numeric log level for efficient filtering (10=DEBUG, 20=INFO, 30=WARNING, 40=ERROR, 50=CRITICAL)
    level_no: Mapped[int] = mapped_column(index=True)

    # Logger name (module path, e.g., "api.services.road_service")
    module: Mapped[str] = mapped_column(String(255), index=True)

    # Log message content
    message: Mapped[str] = mapped_column(Text)

    # Context tracking - IDs for request correlation
    request_id: Mapped[Optional[str]] = mapped_column(
        String(16), nullable=True, index=True
    )
    session_id: Mapped[Optional[str]] = mapped_column(
        String(36), nullable=True, index=True
    )
    user_email: Mapped[Optional[str]] = mapped_column(
        String(320), nullable=True, index=True
    )

    # Source code location
    func_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    line_no: Mapped[Optional[int]] = mapped_column(nullable=True)

    # Exception traceback (if any)
    exc_info: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Composite indexes for common query patterns
    __table_args__ = (
        Index("idx_app_log_timestamp_level", "timestamp", "level_no"),
        Index("idx_app_log_module_timestamp", "module", "timestamp"),
        Index("idx_app_log_user_email_timestamp", "user_email", "timestamp"),
        Index("idx_app_log_session_timestamp", "session_id", "timestamp"),
        Index("idx_app_log_request_timestamp", "request_id", "timestamp"),
    )

    def __repr__(self) -> str:
        return (
            f"<ApplicationLog(id='{self.id[:8]}...', level='{self.level}', "
            f"module='{self.module}', message='{self.message[:50]}...')>"
        )
