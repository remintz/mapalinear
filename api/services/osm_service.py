import overpass
import osmnx as ox
import geopy.distance
import uuid
from typing import Dict, List, Optional, Any, Tuple
from geopy.geocoders import Nominatim
import logging
from datetime import datetime

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
        self.overpass_api = overpass.API()
        self.geolocator = Nominatim(user_agent="mapalinear/1.0")
        self.cache = {}  # Simple cache for geocoding results
    
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
            # Merge graphs
            G = ox.graph_from_gdfs(
                ox.graph_to_gdfs(G, nodes=True, edges=True)[0],
                ox.graph_to_gdfs(G, nodes=True, edges=True)[1].append(
                    ox.graph_to_gdfs(G_dest, nodes=True, edges=True)[1]
                )
            )
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
                    name=edge.get('name', None),
                    highway_type=edge.get('highway', 'unknown'),
                    ref=edge.get('ref', None),
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
    
    def _query_osm_route(self, origin_coords: Tuple[float, float], dest_coords: Tuple[float, float]) -> Dict:
        """
        Query OSM for a route between two points using Overpass API.
        """
        origin_lat, origin_lon = origin_coords
        dest_lat, dest_lon = dest_coords
        
        # Bounding box with some buffer
        min_lat = min(origin_lat, dest_lat) - 0.1
        max_lat = max(origin_lat, dest_lat) + 0.1
        min_lon = min(origin_lon, dest_lon) - 0.1
        max_lon = max(origin_lon, dest_lon) + 0.1
        
        # Overpass query to get highways in the bounding box
        query = f"""
        [out:json];
        (
            way({min_lat},{min_lon},{max_lat},{max_lon})["highway"];
        );
        out body geom;
        """
        
        result = self.overpass_api.get(query, responseformat="json")
        return result 