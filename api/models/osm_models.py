from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from enum import Enum
from datetime import datetime


class RoadType(str, Enum):
    HIGHWAY = "highway"
    MOTORWAY = "motorway"
    TRUNK = "trunk"
    PRIMARY = "primary"
    SECONDARY = "secondary"
    ALL = "all"


class Coordinates(BaseModel):
    lat: float = Field(..., description="Latitude")
    lon: float = Field(..., description="Longitude")


class OSMSearchRequest(BaseModel):
    origin: str = Field(..., description="Ponto de origem (ex: 'São Paulo, SP')")
    destination: str = Field(..., description="Ponto de destino (ex: 'Rio de Janeiro, RJ')")
    road_type: Optional[RoadType] = Field(RoadType.ALL, description="Tipo de estrada")


class OSMRoadSegment(BaseModel):
    id: str = Field(..., description="ID do segmento de estrada no OSM")
    name: Optional[str] = Field(None, description="Nome da estrada")
    highway_type: str = Field(..., description="Tipo de estrada (motorway, trunk, etc.)")
    ref: Optional[str] = Field(None, description="Referência da estrada (ex: 'BR-101')")
    geometry: List[Coordinates] = Field(..., description="Coordenadas do segmento")
    length_meters: float = Field(..., description="Comprimento do segmento em metros")
    start_node: str = Field(..., description="ID do nó inicial")
    end_node: str = Field(..., description="ID do nó final")
    tags: Dict[str, Any] = Field(default_factory=dict, description="Tags adicionais do OSM")


class OSMSearchResponse(BaseModel):
    road_segments: List[OSMRoadSegment] = Field(..., description="Segmentos de estrada encontrados")
    total_length_km: float = Field(..., description="Comprimento total da rota em quilômetros")
    straight_line_distance_km: float = Field(..., description="Distância em linha reta entre origem e destino")
    origin_coordinates: Coordinates = Field(..., description="Coordenadas do ponto de origem")
    destination_coordinates: Coordinates = Field(..., description="Coordenadas do ponto de destino")
    road_id: str = Field(..., description="ID da estrada completa")
    timestamp: datetime = Field(default_factory=datetime.now, description="Data e hora da busca")


class OSMRoadDetailsResponse(BaseModel):
    road_id: str = Field(..., description="ID da estrada")
    name: Optional[str] = Field(None, description="Nome principal da estrada")
    refs: List[str] = Field(default_factory=list, description="Referências da estrada (ex: ['BR-101', 'SP-070'])")
    segments: List[OSMRoadSegment] = Field(..., description="Segmentos que compõem a estrada")
    total_length_km: float = Field(..., description="Comprimento total da estrada em quilômetros")
    origin: Optional[str] = Field(None, description="Ponto de origem (cidade, estado)")
    destination: Optional[str] = Field(None, description="Ponto de destino (cidade, estado)")
    bounds: Dict[str, float] = Field(..., description="Limites geográficos (min_lat, min_lon, max_lat, max_lon)")


class OSMPointOfInterestType(str, Enum):
    CITY = "city"
    TOWN = "town"
    VILLAGE = "village"
    GAS_STATION = "gas_station"
    RESTAURANT = "restaurant"
    HOTEL = "hotel"
    REST_AREA = "rest_area"
    TOLL_BOOTH = "toll_booth"
    HOSPITAL = "hospital"
    POLICE = "police"
    OTHER = "other"


class OSMPointOfInterestResponse(BaseModel):
    id: str = Field(..., description="ID do ponto de interesse no OSM")
    name: str = Field(..., description="Nome do ponto de interesse")
    type: OSMPointOfInterestType = Field(..., description="Tipo do ponto de interesse")
    coordinates: Coordinates = Field(..., description="Coordenadas do ponto de interesse")
    distance_from_road_meters: float = Field(..., description="Distância da estrada em metros")
    distance_from_origin_km: float = Field(..., description="Distância do ponto de origem em quilômetros")
    tags: Dict[str, Any] = Field(default_factory=dict, description="Tags adicionais do OSM") 