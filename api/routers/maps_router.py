"""
Router for managing saved linear maps.

Endpoints:
- GET /api/maps - List all saved maps for current user
- GET /api/maps/available - List all available maps (for browsing/adopting)
- GET /api/maps/{map_id} - Get a specific map
- GET /api/maps/{map_id}/pdf - Export map to PDF
- POST /api/maps/{map_id}/adopt - Add existing map to user's collection
- DELETE /api/maps/{map_id} - Unlink map (user) or permanently delete (admin)
- DELETE /api/maps/{map_id}/permanent - Permanently delete a map (admin only)
- POST /api/maps/{map_id}/regenerate - Regenerate a map (admin only)
"""

import logging
import re
import unicodedata
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import MapPOIRepository, MapRepository, POIRepository, get_db
from ..database.models.user import User
from ..middleware.auth import get_current_admin, get_current_user
from ..middleware.request_id import get_request_id
from ..models.road_models import LinearMapResponse, SavedMapResponse
from ..services.async_service import AsyncService
from ..services.map_storage_service_db import MapStorageServiceDB
from ..services.road_service import RoadService
from ..utils.export_utils import export_to_pdf

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/maps", tags=["Saved Maps"])


@router.get("", response_model=List[SavedMapResponse])
async def list_saved_maps(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    List all saved linear maps for the current user (metadata only).

    Returns:
        List of saved map metadata, sorted by creation date (newest first)
    """
    try:
        storage = MapStorageServiceDB(db)
        maps = await storage.list_user_maps(user_id=current_user.id)
        return maps
    except Exception as e:
        logger.error(f"Error listing maps: {e}")
        raise HTTPException(status_code=500, detail="Error listing saved maps")


@router.get("/suggested", response_model=List[SavedMapResponse])
async def get_suggested_maps(
    limit: int = Query(10, ge=1, le=20, description="Maximum maps to return"),
    lat: Optional[float] = Query(
        None, description="User latitude for proximity sorting"
    ),
    lon: Optional[float] = Query(
        None, description="User longitude for proximity sorting"
    ),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get suggested maps for the create page.

    Returns a small number of maps, optionally sorted by proximity to user's location.
    If lat/lon provided, maps with origin near the user are prioritized.

    Args:
        limit: Maximum number of maps to return (default 10)
        lat: User's latitude (optional, for proximity sorting)
        lon: User's longitude (optional, for proximity sorting)

    Returns:
        List of suggested maps
    """
    try:
        storage = MapStorageServiceDB(db)
        maps = await storage.get_suggested_maps(limit=limit, user_lat=lat, user_lon=lon)
        return maps
    except Exception as e:
        logger.error(f"Error getting suggested maps: {e}")
        raise HTTPException(status_code=500, detail="Error getting suggested maps")


@router.get("/available", response_model=List[SavedMapResponse])
async def list_available_maps(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=500, description="Maximum records to return"),
    origin: Optional[str] = Query(None, description="Filter by origin (partial match)"),
    destination: Optional[str] = Query(
        None, description="Filter by destination (partial match)"
    ),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    List all available maps for browsing/adopting.

    Users can search for existing maps by origin/destination and add them
    to their collection instead of creating duplicates.

    Args:
        skip: Number of records to skip for pagination
        limit: Maximum number of records to return
        origin: Optional filter by origin location (partial match)
        destination: Optional filter by destination location (partial match)

    Returns:
        List of available maps
    """
    try:
        storage = MapStorageServiceDB(db)
        maps = await storage.list_available_maps(
            skip=skip, limit=limit, origin=origin, destination=destination
        )
        return maps
    except Exception as e:
        logger.error(f"Error listing available maps: {e}")
        raise HTTPException(status_code=500, detail="Error listing available maps")


@router.get("/{map_id}", response_model=LinearMapResponse)
async def get_saved_map(
    map_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get a specific saved map by ID.

    User must have the map in their collection to access it,
    unless they are an admin (can view any map).

    Args:
        map_id: ID of the map to retrieve

    Returns:
        The complete linear map data
    """
    try:
        storage = MapStorageServiceDB(db)

        # Admins can view any map, regular users only their own collection
        if current_user.is_admin:
            linear_map = await storage.load_map(map_id)
        else:
            linear_map = await storage.load_map(map_id, user_id=current_user.id)

        if linear_map is None:
            raise HTTPException(status_code=404, detail=f"Map {map_id} not found")

        return linear_map
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error loading map {map_id}: {e}")
        raise HTTPException(status_code=500, detail="Error loading saved map")


def _sanitize_filename(text: str) -> str:
    """Sanitiza um texto para ser usado como nome de arquivo."""
    text = unicodedata.normalize("NFD", text)
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")
    text = re.sub(r"[^\w\s-]", "", text).strip()
    text = re.sub(r"[-\s]+", "_", text)
    return text


@router.get("/{map_id}/pdf")
async def export_map_to_pdf(
    map_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    types: Optional[str] = Query(
        None,
        description="Tipos de POI separados por virgula (ex: gas_station,restaurant)",
    ),
):
    """
    Export a saved map to PDF format.

    User must have the map in their collection to export it.

    Args:
        map_id: ID of the map to export
        types: Optional comma-separated list of POI types to include

    Returns:
        PDF file with the list of POIs
    """
    try:
        storage = MapStorageServiceDB(db)
        linear_map = await storage.load_map(map_id, user_id=current_user.id)

        if linear_map is None:
            raise HTTPException(status_code=404, detail=f"Map {map_id} not found")

        # Parse types filter
        poi_types_filter = None
        if types:
            poi_types_filter = [t.strip() for t in types.split(",")]

        # Generate PDF directly from the saved map data
        pdf_bytes = export_to_pdf(linear_map, poi_types_filter=poi_types_filter)

        # Generate filename
        origin_clean = _sanitize_filename(linear_map.origin)
        destination_clean = _sanitize_filename(linear_map.destination)
        filename = f"pois_{origin_clean}_{destination_clean}.pdf"
        filename_encoded = filename.encode("ascii", "ignore").decode("ascii")

        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="{filename_encoded}"',
                "Content-Type": "application/pdf",
            },
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error exporting map {map_id} to PDF: {e}")
        raise HTTPException(status_code=500, detail=f"Error exporting to PDF: {str(e)}")


@router.post("/{map_id}/adopt")
async def adopt_map(
    map_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Add an existing map to user's collection.

    This allows users to "adopt" maps created by other users without
    creating duplicates in the system.

    Args:
        map_id: ID of the map to adopt

    Returns:
        Success message
    """
    try:
        storage = MapStorageServiceDB(db)

        success = await storage.adopt_map(map_id, user_id=current_user.id)

        if not success:
            raise HTTPException(status_code=404, detail=f"Map {map_id} not found")

        await db.commit()
        return {"message": f"Map {map_id} added to your collection"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error adopting map {map_id}: {e}")
        raise HTTPException(status_code=500, detail="Error adopting map")


@router.delete("/{map_id}")
async def remove_map_from_collection(
    map_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Remove a map from user's collection (unlink).

    This only removes the map from the user's collection.
    The map remains in the system for other users.

    For permanent deletion, use DELETE /maps/{map_id}/permanent (admin only).

    Args:
        map_id: ID of the map to remove from collection

    Returns:
        Success message
    """
    try:
        storage = MapStorageServiceDB(db)

        # Check if user has this map
        has_map = await storage.user_has_map(current_user.id, map_id)
        if not has_map:
            raise HTTPException(
                status_code=404, detail=f"Map {map_id} not found in your collection"
            )

        # Always just unlink (remove from collection)
        success = await storage.unlink_map(map_id, user_id=current_user.id)
        if not success:
            raise HTTPException(
                status_code=500, detail="Failed to remove map from collection"
            )
        await db.commit()
        return {"message": f"Map {map_id} removed from your collection"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error unlinking map {map_id}: {e}")
        raise HTTPException(status_code=500, detail="Error removing map")


@router.delete("/{map_id}/permanent")
async def permanently_delete_map(
    map_id: str,
    current_user: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Permanently delete a map from the system (admin only).

    This removes the map and all user associations. Cannot be undone.

    Args:
        map_id: ID of the map to delete

    Returns:
        Success message
    """
    try:
        storage = MapStorageServiceDB(db)

        # Check if map exists
        exists = await storage.map_exists(map_id)
        if not exists:
            raise HTTPException(status_code=404, detail=f"Map {map_id} not found")

        success = await storage.delete_map_permanently(map_id)

        if not success:
            raise HTTPException(status_code=500, detail="Failed to delete map")

        await db.commit()
        return {"message": f"Map {map_id} permanently deleted"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error permanently deleting map {map_id}: {e}")
        raise HTTPException(status_code=500, detail="Error deleting map")


@router.post("/{map_id}/regenerate")
async def regenerate_map(
    map_id: str,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Regenerate a saved map with segment versioning (admin only).

    This endpoint regenerates a map creating NEW versions of all segments:
    1. Creates new segment versions (never reuses existing segments)
    2. Completely recalculates route, POIs, junctions, and sides
    3. Generates debug information for POI calculations
    4. Atomically replaces original map data with new versioned data
    5. Cleans up orphan segments after successful regeneration

    The original map ID is preserved, maintaining all user associations.
    Other maps using the same route segments continue using the old versions.

    Args:
        map_id: ID of the map to regenerate

    Returns:
        Async operation ID for tracking the regeneration progress
    """
    try:
        storage = MapStorageServiceDB(db)

        # Admin can load any map (don't filter by user_id)
        existing_map = await storage.load_map(map_id)
        if existing_map is None:
            raise HTTPException(status_code=404, detail=f"Map {map_id} not found")

        # Store map info before the session closes
        origin = existing_map.origin
        destination = existing_map.destination
        user_id = str(current_user.id)

        # Create new async operation for regeneration
        road_service = RoadService()

        # Start async operation with initial metadata for display
        operation = await AsyncService.create_operation(
            "map_regeneration",
            user_id=user_id,
            initial_result={
                "origin": origin,
                "destination": destination,
                "message": "Creating new segment versions...",
            },
        )

        # Define the function to execute in background
        def process_regeneration(progress_callback=None):
            temp_map_id = None
            try:
                logger.info(
                    f"Starting VERSIONED regeneration for map {map_id}: "
                    f"{origin} -> {destination}"
                )

                # Generate new temporary map with NEW segment versions
                # force_new_segments=True ensures all segments are new versions
                linear_map = road_service.generate_linear_map(
                    origin=origin,
                    destination=destination,
                    max_distance_from_road=3000,
                    progress_callback=progress_callback,
                    user_id=user_id,
                    force_new_segments=True,  # Create new segment versions
                )
                temp_map_id = linear_map.id
                logger.info(
                    f"Temporary map created with new segment versions: {temp_map_id}"
                )

                # Replace original map data with temporary map data
                # This preserves the original map ID and user associations
                # Old segments have usage decremented, new segments are linked
                from ..services.map_storage_service_db import replace_map_data_sync

                success = replace_map_data_sync(map_id, temp_map_id)
                if not success:
                    raise Exception("Failed to replace map data")

                logger.info(
                    f"Map {map_id} successfully regenerated with new segment versions"
                )

                # Clean up orphan segments in the background
                _cleanup_orphan_segments()

                # Result uses original map_id (unchanged for users)
                result = {
                    "map_id": map_id,  # Original ID preserved
                    "origin": linear_map.origin,
                    "destination": linear_map.destination,
                    "total_length_km": linear_map.total_length_km,
                    "segments": [
                        s.model_dump(mode="json") for s in linear_map.segments
                    ],
                    "milestones": [
                        m.model_dump(mode="json") for m in linear_map.milestones
                    ],
                    "versioning": {
                        "new_segments_created": True,
                        "old_segments_orphaned": True,
                    },
                }

                return result

            except Exception as e:
                logger.error(f"Error regenerating map: {e}")
                # Clean up temporary map if it was created
                if temp_map_id:
                    try:
                        from ..services.map_storage_service_db import delete_map_sync
                        delete_map_sync(temp_map_id)
                        logger.info(f"Cleaned up temporary map {temp_map_id}")
                    except Exception as cleanup_error:
                        logger.warning(f"Failed to cleanup temp map: {cleanup_error}")
                AsyncService.fail_operation(operation.operation_id, str(e))
                raise

        # Execute in background
        background_tasks.add_task(
            AsyncService.run_async,
            operation.operation_id,
            process_regeneration,
            request_id=get_request_id()
        )

        return {"operation_id": operation.operation_id}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error starting map regeneration for {map_id}: {e}")
        raise HTTPException(status_code=500, detail="Error starting map regeneration")


def _cleanup_orphan_segments():
    """
    Clean up orphan segments after map regeneration.

    Orphan segments are RouteSegments that are not referenced by any MapSegment.
    This typically happens after map regeneration when old segment versions
    are no longer used by any map.
    """
    import asyncio
    from sqlalchemy.ext.asyncio import (
        AsyncSession,
        async_sessionmaker,
        create_async_engine,
    )
    from api.database.repositories.route_segment import RouteSegmentRepository
    from api.providers.settings import get_settings

    settings = get_settings()

    async def _cleanup():
        database_url = (
            f"postgresql+asyncpg://{settings.postgres_user}:{settings.postgres_password}"
            f"@{settings.postgres_host}:{settings.postgres_port}/{settings.postgres_database}"
        )
        engine = create_async_engine(
            database_url,
            pool_size=1,
            max_overflow=0,
            pool_pre_ping=True,
        )
        session_maker = async_sessionmaker(
            engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )

        try:
            async with session_maker() as session:
                try:
                    repo = RouteSegmentRepository(session)
                    deleted = await repo.delete_orphan_segments()
                    await session.commit()
                    if deleted > 0:
                        logger.info(
                            f"Orphan cleanup: deleted {deleted} unused segments"
                        )
                except Exception as e:
                    await session.rollback()
                    logger.warning(f"Orphan cleanup failed: {e}")
        finally:
            await engine.dispose()

    try:
        asyncio.run(_cleanup())
    except Exception as e:
        logger.warning(f"Error running orphan cleanup: {e}")
