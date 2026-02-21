"""
Configurações e constantes para o teste comparativo de busca de POIs.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Carregar variáveis de ambiente do arquivo .env local
env_path = Path(__file__).parent / ".env"
load_dotenv(env_path)

# Configurações de busca
SEARCH_RADIUS_METERS = 1000  # Raio de busca em metros
MAX_POI_PER_QUERY = 20       # Máximo de POIs por query
REQUEST_DELAY_SECONDS = 1.0  # Delay entre requisições (para evitar rate limit)

# Categorias de POI a buscar (mesmas do MapaLinear)
POI_CATEGORIES = [
    "gas_station",
    "fuel",
    "restaurant",
    "food",
    "hotel",
    "lodging",
    "camping",
    "hospital",
    "city",
    "town",
    "village",
]

# API Keys (variáveis de ambiente)
# Configure estas variáveis ou preencha diretamente
MAPBOX_TOKEN = os.environ.get(
    "MAPBOX_ACCESS_TOKEN",
    ""
)

HERE_API_KEY = os.environ.get(
    "HERE_API_KEY",
    ""
)

# Endpoints
OVERPASS_ENDPOINTS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
]

# Arquivo de dados da rota
ROUTE_DATA_FILE = "data/bh_ouro_preto.json"

# Arquivo de saída do relatório
REPORT_FILE = "comparativo.md"

# Pontos de teste ao longo da rota BH -> Ouro Preto (99km)
# Distribuídos a cada ~5km para ter 20 pontos
TEST_POINTS = [
    {"index": 1, "distance_km": 2.0, "lat": -19.9557, "lon": -43.9407, "location": "Belo Horizonte"},
    {"index": 2, "distance_km": 3.0, "lat": -19.9928, "lon": -43.9591, "location": "Belo Horizonte"},
    {"index": 3, "distance_km": 5.0, "lat": -20.0382, "lon": -43.9684, "location": "Contagem"},
    {"index": 4, "distance_km": 7.0, "lat": -20.0530, "lon": -43.9698, "location": "Ibirité"},
    {"index": 5, "distance_km": 9.0, "lat": -20.0593, "lon": -43.9764, "location": "Ibirité"},
    {"index": 6, "distance_km": 11.0, "lat": -20.0832, "lon": -43.9782, "location": "Ibirité"},
    {"index": 7, "distance_km": 13.0, "lat": -20.1007, "lon": -43.9753, "location": "Betim"},
    {"index": 8, "distance_km": 15.0, "lat": -20.1168, "lon": -43.9686, "location": "Betim"},
    {"index": 9, "distance_km": 17.0, "lat": -20.1341, "lon": -43.9632, "location": "Betim"},
    {"index": 10, "distance_km": 19.0, "lat": -20.1506, "lon": -43.9622, "location": "Betim"},
    {"index": 11, "distance_km": 22.0, "lat": -20.1630, "lon": -43.9365, "location": "BR-040"},
    {"index": 12, "distance_km": 25.0, "lat": -20.1802, "lon": -43.9174, "location": "BR-040"},
    {"index": 13, "distance_km": 28.0, "lat": -20.1923, "lon": -43.8620, "location": "BR-040"},
    {"index": 14, "distance_km": 31.0, "lat": -20.1995, "lon": -43.8644, "location": "BR-040"},
    {"index": 15, "distance_km": 34.0, "lat": -20.2051, "lon": -43.8409, "location": "BR-040"},
    {"index": 16, "distance_km": 37.0, "lat": -20.2129, "lon": -43.8396, "location": "BR-040"},
    {"index": 17, "distance_km": 40.0, "lat": -20.2200, "lon": -43.8239, "location": "BR-040"},
    {"index": 18, "distance_km": 43.0, "lat": -20.2298, "lon": -43.8000, "location": "BR-040"},
    {"index": 19, "distance_km": 46.0, "lat": -20.2459, "lon": -43.7969, "location": "Itabirito"},
    {"index": 20, "distance_km": 49.0, "lat": -20.2595, "lon": -43.7862, "location": "Itabirito"},
]

# Mapeamento de categorias para Overpass
OVERPASS_CATEGORY_MAP = {
    "gas_station": ["amenity=fuel"],
    "fuel": ["amenity=fuel"],
    "restaurant": ["amenity=restaurant"],
    "food": ["amenity=restaurant", "amenity=fast_food", "amenity=food_court"],
    "hotel": ["tourism=hotel", "tourism=motel"],
    "lodging": ["tourism=hotel", "tourism=motel", "tourism=guest_house"],
    "camping": ["tourism=camping"],
    "hospital": ["amenity=hospital", "amenity=clinic"],
    "city": ["place=city"],
    "town": ["place=town"],
    "village": ["place=village"],
}

# Mapeamento de categorias para Mapbox
MAPBOX_CATEGORY_MAP = {
    "gas_station": "gas_station",
    "fuel": "gas_station",
    "restaurant": "restaurant",
    "food": "restaurant",
    "hotel": "hotel",
    "lodging": "hotel",
    "camping": "campground",
    "hospital": "hospital",
    "city": "place",
    "town": "place",
    "village": "place",
}

# Mapeamento de categorias para HERE
HERE_CATEGORY_MAP = {
    "gas_station": "700-7600-0116",
    "fuel": "700-7600-0116",
    "restaurant": "100-1000",
    "food": "100-1000,100-1000-0001",
    "hotel": "500-5000,500-5100",
    "lodging": "500-5000,500-5100",
    "camping": "500-5300",
    "hospital": "800-8000-0159",
    "city": "",
    "town": "",
    "village": "",
}