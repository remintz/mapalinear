from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional, Dict, Any
from enum import Enum
from pydantic import BaseModel, Field

from api.models.road_models import RoadMilestone, MilestoneType, Coordinates
from api.services.osm_service import OSMService

router = APIRouter()
osm_service = OSMService()

class SortBy(str, Enum):
    DISTANCE = "distance"
    NAME = "name"
    QUALITY = "quality"

class POISearchResponse(BaseModel):
    """Resposta da busca de POIs."""
    pois: List[RoadMilestone] = Field(..., description="Lista de POIs encontrados")
    total_count: int = Field(..., description="Número total de POIs encontrados")
    search_radius_meters: float = Field(..., description="Raio de busca utilizado")
    center_coordinates: Coordinates = Field(..., description="Coordenadas centrais da busca")

@router.get("/search", response_model=POISearchResponse)
async def search_pois(
    lat: float = Query(..., description="Latitude do centro da busca"),
    lon: float = Query(..., description="Longitude do centro da busca"),
    radius: int = Query(1000, ge=100, le=5000, description="Raio de busca em metros (100-5000)"),
    types: Optional[List[str]] = Query(None, description="Tipos de POI a buscar (gas_station, restaurant, toll_booth)"),
    has_name: bool = Query(False, description="Filtrar apenas POIs com nome"),
    has_phone: bool = Query(False, description="Filtrar apenas POIs com telefone"),
    has_hours: bool = Query(False, description="Filtrar apenas POIs com horário de funcionamento"),
    brand: Optional[str] = Query(None, description="Filtrar por marca específica"),
    operator: Optional[str] = Query(None, description="Filtrar por operadora específica"),
    cuisine: Optional[str] = Query(None, description="Filtrar por tipo de culinária (para restaurantes)"),
    sort_by: SortBy = Query(SortBy.DISTANCE, description="Ordenação dos resultados"),
    limit: int = Query(50, ge=1, le=200, description="Limite de resultados (1-200)")
):
    """
    Busca POIs ao redor de uma coordenada com filtros avançados.
    
    Esta busca permite encontrar pontos de interesse com critérios específicos
    como presença de nome, telefone, marca, etc.
    """
    try:
        # Validar tipos de POI
        valid_types = {"gas_station", "restaurant", "toll_booth"}
        if types:
            invalid_types = set(types) - valid_types
            if invalid_types:
                raise HTTPException(
                    status_code=400, 
                    detail=f"Tipos inválidos: {invalid_types}. Tipos válidos: {valid_types}"
                )
        else:
            types = ["gas_station", "restaurant", "toll_booth"]
        
        # Construir tipos de POI para query OSM
        poi_types = []
        if "gas_station" in types:
            poi_types.append({"amenity": "fuel"})
        if "restaurant" in types:
            poi_types.append({"amenity": "restaurant"})
        if "toll_booth" in types:
            poi_types.append({"barrier": "toll_booth"})
        
        # Buscar POIs
        coordinates = [Coordinates(lat=lat, lon=lon)]
        elements = osm_service.search_pois_around_coordinates(
            coordinates=coordinates,
            radius_meters=radius,
            poi_types=poi_types,
            max_concurrent_requests=1,
            max_coords_per_batch=1
        )
        
        # Processar resultados
        pois = []
        from api.services.road_service import RoadService
        road_service = RoadService()
        
        for element in elements:
            if 'lat' not in element or 'lon' not in element:
                continue
                
            element_tags = element.get('tags', {})
            
            # Aplicar filtros de qualidade
            if road_service._is_poi_abandoned(element_tags):
                continue
            
            quality_score = road_service._calculate_poi_quality_score(element_tags)
            
            # Aplicar filtros específicos
            if has_name and not element_tags.get('name'):
                continue
            if has_phone and not (element_tags.get('phone') or element_tags.get('contact:phone')):
                continue
            if has_hours and not element_tags.get('opening_hours'):
                continue
            if brand and element_tags.get('brand', '').lower() != brand.lower():
                continue
            if operator and element_tags.get('operator', '').lower() != operator.lower():
                continue
            if cuisine and element_tags.get('cuisine', '').lower() != cuisine.lower():
                continue
            
            # Determinar tipo do POI
            poi_type = None
            name = "POI"
            
            if element_tags.get('amenity') == 'fuel':
                poi_type = MilestoneType.GAS_STATION
                name = element_tags.get('name') or element_tags.get('brand') or element_tags.get('operator') or 'Posto de Combustível'
            elif element_tags.get('amenity') == 'restaurant':
                poi_type = MilestoneType.RESTAURANT
                name = element_tags.get('name') or element_tags.get('brand') or 'Restaurante'
            elif element_tags.get('barrier') == 'toll_booth':
                poi_type = MilestoneType.TOLL_BOOTH
                name = element_tags.get('name') or element_tags.get('operator') or 'Pedágio'
            
            if not poi_type:
                continue
            
            # Calcular distância do centro
            import geopy.distance
            distance_meters = geopy.distance.geodesic(
                (lat, lon),
                (element['lat'], element['lon'])
            ).meters
            
            # Criar POI
            poi = RoadMilestone(
                id=str(element.get('id', '')),
                name=name,
                type=poi_type,
                coordinates=Coordinates(lat=element['lat'], lon=element['lon']),
                distance_from_origin_km=distance_meters / 1000,
                distance_from_road_meters=distance_meters,
                side="unknown",
                tags=element_tags,
                operator=element_tags.get('operator'),
                brand=element_tags.get('brand'),
                opening_hours=element_tags.get('opening_hours'),
                phone=element_tags.get('phone') or element_tags.get('contact:phone'),
                website=element_tags.get('website') or element_tags.get('contact:website'),
                cuisine=element_tags.get('cuisine'),
                amenities=road_service._extract_amenities(element_tags),
                quality_score=quality_score
            )
            
            pois.append(poi)
        
        # Ordenar resultados
        if sort_by == SortBy.DISTANCE:
            pois.sort(key=lambda p: p.distance_from_road_meters)
        elif sort_by == SortBy.NAME:
            pois.sort(key=lambda p: p.name.lower())
        elif sort_by == SortBy.QUALITY:
            pois.sort(key=lambda p: p.quality_score or 0, reverse=True)
        
        # Aplicar limite
        pois = pois[:limit]
        
        return POISearchResponse(
            pois=pois,
            total_count=len(pois),
            search_radius_meters=radius,
            center_coordinates=Coordinates(lat=lat, lon=lon)
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao buscar POIs: {str(e)}")

@router.get("/types", response_model=Dict[str, Any])
async def get_poi_types():
    """
    Retorna os tipos de POI disponíveis e suas descrições.
    """
    return {
        "types": {
            "gas_station": {
                "description": "Postos de combustível",
                "osm_tags": ["amenity=fuel"],
                "example_brands": ["Petrobras", "Shell", "Ipiranga", "Esso"]
            },
            "restaurant": {
                "description": "Restaurantes e lanchonetes",
                "osm_tags": ["amenity=restaurant"],
                "example_cuisines": ["brazilian", "fast_food", "pizza", "italian"]
            },
            "toll_booth": {
                "description": "Pedágios",
                "osm_tags": ["barrier=toll_booth"],
                "example_operators": ["CCR", "Arteris", "EcoRodovias"]
            }
        },
        "sort_options": ["distance", "name", "quality"],
        "max_radius_meters": 5000,
        "max_results": 200
    }