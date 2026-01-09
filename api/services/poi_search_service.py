"""
POI Search Service - Core algorithm for finding POIs along routes.

This service handles:
- Searching for POIs around route segments
- Calculating junction points for distant POIs
- Determining POI side (left/right) relative to road
- Finding route intersections for access routes
"""

import logging
import math
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

from uuid import UUID

from api.database.models.route_segment import RouteSegment
from api.models.road_models import Coordinates, LinearRoadSegment, RoadMilestone
from api.providers.base import GeoProvider
from api.providers.models import GeoLocation, POI, POICategory, Route
from api.providers.settings import get_settings
from api.services.milestone_factory import MilestoneFactory
from api.services.poi_debug_service import POIDebugDataCollector
from api.services.poi_quality_service import POIQualityService
from api.services.route_segmentation_service import RouteSegmentationService
from api.utils.geo_utils import (
    calculate_distance_along_route,
    calculate_distance_meters,
    interpolate_coordinate_at_distance,
)

logger = logging.getLogger(__name__)


class POISearchService:
    """
    Service for searching and processing POIs along a route.

    This is the core service that finds POIs near a route, calculates
    junction points for distant POIs, and determines which side of
    the road each POI is on.
    """

    def __init__(
        self,
        geo_provider: GeoProvider,
        poi_provider: GeoProvider,
        milestone_factory: Optional[MilestoneFactory] = None,
        quality_service: Optional[POIQualityService] = None,
    ):
        """
        Initialize the POI Search Service.

        Args:
            geo_provider: Provider for routing/geocoding
            poi_provider: Provider for POI search
            milestone_factory: Factory for creating milestones (optional)
            quality_service: Service for quality assessment (optional)
        """
        self.geo_provider = geo_provider
        self.poi_provider = poi_provider
        self.milestone_factory = milestone_factory or MilestoneFactory(geo_provider)
        self.quality_service = quality_service or POIQualityService()

    async def find_milestones(
        self,
        segments: List[LinearRoadSegment],
        categories: List[POICategory],
        max_distance_from_road: float,
        max_detour_distance_km: float = 5.0,
        exclude_cities: Optional[List[Optional[str]]] = None,
        progress_callback: Optional[Callable[[float], None]] = None,
        main_route: Optional[Route] = None,
        debug_collector: Optional[POIDebugDataCollector] = None,
    ) -> List[RoadMilestone]:
        """
        Find POI milestones along the route using segment points.

        This method:
        1. Extracts search points from segments
        2. Searches for POIs around each point
        3. Converts POIs to milestones
        4. For distant POIs (>500m), calculates junction point
        5. Filters POIs with detour distance > max_detour_distance_km
        6. Enriches with city information
        7. Filters excluded cities

        Args:
            segments: List of road segments
            categories: POI categories to search
            max_distance_from_road: Maximum search radius in meters
            max_detour_distance_km: Maximum allowed detour distance in km
            exclude_cities: Cities to exclude from results
            progress_callback: Callback for progress updates
            main_route: Main route for junction calculations
            debug_collector: Optional collector for debug data

        Returns:
            List of RoadMilestone objects
        """
        segmentation_service = RouteSegmentationService()
        search_points = segmentation_service.extract_search_points_from_segments(segments)
        total_points = len(search_points)

        logger.info(f"Starting milestone search with {total_points} search points")
        logger.info(f"Categories: {[cat.value for cat in categories]}")
        logger.info(
            f"Parameters: max_distance={max_distance_from_road}m, "
            f"max_detour={max_detour_distance_km}km"
        )

        # Normalize excluded cities
        exclude_cities_filtered = [
            city.strip().lower() for city in (exclude_cities or []) if city
        ]
        if exclude_cities_filtered:
            logger.info(f"Cities to exclude: {exclude_cities_filtered}")

        # Statistics
        milestones: List[RoadMilestone] = []
        total_errors = 0
        total_requests = 0
        consecutive_errors = 0
        pois_abandoned_no_junction = 0
        pois_abandoned_detour_too_long = 0
        junction_recalculations = 0

        # Track POIs that have been ADDED as milestones
        milestone_poi_ids: set = set()

        # Track best junction info for distant POIs
        best_junction_for_poi: Dict[
            str, Tuple[Any, float, Tuple[float, float], POI]
        ] = {}

        # Track distant POIs that were processed
        distant_pois_processed: set = set()

        # Optimization tracking
        junction_lookback_for_poi: Dict[str, Tuple[float, float]] = {}
        recalc_attempts_without_improvement: Dict[str, int] = {}
        skipped_similar_lookback = 0
        skipped_past_junction = 0
        skipped_max_attempts = 0

        # Collect all unique POIs
        all_unique_pois_dict: Dict[str, POI] = {}

        # Store junction debug data
        junction_debug_data: Dict[str, Dict[str, Any]] = {}

        for i, (point, distance_from_origin) in enumerate(search_points):
            # Update progress (10% to 90%)
            if progress_callback:
                progress = round(10.0 + (i / total_points) * 80.0)
                progress_callback(progress)
            total_requests += 1

            try:
                # Search for POIs around this point
                pois = await self.poi_provider.search_pois(
                    location=GeoLocation(latitude=point[0], longitude=point[1]),
                    radius=max_distance_from_road,
                    categories=categories,
                    limit=20,
                )

                logger.debug(f"Point {i}: {len(pois)} POIs found")
                consecutive_errors = 0

                for poi in pois:
                    try:
                        # Skip POIs already added as milestones
                        if poi.id in milestone_poi_ids:
                            continue

                        # Collect POI for later persistence
                        if poi.id not in all_unique_pois_dict:
                            all_unique_pois_dict[poi.id] = poi

                        # Validate POI category
                        if not isinstance(poi.category, POICategory):
                            logger.error(
                                f"POI has invalid category: {poi.category}"
                            )
                            continue

                        # Skip abandoned POIs (they are still collected for persistence)
                        provider_data = poi.provider_data or {}
                        if provider_data.get('is_abandoned', False):
                            logger.debug(
                                f"Skipping abandoned POI: {poi.name} ({poi.id})"
                            )
                            continue

                        # Calculate distance from POI to search point
                        poi_distance_from_road = calculate_distance_meters(
                            poi.location.latitude,
                            poi.location.longitude,
                            point[0],
                            point[1],
                        )

                        # Filter out POIs beyond maximum distance
                        if poi_distance_from_road > max_distance_from_road:
                            continue

                        # For nearby POIs (<500m), add directly as milestone
                        if poi_distance_from_road <= 500 or not main_route:
                            milestone = self.milestone_factory.create_from_poi(
                                poi, distance_from_origin, point, None
                            )
                            milestones.append(milestone)
                            milestone_poi_ids.add(poi.id)
                            continue

                        # For distant POIs (>500m), calculate junction
                        distant_pois_processed.add(poi.id)

                        # Check if we already have a junction for this POI
                        is_recalculation = poi.id in best_junction_for_poi

                        # Optimization: Skip recalculation if criteria are met
                        if is_recalculation:
                            prev_junction_info, _, _, _ = best_junction_for_poi[poi.id]
                            prev_junction_km, _, _, _ = prev_junction_info

                            # Calculate lookback point for this recalculation
                            settings = get_settings()
                            lookback_count = settings.lookback_milestones_count
                            lookback_index = i - lookback_count

                            if lookback_index >= 0:
                                new_lookback, _ = search_points[lookback_index]
                            elif i > 0:
                                new_lookback, _ = search_points[0]
                            else:
                                poi_distance_km = poi_distance_from_road / 1000.0
                                lookback_km = min(20.0, max(5.0, poi_distance_km * 2))
                                lookback_distance_km = max(
                                    0, distance_from_origin - lookback_km
                                )
                                new_lookback = interpolate_coordinate_at_distance(
                                    main_route.geometry,
                                    lookback_distance_km,
                                    main_route.total_distance,
                                )

                            # Skip 1: Similar lookback point
                            if poi.id in junction_lookback_for_poi:
                                prev_lookback = junction_lookback_for_poi[poi.id]
                                lookback_distance_m = calculate_distance_meters(
                                    new_lookback[0],
                                    new_lookback[1],
                                    prev_lookback[0],
                                    prev_lookback[1],
                                )
                                if lookback_distance_m < 500:
                                    skipped_similar_lookback += 1
                                    continue

                            # Skip 2: Past junction point
                            if distance_from_origin > prev_junction_km + 2.0:
                                skipped_past_junction += 1
                                continue

                            # Skip 3: Max attempts reached
                            attempts = recalc_attempts_without_improvement.get(
                                poi.id, 0
                            )
                            if attempts >= 3:
                                skipped_max_attempts += 1
                                continue

                            junction_recalculations += 1

                        # Calculate junction
                        junction_result = await self._calculate_junction_for_distant_poi(
                            poi=poi,
                            search_point=point,
                            search_point_distance_km=distance_from_origin,
                            main_route=main_route,
                            all_search_points=search_points,
                            current_search_point_index=i,
                            return_debug=debug_collector is not None,
                        )

                        if not junction_result:
                            continue

                        # Handle return value
                        current_debug_data: Optional[Dict[str, Any]] = None
                        if debug_collector is not None:
                            junction_info, current_debug_data = junction_result
                        else:
                            junction_info = junction_result

                        _, _, access_route_distance_km, _ = junction_info

                        # Calculate lookback for tracking
                        if not is_recalculation:
                            settings = get_settings()
                            lookback_count = settings.lookback_milestones_count
                            lookback_index = i - lookback_count

                            if lookback_index >= 0:
                                new_lookback, _ = search_points[lookback_index]
                            elif i > 0:
                                new_lookback, _ = search_points[0]
                            else:
                                poi_distance_km = poi_distance_from_road / 1000.0
                                lookback_km = min(20.0, max(5.0, poi_distance_km * 2))
                                lookback_distance_km = max(
                                    0, distance_from_origin - lookback_km
                                )
                                new_lookback = interpolate_coordinate_at_distance(
                                    main_route.geometry,
                                    lookback_distance_km,
                                    main_route.total_distance,
                                )

                        # Check if better than previous
                        if poi.id in best_junction_for_poi:
                            prev_junction_info, _, _, _ = best_junction_for_poi[poi.id]
                            _, _, prev_detour, _ = prev_junction_info
                            if access_route_distance_km < prev_detour:
                                best_junction_for_poi[poi.id] = (
                                    junction_info,
                                    distance_from_origin,
                                    point,
                                    poi,
                                )
                                junction_lookback_for_poi[poi.id] = new_lookback
                                recalc_attempts_without_improvement[poi.id] = 0
                                if current_debug_data:
                                    junction_debug_data[poi.id] = current_debug_data
                            else:
                                recalc_attempts_without_improvement[poi.id] = (
                                    recalc_attempts_without_improvement.get(poi.id, 0)
                                    + 1
                                )
                        else:
                            best_junction_for_poi[poi.id] = (
                                junction_info,
                                distance_from_origin,
                                point,
                                poi,
                            )
                            junction_lookback_for_poi[poi.id] = new_lookback
                            if current_debug_data:
                                junction_debug_data[poi.id] = current_debug_data

                    except Exception as e:
                        logger.error(f"Error converting POI: {e}")
                        continue

            except Exception as e:
                total_errors += 1
                consecutive_errors += 1
                logger.error(f"Error searching POIs at point {i}: {e}")

                # Fail fast
                if consecutive_errors >= 5:
                    raise RuntimeError(
                        f"POI search failed: {consecutive_errors} consecutive failures"
                    )

                if total_requests >= 5:
                    error_rate = total_errors / total_requests
                    if error_rate > 0.9:
                        raise RuntimeError(
                            f"POI search failed: {error_rate:.1%} failure rate"
                        )
                continue

        # Count POIs without junction
        pois_abandoned_no_junction = len(distant_pois_processed) - len(
            best_junction_for_poi
        )

        # Process distant POIs with valid junctions
        logger.info(
            f"Processing {len(best_junction_for_poi)} distant POIs with junctions "
            f"(of {len(distant_pois_processed)} processed)"
        )

        # Log optimization stats
        total_skipped = (
            skipped_similar_lookback + skipped_past_junction + skipped_max_attempts
        )
        if total_skipped > 0:
            logger.info(
                f"Optimization: {total_skipped} recalculations avoided "
                f"(similar lookback: {skipped_similar_lookback}, "
                f"past junction: {skipped_past_junction}, "
                f"max attempts: {skipped_max_attempts})"
            )

        distant_pois_added = 0
        # Cities and towns get 3x max detour distance (villages use normal limit)
        locality_categories = (POICategory.CITY, POICategory.TOWN)

        for poi_id, (
            junction_info,
            dist_from_origin,
            search_pt,
            poi,
        ) in best_junction_for_poi.items():
            if poi_id in milestone_poi_ids:
                continue

            junction_distance_km, _, access_route_distance_km, _ = junction_info

            # Apply 3x multiplier for localities
            effective_max_detour = max_detour_distance_km
            if poi.category in locality_categories:
                effective_max_detour = max_detour_distance_km * 3

            if access_route_distance_km <= effective_max_detour:
                distant_pois_added += 1
                milestone = self.milestone_factory.create_from_poi(
                    poi, junction_distance_km, search_pt, junction_info
                )
                milestones.append(milestone)
                milestone_poi_ids.add(poi_id)
            else:
                pois_abandoned_detour_too_long += 1

        logger.info(f"RESULT: {len(milestones)} milestones found along route")
        logger.info(f"Unique POIs found: {len(all_unique_pois_dict)}")
        logger.info(f"Distant POIs analyzed: {len(best_junction_for_poi)}")
        logger.info(f"Distant POIs added: {distant_pois_added}")

        if pois_abandoned_no_junction > 0:
            logger.info(f"POIs without junction: {pois_abandoned_no_junction}")
        if pois_abandoned_detour_too_long > 0:
            logger.info(f"POIs abandoned (detour too long): {pois_abandoned_detour_too_long}")

        # Persist POIs to database
        if all_unique_pois_dict:
            try:
                await self._persist_pois_to_database(
                    list(all_unique_pois_dict.values()), milestone_poi_ids
                )
            except Exception as e:
                logger.warning(f"Error persisting POIs: {e}")

        # Update progress
        if progress_callback:
            progress_callback(90)

        # Enrich with cities
        await self.milestone_factory.enrich_with_cities(milestones)

        # Update progress
        if progress_callback:
            progress_callback(95)

        # Filter excluded cities
        milestones = self.quality_service.filter_by_excluded_cities(
            milestones, exclude_cities_filtered
        )

        # Collect debug data
        if debug_collector and main_route:
            await self._collect_milestone_debug_data(
                milestones, main_route, debug_collector, junction_debug_data
            )

        return milestones

    def determine_poi_side(
        self,
        main_route_geometry: List[Tuple[float, float]],
        junction_point: Tuple[float, float],
        poi_location: Tuple[float, float],
        return_debug: bool = False,
    ) -> Union[str, Tuple[str, Dict[str, Any]]]:
        """
        Determine if POI is on the left or right side of the road.

        Uses cross product to determine the side relative to road direction.

        Args:
            main_route_geometry: Main route geometry as list of (lat, lon) tuples
            junction_point: Junction coordinates (lat, lon)
            poi_location: POI coordinates (lat, lon)
            return_debug: If True, also return debug calculation info

        Returns:
            'left' or 'right' (or tuple with debug info if return_debug=True)
        """
        # Find the segment closest to junction point
        min_distance = float("inf")
        segment_idx = 0

        for i in range(len(main_route_geometry) - 1):
            seg_start = main_route_geometry[i]
            seg_end = main_route_geometry[i + 1]
            midpoint = (
                (seg_start[0] + seg_end[0]) / 2,
                (seg_start[1] + seg_end[1]) / 2,
            )

            dist = calculate_distance_meters(
                junction_point[0], junction_point[1], midpoint[0], midpoint[1]
            )

            if dist < min_distance:
                min_distance = dist
                segment_idx = i

        # Get road direction vector
        seg_start = main_route_geometry[segment_idx]
        seg_end = main_route_geometry[segment_idx + 1]

        # Vector from segment start to end (road direction)
        road_vector = (
            seg_end[1] - seg_start[1],
            seg_end[0] - seg_start[0],
        )  # (dx, dy)

        # Vector from junction to POI
        poi_vector = (
            poi_location[1] - junction_point[1],
            poi_location[0] - junction_point[0],
        )  # (dx, dy)

        # Cross product
        cross_product = road_vector[0] * poi_vector[1] - road_vector[1] * poi_vector[0]

        side = "left" if cross_product > 0 else "right"

        if return_debug:
            debug_info = {
                "road_vector": {"dx": road_vector[0], "dy": road_vector[1]},
                "poi_vector": {"dx": poi_vector[0], "dy": poi_vector[1]},
                "cross_product": cross_product,
                "resulting_side": side,
                "segment_start": {"lat": seg_start[0], "lon": seg_start[1]},
                "segment_end": {"lat": seg_end[0], "lon": seg_end[1]},
                "segment_idx": segment_idx,
            }
            return (side, debug_info)

        return side

    def determine_side_from_access_route(
        self,
        main_route_geometry: List[Tuple[float, float]],
        junction_point: Tuple[float, float],
        access_route_geometry: List[Tuple[float, float]],
        poi_location: Optional[Tuple[float, float]] = None,
        return_debug: bool = False,
    ) -> Union[str, Tuple[str, Dict[str, Any]]]:
        """
        Determine if driver needs to turn left or right based on access route.

        This method looks at the initial direction of the access route from
        the junction point, which represents the actual turn needed.

        Args:
            main_route_geometry: Main route geometry
            junction_point: Junction coordinates
            access_route_geometry: Access route from lookback to POI
            poi_location: Optional POI location for fallback
            return_debug: If True, return debug info

        Returns:
            'left' or 'right' (or tuple with debug if return_debug=True)
        """
        # Find segment closest to junction point
        min_distance = float("inf")
        segment_idx = 0

        for i in range(len(main_route_geometry) - 1):
            seg_start = main_route_geometry[i]
            seg_end = main_route_geometry[i + 1]
            midpoint = (
                (seg_start[0] + seg_end[0]) / 2,
                (seg_start[1] + seg_end[1]) / 2,
            )

            dist = calculate_distance_meters(
                junction_point[0], junction_point[1], midpoint[0], midpoint[1]
            )

            if dist < min_distance:
                min_distance = dist
                segment_idx = i

        # Get road direction vector
        seg_start = main_route_geometry[segment_idx]
        seg_end = main_route_geometry[segment_idx + 1]
        road_vector = (seg_end[1] - seg_start[1], seg_end[0] - seg_start[0])

        # Find point on access route closest to junction
        min_dist_to_junction = float("inf")
        junction_idx_on_access = 0

        for i, point in enumerate(access_route_geometry):
            dist = calculate_distance_meters(
                junction_point[0], junction_point[1], point[0], point[1]
            )
            if dist < min_dist_to_junction:
                min_dist_to_junction = dist
                junction_idx_on_access = i

        # Get direction after junction
        access_direction_point_idx = min(
            junction_idx_on_access + 5, len(access_route_geometry) - 1
        )

        if access_direction_point_idx <= junction_idx_on_access:
            access_direction_point_idx = len(access_route_geometry) - 1

        access_start = access_route_geometry[junction_idx_on_access]
        access_direction_point = access_route_geometry[access_direction_point_idx]

        # Access vector
        access_vector = (
            access_direction_point[1] - access_start[1],
            access_direction_point[0] - access_start[0],
        )

        # Cross product
        cross_product = (
            road_vector[0] * access_vector[1] - road_vector[1] * access_vector[0]
        )

        # Calculate magnitudes for parallel check
        road_magnitude = math.sqrt(road_vector[0] ** 2 + road_vector[1] ** 2)
        access_magnitude = math.sqrt(access_vector[0] ** 2 + access_vector[1] ** 2)

        used_fallback = False
        fallback_reason = None
        original_cross_product = cross_product
        original_access_vector = access_vector

        # Check for parallel vectors
        PARALLEL_THRESHOLD = 0.1

        if road_magnitude > 0 and access_magnitude > 0:
            normalized_cross = abs(cross_product) / (road_magnitude * access_magnitude)

            if normalized_cross < PARALLEL_THRESHOLD and poi_location is not None:
                used_fallback = True
                fallback_reason = (
                    f"vectors_nearly_parallel (normalized={normalized_cross:.6f})"
                )

                poi_vector = (
                    poi_location[1] - junction_point[1],
                    poi_location[0] - junction_point[0],
                )
                access_vector = poi_vector
                cross_product = (
                    road_vector[0] * poi_vector[1] - road_vector[1] * poi_vector[0]
                )

        side = "left" if cross_product > 0 else "right"

        if return_debug:
            debug_info = {
                "road_vector": {"dx": road_vector[0], "dy": road_vector[1]},
                "access_vector": {"dx": access_vector[0], "dy": access_vector[1]},
                "cross_product": cross_product,
                "resulting_side": side,
                "segment_start": {"lat": seg_start[0], "lon": seg_start[1]},
                "segment_end": {"lat": seg_end[0], "lon": seg_end[1]},
                "segment_idx": segment_idx,
                "junction_idx_on_access": junction_idx_on_access,
                "access_direction_point_idx": access_direction_point_idx,
                "method": "access_route_direction",
                "used_fallback": used_fallback,
                "fallback_reason": fallback_reason,
            }
            if used_fallback:
                debug_info["original_access_vector"] = {
                    "dx": original_access_vector[0],
                    "dy": original_access_vector[1],
                }
                debug_info["original_cross_product"] = original_cross_product
            return (side, debug_info)

        return side

    def _find_route_intersection(
        self,
        main_route_geometry: List[Tuple[float, float]],
        access_route_geometry: List[Tuple[float, float]],
        tolerance_meters: float = 100.0,
    ) -> Optional[Dict[str, Any]]:
        """
        Find the divergence point where access route first leaves the main route.

        Args:
            main_route_geometry: Main route geometry
            access_route_geometry: Access route to POI
            tolerance_meters: Max distance to consider as "on main route"

        Returns:
            Dict with exit point info or None
        """
        if not main_route_geometry or not access_route_geometry:
            return None

        first_segment_start = None
        first_segment_end = None
        first_segment_end_on_main = None
        first_segment_end_index = 0
        first_segment_end_distance_m = 0.0
        first_segment_end_distance_to_main = 0.0

        cumulative_distance_m = 0.0
        in_following_segment = False
        segment_ended = False

        for i, access_point in enumerate(access_route_geometry):
            if i > 0:
                prev_point = access_route_geometry[i - 1]
                segment_distance = calculate_distance_meters(
                    prev_point[0], prev_point[1], access_point[0], access_point[1]
                )
                cumulative_distance_m += segment_distance

            if segment_ended:
                break

            # Find closest point on main route
            closest_distance = float("inf")
            closest_main_point = None

            for main_point in main_route_geometry:
                distance = calculate_distance_meters(
                    access_point[0], access_point[1], main_point[0], main_point[1]
                )

                if distance < closest_distance:
                    closest_distance = distance
                    closest_main_point = main_point

            is_within_tolerance = (
                closest_distance < tolerance_meters and closest_main_point is not None
            )

            if is_within_tolerance:
                if not in_following_segment:
                    in_following_segment = True
                    first_segment_start = i

                first_segment_end = access_point
                first_segment_end_on_main = closest_main_point
                first_segment_end_index = i
                first_segment_end_distance_m = cumulative_distance_m
                first_segment_end_distance_to_main = closest_distance
            else:
                if in_following_segment:
                    segment_ended = True

        if first_segment_end_on_main and first_segment_end:
            return {
                "exit_point_on_access": first_segment_end,
                "corresponding_point_on_main": first_segment_end_on_main,
                "distance_along_access_km": first_segment_end_distance_m / 1000.0,
                "exit_point_index": first_segment_end_index,
                "intersection_distance_m": first_segment_end_distance_to_main,
            }

        return None

    async def _calculate_junction_for_distant_poi(
        self,
        poi: POI,
        search_point: Tuple[float, float],
        search_point_distance_km: float,
        main_route: Route,
        all_search_points: List[Tuple[Tuple[float, float], float]],
        current_search_point_index: int,
        return_debug: bool = False,
    ) -> Optional[
        Union[
            Tuple[float, Tuple[float, float], float, str],
            Tuple[Tuple[float, Tuple[float, float], float, str], Dict[str, Any]],
        ]
    ]:
        """
        Calculate the junction/exit point for a distant POI.

        Args:
            poi: The POI object
            search_point: Search point on main route
            search_point_distance_km: Distance of search point from origin
            main_route: Complete main route object
            all_search_points: List of all search points
            current_search_point_index: Current index in search points
            return_debug: If True, return debug data

        Returns:
            Tuple of (junction_distance_km, junction_coords, access_distance_km, side)
            or None if not found
        """
        debug_data: Dict[str, Any] = {}
        settings = get_settings()

        poi_distance_from_road_m = calculate_distance_meters(
            poi.location.latitude,
            poi.location.longitude,
            search_point[0],
            search_point[1],
        )

        # Find lookback point
        lookback_count = settings.lookback_milestones_count
        lookback_index = current_search_point_index - lookback_count

        if lookback_index >= 0:
            lookback_point, lookback_distance_km = all_search_points[lookback_index]
            lookback_method = "search_point"
        elif current_search_point_index > 0:
            lookback_point, lookback_distance_km = all_search_points[0]
            lookback_method = "search_point_first"
        else:
            poi_distance_km = poi_distance_from_road_m / 1000.0
            lookback_km = min(20.0, max(5.0, poi_distance_km * 2))
            lookback_distance_km = max(0, search_point_distance_km - lookback_km)
            lookback_point = interpolate_coordinate_at_distance(
                main_route.geometry, lookback_distance_km, main_route.total_distance
            )
            lookback_method = "interpolated"

        if return_debug:
            debug_data["lookback_data"] = {
                "poi_distance_from_road_m": poi_distance_from_road_m,
                "lookback_distance_km": lookback_distance_km,
                "lookback_point": {"lat": lookback_point[0], "lon": lookback_point[1]},
                "lookback_method": lookback_method,
            }

        try:
            # Calculate route from lookback to POI
            access_route = await self.geo_provider.calculate_route(
                GeoLocation(latitude=lookback_point[0], longitude=lookback_point[1]),
                GeoLocation(
                    latitude=poi.location.latitude, longitude=poi.location.longitude
                ),
            )

            if not access_route or not access_route.geometry:
                return None

            if return_debug:
                geometry = access_route.geometry
                if len(geometry) > 100:
                    step = len(geometry) // 100
                    sampled = geometry[::step]
                    if geometry[-1] not in sampled:
                        sampled.append(geometry[-1])
                    debug_data["access_route_geometry"] = [
                        [p[0], p[1]] for p in sampled
                    ]
                else:
                    debug_data["access_route_geometry"] = [
                        [p[0], p[1]] for p in geometry
                    ]

            # Find intersection
            intersection = self._find_route_intersection(
                main_route.geometry, access_route.geometry, tolerance_meters=50.0
            )

            if intersection:
                exit_point_on_access = intersection["exit_point_on_access"]
                corresponding_point_on_main = intersection["corresponding_point_on_main"]
                exit_point_index = intersection["exit_point_index"]

                junction_distance_km = calculate_distance_along_route(
                    main_route.geometry, corresponding_point_on_main
                )

                junction_coords = corresponding_point_on_main

                # Calculate access route distance from exit point to POI
                access_route_distance_km = 0.0
                for i in range(exit_point_index, len(access_route.geometry) - 1):
                    access_route_distance_km += (
                        calculate_distance_meters(
                            access_route.geometry[i][0],
                            access_route.geometry[i][1],
                            access_route.geometry[i + 1][0],
                            access_route.geometry[i + 1][1],
                        )
                        / 1000.0
                    )

                # Determine side
                poi_loc = (poi.location.latitude, poi.location.longitude)
                if return_debug:
                    side, side_debug = self.determine_side_from_access_route(
                        main_route.geometry,
                        corresponding_point_on_main,
                        access_route.geometry,
                        poi_location=poi_loc,
                        return_debug=True,
                    )
                    debug_data["side_calculation"] = side_debug
                    debug_data["access_route_distance_km"] = access_route_distance_km
                else:
                    side = self.determine_side_from_access_route(
                        main_route.geometry,
                        corresponding_point_on_main,
                        access_route.geometry,
                        poi_location=poi_loc,
                    )

                junction_info = (
                    junction_distance_km,
                    junction_coords,
                    access_route_distance_km,
                    side,
                )

                if return_debug:
                    return (junction_info, debug_data)
                return junction_info
            else:
                return None

        except Exception as e:
            logger.error(f"Error calculating junction for {poi.name}: {e}")
            return None

    async def _persist_pois_to_database(
        self, pois: List[POI], referenced_poi_ids: set
    ) -> None:
        """Persist POIs to the database."""
        from sqlalchemy.ext.asyncio import (
            AsyncSession,
            async_sessionmaker,
            create_async_engine,
        )

        from .poi_persistence_service import persist_pois_batch

        settings = get_settings()

        database_url = (
            f"postgresql+asyncpg://{settings.postgres_user}:{settings.postgres_password}"
            f"@{settings.postgres_host}:{settings.postgres_port}/{settings.postgres_database}"
        )
        engine = create_async_engine(
            database_url, pool_size=1, max_overflow=0, pool_pre_ping=True
        )
        session_maker = async_sessionmaker(
            engine, class_=AsyncSession, expire_on_commit=False
        )

        try:
            async with session_maker() as session:
                await persist_pois_batch(
                    session=session, pois=pois, referenced_poi_ids=referenced_poi_ids
                )
        finally:
            await engine.dispose()

    async def _collect_milestone_debug_data(
        self,
        milestones: List[RoadMilestone],
        main_route: Route,
        debug_collector: POIDebugDataCollector,
        junction_debug_data: Optional[Dict[str, Dict[str, Any]]] = None,
    ) -> None:
        """Collect debug data for all milestones."""
        junction_debug_data = junction_debug_data or {}

        for milestone in milestones:
            try:
                poi_lat = milestone.coordinates.latitude
                poi_lon = milestone.coordinates.longitude

                poi_junction_debug = junction_debug_data.get(milestone.id, {})

                access_route_geometry = poi_junction_debug.get("access_route_geometry")
                access_route_distance_km = poi_junction_debug.get(
                    "access_route_distance_km"
                )
                lookback_data = poi_junction_debug.get("lookback_data")
                junction_calculation = poi_junction_debug.get("junction_calculation")
                side_calculation = poi_junction_debug.get("side_calculation")

                if not side_calculation:
                    # Calculate side based on closest point
                    closest_idx = 0
                    min_distance = float("inf")
                    for i, (pt_lat, pt_lon) in enumerate(main_route.geometry):
                        dist = ((pt_lat - poi_lat) ** 2 + (pt_lon - poi_lon) ** 2) ** 0.5
                        if dist < min_distance:
                            min_distance = dist
                            closest_idx = i

                    route_point = main_route.geometry[closest_idx]
                    try:
                        result = self.determine_poi_side(
                            main_route.geometry, route_point, (poi_lat, poi_lon), True
                        )
                        if isinstance(result, tuple):
                            _, side_calculation = result
                    except Exception:
                        pass

                junction_lat = None
                junction_lon = None
                if milestone.junction_coordinates:
                    junction_lat = milestone.junction_coordinates.latitude
                    junction_lon = milestone.junction_coordinates.longitude

                debug_collector.collect_poi_data(
                    poi_id=milestone.id,
                    poi_name=milestone.name or "Sem nome",
                    poi_type=milestone.type.value if milestone.type else "unknown",
                    poi_lat=poi_lat,
                    poi_lon=poi_lon,
                    distance_from_road_m=milestone.distance_from_road_meters or 0,
                    final_side=milestone.side or "center",
                    requires_detour=milestone.requires_detour or False,
                    junction_lat=junction_lat,
                    junction_lon=junction_lon,
                    junction_distance_km=milestone.junction_distance_km,
                    access_route_geometry=access_route_geometry,
                    access_route_distance_km=access_route_distance_km,
                    side_calculation=side_calculation,
                    lookback_data=lookback_data,
                    junction_calculation=junction_calculation,
                )

            except Exception as e:
                logger.warning(f"Error collecting debug for POI {milestone.id}: {e}")
                continue

    async def search_pois_for_segment(
        self,
        segment: RouteSegment,
        categories: List[POICategory],
        max_distance_from_road: float = 3000,
    ) -> List[Tuple[POI, int, int]]:
        """
        Search for POIs using a segment's pre-computed search points.

        This method is optimized for the reusable segments architecture:
        - Uses the segment's stored search_points
        - Returns POIs with discovery metadata for SegmentPOI creation

        Args:
            segment: RouteSegment with pre-computed search_points
            categories: POI categories to search for
            max_distance_from_road: Maximum search radius in meters

        Returns:
            List of tuples (POI, search_point_index, straight_line_distance_m)
        """
        if not segment.search_points:
            logger.debug(f"Segment {segment.id} has no search points")
            return []

        # Track unique POIs with best discovery data
        # Key: poi_id, Value: (POI, search_point_index, distance_m)
        best_discovery: Dict[str, Tuple[POI, int, int]] = {}

        for sp in segment.search_points:
            sp_index = sp["index"]
            sp_lat = sp["lat"]
            sp_lon = sp["lon"]

            try:
                pois = await self.poi_provider.search_pois(
                    location=GeoLocation(latitude=sp_lat, longitude=sp_lon),
                    radius=max_distance_from_road,
                    categories=categories,
                    limit=20,
                )

                for poi in pois:
                    # Calculate straight-line distance
                    distance_m = int(
                        calculate_distance_meters(
                            poi.location.latitude,
                            poi.location.longitude,
                            sp_lat,
                            sp_lon,
                        )
                    )

                    # Skip abandoned POIs
                    provider_data = poi.provider_data or {}
                    if provider_data.get("is_abandoned", False):
                        continue

                    # Keep best (closest) discovery for each POI
                    if poi.id in best_discovery:
                        _, _, prev_distance = best_discovery[poi.id]
                        if distance_m < prev_distance:
                            best_discovery[poi.id] = (poi, sp_index, distance_m)
                    else:
                        best_discovery[poi.id] = (poi, sp_index, distance_m)

            except Exception as e:
                logger.warning(
                    f"Error searching POIs at search point {sp_index}: {e}"
                )
                continue

        logger.info(
            f"Found {len(best_discovery)} unique POIs for segment {segment.id}"
        )

        return list(best_discovery.values())
