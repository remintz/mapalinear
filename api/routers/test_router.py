from fastapi import APIRouter, HTTPException, Depends, Query, Body
from typing import Dict, Any, List
import logging

router = APIRouter()
logger = logging.getLogger("api.routers.test_router")

class CustomException(Exception):
    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)

@router.get("/simple-error")
async def test_simple_error():
    """Gera um erro simples para testar o middleware."""
    logger.info("Gerando erro simples...")
    raise ValueError("Este é um erro simples para testar o middleware")

@router.get("/http-error")
async def test_http_error():
    """Gera um erro HTTP para testar o middleware."""
    logger.info("Gerando erro HTTP...")
    raise HTTPException(status_code=404, detail="Recurso não encontrado")

@router.get("/custom-error")
async def test_custom_error():
    """Gera um erro customizado para testar o middleware."""
    logger.info("Gerando erro customizado...")
    raise CustomException("Este é um erro customizado para testar o middleware")

@router.post("/validation-error")
async def test_validation_error(
    data: Dict[str, Any] = Body(..., examples=[{"name": "Test", "age": 30}])
):
    """Rota para testar erros de validação."""
    return {"message": "Dados válidos", "data": data}

@router.get("/nested-error")
async def test_nested_error():
    """Gera um erro aninhado para testar o stack trace."""
    return _nested_function_1()

def _nested_function_1():
    """Função aninhada nível 1."""
    return _nested_function_2()

def _nested_function_2():
    """Função aninhada nível 2."""
    return _nested_function_3()

def _nested_function_3():
    """Função aninhada nível 3 que gera um erro."""
    a = [1, 2, 3]
    # Gerando erro de índice fora do intervalo
    return a[10] 