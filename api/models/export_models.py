"""
Modelos para exportação de dados de rotas e POIs.
"""

from pydantic import BaseModel, Field, model_validator
from typing import List, Optional, Dict, Any
from api.models.road_models import Coordinates


class ExportCoordinates(BaseModel):
    """Coordenadas que aceitam tanto lat/lon quanto latitude/longitude."""
    lat: float
    lon: float

    @model_validator(mode='before')
    @classmethod
    def normalize_coordinates(cls, data: Any) -> Any:
        """Normaliza latitude/longitude para lat/lon."""
        if isinstance(data, dict):
            # Se veio latitude/longitude, converte para lat/lon
            if 'latitude' in data and 'lat' not in data:
                data['lat'] = data['latitude']
            if 'longitude' in data and 'lon' not in data:
                data['lon'] = data['longitude']
        return data


class ExportPOI(BaseModel):
    id: str
    name: str
    type: str
    coordinates: ExportCoordinates
    distance_from_origin_km: float
    brand: Optional[str] = None
    operator: Optional[str] = None
    opening_hours: Optional[str] = None
    # Campos adicionais para consistência com a tela
    city: Optional[str] = None
    requires_detour: Optional[bool] = False
    junction_distance_km: Optional[float] = None
    distance_from_road_meters: Optional[float] = None
    side: Optional[str] = None


class ExportSegment(BaseModel):
    id: str
    name: Optional[str] = None
    geometry: List[ExportCoordinates]
    length_km: float


class ExportRouteData(BaseModel):
    """Modelo flexível para dados de exportação vindos do frontend."""
    origin: str
    destination: str
    total_distance_km: float
    segments: List[ExportSegment] = Field(default_factory=list)
    pois: List[ExportPOI] = Field(default_factory=list)
    
    def to_linear_map_response(self) -> Dict[str, Any]:
        """Converte para formato LinearMapResponse para compatibilidade."""
        from api.models.road_models import MilestoneType
        from api.models.road_models import Coordinates
        
        # Converter POIs para milestones
        milestones = []
        for poi in self.pois:
            # Mapear tipos de POI para MilestoneType
            milestone_type = MilestoneType.OTHER
            if poi.type == "gas_station":
                milestone_type = MilestoneType.GAS_STATION
            elif poi.type == "restaurant":
                milestone_type = MilestoneType.RESTAURANT
            elif poi.type == "toll_booth":
                milestone_type = MilestoneType.TOLL_BOOTH
            elif poi.type in ["city", "town", "village"]:
                milestone_type = MilestoneType.CITY
            
            milestone = {
                "id": poi.id,
                "name": poi.name,
                "type": milestone_type,
                "coordinates": Coordinates(latitude=poi.coordinates.lat, longitude=poi.coordinates.lon),
                "distance_from_origin_km": poi.distance_from_origin_km,
                "distance_from_road_meters": 0.0,
                "side": "right",
                "tags": {},
                "operator": poi.operator,
                "brand": poi.brand,
                "opening_hours": poi.opening_hours
            }
            milestones.append(milestone)
        
        # Converter segmentos
        converted_segments = []
        for seg in self.segments:
            geometry = [Coordinates(latitude=coord.lat, longitude=coord.lon) for coord in seg.geometry]
            converted_segment = {
                "id": seg.id,
                "name": seg.name or "Segmento",
                "ref": None,
                "start_distance_km": 0.0,  # Será calculado se necessário
                "end_distance_km": seg.length_km,
                "length_km": seg.length_km,
                "geometry": geometry,
                "milestones": []  # Milestones serão associados depois se necessário
            }
            converted_segments.append(converted_segment)
        
        return {
            "id": "export-temp",
            "origin": self.origin,
            "destination": self.destination,
            "total_length_km": self.total_distance_km,
            "segments": converted_segments,
            "milestones": milestones,
            "creation_date": "2024-01-01T00:00:00",
            "road_id": "export-temp"
        }