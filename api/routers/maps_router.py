"""
Router for managing saved linear maps.

Endpoints:
- GET /api/maps - List all saved maps
- GET /api/maps/{map_id} - Get a specific map
- DELETE /api/maps/{map_id} - Delete a saved map
- POST /api/maps/{map_id}/regenerate - Regenerate a map
"""

import logging
from typing import List

from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse

from ..models.road_models import LinearMapResponse, SavedMapResponse, LinearMapRequest
from ..services.map_storage_service import get_storage_service
from ..services.road_service import RoadService
from ..services.async_service import AsyncService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/maps", tags=["Saved Maps"])


@router.get("", response_model=List[SavedMapResponse])
async def list_saved_maps():
    """
    List all saved linear maps (metadata only).

    Returns:
        List of saved map metadata, sorted by creation date (newest first)
    """
    try:
        storage = get_storage_service()
        maps = storage.list_maps()
        return maps
    except Exception as e:
        logger.error(f"Error listing maps: {e}")
        raise HTTPException(status_code=500, detail="Error listing saved maps")


@router.get("/{map_id}", response_model=LinearMapResponse)
async def get_saved_map(map_id: str):
    """
    Get a specific saved map by ID.

    Args:
        map_id: ID of the map to retrieve

    Returns:
        The complete linear map data
    """
    try:
        storage = get_storage_service()
        linear_map = storage.load_map(map_id)

        if linear_map is None:
            raise HTTPException(status_code=404, detail=f"Map {map_id} not found")

        return linear_map
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error loading map {map_id}: {e}")
        raise HTTPException(status_code=500, detail="Error loading saved map")


@router.delete("/{map_id}")
async def delete_saved_map(map_id: str):
    """
    Delete a saved map.

    Args:
        map_id: ID of the map to delete

    Returns:
        Success message
    """
    try:
        storage = get_storage_service()

        if not storage.map_exists(map_id):
            raise HTTPException(status_code=404, detail=f"Map {map_id} not found")

        success = storage.delete_map(map_id)

        if not success:
            raise HTTPException(status_code=500, detail="Failed to delete map")

        return {"message": f"Map {map_id} deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting map {map_id}: {e}")
        raise HTTPException(status_code=500, detail="Error deleting map")


@router.post("/{map_id}/regenerate")
async def regenerate_map(map_id: str, background_tasks: BackgroundTasks):
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
        storage = get_storage_service()

        # Load existing map to get origin/destination
        existing_map = storage.load_map(map_id)
        if existing_map is None:
            raise HTTPException(status_code=404, detail=f"Map {map_id} not found")

        # Create new async operation for regeneration
        road_service = RoadService()

        # Start async operation
        operation = AsyncService.create_operation("map_regeneration")

        # Define the function to execute in background
        def process_regeneration(progress_callback=None):
            try:
                logger.info(f"🔄 Starting regeneration for map {map_id}: {existing_map.origin} → {existing_map.destination}")

                # Generate new map
                linear_map = road_service.generate_linear_map(
                    origin=existing_map.origin,
                    destination=existing_map.destination,
                    max_distance_from_road=3000,  # Default value
                    progress_callback=progress_callback
                )

                # Delete old map
                storage.delete_map(map_id)
                logger.info(f"🗑️ Old map {map_id} deleted")

                # Result will be the new map (it's already saved by road_service)
                result = {
                    "origin": linear_map.origin,
                    "destination": linear_map.destination,
                    "total_length_km": linear_map.total_length_km,
                    "segments": [s.model_dump(mode='json') for s in linear_map.segments],
                    "milestones": [m.model_dump(mode='json') for m in linear_map.milestones]
                }

                return result

            except Exception as e:
                logger.error(f"Error regenerating map: {e}")
                AsyncService.fail_operation(operation.operation_id, str(e))
                raise

        # Execute in background
        background_tasks.add_task(
            AsyncService.run_async,
            operation.operation_id,
            process_regeneration
        )

        return {"operation_id": operation.operation_id}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error starting map regeneration for {map_id}: {e}")
        raise HTTPException(status_code=500, detail="Error starting map regeneration")
