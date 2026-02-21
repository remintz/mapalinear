"""
Utils package for POI comparison.
"""

from .geometry import (
    calculate_distance_meters,
    interpolate_points,
    get_points_along_route,
)
from .metrics import (
    compare_results,
    calculate_category_stats,
    generate_summary,
)

__all__ = [
    "calculate_distance_meters",
    "interpolate_points",
    "get_points_along_route",
    "compare_results",
    "calculate_category_stats",
    "generate_summary",
]