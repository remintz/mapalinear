"""
Admin POIs router for managing Points of Interest.

This router provides endpoints for:
- Listing all POIs with filters
- Viewing POI details
- Getting POI statistics
- Recalculating quality for all POIs
"""

import logging
from typing import Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from api.database.connection import get_db
from api.database.models.poi import POI
from api.database.models.user import User
from api.database.repositories.poi import POIRepository
from api.database.repositories.system_settings import SystemSettingsRepository
from api.middleware.auth import get_current_admin
from api.models.base import UTCDatetime
from api.services.poi_quality_service import POIQualityService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/admin/pois", tags=["admin", "pois"])


# Response models
class POIResponse(BaseModel):
    """POI information for admin."""

    id: str = Field(..., description="POI UUID")
    osm_id: Optional[str] = Field(None, description="OpenStreetMap ID")
    here_id: Optional[str] = Field(None, description="HERE Maps ID")
    name: str = Field(..., description="POI name")
    type: str = Field(..., description="POI type (gas_station, restaurant, etc.)")
    latitude: float = Field(..., description="Latitude")
    longitude: float = Field(..., description="Longitude")
    city: Optional[str] = Field(None, description="City name")

    # Quality fields
    quality_score: Optional[float] = Field(None, description="Quality score (0.0-1.0)")
    is_low_quality: bool = Field(False, description="Whether POI has low quality")
    missing_tags: List[str] = Field(default_factory=list, description="Required tags that are missing")
    quality_issues: List[str] = Field(default_factory=list, description="Legacy quality issues")

    # Enriched data
    brand: Optional[str] = Field(None, description="Brand name")
    operator: Optional[str] = Field(None, description="Operator name")
    phone: Optional[str] = Field(None, description="Phone number")
    website: Optional[str] = Field(None, description="Website URL")
    opening_hours: Optional[str] = Field(None, description="Opening hours")
    cuisine: Optional[str] = Field(None, description="Cuisine type (restaurants)")
    rating: Optional[float] = Field(None, description="Google rating (1.0-5.0)")
    rating_count: Optional[int] = Field(None, description="Number of Google reviews")

    # Data availability indicators
    has_name: bool = Field(..., description="Has proper name")
    has_phone: bool = Field(..., description="Has phone number")
    has_website: bool = Field(..., description="Has website")
    has_opening_hours: bool = Field(..., description="Has opening hours")
    has_brand: bool = Field(..., description="Has brand")
    has_operator: bool = Field(..., description="Has operator")

    created_at: UTCDatetime = Field(..., description="When POI was created")

    model_config = {"from_attributes": True}


class POIDetailResponse(POIResponse):
    """Detailed POI information including raw tags."""

    osm_tags: Dict = Field(default_factory=dict, description="OSM tags from data")
    here_data: Optional[Dict] = Field(None, description="HERE Maps enrichment data")
    enriched_by: List[str] = Field(default_factory=list, description="Enrichment sources")
    google_maps_uri: Optional[str] = Field(None, description="Google Maps URI")
    is_referenced: bool = Field(False, description="Used in any map")
    amenities: List[str] = Field(default_factory=list, description="Amenities list")


class POIListResponse(BaseModel):
    """Response with list of POIs."""

    pois: List[POIResponse]
    total: int = Field(..., description="Total count matching filters")
    page: int = Field(..., description="Current page number")
    limit: int = Field(..., description="Items per page")


class POIFiltersResponse(BaseModel):
    """Available filter values."""

    cities: List[str] = Field(default_factory=list, description="Available cities")
    types: List[str] = Field(default_factory=list, description="Available POI types")


class POIStatisticsResponse(BaseModel):
    """POI statistics."""

    total: int = Field(..., description="Total POIs")
    low_quality: int = Field(..., description="Low quality POIs count")
    by_type: Dict[str, int] = Field(default_factory=dict, description="Count by POI type")
    by_city: Dict[str, int] = Field(default_factory=dict, description="Count by city (top 20)")


class RecalculateQualityResponse(BaseModel):
    """Response for recalculate quality endpoint."""

    updated: int = Field(..., description="Number of POIs updated")
    total: int = Field(..., description="Total POIs processed")
    message: str = Field(..., description="Status message")


def _poi_to_response(poi: POI) -> POIResponse:
    """Convert POI model to response."""
    return POIResponse(
        id=str(poi.id),
        osm_id=poi.osm_id,
        here_id=poi.here_id,
        name=poi.name,
        type=poi.type,
        latitude=poi.latitude,
        longitude=poi.longitude,
        city=poi.city,
        quality_score=poi.quality_score,
        is_low_quality=poi.is_low_quality,
        missing_tags=poi.missing_tags or [],
        quality_issues=poi.quality_issues or [],
        brand=poi.brand,
        operator=poi.operator,
        phone=poi.phone,
        website=poi.website,
        opening_hours=poi.opening_hours,
        cuisine=poi.cuisine,
        rating=poi.rating,
        rating_count=poi.rating_count,
        has_name=bool(poi.name and poi.name not in ['Unknown POI', '']),
        has_phone=bool(poi.phone),
        has_website=bool(poi.website),
        has_opening_hours=bool(poi.opening_hours),
        has_brand=bool(poi.brand),
        has_operator=bool(poi.operator),
        created_at=poi.created_at,
    )


def _poi_to_detail_response(poi: POI) -> POIDetailResponse:
    """Convert POI model to detailed response."""
    tags = poi.tags or {}
    osm_tags = tags.get('osm_tags', {})

    return POIDetailResponse(
        id=str(poi.id),
        osm_id=poi.osm_id,
        here_id=poi.here_id,
        name=poi.name,
        type=poi.type,
        latitude=poi.latitude,
        longitude=poi.longitude,
        city=poi.city,
        quality_score=poi.quality_score,
        is_low_quality=poi.is_low_quality,
        missing_tags=poi.missing_tags or [],
        quality_issues=poi.quality_issues or [],
        brand=poi.brand,
        operator=poi.operator,
        phone=poi.phone,
        website=poi.website,
        opening_hours=poi.opening_hours,
        cuisine=poi.cuisine,
        rating=poi.rating,
        rating_count=poi.rating_count,
        has_name=bool(poi.name and poi.name not in ['Unknown POI', '']),
        has_phone=bool(poi.phone),
        has_website=bool(poi.website),
        has_opening_hours=bool(poi.opening_hours),
        has_brand=bool(poi.brand),
        has_operator=bool(poi.operator),
        created_at=poi.created_at,
        osm_tags=osm_tags,
        here_data=poi.here_data,
        enriched_by=poi.enriched_by or [],
        google_maps_uri=poi.google_maps_uri,
        is_referenced=poi.is_referenced,
        amenities=poi.amenities or [],
    )


@router.get("", response_model=POIListResponse)
async def list_pois(
    name: Optional[str] = Query(None, description="Filter by POI name (partial match)"),
    city: Optional[str] = Query(None, description="Filter by city name (partial match)"),
    poi_type: Optional[str] = Query(None, description="Filter by POI type"),
    low_quality_only: bool = Query(False, description="Show only low quality POIs"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(50, ge=1, le=200, description="Items per page"),
    admin_user: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> POIListResponse:
    """
    List all POIs with optional filters.

    Requires admin privileges.
    """
    poi_repo = POIRepository(db)
    offset = (page - 1) * limit

    pois = await poi_repo.list_all_pois(
        name_filter=name,
        city_filter=city,
        type_filter=poi_type,
        low_quality_only=low_quality_only,
        limit=limit,
        offset=offset
    )

    total = await poi_repo.count_all_pois(
        name_filter=name,
        city_filter=city,
        type_filter=poi_type,
        low_quality_only=low_quality_only
    )

    return POIListResponse(
        pois=[_poi_to_response(poi) for poi in pois],
        total=total,
        page=page,
        limit=limit
    )


@router.get("/filters", response_model=POIFiltersResponse)
async def get_filters(
    admin_user: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> POIFiltersResponse:
    """
    Get available filter values for POI listing.

    Requires admin privileges.
    """
    poi_repo = POIRepository(db)

    cities = await poi_repo.get_distinct_cities()
    types = await poi_repo.get_distinct_types()

    return POIFiltersResponse(
        cities=cities,
        types=types
    )


@router.get("/stats", response_model=POIStatisticsResponse)
async def get_statistics(
    admin_user: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> POIStatisticsResponse:
    """
    Get POI statistics.

    Requires admin privileges.
    """
    poi_repo = POIRepository(db)
    stats = await poi_repo.get_statistics()

    return POIStatisticsResponse(
        total=stats["total"],
        low_quality=stats["low_quality"],
        by_type=stats["by_type"],
        by_city=stats["by_city"]
    )


@router.post("/recalculate-quality", response_model=RecalculateQualityResponse)
async def recalculate_quality(
    admin_user: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> RecalculateQualityResponse:
    """
    Recalculate quality for all POIs based on current required tags configuration.

    This updates missing_tags and is_low_quality for all POIs.

    Requires admin privileges.
    """
    poi_repo = POIRepository(db)
    settings_repo = SystemSettingsRepository(db)
    quality_service = POIQualityService()

    # Get current required tags configuration
    required_tags_config = await settings_repo.get_required_tags()

    # Process POIs in batches
    batch_size = 100
    offset = 0
    total_processed = 0
    total_updated = 0

    while True:
        pois = await poi_repo.list_all_pois(limit=batch_size, offset=offset)
        if not pois:
            break

        for poi in pois:
            was_updated = quality_service.update_poi_quality_fields(poi, required_tags_config)
            total_processed += 1
            if was_updated:
                total_updated += 1

        await db.flush()
        offset += batch_size

    await db.commit()

    logger.info(
        f"Quality recalculated by {admin_user.email}: "
        f"{total_updated}/{total_processed} POIs updated"
    )

    return RecalculateQualityResponse(
        updated=total_updated,
        total=total_processed,
        message=f"Qualidade recalculada para {total_processed} POIs. {total_updated} foram atualizados."
    )


@router.get("/{poi_id}", response_model=POIDetailResponse)
async def get_poi(
    poi_id: str,
    admin_user: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> POIDetailResponse:
    """
    Get detailed information about a specific POI.

    Requires admin privileges.
    """
    poi_repo = POIRepository(db)

    try:
        poi_uuid = UUID(poi_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid POI ID format"
        )

    poi = await poi_repo.get_by_id(poi_uuid)

    if not poi:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="POI not found"
        )

    return _poi_to_detail_response(poi)
