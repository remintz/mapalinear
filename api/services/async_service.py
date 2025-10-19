import os
import json
import uuid
import logging
import threading
import time
from typing import Dict, Any, Optional, Callable, List
from datetime import datetime, timedelta
from pathlib import Path

from api.models.road_models import AsyncOperationResponse, OperationStatus

logger = logging.getLogger(__name__)

# Diretório onde os arquivos de operação serão armazenados
ASYNC_DATA_DIR = os.environ.get("MAPALINEAR_ASYNC_DIR", "cache/async_operations")

# Garante que o diretório de cache exista
Path(ASYNC_DATA_DIR).mkdir(parents=True, exist_ok=True)

# Armazenamento em memória de operações ativas
active_operations = {}

class AsyncService:
    """Serviço para gerenciar operações assíncronas."""
    
    @staticmethod
    def _get_operation_path(operation_id: str) -> Path:
        """Retorna o caminho do arquivo para uma operação específica."""
        return Path(ASYNC_DATA_DIR) / f"{operation_id}.json"
    
    @staticmethod
    def create_operation(operation_type: str) -> AsyncOperationResponse:
        """
        Cria uma nova operação assíncrona.
        
        Args:
            operation_type: Tipo da operação (ex: linear_map)
            
        Returns:
            Objeto de resposta da operação assíncrona
        """
        operation_id = str(uuid.uuid4())
        
        # Criar uma nova operação
        operation = AsyncOperationResponse(
            operation_id=operation_id,
            type=operation_type,
            status=OperationStatus.IN_PROGRESS,
            started_at=datetime.now(),
            progress_percent=0,
            estimated_completion=datetime.now() + timedelta(minutes=5)  # Estimativa inicial
        )
        
        # Salvar a operação
        AsyncService.save_operation(operation)
        
        # Registrar no armazenamento em memória
        active_operations[operation_id] = operation
        
        return operation
    
    @staticmethod
    def get_operation(operation_id: str) -> Optional[AsyncOperationResponse]:
        """
        Obtém uma operação existente pelo seu ID.
        
        Args:
            operation_id: ID da operação
            
        Returns:
            Objeto de resposta da operação ou None se não encontrado
        """
        # Verificar primeiro no armazenamento em memória
        if operation_id in active_operations:
            return active_operations[operation_id]
        
        # Se não estiver em memória, tenta carregar do arquivo
        operation_path = AsyncService._get_operation_path(operation_id)
        if not operation_path.exists():
            return None
        
        try:
            with open(operation_path, "r") as f:
                operation_data = json.load(f)
            
            operation = AsyncOperationResponse(**operation_data)
            
            # Se a operação já foi concluída ou falhou, não a adicione ao armazenamento em memória
            if operation.status == OperationStatus.IN_PROGRESS:
                active_operations[operation_id] = operation
                
            return operation
        except Exception as e:
            logger.error(f"Erro ao carregar operação {operation_id}: {str(e)}")
            return None
    
    @staticmethod
    def save_operation(operation: AsyncOperationResponse) -> None:
        """
        Salva uma operação em disco.
        
        Args:
            operation: Objeto de operação a ser salvo
        """
        operation_path = AsyncService._get_operation_path(operation.operation_id)
        
        try:
            with open(operation_path, "w") as f:
                json.dump(operation.model_dump(), f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Erro ao salvar operação {operation.operation_id}: {str(e)}")
    
    @staticmethod
    def update_progress(operation_id: str, progress_percent: float, estimated_completion: Optional[datetime] = None) -> None:
        """
        Atualiza o progresso de uma operação.
        
        Args:
            operation_id: ID da operação
            progress_percent: Percentual de progresso (0-100)
            estimated_completion: Estimativa de conclusão atualizada
        """
        operation = AsyncService.get_operation(operation_id)
        if not operation:
            logger.warning(f"Tentativa de atualizar operação inexistente: {operation_id}")
            return
        
        operation.progress_percent = progress_percent
        if estimated_completion:
            operation.estimated_completion = estimated_completion
            
        AsyncService.save_operation(operation)
    
    @staticmethod
    def complete_operation(operation_id: str, result: Dict[str, Any]) -> None:
        """
        Marca uma operação como concluída e salva seu resultado.
        
        Args:
            operation_id: ID da operação
            result: Resultado da operação
        """
        operation = AsyncService.get_operation(operation_id)
        if not operation:
            logger.warning(f"Tentativa de completar operação inexistente: {operation_id}")
            return
        
        operation.status = OperationStatus.COMPLETED
        operation.progress_percent = 100
        operation.result = result
        operation.estimated_completion = None
        
        AsyncService.save_operation(operation)
        
        # Remover da memória após completar
        if operation_id in active_operations:
            del active_operations[operation_id]
    
    @staticmethod
    def fail_operation(operation_id: str, error: str) -> None:
        """
        Marca uma operação como falha.
        
        Args:
            operation_id: ID da operação
            error: Mensagem de erro
        """
        operation = AsyncService.get_operation(operation_id)
        if not operation:
            logger.warning(f"Tentativa de falhar operação inexistente: {operation_id}")
            return
        
        operation.status = OperationStatus.FAILED
        operation.error = error
        operation.estimated_completion = None
        
        AsyncService.save_operation(operation)
        
        # Remover da memória após falhar
        if operation_id in active_operations:
            del active_operations[operation_id]
    
    @staticmethod
    def list_operations(active_only: bool = True) -> List[AsyncOperationResponse]:
        """
        Lista operações assíncronas.
        
        Args:
            active_only: Se True, lista apenas operações em progresso
            
        Returns:
            Lista de operações
        """
        operations = []
        
        # Listar arquivos no diretório de operações
        for file_path in Path(ASYNC_DATA_DIR).glob("*.json"):
            try:
                with open(file_path, "r") as f:
                    operation_data = json.load(f)
                
                operation = AsyncOperationResponse(**operation_data)
                
                if not active_only or operation.status == OperationStatus.IN_PROGRESS:
                    operations.append(operation)
            except Exception as e:
                logger.error(f"Erro ao carregar operação de {file_path}: {str(e)}")
        
        return operations
    
    @staticmethod
    def run_async(
        operation_id: str,
        function: Callable,
        *args,
        **kwargs
    ) -> None:
        """
        Executa uma função de forma assíncrona.
        
        Args:
            operation_id: ID da operação
            function: Função a ser executada
            *args, **kwargs: Argumentos para a função
        """
        def _update_progress(progress: float):
            AsyncService.update_progress(
                operation_id, 
                progress,
                estimated_completion=datetime.now() + timedelta(minutes=5 * (100 - progress) / 100)
            )

        def _worker():
            # Criar um novo event loop para esta thread
            import asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                # Atualiza para 5% para mostrar que iniciou
                _update_progress(5)
                
                # Executa a função com o callback de progresso
                result = function(
                    progress_callback=_update_progress,
                    *args, 
                    **kwargs
                )
                
                # Marca como concluída
                AsyncService.complete_operation(operation_id, result)
                logger.info(f"Operação {operation_id} concluída com sucesso")
            except Exception as e:
                logger.error(f"Erro na operação assíncrona {operation_id}: {str(e)}")
                AsyncService.fail_operation(operation_id, str(e))
            finally:
                # NÃO fechar o event loop - deixar vivo para reutilização da thread
                # O event loop será reusado se a thread for reusada
                pass
        
        # Inicia a thread em segundo plano
        thread = threading.Thread(target=_worker)
        thread.daemon = True
        thread.start()
        
        logger.info(f"Operação assíncrona {operation_id} iniciada em segundo plano")
        
    @staticmethod
    def cleanup_old_operations(max_age_hours: int = 24) -> int:
        """
        Remove operações antigas do sistema.
        
        Args:
            max_age_hours: Idade máxima em horas para manter operações
            
        Returns:
            Número de operações removidas
        """
        cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
        removed_count = 0
        
        for file_path in Path(ASYNC_DATA_DIR).glob("*.json"):
            try:
                with open(file_path, "r") as f:
                    operation_data = json.load(f)
                
                # Converter a string de data para objeto datetime
                started_at = datetime.fromisoformat(operation_data.get('started_at').replace('Z', '+00:00'))
                
                # Remover se for muito antigo
                if started_at < cutoff_time:
                    operation_id = operation_data.get('operation_id')
                    
                    # Remover da memória se estiver ativo
                    if operation_id in active_operations:
                        del active_operations[operation_id]
                    
                    # Remover o arquivo
                    file_path.unlink()
                    removed_count += 1
                    logger.info(f"Operação antiga removida: {operation_id}")
            except Exception as e:
                logger.error(f"Erro ao processar operação de {file_path}: {str(e)}")
        
        return removed_count 