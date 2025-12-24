from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from typing import Dict, Any, Optional
import logging

from api.providers.settings import get_settings
from api.database.connection import get_db
from api.database.models.user import User
from api.database.repositories.map import MapRepository
from api.database.repositories.system_settings import SystemSettingsRepository
from api.middleware.auth import get_current_user
from api.models.road_models import (
    AsyncOperationResponse,
    LinearMapRequest,
)
from api.providers.manager import get_manager
from api.services.async_service import AsyncService
from api.services.road_service import RoadService
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)
settings = get_settings()

router = APIRouter()
road_service = RoadService()

@router.get("/{operation_id}", response_model=AsyncOperationResponse)
async def get_operation(
    operation_id: str,
    current_user: User = Depends(get_current_user),
):
    """
    Obtém o status de uma operação assíncrona pelo seu ID.
    """
    operation = await AsyncService.get_operation(operation_id)
    if not operation:
        raise HTTPException(status_code=404, detail=f"Operação {operation_id} não encontrada")
    return operation

@router.post("/linear-map", response_model=AsyncOperationResponse)
async def start_async_linear_map(
    request: LinearMapRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Inicia uma operação assíncrona para gerar um mapa linear de uma estrada.
    Backend sempre busca todos os tipos de POI - filtros são aplicados no frontend.
    """
    logger.info(f"🔍 Requisição recebida: origin={request.origin}, destination={request.destination}")

    # Geocodificar origem e destino para validação de duplicatas
    try:
        geo_provider = get_manager().get_provider()
        origin_location = await geo_provider.geocode(request.origin)
        dest_location = await geo_provider.geocode(request.destination)

        if not origin_location or not dest_location:
            raise HTTPException(
                status_code=400,
                detail="Não foi possível geocodificar origem ou destino"
            )

        # Buscar tolerância de duplicatas do banco de dados
        settings_repo = SystemSettingsRepository(db)
        tolerance_str = await settings_repo.get_value("duplicate_map_tolerance_km", "10")
        tolerance_km = float(tolerance_str)

        # Verificar se já existe um mapa com coordenadas próximas
        map_repo = MapRepository(db)
        existing_map = await map_repo.find_by_coordinates_proximity(
            origin_lat=origin_location.latitude,
            origin_lon=origin_location.longitude,
            dest_lat=dest_location.latitude,
            dest_lon=dest_location.longitude,
            tolerance_km=tolerance_km,
        )

        if existing_map:
            logger.info(f"⚠️ Mapa duplicado detectado por proximidade: {existing_map.id}")
            raise HTTPException(
                status_code=409,
                detail={
                    "message": "Já existe um mapa com origem e destino equivalentes",
                    "existing_map_id": str(existing_map.id),
                    "origin": existing_map.origin,
                    "destination": existing_map.destination,
                    "hint": "Você pode adicionar este mapa à sua mapoteca"
                }
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.warning(f"⚠️ Erro ao verificar duplicatas: {e}. Continuando sem validação.")

    # Store user_id for the background task
    user_id = str(current_user.id)

    # Criar uma nova operação
    operation = await AsyncService.create_operation("linear_map")
    
    # Definir a função que executará o processamento em segundo plano
    # NOTA: Não use try/except aqui - o run_async._worker já trata erros
    # corretamente usando engine standalone para a thread
    def process_linear_map(progress_callback=None):
        # Gerar o mapa linear (sempre busca todos os tipos de POI)
        result = road_service.generate_linear_map(
            origin=request.origin,
            destination=request.destination,
            road_id=request.road_id,
            include_cities=request.include_cities,
            max_distance_from_road=request.max_distance_from_road,
            max_detour_distance_km=request.max_detour_distance_km,
            min_distance_from_origin_km=request.min_distance_from_origin_km,
            progress_callback=progress_callback,
            user_id=user_id
        )
        
        # Converter para dicionário para armazenamento
        return result.model_dump()
    
    # Adicionar a tarefa em segundo plano
    background_tasks.add_task(
        AsyncService.run_async,
        operation.operation_id,
        process_linear_map
    )
    
    return operation


@router.get("/debug/segments", response_model=Dict[str, Any])
async def get_debug_segments(
    operation_id: Optional[str] = None,
    current_user: User = Depends(get_current_user),
):
    """
    Endpoint de debug para visualizar os segmentos de 10km criados a partir da rota.
    Se operation_id não for fornecido, retorna os segmentos do último mapa linear gerado.
    """
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        # Se operation_id não foi fornecido, buscar a última operação concluída
        if not operation_id:
            operations = await AsyncService.list_operations(active_only=False)
            
            # Filtrar apenas operações de tipo "linear_map" que foram concluídas
            completed_maps = [
                op for op in operations 
                if op.type == "linear_map" and op.status == "completed" and op.result is not None
            ]
            
            if not completed_maps:
                raise HTTPException(
                    status_code=404, 
                    detail="Nenhum mapa linear foi gerado ainda. Gere um mapa primeiro na página de busca."
                )
            
            # Ordenar por data de início (mais recente primeiro)
            completed_maps.sort(key=lambda x: x.started_at, reverse=True)
            latest_operation = completed_maps[0]
            operation_id = latest_operation.operation_id
            logger.info(f"Using latest operation: {operation_id}")
        
        # Buscar a operação específica
        operation = await AsyncService.get_operation(operation_id)
        if not operation:
            raise HTTPException(status_code=404, detail=f"Operação {operation_id} não encontrada")
        
        if operation.status != "completed":
            raise HTTPException(
                status_code=400, 
                detail=f"Operação {operation_id} ainda não foi concluída. Status: {operation.status}"
            )
        
        if not operation.result:
            raise HTTPException(
                status_code=404, 
                detail=f"Operação {operation_id} não possui resultado"
            )
        
        # Extrair os segmentos do resultado
        result = operation.result
        segments = result.get("segments", [])
        
        if not segments:
            raise HTTPException(
                status_code=404, 
                detail="Nenhum segmento encontrado no resultado da operação"
            )
        
        # Preparar resposta com os segmentos
        segments_data = []
        for segment in segments:
            segment_info = {
                "id": segment.get("id"),
                "start_distance_km": segment.get("start_distance_km"),
                "end_distance_km": segment.get("end_distance_km"),
                "length_km": segment.get("length_km"),
                "name": segment.get("name"),
                "start_coordinates": segment.get("start_coordinates"),
                "end_coordinates": segment.get("end_coordinates"),
            }
            segments_data.append(segment_info)
        
        logger.info(f"Returning {len(segments_data)} debug segments from operation {operation_id}")
        
        return {
            "operation_id": operation_id,
            "origin": result.get("origin"),
            "destination": result.get("destination"),
            "total_distance_km": result.get("total_length_km"),
            "total_segments": len(segments_data),
            "segments": segments_data
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating debug segments: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Erro ao gerar segmentos de debug: {str(e)}")
