"""
Map Assembly Service - Assembles maps from reusable segments.

This service handles:
- Creating MapSegment records linking a map to its segments
- Creating MapPOI records with junction/side calculations
- POI deduplication when the same POI appears in multiple segments
- Calculating distances from map origin
"""

import logging
from decimal import Decimal
from typing import Dict, List, Optional, Set, Tuple
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from api.database.models.map import Map
from api.database.models.map_poi import MapPOI
from api.database.models.map_segment import MapSegment
from api.database.models.poi import POI
from api.database.models.route_segment import RouteSegment
from api.database.models.segment_poi import SegmentPOI
from api.database.repositories.map import MapRepository
from api.database.repositories.map_poi import MapPOIRepository
from api.database.repositories.map_segment import MapSegmentRepository
from api.database.repositories.poi import POIRepository
from api.database.repositories.segment_poi import SegmentPOIRepository
from api.models.road_models import Coordinates, MapSegmentResponse
from api.providers.base import GeoProvider
from api.services.junction_calculation_service import (
    GlobalSearchPoint,
    JunctionCalculationService,
    JunctionResult,
)
from api.services.poi_debug_service import POIDebugDataCollector

logger = logging.getLogger(__name__)


class MapAssemblyService:
    """
    Service for assembling maps from reusable route segments.

    This service takes a list of RouteSegments and creates all the
    necessary database records to represent a complete map, including:
    - MapSegment associations
    - MapPOI records with calculated junction data
    - POI deduplication
    """

    def __init__(
        self,
        session: AsyncSession,
        geo_provider: Optional[GeoProvider] = None,
    ):
        """
        Initialize the Map Assembly Service.

        Args:
            session: SQLAlchemy async session
            geo_provider: Geographic provider for junction routing (optional)
        """
        self.session = session
        self.map_repo = MapRepository(session)
        self.map_segment_repo = MapSegmentRepository(session)
        self.map_poi_repo = MapPOIRepository(session)
        self.poi_repo = POIRepository(session)
        self.segment_poi_repo = SegmentPOIRepository(session)
        self.junction_service = JunctionCalculationService(geo_provider)

    async def assemble_map(
        self,
        map_id: UUID,
        segments: List[RouteSegment],
        route_geometry: List[Tuple[float, float]],
        route_total_km: float,
        debug_collector: Optional[POIDebugDataCollector] = None,
        origin_city: Optional[str] = None,
    ) -> Tuple[int, int, Dict[str, UUID]]:
        """
        Assemble a map from a list of route segments.

        This method:
        1. Creates MapSegment records linking segments to the map
        2. Aggregates search points for junction calculation
        3. Creates MapPOI records with calculated junction data
        4. Deduplicates POIs that appear in multiple segments
        5. Filters out POIs in the origin city
        6. Collects debug data if debug_collector is provided

        Args:
            map_id: ID of the map to assemble
            segments: List of RouteSegments in order
            route_geometry: Full route geometry as [(lat, lon), ...]
            route_total_km: Total route length in km
            debug_collector: Optional collector for POI debug data
            origin_city: Optional origin city name to filter out POIs

        Returns:
            Tuple of (num_map_segments_created, num_map_pois_created, poi_to_map_poi_mapping)
        """
        # Set main route geometry in debug collector if provided
        if debug_collector:
            debug_collector.set_main_route_geometry(route_geometry)

        # Step 1: Create MapSegment records
        map_segments = await self._create_map_segments(map_id, segments)
        logger.info(f"Created {len(map_segments)} MapSegment records for map {map_id}")

        # Step 2: Build segment lookup and aggregate search points
        segment_lookup = {s.id: s for s in segments}
        global_sps = self.junction_service.aggregate_search_points(
            map_segments, segment_lookup
        )
        logger.info(f"Aggregated {len(global_sps)} global search points")

        # Step 3: Collect all SegmentPOIs from all segments
        all_segment_pois: List[Tuple[SegmentPOI, MapSegment]] = []
        for map_segment in map_segments:
            segment_pois = await self.segment_poi_repo.get_by_segment_with_pois(
                map_segment.segment_id
            )
            for sp in segment_pois:
                all_segment_pois.append((sp, map_segment))

        logger.info(f"Found {len(all_segment_pois)} SegmentPOIs across all segments")

        # Step 4: Create MapPOI records with deduplication
        num_pois, poi_to_map_poi = await self._create_map_pois(
            map_id=map_id,
            segment_pois_with_map_segments=all_segment_pois,
            route_geometry=route_geometry,
            route_total_km=route_total_km,
            global_sps=global_sps,
            debug_collector=debug_collector,
            origin_city=origin_city,
        )

        return len(map_segments), num_pois, poi_to_map_poi

    async def _create_map_segments(
        self,
        map_id: UUID,
        segments: List[RouteSegment],
    ) -> List[MapSegment]:
        """
        Create MapSegment records linking segments to the map.

        Args:
            map_id: Map ID
            segments: List of RouteSegments in order

        Returns:
            List of created MapSegment records
        """
        map_segments = []
        cumulative_distance = Decimal("0.0")

        for i, segment in enumerate(segments):
            map_segment = MapSegment(
                map_id=map_id,
                segment_id=segment.id,
                sequence_order=i,
                distance_from_origin_km=cumulative_distance,
            )
            map_segments.append(map_segment)
            cumulative_distance += segment.length_km

        await self.map_segment_repo.bulk_create(map_segments)
        return map_segments

    async def _create_map_pois(
        self,
        map_id: UUID,
        segment_pois_with_map_segments: List[Tuple[SegmentPOI, MapSegment]],
        route_geometry: List[Tuple[float, float]],
        route_total_km: float,
        global_sps: List[GlobalSearchPoint],
        debug_collector: Optional[POIDebugDataCollector] = None,
        origin_city: Optional[str] = None,
    ) -> Tuple[int, Dict[str, UUID]]:
        """
        Create MapPOI records with junction calculation and deduplication.

        Args:
            map_id: Map ID
            segment_pois_with_map_segments: List of (SegmentPOI, MapSegment) tuples
            route_geometry: Full route geometry
            route_total_km: Total route length
            global_sps: Aggregated search points
            debug_collector: Optional collector for POI debug data
            origin_city: Optional origin city name to filter out POIs

        Returns:
            Tuple of (num_pois_created, poi_id_to_map_poi_id_mapping)
        """
        # Step 1: Collect unique POIs and enrich with city BEFORE junction calculation
        unique_pois: Dict[UUID, Tuple[POI, SegmentPOI, MapSegment]] = {}
        for segment_poi, map_segment in segment_pois_with_map_segments:
            poi = segment_poi.poi
            if not poi:
                continue
            # Keep first occurrence (will deduplicate later based on junction distance)
            if poi.id not in unique_pois:
                unique_pois[poi.id] = (poi, segment_poi, map_segment)

        # Enrich POIs without city via reverse geocoding
        pois_needing_city = [poi for poi, _, _ in unique_pois.values() if not poi.city]
        if pois_needing_city and self.junction_service.geo_provider:
            await self._enrich_pois_with_city(pois_needing_city)

        # Step 2: Filter out POIs in origin city and disabled POIs BEFORE junction calculation
        filtered_out_count = 0
        disabled_count = 0
        origin_city_lower = origin_city.lower().strip() if origin_city else None

        filtered_segment_pois: List[Tuple[SegmentPOI, MapSegment]] = []
        for segment_poi, map_segment in segment_pois_with_map_segments:
            poi = segment_poi.poi
            if not poi:
                continue

            # Check if POI is disabled
            if poi.is_disabled:
                if poi.id in unique_pois:
                    disabled_count += 1
                    del unique_pois[poi.id]
                    logger.debug(f"Filtering out disabled POI '{poi.name}'")
                continue

            # Check if POI is in origin city
            if origin_city_lower:
                poi_city = (poi.city or "").lower().strip()
                if poi_city and poi_city == origin_city_lower:
                    # Only count once per unique POI
                    if poi.id in unique_pois:
                        filtered_out_count += 1
                        del unique_pois[poi.id]
                    continue

            filtered_segment_pois.append((segment_poi, map_segment))

        if disabled_count > 0:
            logger.info(f"Filtered out {disabled_count} disabled POIs")
        if filtered_out_count > 0:
            logger.info(f"Filtered out {filtered_out_count} POIs in origin city '{origin_city}'")

        # Step 3: Calculate junctions only for filtered POIs
        best_junction_for_poi: Dict[UUID, Tuple[JunctionResult, SegmentPOI, MapSegment, POI]] = {}
        skipped_pois = 0

        for segment_poi, map_segment in filtered_segment_pois:
            poi = segment_poi.poi
            if not poi:
                continue

            # Calculate junction for this POI
            junction = await self.junction_service.calculate_junction(
                poi_lat=poi.latitude,
                poi_lon=poi.longitude,
                segment_poi=segment_poi,
                map_segment=map_segment,
                route_geometry=route_geometry,
                route_total_km=route_total_km,
                global_sps=global_sps,
            )

            # Skip POI if junction calculation failed
            if junction is None:
                skipped_pois += 1
                continue

            # Check if we already have a better junction for this POI
            if poi.id in best_junction_for_poi:
                existing_junction, _, _, _ = best_junction_for_poi[poi.id]
                # Keep the one with shorter access distance
                if junction.access_distance_km < existing_junction.access_distance_km:
                    best_junction_for_poi[poi.id] = (junction, segment_poi, map_segment, poi)
            else:
                best_junction_for_poi[poi.id] = (junction, segment_poi, map_segment, poi)

        if skipped_pois > 0:
            logger.info(f"Skipped {skipped_pois} POIs due to failed junction calculation")

        # Step 4: Create MapPOI records for best junctions
        map_pois = []
        poi_to_map_poi: Dict[str, UUID] = {}

        for poi_id, (junction, segment_poi, map_segment, poi) in best_junction_for_poi.items():
            map_poi = MapPOI(
                map_id=map_id,
                poi_id=poi_id,
                segment_poi_id=segment_poi.id,
                segment_index=map_segment.sequence_order,
                distance_from_origin_km=junction.junction_distance_km,
                distance_from_road_meters=junction.access_distance_km * 1000,
                side=junction.side,
                junction_distance_km=junction.junction_distance_km,
                junction_lat=junction.junction_lat,
                junction_lon=junction.junction_lon,
                requires_detour=junction.requires_detour,
                quality_score=poi.quality_score,
            )
            map_pois.append(map_poi)

            # Collect debug data if collector is provided
            if debug_collector:
                self._collect_debug_data(
                    debug_collector=debug_collector,
                    poi=poi,
                    junction=junction,
                    segment_poi=segment_poi,
                    map_segment=map_segment,
                    route_geometry=route_geometry,
                    global_sps=global_sps,
                )

        if map_pois:
            await self.map_poi_repo.bulk_create(map_pois)

        # Build the mapping after bulk_create (IDs are assigned)
        for map_poi in map_pois:
            poi_to_map_poi[str(map_poi.poi_id)] = map_poi.id

        logger.info(
            f"Created {len(map_pois)} MapPOI records "
            f"(deduplicated from {len(segment_pois_with_map_segments)} SegmentPOIs)"
        )

        return len(map_pois), poi_to_map_poi

    def _collect_debug_data(
        self,
        debug_collector: POIDebugDataCollector,
        poi: POI,
        junction: JunctionResult,
        segment_poi: SegmentPOI,
        map_segment: MapSegment,
        route_geometry: List[Tuple[float, float]],
        global_sps: List[GlobalSearchPoint],
    ) -> None:
        """
        Collect debug data for a POI.

        Args:
            debug_collector: The debug collector
            poi: POI model
            junction: Junction calculation result
            segment_poi: SegmentPOI association
            map_segment: MapSegment record
            route_geometry: Full route geometry
            global_sps: All global search points
        """
        try:
            # Find the search point that discovered this POI
            discovery_sp = None
            for sp in global_sps:
                if (sp.segment_id == segment_poi.segment_id and
                    sp.segment_sp_index == segment_poi.search_point_index):
                    discovery_sp = sp
                    break

            # Find lookback point
            poi_approx_distance_km = discovery_sp.distance_from_map_origin_km if discovery_sp else junction.junction_distance_km
            lookback_sp = self.junction_service.find_lookback_point(
                poi_approx_distance_km, global_sps
            )

            # Build side calculation data
            side_calculation = None
            if route_geometry and len(route_geometry) >= 2:
                # Find junction index in route
                junction_idx = 0
                best_dist = float('inf')
                from api.utils.geo_utils import calculate_distance_meters
                for i, point in enumerate(route_geometry):
                    dist = calculate_distance_meters(
                        junction.junction_lat, junction.junction_lon, point[0], point[1]
                    )
                    if dist < best_dist:
                        best_dist = dist
                        junction_idx = i

                # Get segment for direction calculation
                prev_idx = max(0, junction_idx - 1)
                next_idx = min(len(route_geometry) - 1, junction_idx + 1)

                if prev_idx != next_idx:
                    # Direction vector
                    dx = route_geometry[next_idx][1] - route_geometry[prev_idx][1]  # lon
                    dy = route_geometry[next_idx][0] - route_geometry[prev_idx][0]  # lat

                    # Vector from junction to POI
                    px = float(poi.longitude) - junction.junction_lon
                    py = float(poi.latitude) - junction.junction_lat

                    # Cross product
                    cross = dx * py - dy * px

                    side_calculation = {
                        "road_vector": {"dx": dx, "dy": dy},
                        "poi_vector": {"dx": px, "dy": py},
                        "cross_product": cross,
                        "segment_start": {
                            "lat": route_geometry[prev_idx][0],
                            "lon": route_geometry[prev_idx][1],
                        },
                        "segment_end": {
                            "lat": route_geometry[next_idx][0],
                            "lon": route_geometry[next_idx][1],
                        },
                        "resulting_side": junction.side,
                        "method": "cross_product",
                    }

            # Build lookback data
            lookback_data = None
            if discovery_sp and lookback_sp:
                lookback_data = {
                    "poi_distance_from_road_m": segment_poi.straight_line_distance_m,
                    "current_search_point_index": discovery_sp.segment_sp_index,
                    "lookback_index": lookback_sp.segment_sp_index if lookback_sp else None,
                    "lookback_km": self.junction_service.DEFAULT_LOOKBACK_KM,
                    "lookback_distance_km": lookback_sp.distance_from_map_origin_km if lookback_sp else 0.0,
                    "lookback_point": {
                        "lat": lookback_sp.lat if lookback_sp else 0.0,
                        "lon": lookback_sp.lon if lookback_sp else 0.0,
                    },
                    "search_point": {
                        "lat": discovery_sp.lat,
                        "lon": discovery_sp.lon,
                    },
                    "search_point_distance_km": discovery_sp.distance_from_map_origin_km,
                    "lookback_count_setting": 10,  # Default lookback in search points
                    "lookback_method": "search_point",
                }

            # Build junction calculation data
            junction_calculation = {
                "method": "segment_based",
                "junction_distance_km": junction.junction_distance_km,
                "access_route_total_km": junction.access_distance_km,
            }

            # Use access route geometry from junction calculation
            access_route_geometry = None
            if junction.access_route_geometry:
                # Convert tuples to lists for JSON serialization
                access_route_geometry = [
                    [coord[0], coord[1]] for coord in junction.access_route_geometry
                ]

            debug_collector.collect_poi_data(
                poi_id=str(poi.id),  # Use POI ID as string for consistency
                poi_name=poi.name or "Sem nome",
                poi_type=poi.type or "unknown",
                poi_lat=float(poi.latitude),
                poi_lon=float(poi.longitude),
                distance_from_road_m=segment_poi.straight_line_distance_m,
                final_side=junction.side,
                requires_detour=junction.requires_detour,
                junction_lat=junction.junction_lat,
                junction_lon=junction.junction_lon,
                junction_distance_km=junction.junction_distance_km,
                access_route_geometry=access_route_geometry,
                access_route_distance_km=junction.access_distance_km,
                side_calculation=side_calculation,
                lookback_data=lookback_data,
                junction_calculation=junction_calculation,
            )

        except Exception as e:
            logger.warning(f"Failed to collect debug data for POI {poi.name}: {e}")

    async def recalculate_distances(self, map_id: UUID) -> int:
        """
        Recalculate distance_from_origin for all POIs in a map.

        This is useful after modifying the route or segment order.

        Args:
            map_id: Map ID

        Returns:
            Number of POIs updated
        """
        # Get all MapPOIs ordered by current distance
        map_pois = await self.map_poi_repo.get_pois_for_map(map_id)

        # Get MapSegments to calculate proper distances
        map_segments = await self.map_segment_repo.get_by_map(map_id)
        segment_distances = {
            ms.segment_id: float(ms.distance_from_origin_km)
            for ms in map_segments
        }

        updated_count = 0
        for map_poi in map_pois:
            # Get the segment this POI belongs to
            segment_poi = await self.segment_poi_repo.get_by_id(map_poi.segment_poi_id)
            if not segment_poi:
                continue

            # Calculate new distance based on segment position + search point offset
            segment_start_km = segment_distances.get(segment_poi.segment_id, 0)
            # Approximate POI distance based on search point index
            poi_offset_km = segment_poi.search_point_index * 1.0  # 1km per search point

            new_distance = segment_start_km + poi_offset_km

            if abs(map_poi.distance_from_origin_km - new_distance) > 0.01:
                map_poi.distance_from_origin_km = new_distance
                updated_count += 1

        if updated_count > 0:
            await self.session.flush()

        return updated_count

    async def order_pois_by_distance(self, map_id: UUID) -> List[MapPOI]:
        """
        Get all POIs for a map ordered by distance from origin.

        Args:
            map_id: Map ID

        Returns:
            List of MapPOI records ordered by distance
        """
        return await self.map_poi_repo.get_pois_for_map(map_id, include_poi_details=True)

    async def get_map_statistics(self, map_id: UUID) -> Dict:
        """
        Get statistics about a map's segments and POIs.

        Args:
            map_id: Map ID

        Returns:
            Dictionary with statistics
        """
        num_segments = await self.map_segment_repo.count_by_map(map_id)
        total_distance = await self.map_segment_repo.get_total_distance_for_map(map_id)

        map_pois = await self.map_poi_repo.get_pois_for_map(map_id, include_poi_details=True)

        # Count POIs by type
        poi_counts = {}
        for map_poi in map_pois:
            poi_type = map_poi.poi.type if map_poi.poi else "unknown"
            poi_counts[poi_type] = poi_counts.get(poi_type, 0) + 1

        # Count POIs by side
        side_counts = {"left": 0, "right": 0, "center": 0}
        for map_poi in map_pois:
            side_counts[map_poi.side] = side_counts.get(map_poi.side, 0) + 1

        return {
            "num_segments": num_segments,
            "total_distance_km": total_distance,
            "num_pois": len(map_pois),
            "pois_by_type": poi_counts,
            "pois_by_side": side_counts,
        }

    async def _enrich_pois_with_city(self, pois: List[POI]) -> None:
        """
        Enrich POIs with city information via reverse geocoding.

        This method is called only for POIs that:
        1. Don't already have city information
        2. Will actually appear in the final map (after deduplication)

        Args:
            pois: List of POI models that need city enrichment
        """
        geo_provider = self.junction_service.geo_provider
        if not geo_provider:
            return

        enriched_count = 0
        for poi in pois:
            try:
                reverse_loc = await geo_provider.reverse_geocode(
                    float(poi.latitude),
                    float(poi.longitude),
                    poi_name=poi.name,
                )
                if reverse_loc and reverse_loc.city:
                    poi.city = reverse_loc.city
                    enriched_count += 1
            except Exception as e:
                logger.debug(f"Reverse geocoding failed for POI {poi.name}: {e}")

        if enriched_count > 0:
            logger.info(f"Enriched {enriched_count}/{len(pois)} POIs with city information")

    async def get_segments_for_response(self, map_id: UUID) -> List[MapSegmentResponse]:
        """
        Get segments for a map formatted as MapSegmentResponse objects.

        This method retrieves MapSegments with their RouteSegments and builds
        the response objects with geometry and distance_from_origin_km.

        Args:
            map_id: ID of the map

        Returns:
            List of MapSegmentResponse objects with full geometry and distances
        """
        map_segments = await self.map_segment_repo.get_by_map_with_segments(map_id)

        segments_response = []
        for ms in map_segments:
            segment = ms.segment
            if segment is None:
                continue

            # Convert geometry from [[lat, lon], ...] to List[Coordinates]
            geometry_coords = []
            if segment.geometry:
                for point in segment.geometry:
                    if isinstance(point, (list, tuple)) and len(point) >= 2:
                        geometry_coords.append(
                            Coordinates(latitude=point[0], longitude=point[1])
                        )

            segments_response.append(
                MapSegmentResponse(
                    id=str(segment.id),
                    sequence_order=ms.sequence_order,
                    distance_from_origin_km=float(ms.distance_from_origin_km),
                    length_km=float(segment.length_km),
                    geometry=geometry_coords,
                    road_name=segment.road_name,
                    start_lat=float(segment.start_lat),
                    start_lon=float(segment.start_lon),
                    end_lat=float(segment.end_lat),
                    end_lon=float(segment.end_lon),
                )
            )

        return segments_response
