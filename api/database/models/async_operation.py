"""
Model for async operations tracking.
"""

from datetime import datetime
from typing import Optional
from uuid import uuid4

from sqlalchemy import ForeignKey, Index, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.database.connection import Base


class AsyncOperation(Base):
    """
    Database model for tracking async operations.

    Replaces the file-based storage in cache/async_operations/
    """

    __tablename__ = "async_operations"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )

    # Operation type (e.g., "linear_map")
    operation_type: Mapped[str] = mapped_column(String(100), index=True)

    # Status: in_progress, completed, failed
    status: Mapped[str] = mapped_column(String(20), index=True, default="in_progress")

    # Progress percentage (0-100)
    progress_percent: Mapped[float] = mapped_column(default=0.0)

    # User who requested the operation (optional for backwards compatibility)
    user_id: Mapped[Optional[str]] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Timestamps
    started_at: Mapped[datetime] = mapped_column(default=func.now(), index=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)

    # Estimated completion time
    estimated_completion: Mapped[Optional[datetime]] = mapped_column(nullable=True)

    # Result data (JSON) - stored when operation completes
    result: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    # Error message if operation failed
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationship to user
    user = relationship("User", foreign_keys=[user_id], lazy="joined")

    # Indexes for efficient queries
    __table_args__ = (
        Index("idx_async_op_status_started", "status", "started_at"),
        Index("idx_async_op_type_status", "operation_type", "status"),
    )

    def __repr__(self) -> str:
        return (
            f"<AsyncOperation(id='{self.id[:8]}...', type='{self.operation_type}', "
            f"status='{self.status}', progress={self.progress_percent}%)>"
        )
