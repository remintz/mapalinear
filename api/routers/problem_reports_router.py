"""
Problem reports router for user and admin endpoints.
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Response, UploadFile, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from api.database.connection import get_db
from api.database.models.problem_report import ReportStatus
from api.database.models.user import User
from api.database.repositories.problem_report import ProblemReportRepository
from api.database.repositories.problem_type import ProblemTypeRepository
from api.database.repositories.report_attachment import ReportAttachmentRepository
from api.middleware.auth import get_current_admin, get_current_user
from api.services.auth_service import AuthError, AuthService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/reports", tags=["reports"])

# Security scheme for optional auth header
security = HTTPBearer(auto_error=False)

# Constants
MAX_PHOTOS = 3
MAX_AUDIO = 1
MAX_FILE_SIZE_MB = 10
ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}
ALLOWED_AUDIO_TYPES = {"audio/webm", "audio/mp3", "audio/mpeg", "audio/wav", "audio/ogg", "audio/mp4"}


# Response models
class ProblemTypePublicResponse(BaseModel):
    """Problem type for public use."""

    id: str = Field(..., description="Problem type UUID")
    name: str = Field(..., description="Problem type name")
    description: Optional[str] = Field(None, description="Problem type description")


class ProblemTypesListResponse(BaseModel):
    """List of problem types for public use."""

    types: List[ProblemTypePublicResponse]


class AttachmentResponse(BaseModel):
    """Attachment metadata response."""

    id: str = Field(..., description="Attachment UUID")
    type: str = Field(..., description="Attachment type (image/audio)")
    filename: str = Field(..., description="Original filename")
    mime_type: str = Field(..., description="MIME type")
    size_bytes: int = Field(..., description="File size in bytes")


class UserResponse(BaseModel):
    """Basic user info for reports."""

    id: str
    name: str
    email: str
    avatar_url: Optional[str] = None


class MapResponse(BaseModel):
    """Basic map info for reports."""

    id: str
    origin: str
    destination: str


class POIResponse(BaseModel):
    """Basic POI info for reports."""

    id: str
    name: str
    type: str
    latitude: float
    longitude: float


class ProblemReportResponse(BaseModel):
    """Problem report response."""

    id: str = Field(..., description="Report UUID")
    status: str = Field(..., description="Report status")
    description: str = Field(..., description="Problem description")
    latitude: Optional[float] = Field(None, description="Location latitude")
    longitude: Optional[float] = Field(None, description="Location longitude")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    problem_type: ProblemTypePublicResponse
    user: UserResponse
    map: Optional[MapResponse] = None
    poi: Optional[POIResponse] = None
    attachments: List[AttachmentResponse] = []

    attachment_count: int = Field(0, description="Number of attachments")


class ProblemReportListResponse(BaseModel):
    """List of problem reports."""

    reports: List[ProblemReportResponse]
    total: int = Field(..., description="Total number of reports")
    counts_by_status: Dict[str, int] = Field(..., description="Count by status")


class CreateReportResponse(BaseModel):
    """Response after creating a report."""

    id: str = Field(..., description="Created report UUID")
    message: str = Field(..., description="Success message")


class UpdateStatusRequest(BaseModel):
    """Request to update report status."""

    status: str = Field(..., description="New status (nova, em_andamento, concluido)")


# Public endpoints (authenticated users)


@router.get("/types", response_model=ProblemTypesListResponse)
async def get_problem_types(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ProblemTypesListResponse:
    """
    Get all active problem types.

    Returns:
        List of active problem types for the report form
    """
    repo = ProblemTypeRepository(db)
    types = await repo.get_all_active()

    return ProblemTypesListResponse(
        types=[
            ProblemTypePublicResponse(
                id=str(t.id),
                name=t.name,
                description=t.description,
            )
            for t in types
        ]
    )


@router.post("", response_model=CreateReportResponse, status_code=status.HTTP_201_CREATED)
async def create_report(
    problem_type_id: str = Form(..., description="Problem type UUID"),
    description: str = Form(..., min_length=10, description="Problem description"),
    latitude: Optional[float] = Form(None, description="User latitude"),
    longitude: Optional[float] = Form(None, description="User longitude"),
    map_id: Optional[str] = Form(None, description="Current map UUID"),
    poi_id: Optional[str] = Form(None, description="Selected POI UUID"),
    photos: List[UploadFile] = File(default=[], description="Photo attachments (max 3)"),
    audio: Optional[UploadFile] = File(None, description="Audio attachment (max 1)"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CreateReportResponse:
    """
    Submit a new problem report.

    Accepts multipart form data with optional photo and audio attachments.
    Photos and audio are stored in the database as binary data.

    Args:
        problem_type_id: UUID of the problem type
        description: Detailed description of the problem
        latitude: Optional user's current latitude
        longitude: Optional user's current longitude
        map_id: Optional UUID of the current map
        poi_id: Optional UUID of the selected POI
        photos: Up to 3 photo files
        audio: Optional audio recording

    Returns:
        Created report ID and success message
    """
    # Validate problem type ID
    try:
        pt_uuid = UUID(problem_type_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="ID de tipo de problema invalido",
        )

    # Validate optional UUIDs
    map_uuid = None
    if map_id:
        try:
            map_uuid = UUID(map_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="ID de mapa invalido",
            )

    poi_uuid = None
    if poi_id:
        try:
            poi_uuid = UUID(poi_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="ID de POI invalido",
            )

    # Validate problem type exists
    pt_repo = ProblemTypeRepository(db)
    problem_type = await pt_repo.get_by_id(pt_uuid)
    if not problem_type or not problem_type.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tipo de problema invalido ou inativo",
        )

    # Validate photo count
    if len(photos) > MAX_PHOTOS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Maximo de {MAX_PHOTOS} fotos permitidas",
        )

    # Create the report
    report_repo = ProblemReportRepository(db)
    report = await report_repo.create_report(
        problem_type_id=pt_uuid,
        user_id=current_user.id,
        description=description,
        latitude=latitude,
        longitude=longitude,
        map_id=map_uuid,
        poi_id=poi_uuid,
    )

    # Process attachments
    attachment_repo = ReportAttachmentRepository(db)

    # Process photos
    for photo in photos:
        if photo.filename and photo.size > 0:
            # Validate file type
            if photo.content_type not in ALLOWED_IMAGE_TYPES:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Tipo de imagem nao permitido: {photo.content_type}",
                )

            # Validate file size
            if photo.size > MAX_FILE_SIZE_MB * 1024 * 1024:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Imagem muito grande. Maximo: {MAX_FILE_SIZE_MB}MB",
                )

            # Read and store
            data = await photo.read()
            await attachment_repo.create_attachment(
                report_id=report.id,
                type="image",
                filename=photo.filename,
                mime_type=photo.content_type,
                size_bytes=len(data),
                data=data,
            )

    # Process audio
    if audio and audio.filename and audio.size > 0:
        # Validate file type
        if audio.content_type not in ALLOWED_AUDIO_TYPES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Tipo de audio nao permitido: {audio.content_type}",
            )

        # Validate file size
        if audio.size > MAX_FILE_SIZE_MB * 1024 * 1024:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Audio muito grande. Maximo: {MAX_FILE_SIZE_MB}MB",
            )

        # Read and store
        data = await audio.read()
        await attachment_repo.create_attachment(
            report_id=report.id,
            type="audio",
            filename=audio.filename,
            mime_type=audio.content_type,
            size_bytes=len(data),
            data=data,
        )

    await db.commit()

    logger.info(
        f"Problem report created by {current_user.email}: "
        f"type={problem_type.name}, map_id={map_id}, poi_id={poi_id}"
    )

    return CreateReportResponse(
        id=str(report.id),
        message="Problema reportado com sucesso!",
    )


# Admin endpoints


@router.get("", response_model=ProblemReportListResponse)
async def list_reports(
    skip: int = 0,
    limit: int = 50,
    status_filter: Optional[str] = None,
    map_id: Optional[str] = None,
    admin_user: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> ProblemReportListResponse:
    """
    List all problem reports.

    Requires admin privileges.

    Args:
        skip: Number of records to skip
        limit: Maximum records to return
        status_filter: Filter by status
        map_id: Filter by map

    Returns:
        List of reports with counts
    """
    # Validate status filter
    if status_filter and status_filter not in [s.value for s in ReportStatus]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Status invalido",
        )

    # Validate map_id
    map_uuid = None
    if map_id:
        try:
            map_uuid = UUID(map_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="ID de mapa invalido",
            )

    repo = ProblemReportRepository(db)
    reports = await repo.get_all_with_relations(
        skip=skip,
        limit=limit,
        status=status_filter,
        map_id=map_uuid,
    )

    total = await repo.get_total_count(status=status_filter, map_id=map_uuid)
    counts = await repo.count_by_status()

    return ProblemReportListResponse(
        reports=[_format_report(r) for r in reports],
        total=total,
        counts_by_status=counts,
    )


@router.get("/{report_id}", response_model=ProblemReportResponse)
async def get_report(
    report_id: str,
    admin_user: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> ProblemReportResponse:
    """
    Get a specific report by ID.

    Requires admin privileges.

    Args:
        report_id: UUID of the report

    Returns:
        Report details with attachments
    """
    try:
        uuid = UUID(report_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="ID de report invalido",
        )

    repo = ProblemReportRepository(db)
    report = await repo.get_by_id_with_relations(uuid)

    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report nao encontrado",
        )

    return _format_report(report)


@router.put("/{report_id}/status", response_model=ProblemReportResponse)
async def update_report_status(
    report_id: str,
    request: UpdateStatusRequest,
    admin_user: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> ProblemReportResponse:
    """
    Update the status of a report.

    Requires admin privileges.

    Args:
        report_id: UUID of the report
        request: New status

    Returns:
        Updated report
    """
    try:
        uuid = UUID(report_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="ID de report invalido",
        )

    # Validate status
    if request.status not in [s.value for s in ReportStatus]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Status invalido. Use: nova, em_andamento, concluido",
        )

    repo = ProblemReportRepository(db)
    report = await repo.update_status(uuid, request.status)

    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report nao encontrado",
        )

    await db.commit()

    # Reload with relations
    report = await repo.get_by_id_with_relations(uuid)

    logger.info(f"Report {report_id} status updated to {request.status} by {admin_user.email}")

    return _format_report(report)


class DeleteReportResponse(BaseModel):
    """Response after deleting a report."""

    message: str = Field(..., description="Success message")


@router.delete("/{report_id}", response_model=DeleteReportResponse)
async def delete_report(
    report_id: str,
    admin_user: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> DeleteReportResponse:
    """
    Delete a problem report.

    Requires admin privileges.
    All attachments are automatically deleted via database cascade.

    Args:
        report_id: UUID of the report to delete

    Returns:
        Success message
    """
    try:
        uuid = UUID(report_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="ID de report invalido",
        )

    repo = ProblemReportRepository(db)
    deleted = await repo.delete_by_id(uuid)

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report nao encontrado",
        )

    await db.commit()

    logger.info(f"Report {report_id} deleted by {admin_user.email}")

    return DeleteReportResponse(message="Report excluido com sucesso")


@router.get("/{report_id}/attachments/{attachment_id}")
async def get_attachment(
    report_id: str,
    attachment_id: str,
    token: Optional[str] = Query(None, description="JWT token for img src authentication"),
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> Response:
    """
    Download an attachment.

    Requires admin privileges.
    Supports authentication via either Authorization header or token query parameter.
    The token query parameter is useful for img src tags which can't send headers.

    Args:
        report_id: UUID of the report
        attachment_id: UUID of the attachment
        token: Optional JWT token as query parameter (for img src)

    Returns:
        File content with appropriate MIME type
    """
    # Authenticate using token or header
    auth_service = AuthService(db)
    jwt_token = token
    if not jwt_token and credentials:
        jwt_token = credentials.credentials

    if not jwt_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    try:
        verify_result = await auth_service.verify_jwt(jwt_token)
        user = verify_result.user
    except AuthError as e:
        raise HTTPException(
            status_code=e.status_code,
            detail=e.message,
        )

    if not user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required",
        )

    try:
        att_uuid = UUID(attachment_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="ID de anexo invalido",
        )

    repo = ReportAttachmentRepository(db)
    attachment = await repo.get_by_id(att_uuid)

    if not attachment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Anexo nao encontrado",
        )

    # Verify attachment belongs to the report
    if str(attachment.report_id) != report_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Anexo nao encontrado",
        )

    return Response(
        content=attachment.data,
        media_type=attachment.mime_type,
        headers={
            "Content-Disposition": f'inline; filename="{attachment.filename}"',
        },
    )


def _format_report(report) -> ProblemReportResponse:
    """Format a report model to response."""
    return ProblemReportResponse(
        id=str(report.id),
        status=report.status,
        description=report.description,
        latitude=report.latitude,
        longitude=report.longitude,
        created_at=report.created_at,
        updated_at=report.updated_at,
        problem_type=ProblemTypePublicResponse(
            id=str(report.problem_type.id),
            name=report.problem_type.name,
            description=report.problem_type.description,
        ),
        user=UserResponse(
            id=str(report.user.id),
            name=report.user.name,
            email=report.user.email,
            avatar_url=report.user.avatar_url,
        ),
        map=MapResponse(
            id=str(report.map.id),
            origin=report.map.origin,
            destination=report.map.destination,
        ) if report.map else None,
        poi=POIResponse(
            id=str(report.poi.id),
            name=report.poi.name,
            type=report.poi.type,
            latitude=report.poi.latitude,
            longitude=report.poi.longitude,
        ) if report.poi else None,
        attachments=[
            AttachmentResponse(
                id=str(a.id),
                type=a.type,
                filename=a.filename,
                mime_type=a.mime_type,
                size_bytes=a.size_bytes,
            )
            for a in (report.attachments or [])
        ],
        attachment_count=len(report.attachments) if report.attachments else 0,
    )
