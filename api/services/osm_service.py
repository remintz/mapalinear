import overpass
import osmnx as ox
import geopy.distance
import uuid
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
import requests.exceptions

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
        
        # Get the shortest path using OSMnx
        # Determine network type based on road_type
        network_type = "drive"  # Default network type
        if road_type and road_type != RoadType.ALL:
            custom_filter = f'["highway"="{road_type.value}"]'
        else:
            custom_filter = None
        
        # Get the graph
        try:
            G = ox.graph_from_point((origin_lat, origin_lon), dist=10000, network_type=network_type, 
                                    custom_filter=custom_filter)
        except Exception as e:
            logger.error(f"Error getting graph from origin: {str(e)}")
            # Try with a larger radius
            G = ox.graph_from_point((origin_lat, origin_lon), dist=50000, network_type=network_type)
        
        # Find nearest nodes to origin and destination
        origin_node = ox.distance.nearest_nodes(G, origin_lon, origin_lat)
        
        try:
            # Check if destination is within the graph bounds
            G_dest = ox.graph_from_point((dest_lat, dest_lon), dist=10000, network_type=network_type,
                                         custom_filter=custom_filter)
            
            try:
                # Merge graphs usando pandas.concat em vez de append (deprecado)
                G_nodes = ox.graph_to_gdfs(G, nodes=True, edges=False)
                G_edges = ox.graph_to_gdfs(G, nodes=False, edges=True)
                G_dest_edges = ox.graph_to_gdfs(G_dest, nodes=False, edges=True)
                
                # Concatenar os dataframes de edges
                merged_edges = pd.concat([G_edges, G_dest_edges], ignore_index=True)
                
                # Criar grafo do osmnx a partir dos gdfs
                G = ox.graph_from_gdfs(G_nodes, merged_edges)
            except Exception as merge_error:
                logger.warning(f"Could not merge graphs, using extended origin graph: {str(merge_error)}")
                # Aumentar o raio do grafo para incluir o destino
                try:
                    # Calcular distância aproximada entre os pontos
                    from geopy.distance import geodesic
                    dist_km = geodesic((origin_lat, origin_lon), (dest_lat, dest_lon)).kilometers
                    # Acrescentar 20% à distância para garantir que cubra bem a área
                    radius_m = (dist_km * 1.2) * 1000  # Converter para metros
                    G = ox.graph_from_point((origin_lat, origin_lon), dist=radius_m, network_type=network_type)
                except Exception as e:
                    logger.warning(f"Could not create extended graph: {str(e)}. Using original graph.")
        except Exception as e:
            logger.warning(f"Could not get graph for destination, using extended origin graph: {str(e)}")
        
        dest_node = ox.distance.nearest_nodes(G, dest_lon, dest_lat)
        
        # Get the shortest path
        try:
            route = ox.shortest_path(G, origin_node, dest_node, weight='length')
        except Exception as e:
            logger.error(f"Error finding shortest path: {str(e)}")
            raise ValueError(f"Não foi possível encontrar uma rota entre {origin} e {destination}")
        
        # Extract road segments from the path
        road_segments = []
        total_length = 0
        
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
                    highway_type=self._format_name(edge.get('highway', 'unknown')),
                    ref=self._format_name(edge.get('ref', None)),
                    geometry=geometry,
                    length_meters=length_meters,
                    start_node=str(current_node),
                    end_node=str(next_node),
                    tags=tags
                )
                
                road_segments.append(segment)
        
        # Create response
        road_id = str(uuid.uuid4())
        response = OSMSearchResponse(
            road_segments=road_segments,
            total_length_km=total_length / 1000,  # Convert to kilometers
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
        try:
            # Get sequential call number
            call_number = self._get_next_osm_call_number()
            
            # Normalize line endings and remove extra whitespace
            query = ' '.join(query.split())
            
            # Remove any extra spaces around parentheses
            query = query.replace('( ', '(').replace(' )', ')')
            
            logger.debug(f"Query Overpass #{call_number}: {query}")
            
            # Ensure minimum delay between queries
            self._wait_before_query()
            
            # Execute the query directly using the API
            result = self.overpass_api.get(query, responseformat="json")
            
            # Log the result for debugging
            if result and 'elements' in result:
                logger.debug(f"Query #{call_number} retornou {len(result['elements'])} elementos")
            else:
                logger.debug(f"Query #{call_number} retornou resultado vazio")
            
            return result
        except Exception as e:
            logger.error(f"Erro na query Overpass #{call_number}: {str(e)}")
            raise
    
    def search_pois_around_coordinates(
        self,
        coordinates: List[Coordinates],
        radius_meters: float,
        poi_types: List[Dict[str, str]],
        max_concurrent_requests: int = 5,
        max_coords_per_batch: int = 3  # Limite de coordenadas por batch
    ) -> List[Dict[str, Any]]:
        """
        Busca pontos de interesse ao redor de uma lista de coordenadas usando processamento paralelo.
        
        Args:
            coordinates: Lista de coordenadas para buscar POIs
            radius_meters: Raio de busca em metros
            poi_types: Lista de dicionários com os tipos de POI a buscar
                      Exemplo: [{"amenity": "fuel"}, {"barrier": "toll_booth"}]
            max_concurrent_requests: Número máximo de requisições simultâneas (default: 5)
            max_coords_per_batch: Número máximo de coordenadas por batch (default: 3)
        
        Returns:
            Lista de elementos encontrados
        """
        try:
            # Build query parts for each POI type
            node_queries = []
            for poi_type in poi_types:
                tag_key = list(poi_type.keys())[0]
                tag_value = poi_type[tag_key]
                node_queries.append(f'node["{tag_key}"="{tag_value}"]')
            
            all_results = []
            
            def process_coordinates_batch(coords_batch):
                try:
                    # Build around clauses for each coordinate in the batch
                    around_clauses = []
                    for coord in coords_batch:
                        around_clauses.append(f'(around:{radius_meters},{coord.lat},{coord.lon})')
                    
                    # Build query for this batch using union
                    query_parts = []
                    for node_query in node_queries:
                        for around_clause in around_clauses:
                            query_parts.append(f'{node_query}{around_clause}')
                    
                    query = f"""(
    {';'.join(query_parts)};
)"""
                    
                    # Execute the query
                    result = self.query_overpass(query)
                    
                    if result and 'elements' in result:
                        return result['elements']
                    return []
                except Exception as e:
                    logger.error(f"Erro ao processar batch de coordenadas: {str(e)}")
                    return []
            
            # Split coordinates into smaller batches
            coord_batches = [coordinates[i:i + max_coords_per_batch] for i in range(0, len(coordinates), max_coords_per_batch)]
            
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