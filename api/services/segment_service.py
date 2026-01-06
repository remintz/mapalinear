"""
Segment Service - Manages reusable route segments.

This service handles:
- Creating and reusing route segments from OSRM steps
- Generating search points for POI discovery
- Calculating segment hashes for deduplication
- Associating POIs with segments
"""

import hashlib
import logging
from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Optional, Tuple
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from api.database.models.route_segment import RouteSegment
from api.database.models.segment_poi import SegmentPOI
from api.database.repositories.route_segment import RouteSegmentRepository
from api.database.repositories.segment_poi import SegmentPOIRepository
from api.providers.models import RouteStep
from api.utils.geo_utils import calculate_distance_meters

logger = logging.getLogger(__name__)


class SegmentService:
    """
    Service for managing reusable route segments.

    Route segments are identified by a hash of their start and end coordinates,
    allowing them to be reused across multiple maps. Each segment has pre-computed
    search points for efficient POI discovery.
    """

    # Minimum segment length in km to generate search points
    MIN_SEGMENT_LENGTH_FOR_SEARCH_KM = 1.0

    # Search point interval in km
    SEARCH_POINT_INTERVAL_KM = 1.0

    def __init__(self, session: AsyncSession):
        """
        Initialize the Segment Service.

        Args:
            session: SQLAlchemy async session
        """
        self.session = session
        self.segment_repo = RouteSegmentRepository(session)
        self.segment_poi_repo = SegmentPOIRepository(session)

    @staticmethod
    def calculate_segment_hash(
        start_lat: float,
        start_lon: float,
        end_lat: float,
        end_lon: float,
    ) -> str:
        """
        Calculate a unique hash for a segment based on coordinates.

        Uses 4 decimal places (~11m precision) as per PRD specification.

        Args:
            start_lat: Start latitude
            start_lon: Start longitude
            end_lat: End latitude
            end_lon: End longitude

        Returns:
            MD5 hash string (32 characters)
        """
        # Round to 4 decimal places for ~11m precision
        coords_str = (
            f"{start_lat:.4f},{start_lon:.4f}|{end_lat:.4f},{end_lon:.4f}"
        )
        return hashlib.md5(coords_str.encode()).hexdigest()

    @staticmethod
    def generate_search_points(
        geometry: List[Tuple[float, float]],
        length_km: float,
    ) -> List[dict]:
        """
        Generate search points for a segment.

        Search points are generated every SEARCH_POINT_INTERVAL_KM along the segment.
        Only segments >= MIN_SEGMENT_LENGTH_FOR_SEARCH_KM get search points.

        Args:
            geometry: List of (lat, lon) coordinates
            length_km: Total segment length in km

        Returns:
            List of search point dicts with:
            - index: Sequential index of the search point
            - lat: Latitude
            - lon: Longitude
            - distance_from_segment_start_km: Distance from segment start
        """
        if length_km < SegmentService.MIN_SEGMENT_LENGTH_FOR_SEARCH_KM:
            return []

        if not geometry or len(geometry) < 2:
            return []

        search_points = []
        interval_km = SegmentService.SEARCH_POINT_INTERVAL_KM

        # Calculate cumulative distances for each geometry point
        cumulative_distances = [0.0]
        for i in range(1, len(geometry)):
            prev_lat, prev_lon = geometry[i - 1]
            curr_lat, curr_lon = geometry[i]
            distance_m = calculate_distance_meters(
                prev_lat, prev_lon, curr_lat, curr_lon
            )
            cumulative_distances.append(
                cumulative_distances[-1] + distance_m / 1000.0
            )

        # Generate search points at regular intervals
        target_distance = 0.0
        sp_index = 0

        while target_distance <= length_km:
            # Find the geometry point just before this distance
            point_coords = SegmentService._interpolate_point_at_distance(
                geometry, cumulative_distances, target_distance
            )

            if point_coords:
                search_points.append({
                    "index": sp_index,
                    "lat": point_coords[0],
                    "lon": point_coords[1],
                    "distance_from_segment_start_km": round(target_distance, 3),
                })
                sp_index += 1

            target_distance += interval_km

        return search_points

    @staticmethod
    def _interpolate_point_at_distance(
        geometry: List[Tuple[float, float]],
        cumulative_distances: List[float],
        target_distance_km: float,
    ) -> Optional[Tuple[float, float]]:
        """
        Find the coordinates at a specific distance along the geometry.

        Args:
            geometry: List of (lat, lon) coordinates
            cumulative_distances: Cumulative distances for each point
            target_distance_km: Target distance from start

        Returns:
            (lat, lon) tuple or None if not found
        """
        if target_distance_km <= 0:
            return geometry[0]

        if target_distance_km >= cumulative_distances[-1]:
            return geometry[-1]

        # Find the segment containing the target distance
        for i in range(1, len(cumulative_distances)):
            if cumulative_distances[i] >= target_distance_km:
                # Interpolate between points i-1 and i
                prev_dist = cumulative_distances[i - 1]
                curr_dist = cumulative_distances[i]
                segment_length = curr_dist - prev_dist

                if segment_length <= 0:
                    return geometry[i - 1]

                fraction = (target_distance_km - prev_dist) / segment_length

                prev_lat, prev_lon = geometry[i - 1]
                curr_lat, curr_lon = geometry[i]

                interp_lat = prev_lat + fraction * (curr_lat - prev_lat)
                interp_lon = prev_lon + fraction * (curr_lon - prev_lon)

                return (interp_lat, interp_lon)

        return geometry[-1]

    async def get_or_create_segment(
        self, step: RouteStep
    ) -> Tuple[RouteSegment, bool]:
        """
        Get an existing segment or create a new one from a RouteStep.

        If a segment with the same hash exists, it is returned and its usage
        count is incremented. Otherwise, a new segment is created.

        Args:
            step: RouteStep from OSRM

        Returns:
            Tuple of (RouteSegment, is_new) where is_new is True if created
        """
        start_coords = step.start_coords
        end_coords = step.end_coords

        # Calculate hash
        segment_hash = self.calculate_segment_hash(
            start_coords[0], start_coords[1],
            end_coords[0], end_coords[1]
        )

        # Try to find existing segment
        existing = await self.segment_repo.get_by_hash(segment_hash)
        if existing:
            await self.segment_repo.increment_usage_count(existing.id)
            return existing, False

        # Generate search points
        length_km = step.distance_km
        search_points = self.generate_search_points(step.geometry, length_km)

        # Create new segment
        segment = RouteSegment(
            segment_hash=segment_hash,
            start_lat=Decimal(str(start_coords[0])),
            start_lon=Decimal(str(start_coords[1])),
            end_lat=Decimal(str(end_coords[0])),
            end_lon=Decimal(str(end_coords[1])),
            road_name=step.road_name or None,
            length_km=Decimal(str(length_km)),
            geometry=list(step.geometry),
            search_points=search_points,
            osrm_instruction=None,  # Can be populated from maneuver if needed
            osrm_maneuver_type=step.maneuver_type,
            usage_count=1,
            pois_fetched_at=None,
        )

        created_segment = await self.segment_repo.create(segment)
        return created_segment, True

    async def bulk_get_or_create_segments(
        self, steps: List[RouteStep]
    ) -> List[Tuple[RouteSegment, bool]]:
        """
        Process multiple steps and get or create segments for each.

        Args:
            steps: List of RouteSteps from OSRM

        Returns:
            List of (RouteSegment, is_new) tuples in same order as input
        """
        results = []

        # Calculate all hashes first
        hashes = []
        for step in steps:
            start = step.start_coords
            end = step.end_coords
            hash_val = self.calculate_segment_hash(
                start[0], start[1], end[0], end[1]
            )
            hashes.append(hash_val)

        # Bulk fetch existing segments
        existing_segments = await self.segment_repo.bulk_get_by_hashes(hashes)

        # Process each step
        for i, step in enumerate(steps):
            hash_val = hashes[i]

            if hash_val in existing_segments:
                segment = existing_segments[hash_val]
                await self.segment_repo.increment_usage_count(segment.id)
                results.append((segment, False))
            else:
                segment, is_new = await self.get_or_create_segment(step)
                results.append((segment, is_new))
                # Add to existing_segments to handle duplicate steps
                existing_segments[hash_val] = segment

        return results

    async def associate_pois_to_segment(
        self,
        segment: RouteSegment,
        pois_with_discovery_data: List[Tuple[UUID, int, int]],
    ) -> List[SegmentPOI]:
        """
        Create SegmentPOI associations for POIs found in a segment.

        Args:
            segment: The RouteSegment
            pois_with_discovery_data: List of tuples:
                - poi_id: UUID of the POI
                - search_point_index: Index of search point that found this POI
                - straight_line_distance_m: Distance from search point to POI

        Returns:
            List of created SegmentPOI records
        """
        if not pois_with_discovery_data:
            return []

        segment_pois = []
        for poi_id, sp_index, distance_m in pois_with_discovery_data:
            # Check if association already exists
            exists = await self.segment_poi_repo.exists_for_segment_poi(
                segment.id, poi_id
            )
            if exists:
                continue

            segment_poi = SegmentPOI(
                segment_id=segment.id,
                poi_id=poi_id,
                search_point_index=sp_index,
                straight_line_distance_m=distance_m,
            )
            segment_pois.append(segment_poi)

        if segment_pois:
            await self.segment_poi_repo.bulk_create(segment_pois)

        # Mark segment as having POIs fetched
        await self.segment_repo.mark_pois_fetched(segment.id)

        return segment_pois

    async def get_segment_pois(
        self, segment_id: UUID
    ) -> List[SegmentPOI]:
        """
        Get all POI associations for a segment.

        Args:
            segment_id: Segment UUID

        Returns:
            List of SegmentPOI records with POI data loaded
        """
        return await self.segment_poi_repo.get_by_segment_with_pois(segment_id)

    async def needs_poi_search(self, segment: RouteSegment) -> bool:
        """
        Check if a segment needs POI search.

        A segment needs POI search if:
        - It has never had POIs fetched (pois_fetched_at is None)
        - It is long enough to have search points (>= 1km)

        Args:
            segment: RouteSegment to check

        Returns:
            True if segment needs POI search
        """
        if segment.pois_fetched_at is not None:
            return False

        return float(segment.length_km) >= self.MIN_SEGMENT_LENGTH_FOR_SEARCH_KM
