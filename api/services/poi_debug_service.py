"""
POI Debug Service for collecting and persisting POI calculation debug data.

This service is responsible for:
- Collecting debug data during POI calculation
- Persisting debug data to the database
- Checking if debug mode is enabled via system settings
"""
import logging
from typing import Dict, List, Optional, Any, Tuple
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from api.database.models.poi_debug_data import POIDebugData
from api.database.repositories.poi_debug_data import POIDebugDataRepository
from api.database.repositories.system_settings import SystemSettingsRepository

logger = logging.getLogger(__name__)


class POIDebugDataCollector:
    """
    Collects debug data during POI calculation.

    This is an in-memory collector that stores debug information
    for each POI as it's being processed. The data is indexed
    by the milestone ID (which corresponds to the POI ID).
    """

    def __init__(self):
        """Initialize the collector."""
        # Key: milestone/poi ID (str), Value: debug data dict
        self._data: Dict[str, Dict[str, Any]] = {}
        self._main_route_geometry: Optional[List[Tuple[float, float]]] = None

    def set_main_route_geometry(self, geometry: List[Tuple[float, float]]) -> None:
        """
        Store the main route geometry for later use.

        Args:
            geometry: List of (lat, lon) tuples representing the main route
        """
        self._main_route_geometry = geometry

    def collect_poi_data(
        self,
        poi_id: str,
        poi_name: str,
        poi_type: str,
        poi_lat: float,
        poi_lon: float,
        distance_from_road_m: float,
        final_side: str,
        requires_detour: bool = False,
        junction_lat: Optional[float] = None,
        junction_lon: Optional[float] = None,
        junction_distance_km: Optional[float] = None,
        access_route_geometry: Optional[List[List[float]]] = None,
        access_route_distance_km: Optional[float] = None,
        side_calculation: Optional[Dict[str, Any]] = None,
        lookback_data: Optional[Dict[str, Any]] = None,
        recalculation_history: Optional[List[Dict[str, Any]]] = None,
    ) -> None:
        """
        Collect debug data for a POI.

        Args:
            poi_id: Unique POI identifier
            poi_name: POI name
            poi_type: POI type (gas_station, restaurant, etc.)
            poi_lat: POI latitude
            poi_lon: POI longitude
            distance_from_road_m: Distance from POI to road in meters
            final_side: Final determined side (left/right/center)
            requires_detour: Whether this POI requires a detour
            junction_lat: Junction point latitude (if applicable)
            junction_lon: Junction point longitude (if applicable)
            junction_distance_km: Distance to junction from origin
            access_route_geometry: Route geometry from junction to POI
            access_route_distance_km: Distance of access route
            side_calculation: Side calculation details (vectors, cross product)
            lookback_data: Lookback calculation details
            recalculation_history: History of recalculation attempts
        """
        # Extract main route segment near the POI (±50 points)
        main_route_segment = None
        segment_start_idx = None
        segment_end_idx = None

        if self._main_route_geometry and junction_lat and junction_lon:
            segment_start_idx, segment_end_idx, main_route_segment = (
                self._extract_route_segment_near_point(
                    junction_lat, junction_lon, points_before=50, points_after=50
                )
            )

        self._data[poi_id] = {
            "poi_name": poi_name,
            "poi_type": poi_type,
            "poi_lat": poi_lat,
            "poi_lon": poi_lon,
            "distance_from_road_m": distance_from_road_m,
            "final_side": final_side,
            "requires_detour": requires_detour,
            "junction_lat": junction_lat,
            "junction_lon": junction_lon,
            "junction_distance_km": junction_distance_km,
            "main_route_segment": main_route_segment,
            "segment_start_idx": segment_start_idx,
            "segment_end_idx": segment_end_idx,
            "access_route_geometry": access_route_geometry,
            "access_route_distance_km": access_route_distance_km,
            "side_calculation": side_calculation,
            "lookback_data": lookback_data,
            "recalculation_history": recalculation_history,
        }

    def _extract_route_segment_near_point(
        self,
        lat: float,
        lon: float,
        points_before: int = 50,
        points_after: int = 50
    ) -> Tuple[Optional[int], Optional[int], Optional[List[List[float]]]]:
        """
        Extract a segment of the main route near a given point.

        Returns:
            Tuple of (start_idx, end_idx, segment_as_list)
        """
        if not self._main_route_geometry:
            return None, None, None

        # Find closest point index
        min_distance = float('inf')
        closest_idx = 0

        for i, (pt_lat, pt_lon) in enumerate(self._main_route_geometry):
            # Simple Euclidean distance (good enough for nearby points)
            dist = ((pt_lat - lat) ** 2 + (pt_lon - lon) ** 2) ** 0.5
            if dist < min_distance:
                min_distance = dist
                closest_idx = i

        # Extract segment
        start_idx = max(0, closest_idx - points_before)
        end_idx = min(len(self._main_route_geometry), closest_idx + points_after + 1)

        segment = [
            [pt[0], pt[1]]
            for pt in self._main_route_geometry[start_idx:end_idx]
        ]

        return start_idx, end_idx, segment

    def add_recalculation_attempt(
        self,
        poi_id: str,
        attempt: int,
        search_point: Tuple[float, float],
        search_point_distance_km: float,
        junction_found: bool,
        junction_distance_km: Optional[float] = None,
        access_route_distance_km: Optional[float] = None,
        improvement: bool = False,
        reason: Optional[str] = None
    ) -> None:
        """
        Add a recalculation attempt to the POI's history.

        Args:
            poi_id: POI identifier
            attempt: Attempt number
            search_point: Search point coordinates (lat, lon)
            search_point_distance_km: Distance of search point from origin
            junction_found: Whether a junction was found
            junction_distance_km: Junction distance if found
            access_route_distance_km: Access route distance if found
            improvement: Whether this attempt improved on previous
            reason: Reason for skipping or failure
        """
        if poi_id not in self._data:
            return

        if self._data[poi_id].get("recalculation_history") is None:
            self._data[poi_id]["recalculation_history"] = []

        self._data[poi_id]["recalculation_history"].append({
            "attempt": attempt,
            "search_point": {"lat": search_point[0], "lon": search_point[1]},
            "search_point_distance_km": search_point_distance_km,
            "junction_found": junction_found,
            "junction_distance_km": junction_distance_km,
            "access_route_distance_km": access_route_distance_km,
            "improvement": improvement,
            "reason": reason,
        })

    def get_all_data(self) -> Dict[str, Dict[str, Any]]:
        """Get all collected debug data."""
        return self._data

    def get_poi_data(self, poi_id: str) -> Optional[Dict[str, Any]]:
        """Get debug data for a specific POI."""
        return self._data.get(poi_id)

    def clear(self) -> None:
        """Clear all collected data."""
        self._data.clear()
        self._main_route_geometry = None


class POIDebugService:
    """
    Service for managing POI debug data.

    Handles checking if debug is enabled and persisting debug data.
    """

    def __init__(self, session: AsyncSession):
        """
        Initialize the debug service.

        Args:
            session: SQLAlchemy async session
        """
        self.session = session
        self._debug_repo = POIDebugDataRepository(session)
        self._settings_repo = SystemSettingsRepository(session)

    async def is_debug_enabled(self) -> bool:
        """
        Check if POI debug collection is enabled in system settings.

        Returns:
            True if debug is enabled, False otherwise
        """
        value = await self._settings_repo.get_value("poi_debug_enabled", "true")
        return value.lower() == "true"

    async def persist_debug_data(
        self,
        map_id: UUID,
        poi_id_to_map_poi_id: Dict[str, UUID],
        collector: POIDebugDataCollector
    ) -> int:
        """
        Persist collected debug data to the database.

        Args:
            map_id: The map UUID
            poi_id_to_map_poi_id: Mapping from POI ID to MapPOI UUID
            collector: The debug data collector with collected data

        Returns:
            Number of debug entries created
        """
        debug_data = collector.get_all_data()

        if not debug_data:
            logger.info("No debug data to persist")
            return 0

        entries = []

        for poi_id, data in debug_data.items():
            map_poi_id = poi_id_to_map_poi_id.get(poi_id)

            if not map_poi_id:
                logger.warning(f"No MapPOI ID found for POI {poi_id}, skipping debug data")
                continue

            entry = POIDebugData(
                map_id=map_id,
                map_poi_id=map_poi_id,
                poi_name=data["poi_name"],
                poi_type=data["poi_type"],
                poi_lat=data["poi_lat"],
                poi_lon=data["poi_lon"],
                main_route_segment=data.get("main_route_segment"),
                segment_start_idx=data.get("segment_start_idx"),
                segment_end_idx=data.get("segment_end_idx"),
                junction_lat=data.get("junction_lat"),
                junction_lon=data.get("junction_lon"),
                junction_distance_km=data.get("junction_distance_km"),
                access_route_geometry=data.get("access_route_geometry"),
                access_route_distance_km=data.get("access_route_distance_km"),
                side_calculation=data.get("side_calculation"),
                lookback_data=data.get("lookback_data"),
                recalculation_history=data.get("recalculation_history"),
                final_side=data["final_side"],
                requires_detour=data.get("requires_detour", False),
                distance_from_road_m=data["distance_from_road_m"],
            )
            entries.append(entry)

        if entries:
            await self._debug_repo.bulk_create(entries)
            logger.info(f"Persisted {len(entries)} POI debug entries for map {map_id}")

        return len(entries)

    async def delete_debug_data_for_map(self, map_id: UUID) -> int:
        """
        Delete all debug data for a map (used when regenerating).

        Args:
            map_id: The map UUID

        Returns:
            Number of entries deleted
        """
        count = await self._debug_repo.delete_by_map(map_id)
        logger.info(f"Deleted {count} debug entries for map {map_id}")
        return count

    async def has_debug_data(self, map_id: UUID) -> bool:
        """
        Check if a map has any debug data.

        Args:
            map_id: The map UUID

        Returns:
            True if the map has debug data
        """
        return await self._debug_repo.has_debug_data(map_id)
