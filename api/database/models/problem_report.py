"""
Problem report model for user-submitted issues.
"""
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, List, Optional
from uuid import UUID as PyUUID
from uuid import uuid4

from sqlalchemy import Float, ForeignKey, Index, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.database.connection import Base

if TYPE_CHECKING:
    from api.database.models.map import Map
    from api.database.models.poi import POI
    from api.database.models.problem_type import ProblemType
    from api.database.models.report_attachment import ReportAttachment
    from api.database.models.user import User


class ReportStatus(str, Enum):
    """Status of a problem report."""

    NOVA = "nova"
    EM_ANDAMENTO = "em_andamento"
    CONCLUIDO = "concluido"


class ProblemReport(Base):
    """
    Problem report model for user-submitted issues.

    Stores reports with location, optional POI reference, and attachments.
    """

    __tablename__ = "problem_reports"

    id: Mapped[PyUUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    status: Mapped[str] = mapped_column(
        String(20), default=ReportStatus.NOVA.value, index=True
    )
    description: Mapped[str] = mapped_column(Text)

    # Location data (optional)
    latitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    longitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Foreign Keys
    problem_type_id: Mapped[PyUUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("problem_types.id")
    )
    user_id: Mapped[PyUUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id")
    )
    map_id: Mapped[Optional[PyUUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("maps.id"), nullable=True
    )
    poi_id: Mapped[Optional[PyUUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("pois.id"), nullable=True
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        default=func.now(), onupdate=func.now()
    )

    # Relationships
    problem_type: Mapped["ProblemType"] = relationship("ProblemType")
    user: Mapped["User"] = relationship("User")
    map: Mapped[Optional["Map"]] = relationship("Map")
    poi: Mapped[Optional["POI"]] = relationship("POI")
    attachments: Mapped[List["ReportAttachment"]] = relationship(
        "ReportAttachment",
        back_populates="report",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("idx_reports_status_created", "status", "created_at"),
        Index("idx_reports_user", "user_id"),
        Index("idx_reports_map", "map_id"),
    )

    def __repr__(self) -> str:
        return f"<ProblemReport(id={self.id}, status='{self.status}', user_id={self.user_id})>"
