from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
import traceback
import logging
import sys
import json
from typing import Union, Dict, Any, Optional
import hashlib
import time

# Criar um logger específico para o middleware
logger = logging.getLogger("api.middleware.error_handler")

class ErrorDetail:
    """Classe para detalhes de erro padronizados."""
    
    def __init__(
        self,
        status_code: int,
        message: str,
        error_type: str,
        stack_trace: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        self.status_code = status_code
        self.message = message
        self.error_type = error_type
        self.stack_trace = stack_trace
        self.details = details or {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Converte o erro para um dicionário."""
        error_dict = {
            "status_code": self.status_code,
            "message": self.message,
            "error_type": self.error_type
        }
        
        if self.stack_trace:
            error_dict["stack_trace"] = self.stack_trace
            
        if self.details:
            error_dict["details"] = self.details
            
        return error_dict

def format_stack_trace(stack_trace: str) -> str:
    """Formata o stack trace para ser mais legível no log."""
    lines = stack_trace.split('\n')
    # Adiciona indentação e cores para melhorar legibilidade
    formatted_lines = []
    for line in lines:
        if line.strip():
            formatted_lines.append(f"  │ {line}")
    
    return "\n".join(formatted_lines)

async def error_handler_middleware(request: Request, call_next):
    """
    Middleware para capturar exceções não tratadas e retornar 
    uma resposta JSON com informações sobre o erro.
    """
    # Use um ID único para o erro
    error_id = hashlib.md5(f"{time.time()}-{request.url.path}".encode()).hexdigest()[:8]
    
    try:
        return await call_next(request)
    except Exception as exc:
        # Capture o erro e o stack trace
        exc_type, exc_value, exc_traceback = sys.exc_info()
        stack_trace = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
        formatted_trace = format_stack_trace(stack_trace)
        
        # Detect if this is a Pydantic validation error even if wrapped in another exception
        is_validation_error = False
        error_details = None
        error_msg = str(exc)
        
        # Verificar se a mensagem de erro contém indicações de validação do Pydantic
        if "validation error" in error_msg.lower() or "input should be" in error_msg.lower():
            is_validation_error = True
            # Tenta extrair os detalhes de validação, se disponíveis
            if hasattr(exc, "errors"):
                error_details = exc.errors()
        
        # Log do erro com stack trace completo 
        error_type_emoji = "❌" if not is_validation_error else "⚠️"
        error_type_prefix = "ERRO" if not is_validation_error else "VALID"
        
        error_msg = f"{error_type_emoji} {error_type_prefix}#{error_id}: {request.method} {request.url.path} - {exc.__class__.__name__}: {str(exc)}"
        
        # Sempre mostrar o stack trace para erros
        logger.error(f"{error_msg}\n╭─ Stack Trace ─────────────────────────╮\n{formatted_trace}\n╰───────────────────────────────────────╯")
        
        # Determine error type and status code
        status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        if isinstance(exc, StarletteHTTPException):
            status_code = exc.status_code
            error_type = "http_exception"
        elif isinstance(exc, RequestValidationError) or is_validation_error:
            status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
            error_type = "validation_error"
        else:
            error_type = exc.__class__.__name__
        
        # Create error response with stack trace
        error_detail = ErrorDetail(
            status_code=status_code,
            message=str(exc),
            error_type=error_type,
            stack_trace=stack_trace,
            details=error_details or getattr(exc, "errors", None)
        )
        
        return JSONResponse(
            status_code=status_code,
            content=error_detail.to_dict()
        )

def setup_error_handlers(app):
    """
    Configura o tratamento de erros para a aplicação FastAPI.
    """
    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request, exc):
        """Handler para exceções HTTP."""
        # Use um ID único para o erro
        error_id = hashlib.md5(f"{time.time()}-{request.url.path}".encode()).hexdigest()[:8]
        
        # Capturar o stack trace para erros 500
        stack_trace = None
        if exc.status_code >= 500:
            stack_trace = "".join(traceback.format_exception(*sys.exc_info()))
            formatted_trace = format_stack_trace(stack_trace)
            error_msg = f"❌ HTTP#{error_id}: {request.method} {request.url.path} - {exc.status_code} - {exc.detail}"
            logger.error(f"{error_msg}\n╭─ Stack Trace ─────────────────────────╮\n{formatted_trace}\n╰───────────────────────────────────────╯")
        else:
            logger.warning(f"⚠️ HTTP#{error_id}: {exc.status_code} - {exc.detail}")
        
        error_detail = ErrorDetail(
            status_code=exc.status_code,
            message=str(exc.detail),
            error_type="http_exception",
            stack_trace=stack_trace
        )
        
        return JSONResponse(
            status_code=exc.status_code,
            content=error_detail.to_dict()
        )
    
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request, exc):
        """Handler para erros de validação."""
        # Use um ID único para o erro
        error_id = hashlib.md5(f"{time.time()}-{request.url.path}".encode()).hexdigest()[:8]
        
        # Sempre captura o stack trace completo
        exc_type, exc_value, exc_traceback = sys.exc_info()
        stack_trace = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
        formatted_trace = format_stack_trace(stack_trace)
        
        # Extrair detalhes dos erros de validação de forma organizada
        validation_errors = exc.errors()
        error_details_str = json.dumps(validation_errors, indent=2)
        
        # Log detalhado do erro de validação com stack trace
        error_detail = f"⚠️ VALID#{error_id}: Erro de validação em {request.method} {request.url.path}"
        logger.error(f"{error_detail}\n╭─ Erros de Validação ─────────────────╮\n  │ {error_details_str}\n╰───────────────────────────────────────╯")
        logger.error(f"{error_detail}\n╭─ Stack Trace ─────────────────────────╮\n{formatted_trace}\n╰───────────────────────────────────────╯")
        
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=ErrorDetail(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                message="Erro de validação nos dados da requisição",
                error_type="validation_error",
                stack_trace=stack_trace,
                details=validation_errors
            ).to_dict()
        )
    
    @app.exception_handler(Exception)
    async def generic_exception_handler(request, exc):
        """Handler para exceções genéricas não tratadas."""
        # Use um ID único para o erro
        error_id = hashlib.md5(f"{time.time()}-{request.url.path}".encode()).hexdigest()[:8]
        
        # Capturar stack trace e causa raiz
        exc_type, exc_value, exc_traceback = sys.exc_info()
        stack_trace = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
        formatted_trace = format_stack_trace(stack_trace)
        
        # Tentar extrair informações adicionais do erro
        error_details = {}
        if hasattr(exc, "__dict__"):
            for key, value in exc.__dict__.items():
                if not key.startswith("_") and not callable(value):
                    try:
                        # Tentar serializar para JSON para garantir que é serializável
                        json.dumps({key: value})
                        error_details[key] = value
                    except (TypeError, OverflowError):
                        error_details[key] = str(value)
        
        # Verificar se é uma exceção de validação embrulhada
        error_type = exc.__class__.__name__
        if "validation error" in str(exc).lower() or "input should be" in str(exc).lower():
            error_type = "validation_error"
        
        # Log detalhado do erro genérico
        error_msg = f"❌ EXC#{error_id}: {request.method} {request.url.path} - {error_type}: {str(exc)}"
        logger.error(f"{error_msg}\n╭─ Stack Trace ─────────────────────────╮\n{formatted_trace}\n╰───────────────────────────────────────╯")
        
        if error_details:
            details_str = json.dumps(error_details, indent=2)
            logger.error(f"{error_msg}\n╭─ Error Details ────────────────────────╮\n  │ {details_str}\n╰───────────────────────────────────────╯")
        
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=ErrorDetail(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message=str(exc),
                error_type=error_type,
                stack_trace=stack_trace,
                details=error_details if error_details else None
            ).to_dict()
        ) 