from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import logging
import time

from api.middleware.error_handler import error_handler_middleware, setup_error_handlers
from api.middleware.request_id import RequestIDMiddleware, set_request_id, get_request_id, set_session_id, clear_session_id

# Configurar logger
logger = logging.getLogger("api.main")


async def cleanup_orphaned_operations():
    """Cancel any operations that were in_progress when the server stopped."""
    from api.database.connection import get_session
    from api.database.models.async_operation import AsyncOperation
    from sqlalchemy import update, func

    try:
        async with get_session() as session:
            result = await session.execute(
                update(AsyncOperation)
                .where(AsyncOperation.status == "in_progress")
                .values(
                    status="failed",
                    completed_at=func.now(),
                    error="Operação abortada (servidor reiniciado)",
                )
            )
            count = result.rowcount
            if count > 0:
                logger.info(f"🧹 Limpeza: {count} operação(ões) órfã(s) marcada(s) como falha")
    except Exception as e:
        logger.warning(f"⚠️ Erro ao limpar operações órfãs: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle manager for the FastAPI app."""
    # Startup
    logger.info("🚀 Iniciando servidor...")
    await cleanup_orphaned_operations()
    yield
    # Shutdown
    logger.info("👋 Encerrando servidor...")


app = FastAPI(
    title="Mapa Linear API",
    description="API para geração de mapas lineares de estradas",
    version="0.1.0",
    lifespan=lifespan,
)

# Middleware para logging de requisições
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log de todas as requisições para depuração."""
    # Set request ID for this request (used by logging filter)
    req_id = set_request_id()

    # Capture session ID from frontend header (for log correlation)
    session_id = request.headers.get("X-Session-ID")
    if session_id:
        set_session_id(session_id)

    start_time = time.time()
    path = request.url.path
    method = request.method

    # Skip logging for polling endpoints (too verbose)
    skip_logging = method == "GET" and path.startswith("/api/operations")

    if not skip_logging:
        logger.info(f">> {method} {path}")

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
            logger.info(f"<< {method} {path} - {status_str} - {process_time:.3f}s")

        # Add request ID to response headers
        response.headers["X-Request-ID"] = req_id
        return response
    except Exception as e:
        process_time = time.time() - start_time
        logger.error(f"💥 ERRO: {method} {path} - Exceção: {str(e)} - Tempo: {process_time:.4f}s")
        raise
    finally:
        # Clear session ID after request completes
        clear_session_id()

# Configuração de CORS
# Nota: allow_credentials não é usado pois a autenticação é via Bearer token (JWT)
# e não via cookies. Usar allow_credentials=True com allow_origins=["*"] causa
# erro CORS nos navegadores.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Adicionar middleware de tratamento de erros
app.middleware("http")(error_handler_middleware)

# Configurar handlers de exceção
setup_error_handlers(app)

# Import only required routers
from api.routers import operations_router, export, maps_router, api_logs_router, auth_router, admin_router, settings_router, municipalities_router, problem_types_router, problem_reports_router, poi_debug_router, admin_pois_router, frontend_errors_router, session_activity_router

# Include only required routers
app.include_router(auth_router.router, tags=["Auth"])
app.include_router(operations_router.router, prefix="/api/operations", tags=["Operations"])
app.include_router(export.router, prefix="/api", tags=["Export"])
app.include_router(maps_router.router, prefix="/api", tags=["Saved Maps"])
app.include_router(api_logs_router.router, tags=["API Logs"])
app.include_router(admin_router.router, tags=["Admin"])
app.include_router(settings_router.router, tags=["Settings"])
app.include_router(municipalities_router.router, tags=["Municipalities"])
app.include_router(problem_types_router.router, tags=["Problem Types"])
app.include_router(problem_reports_router.router, tags=["Problem Reports"])
app.include_router(poi_debug_router.router, tags=["POI Debug"])
app.include_router(admin_pois_router.router, tags=["Admin POIs"])
app.include_router(frontend_errors_router.router, tags=["Frontend Errors"])
app.include_router(session_activity_router.router, tags=["Session Activity"])

@app.get("/")
async def root():
    return {"message": "Bem-vindo à API do Mapa Linear"}

@app.get("/health")
async def health_check():
    return {"status": "ok"}