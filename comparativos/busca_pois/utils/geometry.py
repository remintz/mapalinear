"""
Geometry utilities for route analysis and point interpolation.
"""

import math
from typing import List, Tuple, Dict, Any


def calculate_distance_meters(
    lat1: float,
    lon1: float,
    lat2: float,
    lon2: float
) -> float:
    """
    Calculate distance between two points using Haversine formula.
    
    Args:
        lat1: Latitude of first point
        lon1: Longitude of first point
        lat2: Latitude of second point
        lon2: Longitude of second point
        
    Returns:
        Distance in meters
    """
    R = 6371000  # Earth radius in meters
    
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    
    a = (math.sin(delta_phi / 2) ** 2 +
         math.cos(phi1) * math.cos(phi2) *
         math.sin(delta_lambda / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    
    return R * c


def interpolate_points(
    geometry: List[Tuple[float, float]],
    target_distances_km: List[float]
) -> List[Tuple[float, float]]:
    """
    Interpolate points along a route geometry at specific distances.
    
    Args:
        geometry: List of (lat, lon) coordinates
        target_distances_km: List of distances in km from start
        
    Returns:
        List of (lat, lon) coordinates at target distances
    """
    if not geometry or len(geometry) < 2:
        return []
    
    # Calculate cumulative distances for each geometry point
    cumulative_distances = [0.0]
    for i in range(1, len(geometry)):
        prev_lat, prev_lon = geometry[i - 1]
        curr_lat, curr_lon = geometry[i]
        distance_m = calculate_distance_meters(prev_lat, prev_lon, curr_lat, curr_lon)
        cumulative_distances.append(cumulative_distances[-1] + distance_m / 1000.0)
    
    total_length = cumulative_distances[-1]
    
    result = []
    for target_km in target_distances_km:
        if target_km <= 0:
            result.append(geometry[0])
        elif target_km >= total_length:
            result.append(geometry[-1])
        else:
            point = _find_point_at_distance(geometry, cumulative_distances, target_km)
            if point:
                result.append(point)
            else:
                result.append(geometry[-1])
    
    return result


def _find_point_at_distance(
    geometry: List[Tuple[float, float]],
    cumulative_distances: List[float],
    target_distance_km: float
) -> Tuple[float, float]:
    """Find coordinates at a specific distance."""
    # Find the segment containing the target distance
    for i in range(1, len(cumulative_distances)):
        if cumulative_distances[i] >= target_distance_km:
            # Interpolate within this segment
            segment_start = cumulative_distances[i - 1]
            segment_end = cumulative_distances[i]
            segment_fraction = (target_distance_km - segment_start) / (segment_end - segment_start)
            
            lat1, lon1 = geometry[i - 1]
            lat2, lon2 = geometry[i]
            
            lat = lat1 + (lat2 - lat1) * segment_fraction
            lon = lon1 + (lon2 - lon1) * segment_fraction
            
            return (lat, lon)
    
    return geometry[-1]


def get_points_along_route(
    geometry: List[Tuple[float, float]],
    num_points: int = 20
) -> List[Dict[str, Any]]:
    """
    Get evenly distributed points along a route.
    
    Args:
        geometry: List of (lat, lon) coordinates
        num_points: Number of points to generate
        
    Returns:
        List of dicts with index, lat, lon, distance_km
    """
    if not geometry or len(geometry) < 2:
        return []
    
    # Calculate total length
    total_distance = 0.0
    cumulative = [0.0]
    for i in range(1, len(geometry)):
        d = calculate_distance_meters(
            geometry[i-1][0], geometry[i-1][1],
            geometry[i][0], geometry[i][1]
        )
        total_distance += d
        cumulative.append(total_distance)
    
    total_km = total_distance / 1000.0
    
    # Generate evenly spaced distances
    interval = total_km / (num_points - 1) if num_points > 1 else total_km
    
    points = []
    for i in range(num_points):
        target_km = i * interval
        point = _find_point_at_distance(geometry, cumulative, target_km)
        if point:
            points.append({
                "index": i + 1,
                "distance_km": round(target_km, 2),
                "lat": round(point[0], 6),
                "lon": round(point[1], 6),
            })
    
    return points


def calculate_bounding_box(
    points: List[Tuple[float, float]],
    padding_meters: int = 1000
) -> Dict[str, float]:
    """
    Calculate bounding box for a set of points.
    
    Args:
        points: List of (lat, lon) coordinates
        padding_meters: Padding in meters to add
        
    Returns:
        Dict with min_lat, max_lat, min_lon, max_lon
    """
    if not points:
        return {"min_lat": 0, "max_lat": 0, "min_lon": 0, "max_lon": 0}
    
    lats = [p[0] for p in points]
    lons = [p[1] for p in points]
    
    # Convert padding to approximate degree offset
    lat_offset = padding_meters / 111000  # ~111km per degree
    lon_offset = padding_meters / (111000 * math.cos(math.radians(sum(lats) / len(lats))))
    
    return {
        "min_lat": min(lats) - lat_offset,
        "max_lat": max(lats) + lat_offset,
        "min_lon": min(lons) - lon_offset,
        "max_lon": max(lons) + lon_offset,
    }