"""
Geographic utility functions for distance and coordinate calculations.

This module contains pure mathematical functions with no dependencies on
providers or services. All functions are stateless and can be tested independently.
"""

import math
from typing import List, Tuple, Optional


def calculate_distance_meters(
    lat1: float, lon1: float, lat2: float, lon2: float
) -> float:
    """
    Calculate the distance between two points using Haversine formula.

    Args:
        lat1, lon1: First point coordinates (degrees)
        lat2, lon2: Second point coordinates (degrees)

    Returns:
        Distance in meters
    """
    # Convert to radians
    lat1_rad = math.radians(lat1)
    lon1_rad = math.radians(lon1)
    lat2_rad = math.radians(lat2)
    lon2_rad = math.radians(lon2)

    # Haversine formula
    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad

    a = (
        math.sin(dlat / 2) * math.sin(dlat / 2)
        + math.cos(lat1_rad)
        * math.cos(lat2_rad)
        * math.sin(dlon / 2)
        * math.sin(dlon / 2)
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    # Earth radius in meters
    R = 6371000
    distance = R * c

    return distance


def calculate_distance_along_route(
    geometry: List[Tuple[float, float]], target_point: Tuple[float, float]
) -> float:
    """
    Calculate the distance along a route geometry to reach a target point.

    Args:
        geometry: Route geometry as list of (lat, lon) tuples
        target_point: Target point (lat, lon)

    Returns:
        Distance in kilometers from start of geometry to target point
    """
    if not geometry:
        return 0.0

    # Find the segment in geometry closest to target point
    min_distance = float("inf")
    closest_segment_idx = 0

    for i in range(len(geometry) - 1):
        # Calculate distance from target to this segment
        seg_start = geometry[i]
        seg_end = geometry[i + 1]

        # Distance to segment midpoint (simplified)
        midpoint = (
            (seg_start[0] + seg_end[0]) / 2,
            (seg_start[1] + seg_end[1]) / 2,
        )
        dist = calculate_distance_meters(
            target_point[0], target_point[1], midpoint[0], midpoint[1]
        )

        if dist < min_distance:
            min_distance = dist
            closest_segment_idx = i

    # Calculate cumulative distance up to the closest segment
    cumulative_distance = 0.0
    for i in range(closest_segment_idx):
        cumulative_distance += calculate_distance_meters(
            geometry[i][0],
            geometry[i][1],
            geometry[i + 1][0],
            geometry[i + 1][1],
        )

    # Convert to km
    return cumulative_distance / 1000.0


def calculate_distance_from_point_to_end(
    geometry: List[Tuple[float, float]], start_point: Tuple[float, float]
) -> float:
    """
    Calculate the distance from a point along a route to the end of the route.

    This is useful for calculating the remaining distance from an intermediate point
    (like a junction) to the end of the route (like a POI).

    Args:
        geometry: Route geometry as list of (lat, lon) tuples
        start_point: Starting point (lat, lon) along the route

    Returns:
        Distance in kilometers from start_point to end of geometry
    """
    if not geometry or len(geometry) < 2:
        return 0.0

    # Find the segment in geometry closest to start point
    min_distance = float("inf")
    closest_segment_idx = 0
    projection_point = start_point

    for i in range(len(geometry) - 1):
        seg_start = geometry[i]
        seg_end = geometry[i + 1]

        # Calculate projection of start_point onto this segment
        # For simplicity, we'll use the midpoint approach
        midpoint = (
            (seg_start[0] + seg_end[0]) / 2,
            (seg_start[1] + seg_end[1]) / 2,
        )
        dist = calculate_distance_meters(
            start_point[0], start_point[1], midpoint[0], midpoint[1]
        )

        if dist < min_distance:
            min_distance = dist
            closest_segment_idx = i
            # Use the end of this segment as the projection point
            projection_point = seg_end

    # Calculate distance from projection point to end of geometry
    cumulative_distance = 0.0

    # Start from the segment after the closest one
    for i in range(closest_segment_idx + 1, len(geometry) - 1):
        cumulative_distance += calculate_distance_meters(
            geometry[i][0],
            geometry[i][1],
            geometry[i + 1][0],
            geometry[i + 1][1],
        )

    # Also add the distance from the start_point to the projection_point
    cumulative_distance += calculate_distance_meters(
        start_point[0],
        start_point[1],
        projection_point[0],
        projection_point[1],
    )

    # Convert to km
    return cumulative_distance / 1000.0


def interpolate_coordinate_at_distance(
    geometry: List[Tuple[float, float]],
    target_distance_km: float,
    total_distance_km: float,
) -> Tuple[float, float]:
    """
    Interpolate a coordinate at a specific distance along the route geometry.

    Args:
        geometry: Route geometry as list of (lat, lon) tuples
        target_distance_km: Target distance from start in kilometers
        total_distance_km: Total route distance in kilometers

    Returns:
        Interpolated (lat, lon) tuple
    """
    if not geometry:
        return (0.0, 0.0)

    if target_distance_km <= 0:
        return geometry[0]

    if target_distance_km >= total_distance_km:
        return geometry[-1]

    # Calculate the ratio along the route
    ratio = target_distance_km / total_distance_km

    # Find the appropriate segment in the geometry
    total_points = len(geometry)
    target_index = ratio * (total_points - 1)

    # Get the two points to interpolate between
    index_before = int(target_index)
    index_after = min(index_before + 1, total_points - 1)

    if index_before == index_after:
        return geometry[index_before]

    # Interpolate between the two points
    point_before = geometry[index_before]
    point_after = geometry[index_after]
    local_ratio = target_index - index_before

    lat = point_before[0] + (point_after[0] - point_before[0]) * local_ratio
    lon = point_before[1] + (point_after[1] - point_before[1]) * local_ratio

    return (lat, lon)


def find_closest_point_index(
    geometry: List[Tuple[float, float]], target_point: Tuple[float, float]
) -> int:
    """
    Find the index of the closest point in geometry to a target point.

    Args:
        geometry: Route geometry as list of (lat, lon) tuples
        target_point: Target point (lat, lon)

    Returns:
        Index of the closest point in geometry
    """
    if not geometry:
        return 0

    min_distance = float("inf")
    closest_idx = 0

    for i, (pt_lat, pt_lon) in enumerate(geometry):
        dist = (
            (pt_lat - target_point[0]) ** 2 + (pt_lon - target_point[1]) ** 2
        ) ** 0.5
        if dist < min_distance:
            min_distance = dist
            closest_idx = i

    return closest_idx


def find_closest_segment_index(
    geometry: List[Tuple[float, float]], target_point: Tuple[float, float]
) -> int:
    """
    Find the index of the segment in geometry closest to a target point.

    Args:
        geometry: Route geometry as list of (lat, lon) tuples
        target_point: Target point (lat, lon)

    Returns:
        Index of the segment (0 to len(geometry)-2)
    """
    if not geometry or len(geometry) < 2:
        return 0

    min_distance = float("inf")
    segment_idx = 0

    for i in range(len(geometry) - 1):
        seg_start = geometry[i]
        seg_end = geometry[i + 1]
        midpoint = (
            (seg_start[0] + seg_end[0]) / 2,
            (seg_start[1] + seg_end[1]) / 2,
        )

        dist = calculate_distance_meters(
            target_point[0], target_point[1], midpoint[0], midpoint[1]
        )

        if dist < min_distance:
            min_distance = dist
            segment_idx = i

    return segment_idx
