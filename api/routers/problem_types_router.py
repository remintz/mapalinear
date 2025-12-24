"""
Problem types router for admin endpoints.
"""

import logging
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from api.database.connection import get_db
from api.database.models.user import User
from api.database.repositories.problem_type import ProblemTypeRepository
from api.middleware.auth import get_current_admin

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/admin/problem-types", tags=["problem-types"])


# Response models
class ProblemTypeResponse(BaseModel):
    """Problem type response."""

    id: str = Field(..., description="Problem type UUID")
    name: str = Field(..., description="Problem type name")
    description: Optional[str] = Field(None, description="Problem type description")
    is_active: bool = Field(..., description="Whether type is active")
    sort_order: int = Field(..., description="Display order")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    model_config = {"from_attributes": True}


class ProblemTypeListResponse(BaseModel):
    """List of problem types response."""

    types: List[ProblemTypeResponse]
    total: int = Field(..., description="Total number of types")


class CreateProblemTypeRequest(BaseModel):
    """Request to create a problem type."""

    name: str = Field(..., min_length=1, max_length=100, description="Type name")
    description: Optional[str] = Field(None, description="Type description")
    sort_order: int = Field(0, ge=0, description="Display order")


class UpdateProblemTypeRequest(BaseModel):
    """Request to update a problem type."""

    name: Optional[str] = Field(None, min_length=1, max_length=100, description="Type name")
    description: Optional[str] = Field(None, description="Type description")
    is_active: Optional[bool] = Field(None, description="Whether type is active")
    sort_order: Optional[int] = Field(None, ge=0, description="Display order")


@router.get("", response_model=ProblemTypeListResponse)
async def list_problem_types(
    admin_user: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> ProblemTypeListResponse:
    """
    List all problem types (including inactive).

    Requires admin privileges.

    Returns:
        List of all problem types
    """
    repo = ProblemTypeRepository(db)
    types = await repo.get_all_ordered()

    return ProblemTypeListResponse(
        types=[
            ProblemTypeResponse(
                id=str(t.id),
                name=t.name,
                description=t.description,
                is_active=t.is_active,
                sort_order=t.sort_order,
                created_at=t.created_at,
                updated_at=t.updated_at,
            )
            for t in types
        ],
        total=len(types),
    )


@router.get("/{type_id}", response_model=ProblemTypeResponse)
async def get_problem_type(
    type_id: str,
    admin_user: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> ProblemTypeResponse:
    """
    Get a specific problem type by ID.

    Requires admin privileges.

    Args:
        type_id: UUID of the problem type

    Returns:
        Problem type details
    """
    try:
        uuid = UUID(type_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="ID de tipo invalido",
        )

    repo = ProblemTypeRepository(db)
    problem_type = await repo.get_by_id(uuid)

    if not problem_type:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tipo de problema nao encontrado",
        )

    return ProblemTypeResponse(
        id=str(problem_type.id),
        name=problem_type.name,
        description=problem_type.description,
        is_active=problem_type.is_active,
        sort_order=problem_type.sort_order,
        created_at=problem_type.created_at,
        updated_at=problem_type.updated_at,
    )


@router.post("", response_model=ProblemTypeResponse, status_code=status.HTTP_201_CREATED)
async def create_problem_type(
    request: CreateProblemTypeRequest,
    admin_user: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> ProblemTypeResponse:
    """
    Create a new problem type.

    Requires admin privileges.

    Args:
        request: Problem type data

    Returns:
        Created problem type
    """
    repo = ProblemTypeRepository(db)

    # Check if name already exists
    existing = await repo.get_by_name(request.name)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ja existe um tipo de problema com esse nome",
        )

    problem_type = await repo.create_type(
        name=request.name,
        description=request.description,
        sort_order=request.sort_order,
    )
    await db.commit()

    logger.info(f"Problem type '{request.name}' created by {admin_user.email}")

    return ProblemTypeResponse(
        id=str(problem_type.id),
        name=problem_type.name,
        description=problem_type.description,
        is_active=problem_type.is_active,
        sort_order=problem_type.sort_order,
        created_at=problem_type.created_at,
        updated_at=problem_type.updated_at,
    )


@router.put("/{type_id}", response_model=ProblemTypeResponse)
async def update_problem_type(
    type_id: str,
    request: UpdateProblemTypeRequest,
    admin_user: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> ProblemTypeResponse:
    """
    Update a problem type.

    Requires admin privileges.

    Args:
        type_id: UUID of the problem type
        request: Fields to update

    Returns:
        Updated problem type
    """
    try:
        uuid = UUID(type_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="ID de tipo invalido",
        )

    repo = ProblemTypeRepository(db)

    # Check if name already exists (if changing name)
    if request.name:
        existing = await repo.get_by_name(request.name)
        if existing and existing.id != uuid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Ja existe um tipo de problema com esse nome",
            )

    problem_type = await repo.update_type(
        id=uuid,
        name=request.name,
        description=request.description,
        is_active=request.is_active,
        sort_order=request.sort_order,
    )

    if not problem_type:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tipo de problema nao encontrado",
        )

    await db.commit()

    logger.info(f"Problem type '{problem_type.name}' updated by {admin_user.email}")

    return ProblemTypeResponse(
        id=str(problem_type.id),
        name=problem_type.name,
        description=problem_type.description,
        is_active=problem_type.is_active,
        sort_order=problem_type.sort_order,
        created_at=problem_type.created_at,
        updated_at=problem_type.updated_at,
    )


@router.delete("/{type_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_problem_type(
    type_id: str,
    admin_user: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> None:
    """
    Soft delete a problem type (set is_active=False).

    Requires admin privileges.

    Args:
        type_id: UUID of the problem type
    """
    try:
        uuid = UUID(type_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="ID de tipo invalido",
        )

    repo = ProblemTypeRepository(db)
    success = await repo.soft_delete(uuid)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tipo de problema nao encontrado",
        )

    await db.commit()

    logger.info(f"Problem type {type_id} deactivated by {admin_user.email}")
