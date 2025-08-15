from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import logging
import time

from api.middleware.error_handler import error_handler_middleware, setup_error_handlers

# Configurar logger
logger = logging.getLogger("api.main")

app = FastAPI(
    title="Mapa Linear API",
    description="API para extração de dados do OpenStreetMap e criação de mapas lineares de estradas",
    version="0.1.0",
)

# Middleware para logging de requisições
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log de todas as requisições para depuração."""
    # Use um marcador úncido para identificar o início e fim da mesma requisição
    req_id = hash(f"{time.time()}-{request.url.path}")
    
    start_time = time.time()
    path = request.url.path
    method = request.method
    
    # Log mais conciso evitando strings repetitivas
    logger.info(f"🔔 REQ#{req_id} INICIADA: {method} {path}")
    
    try:
        response = await call_next(request)
        
        process_time = time.time() - start_time
        status_code = response.status_code
        
        # Status code colorido por categoria
        if status_code < 400:
            status_str = f"✅ {status_code}"
        elif status_code < 500:
            status_str = f"⚠️ {status_code}"
        else:
            status_str = f"❌ {status_code}"
            
        logger.info(f"🏁 REQ#{req_id} COMPLETA: {method} {path} - Status: {status_str} - Tempo: {process_time:.4f}s")
        return response
    except Exception as e:
        process_time = time.time() - start_time
        logger.error(f"💥 REQ#{req_id} ERRO: {method} {path} - Exceção: {str(e)} - Tempo: {process_time:.4f}s")
        raise

# Configuração de CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Adicionar middleware de tratamento de erros
app.middleware("http")(error_handler_middleware)

# Configurar handlers de exceção
setup_error_handlers(app)

# Import routers
from api.routers import osm_router, road_router, test_router, operations_router, pois_router, export

# Include routers
app.include_router(osm_router.router, prefix="/api/osm", tags=["OpenStreetMap"])
app.include_router(road_router.router, prefix="/api/roads", tags=["Roads"])
app.include_router(pois_router.router, prefix="/api/pois", tags=["Points of Interest"])
app.include_router(operations_router.router, prefix="/api/operations", tags=["Operations"])
app.include_router(export.router, prefix="/api", tags=["Export"])
app.include_router(test_router.router, prefix="/api/test", tags=["Testes"])

@app.get("/")
async def root():
    return {"message": "Bem-vindo à API do Mapa Linear"}

@app.get("/health")
async def health_check():
    return {"status": "ok"}

# Rota de teste para verificar o tratamento de erros
@app.get("/test-error")
async def test_error():
    """Rota para testar o middleware de erro."""
    raise ValueError("Isso é um erro de teste para verificar o middleware de tratamento de erros!") 