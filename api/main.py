from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="Mapa Linear API",
    description="API para extração de dados do OpenStreetMap e criação de mapas lineares de estradas",
    version="0.1.0",
)

# Configuração de CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Import routers
from api.routers import osm_router, road_router

# Include routers
app.include_router(osm_router.router, prefix="/api/osm", tags=["OpenStreetMap"])
app.include_router(road_router.router, prefix="/api/roads", tags=["Roads"])

@app.get("/")
async def root():
    return {"message": "Bem-vindo à API do Mapa Linear"}

@app.get("/health")
async def health_check():
    return {"status": "ok"} 