"""
Report attachment model for storing files in database.
"""
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING
from uuid import uuid4

from sqlalchemy import ForeignKey, Integer, LargeBinary, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.database.connection import Base

if TYPE_CHECKING:
    from api.database.models.problem_report import ProblemReport


class AttachmentType(str, Enum):
    """Types of attachments that can be uploaded."""

    IMAGE = "image"
    AUDIO = "audio"


class ReportAttachment(Base):
    """
    Report attachment model for storing images and audio in database.

    Files are stored as binary data (BYTEA in PostgreSQL).
    """

    __tablename__ = "report_attachments"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    report_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("problem_reports.id", ondelete="CASCADE"),
        index=True,
    )
    type: Mapped[str] = mapped_column(String(20))  # "image" or "audio"
    filename: Mapped[str] = mapped_column(String(255))
    mime_type: Mapped[str] = mapped_column(String(100))
    size_bytes: Mapped[int] = mapped_column(Integer)
    data: Mapped[bytes] = mapped_column(LargeBinary)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(default=func.now())

    # Relationships
    report: Mapped["ProblemReport"] = relationship(
        "ProblemReport", back_populates="attachments"
    )

    def __repr__(self) -> str:
        return f"<ReportAttachment(id={self.id}, type='{self.type}', filename='{self.filename}')>"
