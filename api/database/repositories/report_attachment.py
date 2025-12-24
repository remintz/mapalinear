"""Repository for report attachment operations."""

from typing import List, Optional
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.database.models.report_attachment import ReportAttachment
from api.database.repositories.base import BaseRepository


class ReportAttachmentRepository(BaseRepository[ReportAttachment]):
    """Repository for report attachment CRUD operations."""

    def __init__(self, session: AsyncSession):
        super().__init__(session, ReportAttachment)

    async def get_by_report(self, report_id: UUID) -> List[ReportAttachment]:
        """Get all attachments for a report."""
        result = await self.session.execute(
            select(ReportAttachment)
            .where(ReportAttachment.report_id == report_id)
            .order_by(ReportAttachment.created_at)
        )
        return list(result.scalars().all())

    async def create_attachment(
        self,
        report_id: UUID,
        type: str,
        filename: str,
        mime_type: str,
        size_bytes: int,
        data: bytes,
    ) -> ReportAttachment:
        """Create a new attachment."""
        attachment = ReportAttachment(
            report_id=report_id,
            type=type,
            filename=filename,
            mime_type=mime_type,
            size_bytes=size_bytes,
            data=data,
        )
        return await self.create(attachment)

    async def delete_by_report(self, report_id: UUID) -> int:
        """Delete all attachments for a report. Returns count of deleted."""
        result = await self.session.execute(
            delete(ReportAttachment)
            .where(ReportAttachment.report_id == report_id)
            .returning(ReportAttachment.id)
        )
        await self.session.flush()
        return len(result.all())

    async def get_images_by_report(self, report_id: UUID) -> List[ReportAttachment]:
        """Get only image attachments for a report."""
        result = await self.session.execute(
            select(ReportAttachment)
            .where(
                ReportAttachment.report_id == report_id,
                ReportAttachment.type == "image",
            )
            .order_by(ReportAttachment.created_at)
        )
        return list(result.scalars().all())

    async def get_audio_by_report(self, report_id: UUID) -> Optional[ReportAttachment]:
        """Get the audio attachment for a report (if any)."""
        result = await self.session.execute(
            select(ReportAttachment)
            .where(
                ReportAttachment.report_id == report_id,
                ReportAttachment.type == "audio",
            )
            .limit(1)
        )
        return result.scalar_one_or_none()
