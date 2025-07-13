import overpass
import osmnx as ox
import networkx as nx
import geopy.distance
import uuid
import requests
from typing import Dict, List, Optional, Any, Tuple
from geopy.geocoders import Nominatim
import logging
from datetime import datetime
import pandas as pd
from concurrent.futures import ThreadPoolExecutor, as_completed
from itertools import product
from threading import Lock
import time
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from api.models.osm_models import (
    OSMSearchResponse,
    OSMRoadSegment,
    Coordinates,
    RoadType,
    OSMRoadDetailsResponse,
    OSMPointOfInterestResponse,
    OSMPointOfInterestType,
)

logger = logging.getLogger(__name__)

class OSMService:
    def __init__(self):
        # Usando o servidor Kumi Systems que é mais estável
        self.overpass_api = overpass.API(
            endpoint='https://overpass.kumi.systems/api/interpreter',
            timeout=600  # 10 minutos de timeout
        )
        self.geolocator = Nominatim(user_agent="mapalinear/1.0")
        self.cache = {}  # Simple cache for geocoding results
        self._osm_call_counter = 0
        self._osm_counter_lock = Lock()
        self._last_query_time = 0
        self._query_delay = 1.0  # Delay between queries in seconds
        
    def _get_next_osm_call_number(self) -> int:
        """Thread-safe way to get the next OSM call number."""
        with self._osm_counter_lock:
            self._osm_call_counter += 1
            return self._osm_call_counter
    
    def _wait_before_query(self):
        """Ensure minimum delay between queries."""
        current_time = time.time()
        time_since_last_query = current_time - self._last_query_time
        if time_since_last_query < self._query_delay:
            time.sleep(self._query_delay - time_since_last_query)
        self._last_query_time = time.time()
    
    def _geocode_location(self, location_name: str) -> Tuple[float, float]:
        """Convert a location name to coordinates (latitude, longitude)."""
        if location_name in self.cache:
            return self.cache[location_name]
        
        location = self.geolocator.geocode(location_name + ", Brasil")
        if not location:
            location = self.geolocator.geocode(location_name)  # Try without country
        
        if not location:
            raise ValueError(f"Não foi possível geocodificar o local: {location_name}")
        
        result = (location.latitude, location.longitude)
        self.cache[location_name] = result
        return result
    
    def _format_name(self, name_value) -> Optional[str]:
        """
        Formata o campo nome para garantir que seja sempre uma string ou None.
        OSM pode retornar listas de nomes em alguns casos.
        """
        if name_value is None:
            return None
        if isinstance(name_value, list):
            # Juntar a lista de nomes em uma única string
            return "; ".join(str(n) for n in name_value if n)
        return str(name_value)
    
    def search_road_data(
        self, 
        origin: str, 
        destination: str, 
        road_type: Optional[RoadType] = RoadType.ALL
    ) -> OSMSearchResponse:
        """
        Busca dados de estradas no OpenStreetMap entre pontos de origem e destino.
        """
        # Geocode origin and destination
        origin_lat, origin_lon = self._geocode_location(origin)
        dest_lat, dest_lon = self._geocode_location(destination)
        
        logger.info(f"Searching road from {origin} to {destination}")
        logger.info(f"Origin coordinates: {origin_lat}, {origin_lon}")
        logger.info(f"Destination coordinates: {dest_lat}, {dest_lon}")
        
        # Calculate straight-line distance to determine if this is an intercity route
        straight_distance_km = geopy.distance.distance(
            (origin_lat, origin_lon), 
            (dest_lat, dest_lon)
        ).kilometers
        
        logger.info(f"Straight-line distance: {straight_distance_km:.1f} km")
        is_intercity_route = straight_distance_km > 50  # More than 50km = intercity
        
        if is_intercity_route:
            logger.info("Detected intercity route - expanding search area for highways")
            # For intercity routes, use a more conservative padding to avoid huge areas
            padding = min(0.3, max(0.1, straight_distance_km / 2000))  # 0.1 to 0.3 degrees max
        else:
            logger.info("Detected local route - using standard search area")
            padding = 0.2
        
        north = max(origin_lat, dest_lat) + padding
        south = min(origin_lat, dest_lat) - padding
        east = max(origin_lon, dest_lon) + padding
        west = min(origin_lon, dest_lon) - padding
        
        logger.info(f"Search bounding box: ({south:.3f}, {west:.3f}) to ({north:.3f}, {east:.3f})")
        
        # Get the shortest path using OSMnx
        # Determine network type based on road_type
        network_type = "drive"  # Default network type
        custom_filter = None
        if road_type and road_type != RoadType.ALL:
            custom_filter = f'["highway"="{road_type.value}"]'
            logger.info(f"Using custom filter: {custom_filter}")

        # Get the graph
        G = None
        try:
            logger.info(f"Attempting to get graph for area between {origin} and {destination}")
            logger.info(f"Network type: {network_type}, Custom filter: {custom_filter}")
            
            # For intercity routes, try optimized approach but with quick fallback
            if is_intercity_route:
                logger.info("Detected intercity route - attempting optimized graph acquisition...")
                
                # For very large intercity routes, use highway-only filter to reduce data size
                if straight_distance_km > 150:  # Routes longer than 150km
                    intercity_filter = '["highway"~"^(motorway|trunk|primary)"]'
                    logger.info("Using highway-only filter for long intercity route")
                else:
                    intercity_filter = custom_filter
                
                # Try bounding box approach for full corridor coverage
                try:
                    logger.info(f"Trying bounding box approach for full {straight_distance_km:.0f}km corridor...")
                    
                    G = ox.graph_from_bbox(
                        bbox=(west, south, east, north),
                        network_type=network_type,
                        custom_filter=intercity_filter,
                        truncate_by_edge=True
                    )
                    logger.info(f"Graph obtained with bounding box approach: {len(G.nodes) if G else 0} nodes")
                    
                except Exception as bbox_error:
                    logger.warning(f"Bounding box approach failed: {str(bbox_error)}")
                    
                    # Fallback to point-based approach
                    logger.info("Falling back to point-based approach...")
                    
                    # Use a moderate radius that balances coverage vs. performance
                    if straight_distance_km > 200:
                        radius = 100000  # 100km radius for very long routes
                        logger.warning(f"Long route ({straight_distance_km:.0f}km) detected. Using limited radius ({radius/1000:.0f}km) - route may be incomplete.")
                    else:
                        radius = min(int(straight_distance_km * 800), 150000)  # 0.8x distance, cap at 150km
                    
                    logger.info(f"Trying point-based approach with {radius/1000:.0f}km radius...")
                    
                    # Try from midpoint to get better coverage
                    mid_lat = (origin_lat + dest_lat) / 2
                    mid_lon = (origin_lon + dest_lon) / 2
                    
                    G = ox.graph_from_point(
                        (mid_lat, mid_lon),
                        dist=radius,
                        network_type=network_type,
                        custom_filter=intercity_filter
                    )
                    logger.info(f"Graph obtained with point-based approach: {len(G.nodes) if G else 0} nodes")
                    
                except Exception as e:
                    logger.warning(f"Intercity approach failed: {str(e)}")
                    logger.info("Falling back to place-based approach...")
                    G = None
            
            # For local routes or if intercity approach failed, use the original place-based approach
            if G is None or len(G.nodes) == 0:
                logger.info("Using place-based approach...")
                
                # Primeiro tenta com o filtro customizado
                if custom_filter:
                    try:
                        # Tenta obter o grafo usando o nome da cidade
                        G = ox.graph_from_place(
                            origin,
                            network_type=network_type,
                            custom_filter=custom_filter
                        )
                        logger.info(f"Graph obtained with custom filter: {len(G.nodes) if G else 0} nodes")
                    except Exception as e:
                        logger.warning(f"Failed to get graph with custom filter: {str(e)}")
                        G = None
                
                # Se não conseguiu com o filtro customizado ou não há filtro, tenta sem ele
                if G is None or len(G.nodes) == 0:
                    logger.info("Attempting to get graph without custom filter...")
                    try:
                        # Tenta obter o grafo usando o nome da cidade
                        G = ox.graph_from_place(
                            origin,
                            network_type=network_type
                        )
                        logger.info(f"Graph obtained without custom filter: {len(G.nodes) if G else 0} nodes")
                    except Exception as e:
                        logger.error(f"Failed to get graph without custom filter: {str(e)}")
                        # Tenta uma última vez com a cidade de destino
                        try:
                            logger.info("Attempting with destination city...")
                            G = ox.graph_from_place(
                                destination,
                                network_type=network_type
                            )
                            logger.info(f"Graph obtained with destination city: {len(G.nodes) if G else 0} nodes")
                        except Exception as e2:
                            logger.error(f"Failed to get graph with destination city: {str(e2)}")
                            # Última tentativa: tenta obter o grafo usando as coordenadas
                            try:
                                logger.info("Attempting with coordinates...")
                                # Use larger radius for intercity routes
                                radius = 200000 if is_intercity_route else 50000  # 200km vs 50km
                                logger.info(f"Using radius: {radius/1000:.0f}km for {'intercity' if is_intercity_route else 'local'} route")
                                G = ox.graph_from_point(
                                    (origin_lat, origin_lon),
                                    dist=radius,
                                    network_type=network_type
                                )
                                logger.info(f"Graph obtained with coordinates: {len(G.nodes) if G else 0} nodes")
                            except Exception as e3:
                                logger.error(f"Failed to get graph with coordinates: {str(e3)}")
                                raise ValueError(f"Não foi possível obter dados da rede viária para a região especificada: {str(e)}")
            
            if G is None or len(G.nodes) == 0:
                raise ValueError("Não foi possível obter dados da rede viária para a região especificada")
                
            logger.info(f"Graph obtained successfully with {len(G.nodes)} nodes and {len(G.edges)} edges")
            
        except Exception as e:
            logger.error(f"Error getting graph from origin: {str(e)}")
            raise ValueError(f"Não foi possível obter o grafo da rede para a rota entre {origin} e {destination}: {str(e)}")
        
        if G is None:
            raise ValueError(f"Não foi possível obter o grafo da rede para a rota entre {origin} e {destination}")
        
        # Find nearest nodes to origin and destination
        try:
            origin_node = ox.distance.nearest_nodes(G, origin_lon, origin_lat)
            dest_node = ox.distance.nearest_nodes(G, dest_lon, dest_lat)
            
            # Validate that the nearest nodes are actually close to the intended locations
            origin_node_coords = (G.nodes[origin_node]['y'], G.nodes[origin_node]['x'])
            dest_node_coords = (G.nodes[dest_node]['y'], G.nodes[dest_node]['x'])
            
            origin_distance = geopy.distance.distance(
                (origin_lat, origin_lon), 
                origin_node_coords
            ).kilometers
            
            dest_distance = geopy.distance.distance(
                (dest_lat, dest_lon), 
                dest_node_coords
            ).kilometers
            
            logger.info(f"Origin node distance from target: {origin_distance:.1f} km")
            logger.info(f"Destination node distance from target: {dest_distance:.1f} km")
            
            # For intercity routes, allow larger distances (up to 50km from city center)
            # For local routes, be more strict (up to 10km)
            max_distance = 50 if is_intercity_route else 10
            
            if origin_distance > max_distance:
                logger.warning(f"Origin node is {origin_distance:.1f}km from {origin}, may indicate incomplete graph coverage")
            
            if dest_distance > max_distance:
                logger.warning(f"Destination node is {dest_distance:.1f}km from {destination}, may indicate incomplete graph coverage")
                
                # For intercity routes, if destination is too far, the graph doesn't cover the full route
                if is_intercity_route and dest_distance > 50:
                    error_msg = (f"Route calculation incomplete: destination node is {dest_distance:.1f}km from {destination}. "
                               f"This indicates the road network data doesn't cover the full {straight_distance_km:.0f}km route. "
                               f"The returned route covers only a portion of the journey.")
                    logger.error(error_msg)
                    # For now, continue with partial route but log the issue
                    # In the future, this could trigger a multi-segment approach
                
        except Exception as e:
            logger.error(f"Error finding nearest nodes: {str(e)}")
            raise ValueError(f"Não foi possível encontrar os nós mais próximos para {origin} e {destination}")
        
        # Get the shortest path
        try:
            route = nx.shortest_path(G, origin_node, dest_node, weight='length')
        except Exception as e:
            logger.error(f"Error finding shortest path: {str(e)}")
            raise ValueError(f"Não foi possível encontrar uma rota entre {origin} e {destination}")
        
        # Extract road segments from the path
        road_segments = []
        total_length = 0
        
        # Function to classify road type by highway tag
        def is_major_highway(highway_type):
            """Returns True if the highway type is a major intercity road"""
            if not highway_type:
                return False
            
            major_types = {
                'motorway', 'motorway_link',
                'trunk', 'trunk_link', 
                'primary', 'primary_link'
            }
            
            # Handle lists (when multiple highway types)
            if isinstance(highway_type, list):
                return any(ht in major_types for ht in highway_type)
            
            return highway_type in major_types
        
        def is_urban_road(highway_type):
            """Returns True if the highway type is typically urban/local"""
            if not highway_type:
                return False
                
            urban_types = {
                'residential', 'living_street', 'service', 'unclassified',
                'tertiary', 'tertiary_link', 'secondary', 'secondary_link'
            }
            
            # Handle lists
            if isinstance(highway_type, list):
                return any(ht in urban_types for ht in highway_type)
                
            return highway_type in urban_types
        
        # First pass: collect all segments with classification
        all_segments = []
        
        for i in range(len(route) - 1):
            current_node = route[i]
            next_node = route[i + 1]
            
            # Get the edge data between these nodes
            edge_data = G.get_edge_data(current_node, next_node, 0)
            
            # Sometimes there are multiple edges between nodes, get all of them
            if isinstance(edge_data, dict):
                edge_data = [edge_data]
            
            for edge in edge_data:
                length_meters = edge.get('length', 0)
                highway_type = edge.get('highway', 'unknown')
                total_length += length_meters
                
                # Extract coordinates from edge geometry if available
                geometry = []
                if 'geometry' in edge and edge['geometry'] is not None:
                    # LineString geometry
                    for point in edge['geometry'].coords:
                        geometry.append(Coordinates(lat=point[1], lon=point[0]))
                else:
                    # Use node coordinates if geometry is not available
                    u_node = G.nodes[current_node]
                    v_node = G.nodes[next_node]
                    geometry = [
                        Coordinates(lat=u_node['y'], lon=u_node['x']),
                        Coordinates(lat=v_node['y'], lon=v_node['x'])
                    ]
                
                # Extract tags from edge
                tags = {}
                for key, value in edge.items():
                    if key not in ['length', 'geometry'] and not key.startswith('_'):
                        tags[key] = value
                
                # Create road segment
                segment = OSMRoadSegment(
                    id=str(uuid.uuid4()),
                    name=self._format_name(edge.get('name', None)),
                    highway_type=self._format_name(highway_type),
                    ref=self._format_name(edge.get('ref', None)),
                    geometry=geometry,
                    length_meters=length_meters,
                    start_node=str(current_node),
                    end_node=str(next_node),
                    tags=tags
                )
                
                all_segments.append({
                    'segment': segment,
                    'is_major': is_major_highway(highway_type),
                    'is_urban': is_urban_road(highway_type),
                    'highway_type': highway_type
                })
        
        # Filter segments for intercity routes
        if is_intercity_route and len(all_segments) > 10:  # Only filter if we have enough segments
            logger.info(f"Original route has {len(all_segments)} segments")
            
            # Find first major highway (skip urban roads at start)
            first_major_idx = 0
            for i, seg_info in enumerate(all_segments):
                if seg_info['is_major']:
                    first_major_idx = i
                    logger.info(f"First major highway found at segment {i}: {seg_info['segment'].highway_type}")
                    break
            
            # Find last major highway (skip urban roads at end)  
            last_major_idx = len(all_segments) - 1
            for i in range(len(all_segments) - 1, -1, -1):
                if all_segments[i]['is_major']:
                    last_major_idx = i
                    logger.info(f"Last major highway found at segment {i}: {all_segments[i]['segment'].highway_type}")
                    break
            
            # Include some context around major highways
            context_segments = 5  # Include 5 segments before first major and after last major
            start_idx = max(0, first_major_idx - context_segments)
            end_idx = min(len(all_segments), last_major_idx + context_segments + 1)
            
            filtered_segments = all_segments[start_idx:end_idx]
            
            logger.info(f"Filtered route: segments {start_idx} to {end_idx-1} ({len(filtered_segments)} segments)")
            logger.info(f"Removed {len(all_segments) - len(filtered_segments)} urban segments")
            
            # Use filtered segments
            road_segments = [seg_info['segment'] for seg_info in filtered_segments]
        else:
            # For local routes or short routes, use all segments
            road_segments = [seg_info['segment'] for seg_info in all_segments]
            logger.info(f"Using all {len(road_segments)} segments (local route or insufficient segments)")
        
        # Recalculate total length from selected segments
        total_length = sum(segment.length_meters for segment in road_segments)
        route_distance_km = total_length / 1000
        
        # Validate route distance for intercity routes
        if is_intercity_route:
            route_ratio = route_distance_km / straight_distance_km
            logger.info(f"Route validation - Distance: {route_distance_km:.1f}km, Straight-line: {straight_distance_km:.1f}km, Ratio: {route_ratio:.2f}x")
            
            # Expected ratio for highways is 1.2-1.5x straight distance
            if route_ratio < 0.8:
                logger.warning(f"⚠️  Route appears incomplete! Distance ratio {route_ratio:.2f}x is too low for intercity route")
                logger.warning(f"   Expected: ~{straight_distance_km * 1.3:.0f}km, Got: {route_distance_km:.1f}km")
                logger.warning(f"   This likely indicates partial road network coverage")
            elif route_ratio > 3.0:
                logger.warning(f"⚠️  Route may include unnecessary detours! Distance ratio {route_ratio:.2f}x is unusually high")
            else:
                logger.info(f"✅ Route distance appears reasonable for intercity travel")
        
        # Create response
        road_id = str(uuid.uuid4())
        response = OSMSearchResponse(
            road_segments=road_segments,
            total_length_km=total_length / 1000,  # Convert to kilometers
            straight_line_distance_km=straight_distance_km,  # Add straight-line distance
            origin_coordinates=Coordinates(lat=origin_lat, lon=origin_lon),
            destination_coordinates=Coordinates(lat=dest_lat, lon=dest_lon),
            road_id=road_id,
            timestamp=datetime.now()
        )
        
        return response
    
    def get_road_details(self, road_id: str) -> Optional[OSMRoadDetailsResponse]:
        """
        Obtém detalhes de uma estrada específica pelo seu ID.
        """
        # In a real implementation, this would fetch from a database
        # For now, we'll return a mock response
        # TODO: Implement a database to store road information
        
        # This is a placeholder. In a real implementation, you'd query a database.
        return None
    
    def get_points_of_interest(
        self, 
        road_id: str, 
        distance: Optional[float] = 1000, 
        poi_type: Optional[str] = None
    ) -> List[OSMPointOfInterestResponse]:
        """
        Obtém pontos de interesse ao longo de uma estrada.
        """
        # In a real implementation, this would:
        # 1. Get the road geometry from the database
        # 2. Query Overpass for POIs near the road
        # 3. Filter by distance and type
        # 4. Return the results
        
        # Placeholder implementation
        return []
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type((requests.exceptions.RequestException, overpass.errors.OverpassError))
    )
    def query_overpass(self, query: str) -> Dict:
        """
        Executa uma query no Overpass API com retry em caso de falha.
        """
        import requests
        
        try:
            # Get sequential call number
            call_number = self._get_next_osm_call_number()
            
            # Normalize line endings and remove extra whitespace
            query = ' '.join(query.split())
            
            # Remove any extra spaces around parentheses
            query = query.replace('( ', '(').replace(' )', ')')
            
            # Add output format manually for direct HTTP requests
            full_query = f"[out:json]{query}"
            
            logger.debug(f"Query Overpass #{call_number}: {full_query}")
            
            # Ensure minimum delay between queries
            self._wait_before_query()
            
            # Use direct HTTP request instead of overpass library to avoid automatic modifications
            overpass_servers = [
                "https://overpass-api.de/api/interpreter",  # More stable primary server
                "https://overpass.openstreetmap.ru/api/interpreter",  # Backup server
                "https://overpass.kumi.systems/api/interpreter"  # Additional backup
            ]
            
            last_error = None
            for i, server_url in enumerate(overpass_servers):
                try:
                    logger.debug(f"Tentando servidor {i+1}/{len(overpass_servers)}: {server_url}")
                    response = requests.post(
                        server_url,
                        data={'data': full_query},
                        timeout=(30, 130),  # (connect_timeout, read_timeout)
                        headers={'User-Agent': 'MapaLinear/1.0'}
                    )
                    response.raise_for_status()
                    result = response.json()
                    
                    # Log successful server
                    logger.debug(f"Query #{call_number} executada com sucesso em {server_url}")
                    
                    # Log the result for debugging
                    if result and 'elements' in result:
                        logger.debug(f"Query #{call_number} retornou {len(result['elements'])} elementos")
                    else:
                        logger.debug(f"Query #{call_number} retornou resultado vazio")
                    
                    return result
                    
                except requests.exceptions.RequestException as server_error:
                    last_error = server_error
                    logger.warning(f"Erro no servidor {server_url}: {server_error}")
                    
                    # If it's the last server, raise the error
                    if i == len(overpass_servers) - 1:
                        logger.error(f"Todos os servidores Overpass falharam. Último erro: {server_error}")
                        raise server_error
                    
                    # Wait a bit before trying next server
                    time.sleep(1)
                    continue
            
            # This should not be reached, but just in case
            if last_error:
                raise last_error
            else:
                raise Exception("Nenhum servidor Overpass disponível")
        except Exception as e:
            logger.error(f"Erro na query Overpass #{call_number}: {str(e)}")
            raise
    
    def search_pois_around_coordinates(
        self,
        coordinates: List[Coordinates],
        radius_meters: float,
        poi_types: List[Dict[str, str]],
        max_concurrent_requests: int = 5,
        max_coords_per_batch: int = 3,  # Limite de coordenadas por batch
        timeout: int = 120  # Timeout personalizado para queries complexas
    ) -> List[Dict[str, Any]]:
        """
        Busca pontos de interesse ao redor de uma lista de coordenadas usando processamento paralelo.
        Agora inclui nodes, ways e relations para melhor cobertura de POIs.
        
        Args:
            coordinates: Lista de coordenadas para buscar POIs
            radius_meters: Raio de busca em metros
            poi_types: Lista de dicionários com os tipos de POI a buscar
                      Exemplo: [{"amenity": "fuel"}, {"barrier": "toll_booth"}]
            max_concurrent_requests: Número máximo de requisições simultâneas (default: 5)
            max_coords_per_batch: Número máximo de coordenadas por batch (default: 3)
            timeout: Timeout em segundos para cada query (default: 120)
        
        Returns:
            Lista de elementos encontrados
        """
        try:
            # Log das coordenadas de entrada
            logger.debug(f"Coordenadas de entrada ({len(coordinates)} pontos):")
            # Only log first few and last few coordinates to avoid spam
            if len(coordinates) <= 10:
                for i, coord in enumerate(coordinates):
                    logger.debug(f"  {i+1}. ({coord.lat}, {coord.lon})")
            else:
                for i in range(3):
                    logger.debug(f"  {i+1}. ({coordinates[i].lat}, {coordinates[i].lon})")
                logger.debug(f"  ... ({len(coordinates)-6} more coordinates) ...")
                for i in range(len(coordinates)-3, len(coordinates)):
                    logger.debug(f"  {i+1}. ({coordinates[i].lat}, {coordinates[i].lon})")
            
            # Build unified query using regex for better performance
            poi_filters = []
            for poi_type in poi_types:
                tag_key = list(poi_type.keys())[0]
                tag_value = poi_type[tag_key]
                poi_filters.append(f'"{tag_key}"="{tag_value}"')
            
            # Combine all POI types into a single regex if possible
            amenity_values = []
            barrier_values = []
            other_filters = []
            
            for poi_type in poi_types:
                tag_key = list(poi_type.keys())[0]
                tag_value = poi_type[tag_key]
                if tag_key == "amenity":
                    amenity_values.append(tag_value)
                elif tag_key == "barrier":
                    barrier_values.append(tag_value)
                else:
                    other_filters.append(f'["{tag_key}"="{tag_value}"]')
            
            all_results = []
            
            def process_coordinates_batch(coords_batch):
                try:
                    # Build around clauses for each coordinate in the batch
                    around_clauses = []
                    for coord in coords_batch:
                        around_clauses.append(f'(around:{radius_meters},{coord.lat},{coord.lon})')
                    
                    # Build unified query parts
                    query_parts = []
                    
                    # Add amenity-based POIs if any
                    if amenity_values:
                        amenity_regex = "|".join(amenity_values)
                        for around_clause in around_clauses:
                            # Nodes
                            query_parts.append(f'node["amenity"~"^({amenity_regex})$"]{around_clause}')
                            # Ways (for larger establishments)
                            query_parts.append(f'way["amenity"~"^({amenity_regex})$"]{around_clause}')
                            # Relations (for franchises/chains)
                            query_parts.append(f'rel["amenity"~"^({amenity_regex})$"]{around_clause}')
                    
                    # Add barrier-based POIs if any
                    if barrier_values:
                        barrier_regex = "|".join(barrier_values)
                        for around_clause in around_clauses:
                            query_parts.append(f'node["barrier"~"^({barrier_regex})$"]{around_clause}')
                            query_parts.append(f'way["barrier"~"^({barrier_regex})$"]{around_clause}')
                    
                    # Add other filter types
                    for filter_str in other_filters:
                        for around_clause in around_clauses:
                            query_parts.append(f'node{filter_str}{around_clause}')
                            query_parts.append(f'way{filter_str}{around_clause}')
                    
                    # Build complete query with proper output format
                    # Note: [out:json] is automatically added by overpass library
                    query = f"""[timeout:{timeout}];
(
    {';'.join(query_parts)};
);
out geom;"""
                    
                    # Execute the query
                    result = self.query_overpass(query)
                    
                    if result and 'elements' in result:
                        processed_elements = []
                        for element in result['elements']:
                            # For ways and relations, extract centroid coordinates
                            if element['type'] in ['way', 'relation'] and 'geometry' in element:
                                # Calculate centroid from geometry
                                if element['geometry']:
                                    lats = [point['lat'] for point in element['geometry'] if 'lat' in point]
                                    lons = [point['lon'] for point in element['geometry'] if 'lon' in point]
                                    if lats and lons:
                                        element['lat'] = sum(lats) / len(lats)
                                        element['lon'] = sum(lons) / len(lons)
                                        processed_elements.append(element)
                            elif element['type'] == 'node' and 'lat' in element and 'lon' in element:
                                processed_elements.append(element)
                        
                        return processed_elements
                    return []
                except Exception as e:
                    logger.error(f"Erro ao processar batch de coordenadas: {str(e)}")
                    return []
            
            # Agrupa coordenadas por quilômetro acumulado
            km_coordinates = []
            current_km = 0
            accumulated_distance = 0
            
            # Primeira coordenada sempre é incluída
            km_coordinates.append(coordinates[0])
            logger.info(f"Adicionando coordenada inicial: ({coordinates[0].lat}, {coordinates[0].lon}) - km acumulado: {current_km}")
            current_km += 1
            
            # Processa o resto das coordenadas
            for i in range(1, len(coordinates)):
                # Calcula distância entre coordenadas consecutivas
                prev_coord = coordinates[i-1]
                curr_coord = coordinates[i]
                distance = geopy.distance.geodesic(
                    (prev_coord.lat, prev_coord.lon),
                    (curr_coord.lat, curr_coord.lon)
                ).kilometers
                
                accumulated_distance += distance
                
                # Se passou de 1km, adiciona ao grupo
                if accumulated_distance >= 1.0:
                    km_coordinates.append(coordinates[i])
                    logger.info(f"Adicionando coordenada a cada 1km: ({coordinates[i].lat}, {coordinates[i].lon}) - km acumulado: {current_km}")
                    accumulated_distance = 0  # Reseta o contador
                    current_km += 1
            
            # Adiciona a última coordenada se ainda não foi incluída
            if coordinates[-1] != km_coordinates[-1]:
                km_coordinates.append(coordinates[-1])
                logger.info(f"Adicionando coordenada final: ({coordinates[-1].lat}, {coordinates[-1].lon}) - km acumulado: {current_km}")
            
            logger.info(f"Total de coordenadas após agrupamento por km: {len(km_coordinates)}")
            
            # Split coordinates into smaller batches
            coord_batches = [km_coordinates[i:i + max_coords_per_batch] for i in range(0, len(km_coordinates), max_coords_per_batch)]
            logger.info(f"Total de batches para processamento: {len(coord_batches)}")
            
            # Process batches in parallel
            with ThreadPoolExecutor(max_workers=max_concurrent_requests) as executor:
                future_to_batch = {executor.submit(process_coordinates_batch, batch): batch for batch in coord_batches}
                
                for future in as_completed(future_to_batch):
                    batch_results = future.result()
                    all_results.extend(batch_results)
            
            return all_results
            
        except Exception as e:
            logger.error(f"Erro ao buscar POIs: {str(e)}")
            return [] 