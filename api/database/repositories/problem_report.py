"""Repository for problem report operations."""

from typing import Dict, List, Optional
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from api.database.models.problem_report import ProblemReport, ReportStatus
from api.database.repositories.base import BaseRepository


class ProblemReportRepository(BaseRepository[ProblemReport]):
    """Repository for problem report CRUD operations."""

    def __init__(self, session: AsyncSession):
        super().__init__(session, ProblemReport)

    async def get_by_id_with_relations(self, id: UUID) -> Optional[ProblemReport]:
        """Get a report by ID with all relationships loaded."""
        result = await self.session.execute(
            select(ProblemReport)
            .where(ProblemReport.id == id)
            .options(
                selectinload(ProblemReport.problem_type),
                selectinload(ProblemReport.user),
                selectinload(ProblemReport.map),
                selectinload(ProblemReport.poi),
                selectinload(ProblemReport.attachments),
            )
        )
        return result.scalar_one_or_none()

    async def get_all_with_relations(
        self,
        skip: int = 0,
        limit: int = 50,
        status: Optional[str] = None,
        map_id: Optional[UUID] = None,
    ) -> List[ProblemReport]:
        """Get all reports with relationships, optionally filtered."""
        query = select(ProblemReport).options(
            selectinload(ProblemReport.problem_type),
            selectinload(ProblemReport.user),
            selectinload(ProblemReport.map),
            selectinload(ProblemReport.poi),
            selectinload(ProblemReport.attachments),
        )

        if status:
            query = query.where(ProblemReport.status == status)
        if map_id:
            query = query.where(ProblemReport.map_id == map_id)

        query = query.order_by(ProblemReport.created_at.desc())
        query = query.offset(skip).limit(limit)

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def create_report(
        self,
        problem_type_id: UUID,
        user_id: UUID,
        description: str,
        latitude: float,
        longitude: float,
        map_id: Optional[UUID] = None,
        poi_id: Optional[UUID] = None,
    ) -> ProblemReport:
        """Create a new problem report."""
        report = ProblemReport(
            problem_type_id=problem_type_id,
            user_id=user_id,
            description=description,
            latitude=latitude,
            longitude=longitude,
            map_id=map_id,
            poi_id=poi_id,
            status=ReportStatus.NOVA.value,
        )
        return await self.create(report)

    async def update_status(self, id: UUID, status: str) -> Optional[ProblemReport]:
        """Update the status of a report."""
        report = await self.get_by_id(id)
        if not report:
            return None

        report.status = status
        return await self.update(report)

    async def count_by_status(self) -> Dict[str, int]:
        """Get count of reports grouped by status."""
        result = await self.session.execute(
            select(ProblemReport.status, func.count(ProblemReport.id))
            .group_by(ProblemReport.status)
        )
        counts = {status.value: 0 for status in ReportStatus}
        for row in result.all():
            counts[row[0]] = row[1]
        return counts

    async def get_total_count(
        self,
        status: Optional[str] = None,
        map_id: Optional[UUID] = None,
    ) -> int:
        """Get total count of reports, optionally filtered."""
        query = select(func.count(ProblemReport.id))

        if status:
            query = query.where(ProblemReport.status == status)
        if map_id:
            query = query.where(ProblemReport.map_id == map_id)

        result = await self.session.execute(query)
        return result.scalar_one()

    async def get_by_user(
        self,
        user_id: UUID,
        skip: int = 0,
        limit: int = 50,
    ) -> List[ProblemReport]:
        """Get reports by user."""
        result = await self.session.execute(
            select(ProblemReport)
            .where(ProblemReport.user_id == user_id)
            .options(
                selectinload(ProblemReport.problem_type),
                selectinload(ProblemReport.map),
            )
            .order_by(ProblemReport.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())
