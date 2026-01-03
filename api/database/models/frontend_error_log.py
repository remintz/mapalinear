"""
Model for tracking frontend errors reported by the client application.
"""

from datetime import datetime
from typing import Optional
from uuid import uuid4

from sqlalchemy import Index, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from api.database.connection import Base


class FrontendErrorLog(Base):
    """
    Log entry for frontend errors.

    Tracks JavaScript errors, React errors, and API errors reported by
    the frontend application for debugging and monitoring purposes.
    """

    __tablename__ = "frontend_error_logs"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )

    # Session identification (correlates with api_call_logs)
    session_id: Mapped[str] = mapped_column(String(36), index=True)

    # Error classification
    error_type: Mapped[str] = mapped_column(String(50), index=True)
    # e.g., "unhandled_error", "unhandled_rejection", "react_error", "api_error"

    # Error details
    message: Mapped[str] = mapped_column(Text)
    stack_trace: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    component_stack: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    # React component stack for React errors

    # Context
    url: Mapped[str] = mapped_column(String(2000))
    user_agent: Mapped[str] = mapped_column(String(500))

    # User identification (optional - may not be logged in)
    user_id: Mapped[Optional[str]] = mapped_column(
        UUID(as_uuid=False), nullable=True, index=True
    )

    # Additional context (request info, browser state, etc.)
    extra_context: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    # Timestamp
    created_at: Mapped[datetime] = mapped_column(default=func.now(), index=True)

    # Indexes for efficient queries
    __table_args__ = (
        Index("idx_frontend_error_session_created", "session_id", "created_at"),
        Index("idx_frontend_error_type_created", "error_type", "created_at"),
        Index("idx_frontend_error_user_created", "user_id", "created_at"),
    )

    def __repr__(self) -> str:
        return (
            f"<FrontendErrorLog(id='{self.id[:8]}...', session='{self.session_id[:8]}...', "
            f"type='{self.error_type}', message='{self.message[:50]}...')>"
        )
