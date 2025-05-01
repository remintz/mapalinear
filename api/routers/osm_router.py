from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional

from api.models.osm_models import (
    OSMSearchRequest,
    OSMSearchResponse,
    OSMRoadDetailsResponse,
    OSMPointOfInterestResponse,
)
from api.services.osm_service import OSMService

router = APIRouter()
osm_service = OSMService()

@router.post("/search", response_model=OSMSearchResponse)
async def search_osm_data(request: OSMSearchRequest):
    """
    Busca dados de estradas no OpenStreetMap entre os pontos de origem e destino.
    """
    try:
        result = osm_service.search_road_data(
            origin=request.origin,
            destination=request.destination,
            road_type=request.road_type
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/road/{road_id}", response_model=OSMRoadDetailsResponse)
async def get_road_details(road_id: str):
    """
    Obtém detalhes de uma estrada específica pelo seu ID.
    """
    try:
        result = osm_service.get_road_details(road_id)
        if not result:
            raise HTTPException(status_code=404, detail="Estrada não encontrada")
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/pois", response_model=List[OSMPointOfInterestResponse])
async def get_points_of_interest(
    road_id: str,
    distance: Optional[float] = Query(1000, description="Distância máxima em metros da estrada para buscar pontos de interesse"),
    poi_type: Optional[str] = Query(None, description="Tipo de ponto de interesse (cidade, posto de gasolina, etc.)")
):
    """
    Obtém pontos de interesse ao longo de uma estrada.
    """
    try:
        result = osm_service.get_points_of_interest(road_id, distance, poi_type)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 