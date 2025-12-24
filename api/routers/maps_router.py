"""
Router for managing saved linear maps.

Endpoints:
- GET /api/maps - List all saved maps for current user
- GET /api/maps/{map_id} - Get a specific map
- GET /api/maps/{map_id}/pdf - Export map to PDF
- DELETE /api/maps/{map_id} - Delete a saved map
- POST /api/maps/{map_id}/regenerate - Regenerate a map
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
from ..middleware.auth import get_current_user
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
        maps = await storage.list_maps(user_id=current_user.id)
        return maps
    except Exception as e:
        logger.error(f"Error listing maps: {e}")
        raise HTTPException(status_code=500, detail="Error listing saved maps")


@router.get("/{map_id}", response_model=LinearMapResponse)
async def get_saved_map(
    map_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get a specific saved map by ID.

    Args:
        map_id: ID of the map to retrieve

    Returns:
        The complete linear map data
    """
    try:
        storage = MapStorageServiceDB(db)
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
        None, description="Tipos de POI separados por vírgula (ex: gas_station,restaurant)"
    ),
):
    """
    Export a saved map to PDF format.

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


@router.delete("/{map_id}")
async def delete_saved_map(
    map_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Delete a saved map.

    Args:
        map_id: ID of the map to delete

    Returns:
        Success message
    """
    try:
        storage = MapStorageServiceDB(db)

        if not await storage.map_exists(map_id, user_id=current_user.id):
            raise HTTPException(status_code=404, detail=f"Map {map_id} not found")

        success = await storage.delete_map(map_id, user_id=current_user.id)

        if not success:
            raise HTTPException(status_code=500, detail="Failed to delete map")

        return {"message": f"Map {map_id} deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting map {map_id}: {e}")
        raise HTTPException(status_code=500, detail="Error deleting map")


@router.post("/{map_id}/regenerate")
async def regenerate_map(
    map_id: str,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Regenerate a saved map (creates a new async operation).

    This endpoint loads the existing map metadata, creates a new async operation
    to regenerate the map with fresh data, and deletes the old map.

    Args:
        map_id: ID of the map to regenerate

    Returns:
        Async operation ID for tracking the regeneration progress
    """
    try:
        storage = MapStorageServiceDB(db)

        # Load existing map to get origin/destination
        existing_map = await storage.load_map(map_id, user_id=current_user.id)
        if existing_map is None:
            raise HTTPException(status_code=404, detail=f"Map {map_id} not found")

        # Store map info before the session closes
        origin = existing_map.origin
        destination = existing_map.destination
        user_id = str(current_user.id)

        # Create new async operation for regeneration
        road_service = RoadService()

        # Start async operation
        operation = await AsyncService.create_operation("map_regeneration")

        # Define the function to execute in background
        def process_regeneration(progress_callback=None):
            try:
                logger.info(
                    f"Starting regeneration for map {map_id}: {origin} -> {destination}"
                )

                # Generate new map (this will save it to DB via save_map_sync)
                linear_map = road_service.generate_linear_map(
                    origin=origin,
                    destination=destination,
                    max_distance_from_road=3000,  # Default value
                    progress_callback=progress_callback,
                    user_id=user_id,
                )

                # Delete old map using sync wrapper
                from ..services.map_storage_service_db import delete_map_sync

                delete_map_sync(map_id)
                logger.info(f"Old map {map_id} deleted")

                # Result will be the new map
                result = {
                    "origin": linear_map.origin,
                    "destination": linear_map.destination,
                    "total_length_km": linear_map.total_length_km,
                    "segments": [s.model_dump(mode="json") for s in linear_map.segments],
                    "milestones": [
                        m.model_dump(mode="json") for m in linear_map.milestones
                    ],
                }

                return result

            except Exception as e:
                logger.error(f"Error regenerating map: {e}")
                AsyncService.fail_operation(operation.operation_id, str(e))
                raise

        # Execute in background
        background_tasks.add_task(
            AsyncService.run_async, operation.operation_id, process_regeneration
        )

        return {"operation_id": operation.operation_id}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error starting map regeneration for {map_id}: {e}")
        raise HTTPException(status_code=500, detail="Error starting map regeneration")
