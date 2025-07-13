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
        min_distance_from_origin_km: float = 5.0,
        segment_length_km: float = 10.0
    ) -> List[RoadMilestone]:
        """
        Find milestones along a road using real data from OpenStreetMap.
        """
        logger.info(f"Iniciando busca de marcos: tipos={milestone_types}, distância máxima={max_distance}m")
        milestones = []
        seen_coordinates = set()  # Set to track seen coordinates
        
        # Get all coordinates from road segments
        all_coordinates = []
        accumulated_distances = []  # Lista para armazenar distâncias acumuladas
        current_distance = 0.0
        
        for segment in road_segments:
            for coord in segment.geometry:
                all_coordinates.append(coord)
                accumulated_distances.append(current_distance)
                if len(all_coordinates) > 1:
                    # Calcula a distância entre o ponto atual e o anterior
                    prev_coord = all_coordinates[-2]
                    current_distance += geopy.distance.geodesic(
                        (prev_coord.lat, prev_coord.lon),
                        (coord.lat, coord.lon)
                    ).kilometers
        
        # Calculate total road length
        total_length_km = current_distance
        
        logger.info(f"Comprimento total da estrada: {total_length_km:.2f}km")
        
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
            seen_coordinates.add((all_coordinates[0].lat, all_coordinates[0].lon))
            
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
            seen_coordinates.add((all_coordinates[-1].lat, all_coordinates[-1].lon))
        
        # Coletar todos os pontos de busca primeiro
        all_search_points = []
        current_distance = 0
        target_distance = 1000  # 1km
        
        logger.info("Coletando pontos de busca ao longo da estrada")
        for i in range(len(all_coordinates) - 1):
            start = all_coordinates[i]
            end = all_coordinates[i + 1]
            segment_dist = geopy.distance.geodesic(
                (start.lat, start.lon),
                (end.lat, end.lon)
            ).meters
            
            # Adiciona o ponto inicial do segmento
            all_search_points.append(start)
            
            # Adiciona pontos intermediários a cada 1km
            while current_distance + segment_dist > target_distance:
                # Calcula a fração do segmento para atingir a distância alvo
                fraction = (target_distance - current_distance) / segment_dist
                
                # Calcula o ponto intermediário
                inter_lat = start.lat + fraction * (end.lat - start.lat)
                inter_lon = start.lon + fraction * (end.lon - start.lon)
                
                all_search_points.append(Coordinates(lat=inter_lat, lon=inter_lon))
                target_distance += 1000  # Próximo ponto a 1km
            
            current_distance += segment_dist
        
        # Adiciona o último ponto
        all_search_points.append(all_coordinates[-1])
        
        logger.info(f"Total de pontos de busca coletados: {len(all_search_points)}")
        
        # Build POI types to search
        poi_types = []
        commercial_needed = False
        
        if "gas_station" in milestone_types:
            poi_types.append({"amenity": "fuel"})
            commercial_needed = True
        if "toll_booth" in milestone_types:
            poi_types.append({"barrier": "toll_booth"})
        if "restaurant" in milestone_types:
            poi_types.append({"amenity": "restaurant"})
            commercial_needed = True
        
        # Add commercial landuse search only once if needed
        if commercial_needed:
            poi_types.append({"landuse": "commercial"})
        
        if poi_types:
            try:
                # Busca POIs em uma única chamada
                elements = self.osm_service.search_pois_around_coordinates(
                    coordinates=all_search_points,
                    radius_meters=max_distance,
                    poi_types=poi_types
                )
                
                # Processa os resultados
                nodes_processed = 0
                milestones_found = 0
                
                for element in elements:
                    nodes_processed += 1
                    
                    # Pula elementos sem coordenadas
                    if 'lat' not in element or 'lon' not in element:
                        continue
                    
                    # Pula se já vimos estas coordenadas
                    coord_key = (element['lat'], element['lon'])
                    if coord_key in seen_coordinates:
                        continue
                    
                    # Aplicar filtros de qualidade
                    element_tags = element.get('tags', {})
                    
                    # Excluir POIs abandonados ou fora de uso
                    if self._is_poi_abandoned(element_tags):
                        continue
                    
                    # Priorizar POIs com informações mais completas
                    quality_score = self._calculate_poi_quality_score(element_tags)
                    
                    # Pular POIs de baixa qualidade (sem nome para alguns tipos)
                    if not self._meets_quality_threshold(element_tags, quality_score):
                        continue
                    
                    # Determina o tipo de marco e cria se aplicável
                    milestone = None
                    
                    # Verifica postos de gasolina
                    is_fuel_amenity = element.get('tags', {}).get('amenity') == 'fuel'
                    is_commercial_gas_station = (
                        element.get('tags', {}).get('landuse') == 'commercial' and 
                        'posto' in element_tags.get('name', '').lower()
                    )
                    
                    if "gas_station" in milestone_types and (is_fuel_amenity or is_commercial_gas_station):
                        name = element_tags.get('name') or element_tags.get('brand') or element_tags.get('operator') or 'Posto de Combustível'
                        milestone = RoadMilestone(
                            id=str(uuid.uuid4()),
                            name=name,
                            type=MilestoneType.GAS_STATION,
                            coordinates=Coordinates(
                                lat=element['lat'],
                                lon=element['lon']
                            ),
                            distance_from_origin_km=0.0,  # Será calculado abaixo
                            distance_from_road_meters=0.0,  # Será calculado abaixo
                            side="right",  # Default to right side
                            tags=element_tags,
                            # Metadados enriquecidos
                            operator=element_tags.get('operator'),
                            brand=element_tags.get('brand'),
                            opening_hours=element_tags.get('opening_hours'),
                            phone=element_tags.get('phone') or element_tags.get('contact:phone'),
                            website=element_tags.get('website') or element_tags.get('contact:website'),
                            amenities=self._extract_amenities(element_tags),
                            quality_score=quality_score
                        )
                    
                    # Verifica pedágios
                    elif "toll_booth" in milestone_types and element.get('tags', {}).get('barrier') == 'toll_booth':
                        name = element_tags.get('name') or element_tags.get('operator') or 'Pedágio'
                        milestone = RoadMilestone(
                            id=str(uuid.uuid4()),
                            name=name,
                            type=MilestoneType.TOLL_BOOTH,
                            coordinates=Coordinates(
                                lat=element['lat'],
                                lon=element['lon']
                            ),
                            distance_from_origin_km=0.0,  # Será calculado abaixo
                            distance_from_road_meters=0.0,  # Será calculado abaixo
                            side="center",
                            tags=element_tags,
                            # Metadados enriquecidos
                            operator=element_tags.get('operator'),
                            brand=element_tags.get('brand'),
                            opening_hours=element_tags.get('opening_hours'),
                            phone=element_tags.get('phone') or element_tags.get('contact:phone'),
                            website=element_tags.get('website') or element_tags.get('contact:website'),
                            amenities=self._extract_amenities(element_tags),
                            quality_score=quality_score
                        )
                    
                    # Verifica restaurantes
                    is_restaurant_amenity = element.get('tags', {}).get('amenity') == 'restaurant'
                    is_commercial_restaurant = (
                        element.get('tags', {}).get('landuse') == 'commercial' and 
                        'restaurante' in element_tags.get('name', '').lower()
                    )
                    
                    elif "restaurant" in milestone_types and (is_restaurant_amenity or is_commercial_restaurant):
                        name = element_tags.get('name') or element_tags.get('brand') or 'Restaurante'
                        milestone = RoadMilestone(
                            id=str(uuid.uuid4()),
                            name=name,
                            type=MilestoneType.RESTAURANT,
                            coordinates=Coordinates(
                                lat=element['lat'],
                                lon=element['lon']
                            ),
                            distance_from_origin_km=0.0,  # Será calculado abaixo
                            distance_from_road_meters=0.0,  # Será calculado abaixo
                            side="right",  # Default to right side
                            tags=element_tags,
                            # Metadados enriquecidos
                            operator=element_tags.get('operator'),
                            brand=element_tags.get('brand'),
                            opening_hours=element_tags.get('opening_hours'),
                            phone=element_tags.get('phone') or element_tags.get('contact:phone'),
                            website=element_tags.get('website') or element_tags.get('contact:website'),
                            cuisine=element_tags.get('cuisine'),
                            amenities=self._extract_amenities(element_tags),
                            quality_score=quality_score
                        )
                    
                    # Adiciona o marco se criado
                    if milestone:
                        # Calcula distância da estrada e da origem
                        min_distance = float('inf')
                        min_distance_idx = 0
                        
                        for i, node in enumerate(all_coordinates):
                            dist = geopy.distance.geodesic(
                                (node.lat, node.lon),
                                (element['lat'], element['lon'])
                            ).meters
                            if dist < min_distance:
                                min_distance = dist
                                min_distance_idx = i
                        
                        milestone.distance_from_road_meters = min_distance
                        milestone.distance_from_origin_km = accumulated_distances[min_distance_idx]
                        
                        # Filter out POIs too close to origin
                        if milestone.distance_from_origin_km >= min_distance_from_origin_km:
                            milestones_found += 1
                            milestones.append(milestone)
                            seen_coordinates.add(coord_key)
                
                logger.info(f"Processados {nodes_processed} nós, encontrados {milestones_found} marcos")
                
            except Exception as e:
                logger.error(f"Erro ao buscar POIs: {str(e)}")
        
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
        min_distance_from_origin_km: float = 5.0,
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
            min_distance_from_origin_km,
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
        
        return linear_map
    
    def _process_road_segments(self, osm_segments: List[Any]) -> List[LinearRoadSegment]:
        """
        Process OSM road segments into linear road segments using improved segmentation logic.
        """
        linear_segments = []
        current_distance = 0
        current_name = None
        current_length = 0
        current_ref = None
        current_highway_type = None
        current_way_id = None
        
        for i, segment in enumerate(osm_segments):
            # Get segment metadata
            name = segment.name
            ref = segment.ref
            highway_type = segment.highway_type
            way_id = segment.tags.get('way_id', str(uuid.uuid4()))
            length_km = segment.length_meters / 1000
            
            # Check if this is a new road segment (different name or way_id)
            is_new_segment = (
                i == 0 or  # First segment
                name != current_name or  # Different name
                ref != current_ref or  # Different reference
                way_id != current_way_id  # Different way
            )
            
            if is_new_segment:
                # If we have a previous segment, add it to the list
                if i > 0:
                    linear_segment = LinearRoadSegment(
                        id=str(uuid.uuid4()),
                        start_distance_km=current_distance - current_length,
                        end_distance_km=current_distance,
                        length_km=current_length,
                        name=current_name,
                        ref=current_ref,
                        highway_type=current_highway_type,
                        start_milestone=None,
                        end_milestone=None,
                        milestones=[]
                    )
                    linear_segments.append(linear_segment)
                
                # Start new segment
                current_name = name
                current_ref = ref
                current_highway_type = highway_type
                current_way_id = way_id
                current_length = length_km
            else:
                # Continue current segment
                current_length += length_km
            
            current_distance += length_km
            
            # If this is the last segment, add it to the list
            if i == len(osm_segments) - 1:
                linear_segment = LinearRoadSegment(
                    id=str(uuid.uuid4()),
                    start_distance_km=current_distance - current_length,
                    end_distance_km=current_distance,
                    length_km=current_length,
                    name=current_name,
                    ref=current_ref,
                    highway_type=current_highway_type,
                    start_milestone=None,
                    end_milestone=None,
                    milestones=[]
                )
                linear_segments.append(linear_segment)
        
        logger.info(f"Processed {len(osm_segments)} OSM segments into {len(linear_segments)} linear segments")
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
        # For now, we'll return an empty list since we're not caching anymore
        return []
    
    def _is_poi_abandoned(self, tags: Dict[str, Any]) -> bool:
        """
        Verifica se um POI está abandonado ou fora de uso.
        
        Args:
            tags: Tags do elemento OSM
            
        Returns:
            True se o POI deve ser excluído por estar abandonado
        """
        abandonment_indicators = [
            'abandoned', 'disused', 'demolished', 'razed', 'removed', 
            'ruins', 'former', 'closed', 'destroyed'
        ]
        
        # Verifica tags diretas de abandono
        for indicator in abandonment_indicators:
            if tags.get(indicator) in ['yes', 'true', '1']:
                return True
            # Verifica prefixos (ex: abandoned:amenity=fuel)
            for key in tags.keys():
                if key.startswith(f"{indicator}:"):
                    return True
        
        # Verifica status específicos
        if tags.get('opening_hours') in ['closed', 'no']:
            return True
            
        return False
    
    def _calculate_poi_quality_score(self, tags: Dict[str, Any]) -> float:
        """
        Calcula um score de qualidade para um POI baseado na completude dos dados.
        
        Args:
            tags: Tags do elemento OSM
            
        Returns:
            Score de 0.0 a 1.0, onde 1.0 é melhor qualidade
        """
        score = 0.0
        max_score = 7.0  # Número de critérios de qualidade
        
        # Critério 1: Tem nome
        if tags.get('name'):
            score += 1.0
        
        # Critério 2: Tem operator ou brand
        if tags.get('operator') or tags.get('brand'):
            score += 1.0
        
        # Critério 3: Tem telefone
        if tags.get('phone') or tags.get('contact:phone'):
            score += 1.0
        
        # Critério 4: Tem horário de funcionamento
        if tags.get('opening_hours'):
            score += 1.0
        
        # Critério 5: Tem website
        if tags.get('website') or tags.get('contact:website'):
            score += 1.0
        
        # Critério 6: Para restaurantes, tem tipo de culinária
        if tags.get('amenity') == 'restaurant' and tags.get('cuisine'):
            score += 1.0
        elif tags.get('amenity') != 'restaurant':
            score += 1.0  # Não penalizar não-restaurantes
            
        # Critério 7: Tem endereço estruturado
        if any(tags.get(f'addr:{field}') for field in ['street', 'housenumber', 'city']):
            score += 1.0
        
        return score / max_score
    
    def _meets_quality_threshold(self, tags: Dict[str, Any], quality_score: float) -> bool:
        """
        Verifica se um POI atende ao threshold mínimo de qualidade.
        
        Args:
            tags: Tags do elemento OSM
            quality_score: Score de qualidade calculado
            
        Returns:
            True se o POI deve ser incluído
        """
        amenity = tags.get('amenity')
        barrier = tags.get('barrier')
        
        # Para postos de gasolina, exigir nome OU brand OU operator
        is_fuel_amenity = amenity == 'fuel'
        is_commercial_gas_station = (
            tags.get('landuse') == 'commercial' and 
            'posto' in tags.get('name', '').lower()
        )
        
        if is_fuel_amenity or is_commercial_gas_station:
            if not (tags.get('name') or tags.get('brand') or tags.get('operator')):
                return False
            return quality_score >= 0.3  # Threshold mais baixo para postos
        
        # Para restaurantes, exigir nome
        is_restaurant_amenity = amenity == 'restaurant'
        is_commercial_restaurant = (
            tags.get('landuse') == 'commercial' and 
            'restaurante' in tags.get('name', '').lower()
        )
        
        if is_restaurant_amenity or is_commercial_restaurant:
            if not tags.get('name'):
                return False
            return quality_score >= 0.4  # Threshold médio para restaurantes
        
        # Para pedágios, sempre incluir (mesmo sem nome)
        if barrier == 'toll_booth':
            return True
        
        # Para outros tipos, threshold padrão
        return quality_score >= 0.3
    
    def _extract_amenities(self, tags: Dict[str, Any]) -> List[str]:
        """
        Extrai lista de comodidades/amenidades de um POI baseado nas tags OSM.
        
        Args:
            tags: Tags do elemento OSM
            
        Returns:
            Lista de amenidades encontradas
        """
        amenities = []
        
        # Mapeamento de tags OSM para amenidades legíveis
        amenity_mappings = {
            # Conectividade
            'internet_access': {'wifi', 'internet'},
            'wifi': {'wifi'},
            
            # Estacionamento
            'parking': {'estacionamento'},
            'parking:fee': {'estacionamento pago'},
            
            # Acessibilidade
            'wheelchair': {'acessível'},
            
            # Pagamento
            'payment:cash': {'dinheiro'},
            'payment:cards': {'cartão'},
            'payment:contactless': {'contactless'},
            'payment:credit_cards': {'cartão de crédito'},
            'payment:debit_cards': {'cartão de débito'},
            
            # Combustível específico
            'fuel:diesel': {'diesel'},
            'fuel:octane_91': {'gasolina comum'},
            'fuel:octane_95': {'gasolina aditivada'},
            'fuel:lpg': {'GNV'},
            'fuel:ethanol': {'etanol'},
            
            # Serviços
            'toilets': {'banheiro'},
            'shower': {'chuveiro'},
            'restaurant': {'restaurante'},
            'cafe': {'café'},
            'shop': {'loja'},
            'atm': {'caixa eletrônico'},
            'car_wash': {'lava-jato'},
            'compressed_air': {'calibragem'},
            'vacuum_cleaner': {'aspirador'},
            
            # Outros
            'outdoor_seating': {'área externa'},
            'air_conditioning': {'ar condicionado'},
            'takeaway': {'delivery'},
            'delivery': {'delivery'},
            'drive_through': {'drive-thru'},
        }
        
        # Verifica cada tag e adiciona as amenidades correspondentes
        for tag_key, tag_value in tags.items():
            # Normaliza o valor da tag
            if isinstance(tag_value, str):
                tag_value = tag_value.lower()
            
            # Verifica se a tag indica presença da amenidade
            if tag_value in ['yes', 'true', '1', 'available']:
                if tag_key in amenity_mappings:
                    amenities.extend(amenity_mappings[tag_key])
                elif tag_key.startswith('payment:') and tag_key in amenity_mappings:
                    amenities.extend(amenity_mappings[tag_key])
        
        # Amenidades especiais baseadas no tipo
        amenity_type = tags.get('amenity')
        is_gas_station = (
            amenity_type == 'fuel' or 
            (tags.get('landuse') == 'commercial' and 'posto' in tags.get('name', '').lower())
        )
        
        if is_gas_station:
            # Para postos, assumir algumas amenidades básicas se não especificadas
            if not any('banheiro' in a for a in amenities) and tags.get('toilets') != 'no':
                amenities.append('banheiro')
        
        # Amenidades baseadas em horário
        opening_hours = tags.get('opening_hours', '')
        if '24/7' in opening_hours or 'Mo-Su 00:00-24:00' in opening_hours:
            amenities.append('24h')
        
        # Remove duplicatas e ordena
        amenities = sorted(list(set(amenities)))
        
        return amenities
    
    def get_route_statistics(
        self,
        origin: str,
        destination: str,
        include_gas_stations: bool = True,
        include_restaurants: bool = True,
        include_toll_booths: bool = True,
        max_distance_from_road: float = 1000
    ) -> 'RouteStatisticsResponse':
        """
        Gera estatísticas detalhadas de uma rota.
        
        Args:
            origin: Ponto de origem
            destination: Ponto de destino
            include_gas_stations: Incluir postos nas estatísticas
            include_restaurants: Incluir restaurantes nas estatísticas
            include_toll_booths: Incluir pedágios nas estatísticas
            max_distance_from_road: Distância máxima da estrada para considerar POIs
            
        Returns:
            Estatísticas completas da rota
        """
        from api.models.road_models import (
            RouteStatisticsResponse, POIStatistics, RouteStopRecommendation
        )
        
        # Gerar mapa linear para obter dados
        linear_map = self.generate_linear_map(
            origin=origin,
            destination=destination,
            include_cities=True,
            include_gas_stations=include_gas_stations,
            include_restaurants=include_restaurants,
            include_toll_booths=include_toll_booths,
            max_distance_from_road=max_distance_from_road
        )
        
        # Calcular estatísticas por tipo de POI
        poi_stats = []
        all_milestones = []
        
        # Coletar todos os milestones de todos os segmentos
        for segment in linear_map.segments:
            all_milestones.extend(segment.milestones)
        
        # Agrupar por tipo
        poi_types = {}
        for milestone in all_milestones:
            if milestone.type.value not in poi_types:
                poi_types[milestone.type.value] = []
            poi_types[milestone.type.value].append(milestone)
        
        # Calcular estatísticas para cada tipo
        for poi_type, milestones in poi_types.items():
            if poi_type == "city":  # Pular cidades nas estatísticas
                continue
                
            if len(milestones) > 1:
                # Calcular distância média entre POIs
                distances = []
                sorted_milestones = sorted(milestones, key=lambda m: m.distance_from_origin_km)
                for i in range(1, len(sorted_milestones)):
                    distance = sorted_milestones[i].distance_from_origin_km - sorted_milestones[i-1].distance_from_origin_km
                    distances.append(distance)
                
                avg_distance = sum(distances) / len(distances) if distances else 0
            else:
                avg_distance = linear_map.total_length_km
            
            # Calcular densidade por 100km
            density = (len(milestones) / linear_map.total_length_km) * 100 if linear_map.total_length_km > 0 else 0
            
            poi_stats.append(POIStatistics(
                type=poi_type,
                total_count=len(milestones),
                average_distance_km=avg_distance,
                density_per_100km=density
            ))
        
        # Gerar recomendações de paradas
        recommendations = self._generate_stop_recommendations(all_milestones, linear_map.total_length_km)
        
        # Calcular tempo estimado (assumindo 80 km/h de média)
        estimated_time = linear_map.total_length_km / 80.0
        
        # Métricas de qualidade dos dados
        quality_metrics = self._calculate_quality_metrics(all_milestones)
        
        return RouteStatisticsResponse(
            route_info={
                "origin": origin,
                "destination": destination,
                "road_refs": [seg.ref for seg in linear_map.segments if seg.ref],
                "segment_count": len(linear_map.segments)
            },
            total_length_km=linear_map.total_length_km,
            estimated_travel_time_hours=estimated_time,
            poi_statistics=poi_stats,
            recommendations=recommendations,
            quality_metrics=quality_metrics
        )
    
    def _generate_stop_recommendations(
        self, 
        milestones: List['RoadMilestone'], 
        total_length_km: float
    ) -> List['RouteStopRecommendation']:
        """
        Gera recomendações de paradas estratégicas baseadas nos POIs disponíveis.
        """
        from api.models.road_models import RouteStopRecommendation
        
        recommendations = []
        
        # Filtrar apenas POIs úteis para paradas
        useful_milestones = [m for m in milestones if m.type.value in ['gas_station', 'restaurant']]
        useful_milestones.sort(key=lambda m: m.distance_from_origin_km)
        
        # Recomendações baseadas em distância (a cada 200km aproximadamente)
        last_recommended_km = 0
        for milestone in useful_milestones:
            distance_from_last = milestone.distance_from_origin_km - last_recommended_km
            
            # Se passou mais de 150km desde a última recomendação, considerar esta parada
            if distance_from_last >= 150:
                services = []
                reason = ""
                duration = 15  # minutos padrão
                
                if milestone.type.value == 'gas_station':
                    services.append("Combustível")
                    reason = "Reabastecimento recomendado"
                    duration = 10
                    
                if milestone.type.value == 'restaurant':
                    services.append("Alimentação")
                    reason = "Parada para refeição"
                    duration = 30
                
                # Verificar se há outros POIs próximos (até 5km)
                nearby_pois = [
                    m for m in useful_milestones 
                    if abs(m.distance_from_origin_km - milestone.distance_from_origin_km) <= 5
                    and m != milestone
                ]
                
                for nearby in nearby_pois:
                    if nearby.type.value == 'gas_station' and "Combustível" not in services:
                        services.append("Combustível")
                    elif nearby.type.value == 'restaurant' and "Alimentação" not in services:
                        services.append("Alimentação")
                
                if len(services) > 1:
                    reason = "Parada estratégica - múltiplos serviços"
                    duration = 20
                
                # Adicionar amenidades do POI principal
                if milestone.amenities:
                    services.extend(milestone.amenities[:3])  # Limitar a 3 amenidades extras
                
                recommendations.append(RouteStopRecommendation(
                    distance_km=milestone.distance_from_origin_km,
                    reason=reason,
                    available_services=list(set(services)),  # Remove duplicatas
                    recommended_duration_minutes=duration
                ))
                
                last_recommended_km = milestone.distance_from_origin_km
        
        return recommendations[:5]  # Limitar a 5 recomendações
    
    def _calculate_quality_metrics(self, milestones: List['RoadMilestone']) -> Dict[str, Any]:
        """
        Calcula métricas de qualidade dos dados dos POIs.
        """
        if not milestones:
            return {"overall_quality": 0.0, "data_completeness": 0.0}
        
        total_quality = sum(m.quality_score or 0 for m in milestones)
        average_quality = total_quality / len(milestones)
        
        # Calcular completude dos dados
        fields_to_check = ['phone', 'opening_hours', 'website', 'operator', 'brand']
        completeness_scores = []
        
        for milestone in milestones:
            filled_fields = sum(1 for field in fields_to_check if getattr(milestone, field, None))
            completeness = filled_fields / len(fields_to_check)
            completeness_scores.append(completeness)
        
        average_completeness = sum(completeness_scores) / len(completeness_scores)
        
        return {
            "overall_quality": round(average_quality, 2),
            "data_completeness": round(average_completeness, 2),
            "total_pois_analyzed": len(milestones),
            "pois_with_phone": len([m for m in milestones if m.phone]),
            "pois_with_hours": len([m for m in milestones if m.opening_hours]),
            "pois_with_website": len([m for m in milestones if m.website])
        }