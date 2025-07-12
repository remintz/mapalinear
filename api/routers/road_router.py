from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional

from api.models.road_models import (
    LinearMapRequest,
    LinearMapResponse,
    RoadMilestoneResponse,
    SavedMapResponse,
    RouteStatisticsResponse,
)
from api.services.road_service import RoadService

router = APIRouter()
road_service = RoadService()

@router.post("/linear-map", response_model=LinearMapResponse)
async def generate_linear_map(request: LinearMapRequest):
    """
    Gera um mapa linear de uma estrada entre os pontos de origem e destino.
    """
    try:
        result = road_service.generate_linear_map(
            origin=request.origin,
            destination=request.destination,
            road_id=request.road_id,
            include_cities=request.include_cities,
            include_gas_stations=request.include_gas_stations,
            include_restaurants=request.include_restaurants,
            include_toll_booths=request.include_toll_booths,
            max_distance_from_road=request.max_distance_from_road
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/milestones", response_model=List[RoadMilestoneResponse])
async def get_road_milestones(
    road_id: str,
    origin: Optional[str] = Query(None, description="Ponto de origem"),
    destination: Optional[str] = Query(None, description="Ponto de destino"),
    milestone_type: Optional[str] = Query(None, description="Tipo de marco (cidade, posto, restaurante, etc.)")
):
    """
    Obtém marcos importantes ao longo de uma estrada.
    """
    try:
        result = road_service.get_road_milestones(road_id, origin, destination, milestone_type)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/saved-maps", response_model=List[SavedMapResponse])
async def get_saved_maps():
    """
    Obtém todos os mapas salvos anteriormente.
    """
    try:
        result = road_service.get_saved_maps()
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/saved-maps/{map_id}", response_model=SavedMapResponse)
async def get_saved_map(map_id: str):
    """
    Obtém um mapa salvo pelo seu ID.
    """
    try:
        result = road_service.get_saved_map(map_id)
        if not result:
            raise HTTPException(status_code=404, detail="Mapa não encontrado")
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/stats", response_model=RouteStatisticsResponse)
async def get_route_statistics(
    origin: str = Query(..., description="Ponto de origem (ex: 'São Paulo, SP')"),
    destination: str = Query(..., description="Ponto de destino (ex: 'Rio de Janeiro, RJ')"),
    include_gas_stations: bool = Query(True, description="Incluir postos de gasolina nas estatísticas"),
    include_restaurants: bool = Query(True, description="Incluir restaurantes nas estatísticas"),
    include_toll_booths: bool = Query(True, description="Incluir pedágios nas estatísticas"),
    max_distance_from_road: float = Query(1000, description="Distância máxima em metros da estrada para considerar POIs")
):
    """
    Obtém estatísticas detalhadas de uma rota incluindo densidade de POIs,
    tempo estimado de viagem e recomendações de paradas estratégicas.
    """
    try:
        result = road_service.get_route_statistics(
            origin=origin,
            destination=destination,
            include_gas_stations=include_gas_stations,
            include_restaurants=include_restaurants,
            include_toll_booths=include_toll_booths,
            max_distance_from_road=max_distance_from_road
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 