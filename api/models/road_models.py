from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any, Union, Literal
from enum import Enum
from datetime import datetime
from uuid import uuid4

from api.models.osm_models import Coordinates, OSMPointOfInterestType


class MilestoneType(str, Enum):
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
    INTERSECTION = "intersection"
    EXIT = "exit"
    OTHER = "other"


class LinearMapRequest(BaseModel):
    origin: str = Field(..., description="Ponto de origem (ex: 'São Paulo, SP')")
    destination: str = Field(..., description="Ponto de destino (ex: 'Rio de Janeiro, RJ')")
    road_id: Optional[str] = Field(None, description="ID da estrada (se já conhecido)")
    include_cities: bool = Field(True, description="Incluir cidades como marcos")
    include_gas_stations: bool = Field(True, description="Incluir postos de gasolina como marcos")
    include_restaurants: bool = Field(False, description="Incluir restaurantes como marcos")
    include_toll_booths: bool = Field(True, description="Incluir pedágios como marcos")
    max_distance_from_road: float = Field(1000, description="Distância máxima em metros da estrada para considerar pontos de interesse")


class RoadMilestone(BaseModel):
    id: str = Field(..., description="ID do marco no OSM")
    name: str = Field(..., description="Nome do marco")
    type: MilestoneType = Field(..., description="Tipo do marco")
    coordinates: Coordinates = Field(..., description="Coordenadas do marco")
    distance_from_origin_km: float = Field(..., description="Distância do ponto de origem em quilômetros")
    distance_from_road_meters: float = Field(..., description="Distância da estrada em metros")
    side: str = Field(..., description="Lado da estrada (left, right, center)")
    tags: Dict[str, Any] = Field(default_factory=dict, description="Tags adicionais do OSM")


class LinearRoadSegment(BaseModel):
    id: str = Field(..., description="ID do segmento no mapa linear")
    start_distance_km: float = Field(..., description="Distância do início do segmento em relação ao ponto de origem (km)")
    end_distance_km: float = Field(..., description="Distância do fim do segmento em relação ao ponto de origem (km)")
    length_km: float = Field(..., description="Comprimento do segmento em quilômetros")
    name: Optional[str] = Field(None, description="Nome da estrada neste segmento")
    ref: Optional[str] = Field(None, description="Referência da estrada neste segmento (ex: 'BR-101')")
    highway_type: Optional[str] = Field(None, description="Tipo de estrada (motorway, trunk, etc.)")
    start_milestone: Optional[RoadMilestone] = Field(None, description="Marco no início do segmento")
    end_milestone: Optional[RoadMilestone] = Field(None, description="Marco no fim do segmento")
    milestones: List[RoadMilestone] = Field(default_factory=list, description="Marcos ao longo do segmento")


class LinearMapResponse(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()), description="ID único do mapa linear")
    origin: str = Field(..., description="Ponto de origem")
    destination: str = Field(..., description="Ponto de destino")
    total_length_km: float = Field(..., description="Comprimento total da rota em quilômetros")
    segments: List[LinearRoadSegment] = Field(..., description="Segmentos do mapa linear")
    milestones: List[RoadMilestone] = Field(..., description="Todos os marcos ao longo da rota")
    creation_date: datetime = Field(default_factory=datetime.now, description="Data e hora de criação")
    osm_road_id: str = Field(..., description="ID da estrada no OpenStreetMap")


class RoadMilestoneResponse(BaseModel):
    id: str = Field(..., description="ID do marco")
    name: str = Field(..., description="Nome do marco")
    type: MilestoneType = Field(..., description="Tipo do marco")
    coordinates: Coordinates = Field(..., description="Coordenadas do marco")
    distance_from_origin_km: float = Field(..., description="Distância do ponto de origem em quilômetros")
    road_id: str = Field(..., description="ID da estrada")
    road_name: Optional[str] = Field(None, description="Nome da estrada")
    road_ref: Optional[str] = Field(None, description="Referência da estrada (ex: 'BR-101')")


class SavedMapResponse(BaseModel):
    id: str = Field(..., description="ID do mapa salvo")
    name: Optional[str] = Field(None, description="Nome do mapa")
    origin: str = Field(..., description="Ponto de origem")
    destination: str = Field(..., description="Ponto de destino")
    total_length_km: float = Field(..., description="Comprimento total da rota em quilômetros")
    creation_date: datetime = Field(..., description="Data e hora de criação")
    road_refs: List[str] = Field(default_factory=list, description="Referências das estradas (ex: ['BR-101', 'SP-070'])")
    milestone_count: int = Field(..., description="Número total de marcos no mapa")


class OperationStatus(str, Enum):
    """Status de uma operação assíncrona."""
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class AsyncOperationResponse(BaseModel):
    """Resposta para operações assíncronas."""
    operation_id: str = Field(..., description="ID da operação assíncrona")
    status: OperationStatus = Field(OperationStatus.IN_PROGRESS, description="Status atual da operação")
    type: str = Field(..., description="Tipo da operação (ex: linear_map)")
    started_at: datetime = Field(default_factory=datetime.now, description="Data e hora de início da operação")
    progress_percent: float = Field(0.0, description="Percentual de progresso (0-100)")
    estimated_completion: Optional[datetime] = Field(None, description="Estimativa de conclusão da operação")
    result: Optional[Dict[str, Any]] = Field(None, description="Resultado da operação (quando concluída)")
    error: Optional[str] = Field(None, description="Mensagem de erro (quando falha)") 