import uuid
from typing import List, Optional, Dict, Any, Tuple, Callable
import logging
from datetime import datetime
import osmnx as ox
import geopy.distance
import os

from api.models.road_models import (
    LinearMapResponse,
    LinearRoadSegment,
    RoadMilestone,
    RoadMilestoneResponse,
    SavedMapResponse,
    MilestoneType,
)
from api.services.osm_service import OSMService
from api.models.osm_models import Coordinates

# Configuração do logging
def setup_logging():
    """
    Configura o logging para gravar em arquivo e console.
    """
    # Criar diretório de logs se não existir
    log_dir = "logs"
    os.makedirs(log_dir, exist_ok=True)
    
    # Nome do arquivo de log com timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = os.path.join(log_dir, f"mapalinear_{timestamp}.log")
    
    # Configurar o logger
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)
    logger.propagate = False  # Desabilita a propagação para o logger pai
    
    # Formato do log
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # Handler para arquivo
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)
    
    # Handler para console
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    
    # Adicionar handlers ao logger
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger

# Inicializar o logger
logger = setup_logging()

class RoadService:
    def __init__(self):
        self.osm_service = OSMService()
        # In a real implementation, you would have a database connection here
        self.saved_maps = {}  # Simple in-memory storage for now
    
    def _save_debug_info(self, osm_response, linear_segments, all_milestones):
        """
        Salva informações de debug sobre os segmentos e marcos em um arquivo texto.
        """
        debug_dir = "debug_outputs"
        os.makedirs(debug_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        debug_file = os.path.join(debug_dir, f"road_segments_{timestamp}.txt")
        
        with open(debug_file, "w", encoding="utf-8") as f:
            f.write("=== INFORMAÇÕES DE DEBUG DO MAPA LINEAR ===\n\n")
            
            f.write("=== SEGMENTOS OSM ===\n")
            accumulated_length = 0
            for i, segment in enumerate(osm_response.road_segments):
                f.write(f"\nSegmento OSM {i+1}:\n")
                f.write(f"  Nome: {segment.name}\n")
                f.write(f"  Tipo: {segment.highway_type}\n")
                f.write(f"  Referência: {segment.ref}\n")
                f.write(f"  Comprimento: {segment.length_meters:.2f}m\n")
                accumulated_length += segment.length_meters
                f.write(f"  Comprimento acumulado: {accumulated_length:.2f}m ({accumulated_length/1000:.2f}km)\n")
                f.write(f"  Número de pontos: {len(segment.geometry)}\n")
                f.write(f"  Primeiro ponto: {segment.geometry[0]}\n")
                f.write(f"  Último ponto: {segment.geometry[-1]}\n")
            
            f.write("\n\n=== SEGMENTOS LINEARES ===\n")
            for i, segment in enumerate(linear_segments):
                f.write(f"\nSegmento Linear {i+1}:\n")
                f.write(f"  ID: {segment.id}\n")
                f.write(f"  Nome: {segment.name}\n")
                f.write(f"  Referência: {segment.ref}\n")
                f.write(f"  Distância inicial: {segment.start_distance_km:.2f}km\n")
                f.write(f"  Distância final: {segment.end_distance_km:.2f}km\n")
                f.write(f"  Comprimento: {segment.length_km:.2f}km\n")
                f.write(f"  Número de marcos: {len(segment.milestones)}\n")
            
            f.write("\n\n=== MARCOS ===\n")
            for i, milestone in enumerate(all_milestones):
                f.write(f"\nMarco {i+1}:\n")
                f.write(f"  ID: {milestone.id}\n")
                f.write(f"  Nome: {milestone.name}\n")
                f.write(f"  Tipo: {milestone.type}\n")
                f.write(f"  Coordenadas: {milestone.coordinates}\n")
                f.write(f"  Distância da origem: {milestone.distance_from_origin_km:.2f}km\n")
                f.write(f"  Distância da estrada: {milestone.distance_from_road_meters:.2f}m\n")
                f.write(f"  Lado: {milestone.side}\n")
        
        logger.info(f"Arquivo de debug salvo em: {debug_file}")
        return debug_file

    def _segment_road(self, road_segments: List[Any], segment_length_km: float = 10.0) -> List[Dict[str, Any]]:
        """
        Segmenta a estrada em trechos menores para processamento mais eficiente.
        """
        logger.info(f"Iniciando segmentação da estrada em trechos de {segment_length_km}km")
        segments = []
        current_segment = {
            'start_idx': 0,
            'end_idx': 0,
            'start_distance': 0.0,
            'end_distance': 0.0,
            'center_point': None,
            'length': 0.0
        }
        
        total_length = 0.0
        segment_length_m = segment_length_km * 1000  # Converter para metros
        
        for i, segment in enumerate(road_segments):
            segment_length = segment.length_meters
            total_length += segment_length
            
            # Se o trecho atual ainda não atingiu o tamanho desejado
            if current_segment['length'] < segment_length_m:
                current_segment['end_idx'] = i
                current_segment['length'] += segment_length
                current_segment['end_distance'] = total_length
            else:
                # Calcular o ponto central do trecho
                if current_segment['start_idx'] == current_segment['end_idx']:
                    # Se o trecho é um único segmento, usar seu ponto central
                    segment = road_segments[current_segment['start_idx']]
                    center_idx = len(segment.geometry) // 2
                    current_segment['center_point'] = segment.geometry[center_idx]
                else:
                    # Se o trecho tem múltiplos segmentos, calcular o ponto médio
                    start_segment = road_segments[current_segment['start_idx']]
                    end_segment = road_segments[current_segment['end_idx']]
                    start_point = start_segment.geometry[0]
                    end_point = end_segment.geometry[-1]
                    current_segment['center_point'] = Coordinates(
                        lat=(start_point.lat + end_point.lat) / 2,
                        lon=(start_point.lon + end_point.lon) / 2
                    )
                
                logger.debug(f"Criado trecho de {current_segment['length']/1000:.2f}km com {current_segment['end_idx'] - current_segment['start_idx'] + 1} segmentos")
                segments.append(current_segment)
                
                # Iniciar novo trecho
                current_segment = {
                    'start_idx': i,
                    'end_idx': i,
                    'start_distance': total_length - segment_length,
                    'end_distance': total_length,
                    'center_point': None,
                    'length': segment_length
                }
        
        # Adicionar o último trecho se ele tiver algum comprimento
        if current_segment['length'] > 0:
            if current_segment['start_idx'] == current_segment['end_idx']:
                segment = road_segments[current_segment['start_idx']]
                center_idx = len(segment.geometry) // 2
                current_segment['center_point'] = segment.geometry[center_idx]
            else:
                start_segment = road_segments[current_segment['start_idx']]
                end_segment = road_segments[current_segment['end_idx']]
                start_point = start_segment.geometry[0]
                end_point = end_segment.geometry[-1]
                current_segment['center_point'] = Coordinates(
                    lat=(start_point.lat + end_point.lat) / 2,
                    lon=(start_point.lon + end_point.lon) / 2
                )
            logger.debug(f"Criado último trecho de {current_segment['length']/1000:.2f}km com {current_segment['end_idx'] - current_segment['start_idx'] + 1} segmentos")
            segments.append(current_segment)
        
        logger.info(f"Segmentação concluída: {len(segments)} trechos criados, comprimento total: {total_length/1000:.2f}km")
        return segments

    def _find_milestones_along_road(
        self, 
        road_segments: List[Any], 
        milestone_types: List[str], 
        max_distance: float,
        segment_length_km: float = 10.0
    ) -> List[RoadMilestone]:
        """
        Find milestones along a road using real data from OpenStreetMap.
        """
        logger.info(f"Iniciando busca de marcos: tipos={milestone_types}, distância máxima={max_distance}m")
        milestones = []
        
        # Get all coordinates from road segments
        all_coordinates = []
        for segment in road_segments:
            all_coordinates.extend(segment.geometry)
        
        # Calculate total road length
        total_length_km = sum(segment.length_meters for segment in road_segments) / 1000
        logger.info(f"Comprimento total da estrada: {total_length_km:.2f}km")
        
        # Segment the road into smaller chunks
        road_chunks = self._segment_road(road_segments, segment_length_km)
        
        # Process cities first (start and end points)
        if any(t in ["city", "town", "village"] for t in milestone_types) and all_coordinates:
            logger.info("Adicionando marcos de início e fim")
            # Start city
            start_milestone = RoadMilestone(
                id=str(uuid.uuid4()),
                name=f"{road_segments[0].name or 'Cidade Inicial'} (Início)",
                type=MilestoneType.CITY,
                coordinates=all_coordinates[0],
                distance_from_origin_km=0.0,
                distance_from_road_meters=0.0,
                side="center",
                tags={}
            )
            milestones.append(start_milestone)
            
            # End city
            end_milestone = RoadMilestone(
                id=str(uuid.uuid4()),
                name=f"{road_segments[-1].name or 'Cidade Final'} (Fim)",
                type=MilestoneType.CITY,
                coordinates=all_coordinates[-1],
                distance_from_origin_km=total_length_km,
                distance_from_road_meters=0.0,
                side="center",
                tags={}
            )
            milestones.append(end_milestone)
        
        # Query OSM for all other milestone types in each chunk
        logger.info(f"Iniciando busca de POIs em {len(road_chunks)} trechos")
        for i, chunk in enumerate(road_chunks):
            logger.info(f"Processando trecho {i+1}/{len(road_chunks)}")
            try:
                # Build Overpass query for this chunk
                lat, lon = chunk['center_point'].lat, chunk['center_point'].lon
                radius = max_distance  # in meters
                
                # Build query based on milestone types
                node_queries = []
                if "gas_station" in milestone_types:
                    node_queries.append(f'node["amenity"="fuel"](around:{radius},{lat},{lon})')
                if "toll_booth" in milestone_types:
                    node_queries.append(f'node["barrier"="toll_booth"](around:{radius},{lat},{lon})')
                if "restaurant" in milestone_types:
                    node_queries.append(f'node["amenity"="restaurant"](around:{radius},{lat},{lon})')
                
                if not node_queries:
                    continue
                
                # Build the complete query
                query = f"""[out:json];
(
    {';'.join(node_queries)};
);
out body;"""
                
                logger.debug(f"Query Overpass para trecho {i+1}: {query}")
                
                try:
                    # Execute query using the new method
                    result = self.osm_service.query_overpass(query)
                    
                    if not result:
                        logger.warning(f"Resposta vazia do Overpass API para o trecho {i+1}")
                        continue
                        
                    if 'elements' not in result:
                        logger.warning(f"Nenhum elemento encontrado na resposta do Overpass API para o trecho {i+1}")
                        continue
                    
                    # Process results
                    nodes_processed = 0
                    milestones_found = 0
                    
                    for element in result['elements']:
                        nodes_processed += 1
                        
                        # Skip elements without coordinates
                        if 'lat' not in element or 'lon' not in element:
                            continue
                        
                        # Determine milestone type and create milestone if applicable
                        milestone = None
                        
                        # Check for gas stations
                        if "gas_station" in milestone_types and element.get('tags', {}).get('amenity') == 'fuel':
                            if 'name' in element.get('tags', {}):
                                milestone = RoadMilestone(
                                    id=str(uuid.uuid4()),
                                    name=element['tags']['name'],
                                    type=MilestoneType.GAS_STATION,
                                    coordinates=Coordinates(
                                        lat=element['lat'],
                                        lon=element['lon']
                                    ),
                                    distance_from_origin_km=chunk['start_distance'] / 1000,
                                    distance_from_road_meters=geopy.distance.geodesic(
                                        (chunk['center_point'].lat, chunk['center_point'].lon),
                                        (element['lat'], element['lon'])
                                    ).meters,
                                    side="right",  # Default to right side
                                    tags=element.get('tags', {})
                                )
                        
                        # Check for toll booths
                        elif "toll_booth" in milestone_types and element.get('tags', {}).get('barrier') == 'toll_booth':
                            milestone = RoadMilestone(
                                id=str(uuid.uuid4()),
                                name=element.get('tags', {}).get('name', 'Pedágio'),
                                type=MilestoneType.TOLL_BOOTH,
                                coordinates=Coordinates(
                                    lat=element['lat'],
                                    lon=element['lon']
                                ),
                                distance_from_origin_km=chunk['start_distance'] / 1000,
                                distance_from_road_meters=geopy.distance.geodesic(
                                    (chunk['center_point'].lat, chunk['center_point'].lon),
                                    (element['lat'], element['lon'])
                                ).meters,
                                side="center",
                                tags=element.get('tags', {})
                            )
                        
                        # Check for restaurants
                        elif "restaurant" in milestone_types and element.get('tags', {}).get('amenity') == 'restaurant':
                            if 'name' in element.get('tags', {}):
                                milestone = RoadMilestone(
                                    id=str(uuid.uuid4()),
                                    name=element['tags']['name'],
                                    type=MilestoneType.RESTAURANT,
                                    coordinates=Coordinates(
                                        lat=element['lat'],
                                        lon=element['lon']
                                    ),
                                    distance_from_origin_km=chunk['start_distance'] / 1000,
                                    distance_from_road_meters=geopy.distance.geodesic(
                                        (chunk['center_point'].lat, chunk['center_point'].lon),
                                        (element['lat'], element['lon'])
                                    ).meters,
                                    side="right",  # Default to right side
                                    tags=element.get('tags', {})
                                )
                        
                        # Add milestone if created
                        if milestone:
                            milestones_found += 1
                            milestones.append(milestone)
                    
                    logger.info(f"Trecho {i+1}: processados {nodes_processed} nós, encontrados {milestones_found} marcos")
                    
                except Exception as e:
                    logger.error(f"Erro ao executar query Overpass para o trecho {i+1}: {str(e)}")
                    continue
                        
            except Exception as e:
                logger.error(f"Erro ao processar trecho {i+1}: {str(e)}")
                continue  # Continue with next chunk even if this one fails
        
        logger.info(f"Busca de marcos concluída: {len(milestones)} marcos encontrados no total")
        return milestones

    def generate_linear_map(
        self,
        origin: str,
        destination: str,
        road_id: Optional[str] = None,
        include_cities: bool = True,
        include_gas_stations: bool = True,
        include_restaurants: bool = False,
        include_toll_booths: bool = True,
        max_distance_from_road: float = 1000,
        progress_callback: Optional[Callable[[float], None]] = None,
        segment_length_km: float = 10.0
    ) -> LinearMapResponse:
        """
        Gera um mapa linear de uma estrada entre os pontos de origem e destino.
        """
        # Step 1: Get road data from OSM
        if road_id is None:
            # Search for road data if not provided
            osm_response = self.osm_service.search_road_data(origin, destination)
            road_id = osm_response.road_id
        else:
            # TODO: Retrieve road data from database
            # For now, search again
            osm_response = self.osm_service.search_road_data(origin, destination)
        
        # Step 2: Process road segments into linear segments
        linear_segments = self._process_road_segments(osm_response.road_segments)
        
        # Step 3: Find milestones along the road
        milestone_types = []
        if include_cities:
            milestone_types.extend(["city", "town", "village"])
        if include_gas_stations:
            milestone_types.append("gas_station")
        if include_restaurants:
            milestone_types.append("restaurant")
        if include_toll_booths:
            milestone_types.append("toll_booth")
        
        # In a real implementation, this would query OSM for POIs near the road
        # For now, we'll add some placeholder milestones
        all_milestones = self._find_milestones_along_road(
            osm_response.road_segments,
            milestone_types,
            max_distance_from_road,
            segment_length_km
        )
        
        # Step 4: Assign milestones to segments
        for segment in linear_segments:
            segment.milestones = [
                milestone for milestone in all_milestones
                if segment.start_distance_km <= milestone.distance_from_origin_km <= segment.end_distance_km
            ]
        
        # Save debug information
        debug_file = self._save_debug_info(osm_response, linear_segments, all_milestones)
        
        # Create linear map response
        linear_map = LinearMapResponse(
            origin=origin,
            destination=destination,
            total_length_km=osm_response.total_length_km,
            segments=linear_segments,
            milestones=all_milestones,
            osm_road_id=road_id
        )
        
        # Save the map for later retrieval
        self.saved_maps[linear_map.id] = linear_map
        
        return linear_map
    
    def _process_road_segments(self, osm_segments: List[Any]) -> List[LinearRoadSegment]:
        """
        Process OSM road segments into linear road segments.
        """
        linear_segments = []
        current_distance = 0
        
        for i, segment in enumerate(osm_segments):
            start_distance = current_distance
            length_km = segment.length_meters / 1000
            end_distance = start_distance + length_km
            
            linear_segment = LinearRoadSegment(
                id=str(uuid.uuid4()),
                start_distance_km=start_distance,
                end_distance_km=end_distance,
                length_km=length_km,
                name=segment.name,
                ref=segment.ref,
                start_milestone=None,
                end_milestone=None,
                milestones=[]
            )
            
            linear_segments.append(linear_segment)
            current_distance = end_distance
        
        return linear_segments
    
    def get_road_milestones(
        self, 
        road_id: str, 
        origin: Optional[str] = None, 
        destination: Optional[str] = None, 
        milestone_type: Optional[str] = None
    ) -> List[RoadMilestoneResponse]:
        """
        Obtém marcos importantes ao longo de uma estrada.
        """
        # In a real implementation, this would query the database for milestones
        # For now, we'll generate some milestones if we have the road in memory
        
        # Look for the road in saved maps
        for map_id, map_data in self.saved_maps.items():
            if map_data.osm_road_id == road_id:
                # Filter milestones by type if requested
                milestones = map_data.milestones
                if milestone_type:
                    milestones = [m for m in milestones if m.type.value == milestone_type]
                
                # Convert to response format
                return [
                    RoadMilestoneResponse(
                        id=milestone.id,
                        name=milestone.name,
                        type=milestone.type,
                        coordinates=milestone.coordinates,
                        distance_from_origin_km=milestone.distance_from_origin_km,
                        road_id=road_id,
                        road_name=None,  # Would come from database in real implementation
                        road_ref=None  # Would come from database in real implementation
                    )
                    for milestone in milestones
                ]
        
        # If road not found in saved maps, return empty list
        return []
    
    def get_saved_maps(self) -> List[SavedMapResponse]:
        """
        Obtém todos os mapas salvos anteriormente.
        """
        return [
            SavedMapResponse(
                id=map_id,
                name=None,  # User-provided names would be stored in a real implementation
                origin=map_data.origin,
                destination=map_data.destination,
                total_length_km=map_data.total_length_km,
                creation_date=map_data.creation_date,
                road_refs=[segment.ref for segment in map_data.segments if segment.ref],
                milestone_count=len(map_data.milestones)
            )
            for map_id, map_data in self.saved_maps.items()
        ]
    
    def get_saved_map(self, map_id: str) -> Optional[SavedMapResponse]:
        """
        Obtém um mapa salvo pelo seu ID.
        """
        if map_id in self.saved_maps:
            map_data = self.saved_maps[map_id]
            return SavedMapResponse(
                id=map_id,
                name=None,  # User-provided names would be stored in a real implementation
                origin=map_data.origin,
                destination=map_data.destination,
                total_length_km=map_data.total_length_km,
                creation_date=map_data.creation_date,
                road_refs=[segment.ref for segment in map_data.segments if segment.ref],
                milestone_count=len(map_data.milestones)
            )
        return None