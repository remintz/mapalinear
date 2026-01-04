"""
Settings router for system configuration endpoints.
"""

import logging
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from api.database.connection import get_db
from api.database.models.user import User
from api.database.repositories.system_settings import (
    SystemSettingsRepository,
    AVAILABLE_TAGS,
    DEFAULT_REQUIRED_TAGS,
)
from api.middleware.auth import get_current_admin, get_current_user
from api.models.base import UTCDatetime

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/settings", tags=["settings"])


# Response models
class SettingResponse(BaseModel):
    """Single setting response."""

    key: str = Field(..., description="Setting key")
    value: str = Field(..., description="Setting value")
    description: Optional[str] = Field(None, description="Setting description")
    updated_at: Optional[UTCDatetime] = Field(None, description="Last update time")
    updated_by: Optional[str] = Field(None, description="Who last updated")


class SettingsResponse(BaseModel):
    """All settings response."""

    settings: Dict[str, str] = Field(..., description="All settings as key-value pairs")


class UpdateSettingRequest(BaseModel):
    """Request to update a setting."""

    value: str = Field(..., description="New value for the setting")


class UpdateSettingsRequest(BaseModel):
    """Request to update multiple settings."""

    settings: Dict[str, str] = Field(..., description="Settings to update")


# ===========================================
# Required Tags endpoints - MUST be defined BEFORE {key} routes!
# ===========================================

class RequiredTagsResponse(BaseModel):
    """Response with required tags configuration."""

    required_tags: Dict[str, List[str]] = Field(
        ..., description="Required tags per POI type"
    )
    available_tags: List[str] = Field(
        ..., description="Available tags that can be configured"
    )


class UpdateRequiredTagsRequest(BaseModel):
    """Request to update required tags configuration."""

    required_tags: Dict[str, List[str]] = Field(
        ..., description="Required tags per POI type"
    )


@router.get("/required-tags", response_model=RequiredTagsResponse)
async def get_required_tags(
    db: AsyncSession = Depends(get_db),
) -> RequiredTagsResponse:
    """
    Get required tags configuration.

    Returns the current configuration of required tags per POI type,
    along with the list of available tags that can be configured.

    Returns:
        Required tags config and available tags list
    """
    repo = SystemSettingsRepository(db)
    required_tags = await repo.get_required_tags()
    available_tags = repo.get_available_tags()

    return RequiredTagsResponse(
        required_tags=required_tags,
        available_tags=available_tags
    )


@router.put("/required-tags", response_model=RequiredTagsResponse)
async def update_required_tags(
    request: UpdateRequiredTagsRequest,
    admin_user: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> RequiredTagsResponse:
    """
    Update required tags configuration.

    Requires admin privileges.

    Args:
        request: New required tags configuration

    Returns:
        Updated required tags config
    """
    repo = SystemSettingsRepository(db)

    # Validate that all provided tags are in the available list
    for poi_type, tags in request.required_tags.items():
        invalid_tags = [t for t in tags if t not in AVAILABLE_TAGS]
        if invalid_tags:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Tags inválidas para '{poi_type}': {invalid_tags}. Tags disponíveis: {AVAILABLE_TAGS}"
            )

    await repo.set_required_tags(
        required_tags=request.required_tags,
        updated_by=admin_user.email
    )
    await db.commit()

    logger.info(f"Required tags updated by {admin_user.email}")

    required_tags = await repo.get_required_tags()
    available_tags = repo.get_available_tags()

    return RequiredTagsResponse(
        required_tags=required_tags,
        available_tags=available_tags
    )


@router.post("/required-tags/reset", response_model=RequiredTagsResponse)
async def reset_required_tags(
    admin_user: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> RequiredTagsResponse:
    """
    Reset required tags to default configuration.

    Requires admin privileges.

    Returns:
        Default required tags config
    """
    repo = SystemSettingsRepository(db)

    await repo.set_required_tags(
        required_tags=DEFAULT_REQUIRED_TAGS,
        updated_by=admin_user.email
    )
    await db.commit()

    logger.info(f"Required tags reset to defaults by {admin_user.email}")

    required_tags = await repo.get_required_tags()
    available_tags = repo.get_available_tags()

    return RequiredTagsResponse(
        required_tags=required_tags,
        available_tags=available_tags
    )


# ===========================================
# General settings endpoints
# ===========================================

# Public endpoint to get settings (for frontend use)
@router.get("", response_model=SettingsResponse)
async def get_settings(
    db: AsyncSession = Depends(get_db),
) -> SettingsResponse:
    """
    Get all system settings.

    This endpoint is public so the frontend can read configuration values.

    Returns:
        Dictionary of all settings
    """
    repo = SystemSettingsRepository(db)
    settings = await repo.get_all_as_dict()
    return SettingsResponse(settings=settings)


@router.get("/{key}", response_model=SettingResponse)
async def get_setting(
    key: str,
    db: AsyncSession = Depends(get_db),
) -> SettingResponse:
    """
    Get a single setting by key.

    Args:
        key: The setting key to retrieve

    Returns:
        The setting value and metadata
    """
    repo = SystemSettingsRepository(db)
    setting = await repo.get(key)

    if not setting:
        # Check if it's a default setting
        value = await repo.get_value(key)
        if value is not None:
            return SettingResponse(key=key, value=value)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Setting '{key}' not found"
        )

    return SettingResponse(
        key=setting.key,
        value=setting.value,
        description=setting.description,
        updated_at=setting.updated_at,
        updated_by=setting.updated_by
    )


# Admin-only endpoints for updating settings
@router.put("/{key}", response_model=SettingResponse)
async def update_setting(
    key: str,
    request: UpdateSettingRequest,
    admin_user: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> SettingResponse:
    """
    Update a single setting.

    Requires admin privileges.

    Args:
        key: The setting key to update
        request: The new value

    Returns:
        The updated setting
    """
    repo = SystemSettingsRepository(db)

    # Validate specific settings
    if key == "poi_search_radius_km":
        try:
            radius = int(request.value)
            if radius < 1 or radius > 20:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="O raio de busca deve estar entre 1 e 20 km"
                )
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="O raio de busca deve ser um número inteiro"
            )

    if key == "duplicate_map_tolerance_km":
        try:
            tolerance = int(request.value)
            if tolerance < 1 or tolerance > 50:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="A tolerância deve estar entre 1 e 50 km"
                )
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A tolerância deve ser um número inteiro"
            )

    if key == "poi_debug_enabled":
        if request.value.lower() not in ("true", "false"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="O valor deve ser 'true' ou 'false'"
            )

    if key == "log_retention_days":
        try:
            days = int(request.value)
            if days < 1 or days > 365:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="O período de retenção deve estar entre 1 e 365 dias"
                )
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="O período de retenção deve ser um número inteiro"
            )

    setting = await repo.set(
        key=key,
        value=request.value,
        updated_by=admin_user.email
    )
    await db.commit()

    logger.info(f"Setting '{key}' updated to '{request.value}' by {admin_user.email}")

    return SettingResponse(
        key=setting.key,
        value=setting.value,
        description=setting.description,
        updated_at=setting.updated_at,
        updated_by=setting.updated_by
    )


@router.put("", response_model=SettingsResponse)
async def update_settings(
    request: UpdateSettingsRequest,
    admin_user: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> SettingsResponse:
    """
    Update multiple settings at once.

    Requires admin privileges.

    Args:
        request: Dictionary of settings to update

    Returns:
        All settings after update
    """
    repo = SystemSettingsRepository(db)

    for key, value in request.settings.items():
        # Validate specific settings
        if key == "poi_search_radius_km":
            try:
                radius = int(value)
                if radius < 1 or radius > 20:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="O raio de busca deve estar entre 1 e 20 km"
                    )
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="O raio de busca deve ser um número inteiro"
                )

        if key == "duplicate_map_tolerance_km":
            try:
                tolerance = int(value)
                if tolerance < 1 or tolerance > 50:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="A tolerância deve estar entre 1 e 50 km"
                    )
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="A tolerância deve ser um número inteiro"
                )

        if key == "poi_debug_enabled":
            if value.lower() not in ("true", "false"):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="O valor deve ser 'true' ou 'false'"
                )

        if key == "log_retention_days":
            try:
                days = int(value)
                if days < 1 or days > 365:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="O período de retenção deve estar entre 1 e 365 dias"
                    )
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="O período de retenção deve ser um número inteiro"
                )

        await repo.set(key=key, value=value, updated_by=admin_user.email)

    await db.commit()

    logger.info(f"Multiple settings updated by {admin_user.email}: {list(request.settings.keys())}")

    settings = await repo.get_all_as_dict()
    return SettingsResponse(settings=settings)
