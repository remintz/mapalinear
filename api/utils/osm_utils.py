import osmnx as ox
import overpass
from typing import Dict, List, Tuple, Any, Optional, Union
import logging
import geopy.distance
from shapely.geometry import Point, LineString, shape
import math

logger = logging.getLogger(__name__)

def build_overpass_query(
    bbox: Tuple[float, float, float, float], 
    tags: Dict[str, Optional[str]] = None,
    way_or_node: str = "way"
) -> str:
    """
    Constrói uma consulta Overpass API para um bbox e tags específicos.
    
    Args:
        bbox: Tuple[float, float, float, float] - (min_lat, min_lon, max_lat, max_lon)
        tags: Dict[str, Optional[str]] - Tags a serem filtradas
        way_or_node: str - "way", "node" ou "relation"
        
    Returns:
        str: Consulta Overpass
    """
    if tags is None:
        tags = {}
    
    min_lat, min_lon, max_lat, max_lon = bbox
    tag_filter = ""
    
    for key, value in tags.items():
        if value is None:
            tag_filter += f'["{key}"]'
        else:
            tag_filter += f'["{key}"="{value}"]'
    
    query = f"""
    [out:json];
    (
        {way_or_node}{tag_filter}({min_lat},{min_lon},{max_lat},{max_lon});
    );
    out body geom;
    """
    
    return query


def calculate_distance_from_point_to_line(
    point: Tuple[float, float], 
    line_points: List[Tuple[float, float]]
) -> float:
    """
    Calcula a distância em metros de um ponto para uma linha.
    
    Args:
        point: Tuple[float, float] - (latitude, longitude) do ponto
        line_points: List[Tuple[float, float]] - Lista de pontos (latitude, longitude) da linha
        
    Returns:
        float: Distância em metros
    """
    if len(line_points) < 2:
        return geopy.distance.geodesic(point, line_points[0]).meters if line_points else float('inf')
    
    # Convert to shapely objects
    point_obj = Point(point[1], point[0])  # lon, lat for shapely
    line_obj = LineString([(lon, lat) for lat, lon in line_points])
    
    # Calculate distance
    return point_obj.distance(line_obj) * 111000  # Approximate conversion to meters


def calculate_distance_along_linestring(
    linestring: List[Tuple[float, float]], 
    start_idx: int = 0
) -> List[float]:
    """
    Calcula a distância acumulada ao longo de uma LineString.
    
    Args:
        linestring: List[Tuple[float, float]] - Lista de pontos (latitude, longitude)
        start_idx: int - Índice do ponto inicial
        
    Returns:
        List[float]: Lista de distâncias acumuladas em metros
    """
    distances = [0.0]  # Start with 0
    total_distance = 0.0
    
    for i in range(start_idx, len(linestring) - 1):
        # Calculate distance between consecutive points
        p1 = linestring[i]
        p2 = linestring[i + 1]
        segment_distance = geopy.distance.geodesic(p1, p2).meters
        total_distance += segment_distance
        distances.append(total_distance)
    
    return distances


def find_nearest_point_on_linestring(
    point: Tuple[float, float], 
    linestring: List[Tuple[float, float]]
) -> Tuple[int, float, Tuple[float, float]]:
    """
    Encontra o ponto mais próximo em uma LineString.
    
    Args:
        point: Tuple[float, float] - (latitude, longitude) do ponto
        linestring: List[Tuple[float, float]] - Lista de pontos (latitude, longitude) da linha
        
    Returns:
        Tuple[int, float, Tuple[float, float]]: 
            - Índice do segmento
            - Distância em metros
            - Coordenadas do ponto mais próximo
    """
    if not linestring:
        return -1, float('inf'), (0, 0)
    
    min_distance = float('inf')
    nearest_segment_idx = -1
    nearest_point = linestring[0]
    
    # Convert to shapely
    point_obj = Point(point[1], point[0])  # lon, lat for shapely
    
    for i in range(len(linestring) - 1):
        p1 = linestring[i]
        p2 = linestring[i + 1]
        
        # Create line segment
        segment = LineString([(p1[1], p1[0]), (p2[1], p2[0])])  # lon, lat
        
        # Calculate distance
        dist = point_obj.distance(segment) * 111000  # Approximate conversion to meters
        
        if dist < min_distance:
            min_distance = dist
            nearest_segment_idx = i
            
            # Find nearest point on segment
            nearest_point_on_segment = segment.interpolate(segment.project(point_obj))
            nearest_point = (nearest_point_on_segment.y, nearest_point_on_segment.x)  # lat, lon
    
    return nearest_segment_idx, min_distance, nearest_point


def get_bbox_with_buffer(
    points: List[Tuple[float, float]], 
    buffer_km: float = 1.0
) -> Tuple[float, float, float, float]:
    """
    Obtém um bbox com buffer ao redor de uma lista de pontos.
    
    Args:
        points: List[Tuple[float, float]] - Lista de pontos (latitude, longitude)
        buffer_km: float - Buffer em quilômetros
        
    Returns:
        Tuple[float, float, float, float]: (min_lat, min_lon, max_lat, max_lon)
    """
    if not points:
        return (0, 0, 0, 0)
    
    lats = [p[0] for p in points]
    lons = [p[1] for p in points]
    
    min_lat = min(lats)
    max_lat = max(lats)
    min_lon = min(lons)
    max_lon = max(lons)
    
    # Add buffer (approximate conversion from km to degrees)
    # 1 degree of latitude is approximately 111 km
    lat_buffer = buffer_km / 111.0
    # 1 degree of longitude varies with latitude
    # At the equator, 1 degree of longitude is also approximately 111 km
    # At higher latitudes, it's less
    avg_lat = (min_lat + max_lat) / 2
    lon_buffer = buffer_km / (111.0 * math.cos(math.radians(avg_lat)))
    
    return (
        min_lat - lat_buffer,
        min_lon - lon_buffer,
        max_lat + lat_buffer,
        max_lon + lon_buffer
    )


def convert_osm_tags_to_dict(tags: List[Dict[str, str]]) -> Dict[str, str]:
    """
    Converte tags OSM do formato de lista para dicionário.
    
    Args:
        tags: List[Dict[str, str]] - Lista de tags no formato OSM
        
    Returns:
        Dict[str, str]: Dicionário de tags
    """
    result = {}
    for tag in tags:
        if "k" in tag and "v" in tag:
            result[tag["k"]] = tag["v"]
    return result


def extract_road_refs(tags: Dict[str, str]) -> List[str]:
    """
    Extrai referências de estradas a partir de tags OSM.
    
    Args:
        tags: Dict[str, str] - Tags OSM
        
    Returns:
        List[str]: Lista de referências
    """
    refs = []
    
    # Check common ref tags
    for key in ["ref", "int_ref", "nat_ref", "reg_ref"]:
        if key in tags and tags[key]:
            # Split by semicolon or comma if multiple refs
            if ";" in tags[key]:
                refs.extend([r.strip() for r in tags[key].split(";")])
            elif "," in tags[key]:
                refs.extend([r.strip() for r in tags[key].split(",")])
            else:
                refs.append(tags[key].strip())
    
    # Remove duplicates while preserving order
    seen = set()
    return [r for r in refs if not (r in seen or seen.add(r))]


def classify_poi_from_osm_tags(tags: Dict[str, str]) -> Optional[str]:
    """
    Classifica um ponto de interesse com base em suas tags OSM.
    
    Args:
        tags: Dict[str, str] - Tags OSM
        
    Returns:
        Optional[str]: Tipo de POI ou None se não for reconhecido
    """
    if "highway" in tags and tags["highway"] == "services":
        return "rest_area"
    
    if "highway" in tags and tags["highway"] == "toll_booth":
        return "toll_booth"
    
    if "amenity" in tags:
        amenity = tags["amenity"]
        if amenity == "fuel":
            return "gas_station"
        elif amenity in ["restaurant", "fast_food", "cafe"]:
            return "restaurant"
        elif amenity == "hotel":
            return "hotel"
        elif amenity in ["hospital", "clinic"]:
            return "hospital"
        elif amenity == "police":
            return "police"
    
    if "place" in tags:
        place = tags["place"]
        if place == "city":
            return "city"
        elif place == "town":
            return "town"
        elif place == "village":
            return "village"
    
    return None


def determine_side_of_road(
    point: Tuple[float, float], 
    road_segment: List[Tuple[float, float]], 
    segment_idx: int,
    threshold_meters: float = 50
) -> str:
    """
    Determina o lado da estrada onde um ponto está localizado.
    
    Args:
        point: Tuple[float, float] - (latitude, longitude) do ponto
        road_segment: List[Tuple[float, float]] - Lista de pontos (latitude, longitude) da estrada
        segment_idx: int - Índice do segmento mais próximo
        threshold_meters: float - Distância máxima para ser considerado "center"
        
    Returns:
        str: "left", "right" ou "center"
    """
    if segment_idx < 0 or segment_idx >= len(road_segment) - 1:
        return "center"
    
    p1 = road_segment[segment_idx]
    p2 = road_segment[segment_idx + 1]
    
    # Convert to shapely
    line = LineString([(p1[1], p1[0]), (p2[1], p2[0])])  # lon, lat
    point_obj = Point(point[1], point[0])  # lon, lat
    
    # Check if point is very close to the road
    dist = point_obj.distance(line) * 111000  # Approximate conversion to meters
    if dist < threshold_meters:
        return "center"
    
    # Determine side using cross product
    dx = p2[1] - p1[1]  # lon2 - lon1
    dy = p2[0] - p1[0]  # lat2 - lat1
    
    # Cross product to determine side
    cross_product = (point[1] - p1[1]) * dy - (point[0] - p1[0]) * dx
    
    return "right" if cross_product > 0 else "left" 