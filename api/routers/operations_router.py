from fastapi import APIRouter, HTTPException, BackgroundTasks
from typing import Dict, Any

from api.models.road_models import (
    AsyncOperationResponse,
    LinearMapRequest,
)
from api.services.async_service import AsyncService
from api.services.road_service import RoadService

router = APIRouter()
road_service = RoadService()

@router.get("/{operation_id}", response_model=AsyncOperationResponse)
async def get_operation(operation_id: str):
    """
    Obtém o status de uma operação assíncrona pelo seu ID.
    """
    operation = AsyncService.get_operation(operation_id)
    if not operation:
        raise HTTPException(status_code=404, detail=f"Operação {operation_id} não encontrada")
    return operation

@router.post("/linear-map", response_model=AsyncOperationResponse)
async def start_async_linear_map(request: LinearMapRequest, background_tasks: BackgroundTasks):
    """
    Inicia uma operação assíncrona para gerar um mapa linear de uma estrada.
    """
    # Criar uma nova operação
    operation = AsyncService.create_operation("linear_map")
    
    # Definir a função que executará o processamento em segundo plano
    def process_linear_map(progress_callback=None):
        try:
            # Gerar o mapa linear
            result = road_service.generate_linear_map(
                origin=request.origin,
                destination=request.destination,
                road_id=request.road_id,
                include_cities=request.include_cities,
                include_gas_stations=request.include_gas_stations,
                include_food=request.include_food,
                include_toll_booths=request.include_toll_booths,
                max_distance_from_road=request.max_distance_from_road,
                min_distance_from_origin_km=request.min_distance_from_origin_km,
                progress_callback=progress_callback
            )
            
            # Converter para dicionário para armazenamento
            return result.model_dump()
        except Exception as e:
            # Em caso de erro, falhar a operação
            AsyncService.fail_operation(operation.operation_id, str(e))
            raise
    
    # Adicionar a tarefa em segundo plano
    background_tasks.add_task(
        AsyncService.run_async,
        operation.operation_id,
        process_linear_map
    )
    
    return operation