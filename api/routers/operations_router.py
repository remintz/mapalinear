from fastapi import APIRouter, HTTPException, Query, BackgroundTasks
from typing import List, Optional, Dict, Any

from api.models.road_models import (
    AsyncOperationResponse,
    LinearMapRequest,
    LinearMapResponse,
)
from api.models.osm_models import OSMSearchRequest
from api.services.async_service import AsyncService
from api.services.road_service import RoadService
from api.services.osm_service import OSMService

router = APIRouter()
road_service = RoadService()
osm_service = OSMService()

@router.get("/{operation_id}", response_model=AsyncOperationResponse)
async def get_operation(operation_id: str):
    """
    Obtém o status de uma operação assíncrona pelo seu ID.
    """
    operation = AsyncService.get_operation(operation_id)
    if not operation:
        raise HTTPException(status_code=404, detail=f"Operação {operation_id} não encontrada")
    return operation

@router.get("", response_model=List[AsyncOperationResponse])
async def list_operations(active_only: bool = Query(True, description="Listar apenas operações em andamento")):
    """
    Lista operações assíncronas.
    """
    return AsyncService.list_operations(active_only=active_only)

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
                include_restaurants=request.include_restaurants,
                include_toll_booths=request.include_toll_booths,
                max_distance_from_road=request.max_distance_from_road,
                progress_callback=progress_callback
            )
            
            # Converter para dicionário para armazenamento
            return result.dict()
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

@router.post("/osm-search", response_model=AsyncOperationResponse)
async def start_async_osm_search(request: OSMSearchRequest, background_tasks: BackgroundTasks):
    """
    Inicia uma operação assíncrona para buscar estradas no OpenStreetMap.
    """
    # Criar uma nova operação
    operation = AsyncService.create_operation("osm_search")
    
    # Definir a função que executará o processamento em segundo plano
    def process_osm_search(progress_callback=None):
        try:
            # Executar a busca OSM
            if progress_callback:
                progress_callback(10.0)  # Iniciar com 10% para feedback visual
                
            result = osm_service.search_road_data(
                origin=request.origin,
                destination=request.destination,
                road_type=request.road_type
            )
            
            if progress_callback:
                progress_callback(90.0)  # Quase completo
                
            # Converter para dicionário para armazenamento
            return result.dict()
        except Exception as e:
            # Em caso de erro, falhar a operação
            AsyncService.fail_operation(operation.operation_id, str(e))
            raise
    
    # Adicionar a tarefa em segundo plano
    background_tasks.add_task(
        AsyncService.run_async,
        operation.operation_id,
        process_osm_search
    )
    
    return operation

@router.delete("/{operation_id}", response_model=Dict[str, Any])
async def cancel_operation(operation_id: str):
    """
    Cancela uma operação assíncrona em andamento.
    """
    operation = AsyncService.get_operation(operation_id)
    if not operation:
        raise HTTPException(status_code=404, detail=f"Operação {operation_id} não encontrada")
        
    # Verificar se a operação está em andamento
    if operation.status != "in_progress":
        raise HTTPException(status_code=400, detail=f"Operação {operation_id} não está em andamento")
    
    # Marcar como falhada com mensagem de cancelamento
    AsyncService.fail_operation(operation_id, "Operação cancelada pelo usuário")
    
    return {"message": f"Operação {operation_id} cancelada com sucesso"}

@router.delete("", response_model=Dict[str, Any])
async def cleanup_operations(max_age_hours: int = Query(24, description="Idade máxima em horas das operações a serem limpas")):
    """
    Limpa operações antigas do sistema.
    """
    count = AsyncService.cleanup_old_operations(max_age_hours=max_age_hours)
    return {"message": f"{count} operações antigas foram limpas"} 