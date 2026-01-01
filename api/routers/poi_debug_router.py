"""
POI Debug router for debug data visualization endpoints.

Provides endpoints for admins to visualize how POI positions were calculated,
including side determination, junction points, and access routes.
"""
import logging
from typing import List, Optional, Dict, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from api.database.connection import get_db
from api.database.models.user import User
from api.database.repositories.map import MapRepository
from api.database.repositories.map_poi import MapPOIRepository
from api.database.repositories.poi_debug_data import POIDebugDataRepository
from api.middleware.auth import get_current_admin

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/admin/maps", tags=["poi-debug"])


# Response models
class SideCalculationDetail(BaseModel):
    """Details of the side calculation using cross product."""
    road_vector: Dict[str, float] = Field(..., description="Road direction vector {dx, dy}")
    poi_vector: Optional[Dict[str, float]] = Field(None, description="POI direction vector {dx, dy} - used by old method")
    access_vector: Optional[Dict[str, float]] = Field(None, description="Access route direction vector {dx, dy} - used by new method")
    cross_product: float = Field(..., description="Cross product value (positive=left, negative=right)")
    resulting_side: str = Field(..., description="Calculated side (left/right)")
    segment_start: Dict[str, float] = Field(..., description="Segment start point {lat, lon}")
    segment_end: Dict[str, float] = Field(..., description="Segment end point {lat, lon}")
    segment_idx: Optional[int] = Field(None, description="Index of the segment in main route")
    method: Optional[str] = Field(None, description="Calculation method: 'access_route_direction' or 'poi_position'")
    junction_idx_on_access: Optional[int] = Field(None, description="Index of junction point on access route")
    access_direction_point_idx: Optional[int] = Field(None, description="Index of point used for access direction")
    access_start: Optional[Dict[str, float]] = Field(None, description="Start point for access direction {lat, lon}")
    access_direction_point: Optional[Dict[str, float]] = Field(None, description="Point used for access direction {lat, lon}")


class LookbackDetail(BaseModel):
    """Details of the lookback calculation for distant POIs."""
    poi_distance_from_road_m: float = Field(..., description="Distance from POI to road in meters")
    lookback_km: Optional[float] = Field(None, description="Lookback distance used (only for interpolated method)")
    lookback_distance_km: float = Field(..., description="Distance from origin to lookback point")
    lookback_point: Dict[str, float] = Field(..., description="Lookback point {lat, lon}")
    search_point: Dict[str, float] = Field(..., description="Original search point {lat, lon}")
    search_point_distance_km: float = Field(..., description="Distance from origin to search point")
    lookback_method: Optional[str] = Field(None, description="Method used: 'search_point', 'search_point_first', or 'interpolated'")
    lookback_index: Optional[int] = Field(None, description="Index of the search point used as lookback")
    current_search_point_index: Optional[int] = Field(None, description="Index of the current search point")
    lookback_count_setting: Optional[int] = Field(None, description="Configured number of search points to look back")
    # Legacy fields (kept for compatibility with old data)
    lookback_milestone_name: Optional[str] = Field(None, description="Name of milestone used as lookback point (legacy)")
    milestones_available_before: Optional[int] = Field(None, description="Number of milestones available before search point (legacy)")
    lookback_milestones_count_setting: Optional[int] = Field(None, description="Configured number of milestones to look back (legacy)")


class RecalculationAttempt(BaseModel):
    """Details of a recalculation attempt."""
    attempt: int = Field(..., description="Attempt number")
    search_point: Dict[str, float] = Field(..., description="Search point used {lat, lon}")
    search_point_distance_km: float = Field(..., description="Distance of search point from origin")
    junction_found: bool = Field(..., description="Whether a junction was found")
    junction_distance_km: Optional[float] = Field(None, description="Junction distance if found")
    access_route_distance_km: Optional[float] = Field(None, description="Access route distance if found")
    improvement: bool = Field(..., description="Whether this improved on previous")
    reason: Optional[str] = Field(None, description="Reason for skipping or failure")


class POIDebugDataResponse(BaseModel):
    """Complete debug data for a POI."""
    id: str = Field(..., description="Debug data ID")
    map_poi_id: str = Field(..., description="MapPOI relationship ID")
    poi_name: str = Field(..., description="POI name")
    poi_type: str = Field(..., description="POI type (gas_station, restaurant, etc.)")
    poi_lat: float = Field(..., description="POI latitude")
    poi_lon: float = Field(..., description="POI longitude")
    main_route_segment: Optional[List[List[float]]] = Field(None, description="Route segment near POI [[lat, lon], ...]")
    junction_lat: Optional[float] = Field(None, description="Junction point latitude")
    junction_lon: Optional[float] = Field(None, description="Junction point longitude")
    junction_distance_km: Optional[float] = Field(None, description="Distance from origin to junction")
    access_route_geometry: Optional[List[List[float]]] = Field(None, description="Access route geometry [[lat, lon], ...]")
    access_route_distance_km: Optional[float] = Field(None, description="Access route distance in km")
    side_calculation: Optional[SideCalculationDetail] = Field(None, description="Side calculation details")
    lookback_data: Optional[LookbackDetail] = Field(None, description="Lookback calculation details")
    recalculation_history: Optional[List[RecalculationAttempt]] = Field(None, description="Recalculation attempts")
    final_side: str = Field(..., description="Final determined side (left/right/center)")
    requires_detour: bool = Field(..., description="Whether this POI requires a detour")
    distance_from_road_m: float = Field(..., description="Distance from POI to road in meters")
    created_at: str = Field(..., description="When debug data was created")

    model_config = {"from_attributes": True}


class POIDebugSummary(BaseModel):
    """Summary statistics for debug data."""
    total: int = Field(..., description="Total number of POIs with debug data")
    detour_count: int = Field(..., description="Number of POIs requiring detour")
    left_count: int = Field(..., description="Number of POIs on the left")
    right_count: int = Field(..., description="Number of POIs on the right")
    center_count: int = Field(0, description="Number of POIs in center")


class POIDebugListResponse(BaseModel):
    """Response containing list of POI debug data."""
    pois: List[POIDebugDataResponse] = Field(..., description="List of POI debug data")
    summary: POIDebugSummary = Field(..., description="Summary statistics")
    has_debug_data: bool = Field(..., description="Whether full debug data exists (vs reconstructed)")


class POIDebugBasicResponse(BaseModel):
    """Basic debug data reconstructed from MapPOI (when full debug not available)."""
    id: str
    map_poi_id: str
    poi_name: str
    poi_type: str
    poi_lat: float
    poi_lon: float
    junction_lat: Optional[float] = None
    junction_lon: Optional[float] = None
    junction_distance_km: Optional[float] = None
    final_side: str
    requires_detour: bool
    distance_from_road_m: float


@router.get("/{map_id}/debug", response_model=POIDebugListResponse)
async def get_map_debug_data(
    map_id: str,
    admin_user: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> POIDebugListResponse:
    """
    Get POI debug data for a map.

    Returns detailed calculation data for each POI including:
    - Side calculation vectors and cross product
    - Junction/access route geometry
    - Lookback calculations
    - Recalculation history

    If full debug data is not available (map created before debug feature),
    returns basic data reconstructed from MapPOI records.

    Requires admin privileges.
    """
    try:
        uuid = UUID(map_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="ID de mapa invalido",
        )

    # Check if map exists
    map_repo = MapRepository(db)
    db_map = await map_repo.get_by_id(uuid)
    if not db_map:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Mapa nao encontrado",
        )

    # Try to get full debug data first
    debug_repo = POIDebugDataRepository(db)
    debug_entries = await debug_repo.get_by_map(uuid)

    if debug_entries:
        # Full debug data available
        summary = await debug_repo.get_summary_by_map(uuid)

        pois = []
        for entry in debug_entries:
            pois.append(POIDebugDataResponse(
                id=str(entry.id),
                map_poi_id=str(entry.map_poi_id),
                poi_name=entry.poi_name,
                poi_type=entry.poi_type,
                poi_lat=entry.poi_lat,
                poi_lon=entry.poi_lon,
                main_route_segment=entry.main_route_segment,
                junction_lat=entry.junction_lat,
                junction_lon=entry.junction_lon,
                junction_distance_km=entry.junction_distance_km,
                access_route_geometry=entry.access_route_geometry,
                access_route_distance_km=entry.access_route_distance_km,
                side_calculation=SideCalculationDetail(**entry.side_calculation) if entry.side_calculation else None,
                lookback_data=LookbackDetail(**entry.lookback_data) if entry.lookback_data else None,
                recalculation_history=[RecalculationAttempt(**r) for r in entry.recalculation_history] if entry.recalculation_history else None,
                final_side=entry.final_side,
                requires_detour=entry.requires_detour,
                distance_from_road_m=entry.distance_from_road_m,
                created_at=entry.created_at.isoformat(),
            ))

        return POIDebugListResponse(
            pois=pois,
            summary=POIDebugSummary(**summary),
            has_debug_data=True,
        )

    # No full debug data - reconstruct from MapPOI
    logger.info(f"No full debug data for map {map_id}, reconstructing from MapPOI")

    map_poi_repo = MapPOIRepository(db)
    map_pois = await map_poi_repo.get_pois_for_map(uuid, include_poi_details=True)

    if not map_pois:
        return POIDebugListResponse(
            pois=[],
            summary=POIDebugSummary(total=0, detour_count=0, left_count=0, right_count=0, center_count=0),
            has_debug_data=False,
        )

    # Build basic debug data from MapPOI
    pois = []
    left_count = 0
    right_count = 0
    center_count = 0
    detour_count = 0

    for map_poi in map_pois:
        poi = map_poi.poi
        if not poi:
            continue

        side = map_poi.side or "center"
        if side == "left":
            left_count += 1
        elif side == "right":
            right_count += 1
        else:
            center_count += 1

        if map_poi.requires_detour:
            detour_count += 1

        # Create basic debug response (without full calculation details)
        pois.append(POIDebugDataResponse(
            id=str(map_poi.id),  # Use MapPOI ID as debug ID
            map_poi_id=str(map_poi.id),
            poi_name=poi.name or "Sem nome",
            poi_type=poi.type or "unknown",
            poi_lat=poi.latitude,
            poi_lon=poi.longitude,
            main_route_segment=None,  # Not available without full debug
            junction_lat=map_poi.junction_lat,
            junction_lon=map_poi.junction_lon,
            junction_distance_km=map_poi.junction_distance_km,
            access_route_geometry=None,  # Not available without full debug
            access_route_distance_km=None,
            side_calculation=None,  # Not available without full debug
            lookback_data=None,
            recalculation_history=None,
            final_side=side,
            requires_detour=map_poi.requires_detour,
            distance_from_road_m=map_poi.distance_from_road_meters,
            created_at=db_map.created_at.isoformat() if db_map.created_at else "",
        ))

    return POIDebugListResponse(
        pois=pois,
        summary=POIDebugSummary(
            total=len(pois),
            detour_count=detour_count,
            left_count=left_count,
            right_count=right_count,
            center_count=center_count,
        ),
        has_debug_data=False,
    )


@router.get("/{map_id}/debug/{debug_id}", response_model=POIDebugDataResponse)
async def get_poi_debug_detail(
    map_id: str,
    debug_id: str,
    admin_user: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> POIDebugDataResponse:
    """
    Get detailed debug data for a specific POI.

    Requires admin privileges.
    """
    try:
        debug_uuid = UUID(debug_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="ID de debug invalido",
        )

    debug_repo = POIDebugDataRepository(db)
    entry = await debug_repo.get_by_id(debug_uuid)

    if not entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dados de debug nao encontrados",
        )

    return POIDebugDataResponse(
        id=str(entry.id),
        map_poi_id=str(entry.map_poi_id),
        poi_name=entry.poi_name,
        poi_type=entry.poi_type,
        poi_lat=entry.poi_lat,
        poi_lon=entry.poi_lon,
        main_route_segment=entry.main_route_segment,
        junction_lat=entry.junction_lat,
        junction_lon=entry.junction_lon,
        junction_distance_km=entry.junction_distance_km,
        access_route_geometry=entry.access_route_geometry,
        access_route_distance_km=entry.access_route_distance_km,
        side_calculation=SideCalculationDetail(**entry.side_calculation) if entry.side_calculation else None,
        lookback_data=LookbackDetail(**entry.lookback_data) if entry.lookback_data else None,
        recalculation_history=[RecalculationAttempt(**r) for r in entry.recalculation_history] if entry.recalculation_history else None,
        final_side=entry.final_side,
        requires_detour=entry.requires_detour,
        distance_from_road_m=entry.distance_from_road_m,
        created_at=entry.created_at.isoformat(),
    )


@router.get("/{map_id}/debug/summary", response_model=POIDebugSummary)
async def get_debug_summary(
    map_id: str,
    admin_user: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> POIDebugSummary:
    """
    Get summary statistics for POI debug data.

    Requires admin privileges.
    """
    try:
        uuid = UUID(map_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="ID de mapa invalido",
        )

    debug_repo = POIDebugDataRepository(db)
    has_data = await debug_repo.has_debug_data(uuid)

    if has_data:
        summary = await debug_repo.get_summary_by_map(uuid)
        return POIDebugSummary(**summary)

    # Reconstruct from MapPOI
    map_poi_repo = MapPOIRepository(db)
    map_pois = await map_poi_repo.get_pois_for_map(uuid)

    left_count = sum(1 for mp in map_pois if mp.side == "left")
    right_count = sum(1 for mp in map_pois if mp.side == "right")
    center_count = sum(1 for mp in map_pois if mp.side not in ("left", "right"))
    detour_count = sum(1 for mp in map_pois if mp.requires_detour)

    return POIDebugSummary(
        total=len(map_pois),
        detour_count=detour_count,
        left_count=left_count,
        right_count=right_count,
        center_count=center_count,
    )
