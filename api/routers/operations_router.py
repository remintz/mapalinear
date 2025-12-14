from fastapi import APIRouter, HTTPException, BackgroundTasks
from typing import Dict, Any, Optional

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
    operation = await AsyncService.get_operation(operation_id)
    if not operation:
        raise HTTPException(status_code=404, detail=f"Operação {operation_id} não encontrada")
    return operation

@router.post("/linear-map", response_model=AsyncOperationResponse)
async def start_async_linear_map(request: LinearMapRequest, background_tasks: BackgroundTasks):
    """
    Inicia uma operação assíncrona para gerar um mapa linear de uma estrada.
    Backend sempre busca todos os tipos de POI - filtros são aplicados no frontend.
    """
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"🔍 Requisição recebida: origin={request.origin}, destination={request.destination}")

    # Criar uma nova operação
    operation = await AsyncService.create_operation("linear_map")
    
    # Definir a função que executará o processamento em segundo plano
    def process_linear_map(progress_callback=None):
        try:
            # Gerar o mapa linear (sempre busca todos os tipos de POI)
            result = road_service.generate_linear_map(
                origin=request.origin,
                destination=request.destination,
                road_id=request.road_id,
                include_cities=request.include_cities,
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


@router.get("/debug/segments", response_model=Dict[str, Any])
async def get_debug_segments(operation_id: Optional[str] = None):
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
