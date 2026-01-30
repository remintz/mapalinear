from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any, Union, Literal
from enum import Enum
from datetime import datetime
from uuid import uuid4


class Coordinates(BaseModel):
    """Generic coordinates representation."""
    latitude: float = Field(..., ge=-90, le=90, description="Latitude coordinate")
    longitude: float = Field(..., ge=-180, le=180, description="Longitude coordinate")


class MilestoneType(str, Enum):
    CITY = "city"
    TOWN = "town"
    VILLAGE = "village"
    GAS_STATION = "gas_station"
    RESTAURANT = "restaurant"
    FAST_FOOD = "fast_food"
    CAFE = "cafe"
    BAR = "bar"
    PUB = "pub"
    FOOD_COURT = "food_court"
    BAKERY = "bakery"
    ICE_CREAM = "ice_cream"
    HOTEL = "hotel"
    CAMPING = "camping"
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
    max_distance_from_road: float = Field(1000, description="Distância máxima em metros da estrada para considerar pontos de interesse")
    max_detour_distance_km: float = Field(5.0, description="Distância máxima em km do entroncamento até o POI (POIs com desvio maior serão excluídos)")
    min_distance_from_origin_km: float = Field(0.0, description="Distância mínima em km da origem (não mais usado - filtramos por cidade de origem)")


class RoadMilestone(BaseModel):
    id: str = Field(..., description="ID único do marco")
    name: str = Field(..., description="Nome do marco")
    type: MilestoneType = Field(..., description="Tipo do marco")
    coordinates: Coordinates = Field(..., description="Coordenadas do marco")
    distance_from_origin_km: float = Field(..., description="Distância do ponto de origem em quilômetros")
    distance_from_road_meters: float = Field(..., description="Distância da estrada em metros")
    side: str = Field(..., description="Lado da estrada (left, right, center)")
    tags: Dict[str, Any] = Field(default_factory=dict, description="Metadados adicionais do provider")

    # Metadados enriquecidos
    city: Optional[str] = Field(None, description="Cidade onde o POI está localizado")
    operator: Optional[str] = Field(None, description="Operadora do estabelecimento (ex: 'Petrobras', 'Shell')")
    brand: Optional[str] = Field(None, description="Marca do estabelecimento")
    opening_hours: Optional[str] = Field(None, description="Horário de funcionamento")
    phone: Optional[str] = Field(None, description="Telefone de contato")
    website: Optional[str] = Field(None, description="Website do estabelecimento")
    cuisine: Optional[str] = Field(None, description="Tipo de culinária (para restaurantes)")
    amenities: List[str] = Field(default_factory=list, description="Comodidades disponíveis (ex: 'wi-fi', 'estacionamento')")
    quality_score: Optional[float] = Field(None, description="Score de qualidade (0.0 a 1.0) baseado na completude dos dados")

    # Avaliações do Google (para restaurantes e hotéis)
    rating: Optional[float] = Field(None, description="Avaliação do Google (1.0 a 5.0 estrelas)")
    rating_count: Optional[int] = Field(None, description="Número de avaliações no Google")
    google_maps_uri: Optional[str] = Field(None, description="URL do Google Maps para o estabelecimento")

    # Informações de entroncamento (para POIs afastados)
    junction_distance_km: Optional[float] = Field(None, description="Distância do entroncamento/saída desde a origem (para POIs afastados da estrada)")
    junction_coordinates: Optional[Coordinates] = Field(None, description="Coordenadas do entroncamento onde sair da estrada principal")
    requires_detour: bool = Field(False, description="Se True, POI requer sair da estrada principal (>500m de distância)")


class LinearRoadSegment(BaseModel):
    """
    DEPRECATED: Use MapSegmentResponse instead.
    Kept for backwards compatibility with existing serialized data.
    """
    id: str = Field(..., description="ID do segmento no mapa linear")
    start_distance_km: float = Field(..., description="Distância do início do segmento em relação ao ponto de origem (km)")
    end_distance_km: float = Field(..., description="Distância do fim do segmento em relação ao ponto de origem (km)")
    length_km: float = Field(..., description="Comprimento do segmento em quilômetros")
    name: Optional[str] = Field(None, description="Nome da estrada neste segmento")
    ref: Optional[str] = Field(None, description="Referência da estrada neste segmento (ex: 'BR-101')")
    highway_type: Optional[str] = Field(None, description="Tipo de estrada (motorway, trunk, etc.)")
    start_coordinates: Optional[Coordinates] = Field(None, description="Coordenadas do início do segmento")
    end_coordinates: Optional[Coordinates] = Field(None, description="Coordenadas do fim do segmento")
    geometry: List[Coordinates] = Field(default_factory=list, description="Coordenadas geográficas do segmento")
    start_milestone: Optional[RoadMilestone] = Field(None, description="Marco no início do segmento")
    end_milestone: Optional[RoadMilestone] = Field(None, description="Marco no fim do segmento")
    milestones: List[RoadMilestone] = Field(default_factory=list, description="Marcos ao longo do segmento")


class MapSegmentResponse(BaseModel):
    """
    Response model for map segments using RouteSegment data from database.

    This model replaces LinearRoadSegment and provides all the data needed
    for the frontend to:
    1. Draw the route on the map (via geometry)
    2. Calculate distance from origin for any point on the route
    """
    id: str = Field(..., description="RouteSegment ID")
    sequence_order: int = Field(..., description="Order of this segment in the map (0, 1, 2, ...)")
    distance_from_origin_km: float = Field(..., description="Cumulative distance from origin to START of this segment (km)")
    length_km: float = Field(..., description="Length of this segment in km")
    geometry: List[Coordinates] = Field(..., description="Full geometry of the segment as list of coordinates")
    road_name: Optional[str] = Field(None, description="Name of the road in this segment")
    start_lat: float = Field(..., description="Latitude of segment start")
    start_lon: float = Field(..., description="Longitude of segment start")
    end_lat: float = Field(..., description="Latitude of segment end")
    end_lon: float = Field(..., description="Longitude of segment end")


class LinearMapResponse(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()), description="ID único do mapa linear")
    origin: str = Field(..., description="Ponto de origem")
    destination: str = Field(..., description="Ponto de destino")
    total_length_km: float = Field(..., description="Comprimento total da rota em quilômetros")
    segments: List[Union[MapSegmentResponse, LinearRoadSegment]] = Field(..., description="Segmentos do mapa linear")
    milestones: List[RoadMilestone] = Field(..., description="Todos os marcos ao longo da rota")
    creation_date: datetime = Field(default_factory=datetime.now, description="Data e hora de criação")
    road_id: str = Field(..., description="ID da estrada no provider geográfico")


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


class POIStatistics(BaseModel):
    """Estatísticas de POIs por tipo."""
    type: str = Field(..., description="Tipo de POI")
    total_count: int = Field(..., description="Número total de POIs deste tipo")
    average_distance_km: float = Field(..., description="Distância média entre POIs deste tipo")
    density_per_100km: float = Field(..., description="Densidade de POIs por 100km")


class RouteStopRecommendation(BaseModel):
    """Recomendação de parada estratégica."""
    distance_km: float = Field(..., description="Distância da origem em km")
    reason: str = Field(..., description="Motivo da recomendação")
    available_services: List[str] = Field(..., description="Serviços disponíveis nesta parada")
    recommended_duration_minutes: int = Field(..., description="Duração recomendada da parada")


class RouteStatisticsResponse(BaseModel):
    """Estatísticas completas de uma rota."""
    route_info: Dict[str, Any] = Field(..., description="Informações básicas da rota")
    total_length_km: float = Field(..., description="Distância total da rota")
    estimated_travel_time_hours: float = Field(..., description="Tempo estimado de viagem em horas")
    poi_statistics: List[POIStatistics] = Field(..., description="Estatísticas por tipo de POI")
    recommendations: List[RouteStopRecommendation] = Field(..., description="Recomendações de paradas")
    quality_metrics: Dict[str, Any] = Field(..., description="Métricas de qualidade dos dados")


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
    current_phase: Optional[str] = Field(None, description="Fase atual da operação (ex: geocoding, poi_search)")
    estimated_completion: Optional[datetime] = Field(None, description="Estimativa de conclusão da operação")
    result: Optional[Dict[str, Any]] = Field(None, description="Resultado da operação (quando concluída)")
    error: Optional[str] = Field(None, description="Mensagem de erro (quando falha)") 