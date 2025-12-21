from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import logging
import time

from api.middleware.error_handler import error_handler_middleware, setup_error_handlers

# Configurar logger
logger = logging.getLogger("api.main")

app = FastAPI(
    title="Mapa Linear API",
    description="API para geração de mapas lineares de estradas",
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
    
    # Skip logging for polling endpoints (too verbose)
    skip_logging = method == "GET" and path.startswith("/api/operations")

    if not skip_logging:
        logger.info(f"🔔 {method} {path}")

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

        if not skip_logging:
            logger.info(f"🏁 {method} {path} - {status_str} - {process_time:.3f}s")
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

# Import only required routers
from api.routers import operations_router, export, maps_router, api_logs_router, auth_router

# Include only required routers
app.include_router(auth_router.router, tags=["Auth"])
app.include_router(operations_router.router, prefix="/api/operations", tags=["Operations"])
app.include_router(export.router, prefix="/api", tags=["Export"])
app.include_router(maps_router.router, prefix="/api", tags=["Saved Maps"])
app.include_router(api_logs_router.router, tags=["API Logs"])

@app.get("/")
async def root():
    return {"message": "Bem-vindo à API do Mapa Linear"}

@app.get("/health")
async def health_check():
    return {"status": "ok"}