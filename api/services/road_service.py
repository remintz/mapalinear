"""
Road Service - Main orchestrator for linear map generation.

This service coordinates the generation of linear maps by delegating to
specialized services for each step of the process:
- RouteSegmentationService: Route processing and segmentation
- POISearchService: POI discovery and junction calculation
- MilestoneFactory: Milestone creation and enrichment
- RouteStatisticsService: Route statistics and recommendations
"""

import logging
from typing import Any, Callable, Dict, List, Optional, Tuple

from api.models.road_models import (
    LinearMapResponse,
    LinearRoadSegment,
    RoadMilestone,
    RoadMilestoneResponse,
    RouteStatisticsResponse,
    POIStatistics,
    RouteStopRecommendation,
)
from api.providers.base import GeoProvider, ProviderType
from api.providers.models import GeoLocation, Route, POICategory
from api.providers.settings import get_settings
from api.services.milestone_factory import MilestoneFactory
from api.services.poi_debug_service import POIDebugDataCollector
from api.services.poi_quality_service import POIQualityService
from api.services.poi_search_service import POISearchService
from api.services.route_segmentation_service import RouteSegmentationService
from api.utils.async_utils import run_async_safe
from api.utils.geo_utils import calculate_distance_meters

logger = logging.getLogger(__name__)


def _is_debug_enabled_sync() -> bool:
    """
    Check if POI debug is enabled (sync version for use in generate_linear_map).
    Uses synchronous psycopg2 to avoid event loop conflicts.
    """
    import psycopg2

    settings = get_settings()

    try:
        conn = psycopg2.connect(
            host=settings.postgres_host,
            port=settings.postgres_port,
            database=settings.postgres_database,
            user=settings.postgres_user,
            password=settings.postgres_password,
        )
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT value FROM system_settings WHERE key = 'poi_debug_enabled'"
                )
                row = cur.fetchone()
                if row:
                    return row[0].lower() == "true"
                # Default to true if setting doesn't exist
                return True
        finally:
            conn.close()
    except Exception as e:
        logger.warning(f"Error checking debug config: {e}")
        # Default to true on error
        return True


class RoadService:
    """
    Main service for generating linear maps of routes.

    This class acts as an orchestrator, coordinating specialized services
    to produce complete linear map representations of road routes.
    """

    def __init__(
        self,
        geo_provider: Optional[GeoProvider] = None,
        poi_provider: Optional[GeoProvider] = None,
        segmentation_service: Optional[RouteSegmentationService] = None,
        poi_search_service: Optional[POISearchService] = None,
        milestone_factory: Optional[MilestoneFactory] = None,
        quality_service: Optional[POIQualityService] = None,
    ):
        """
        Initialize RoadService with geographic data providers and services.

        Args:
            geo_provider: Provider for routing/geocoding (always OSM if not specified)
            poi_provider: Provider for POI search (configured via POI_PROVIDER env var)
            segmentation_service: Service for route segmentation (optional)
            poi_search_service: Service for POI search (optional)
            milestone_factory: Factory for milestone creation (optional)
            quality_service: Service for POI quality (optional)
        """
        from ..providers import create_provider

        settings = get_settings()

        # Route provider - always OSM for now
        if geo_provider is None:
            geo_provider = create_provider(ProviderType.OSM)
        self.geo_provider = geo_provider

        # POI provider - configurable via POI_PROVIDER
        if poi_provider is None:
            poi_provider_type = ProviderType(settings.poi_provider.lower())
            poi_provider = create_provider(poi_provider_type)
        self.poi_provider = poi_provider

        # Initialize services with lazy loading
        self._segmentation_service = segmentation_service
        self._quality_service = quality_service
        self._milestone_factory = milestone_factory
        self._poi_search_service = poi_search_service

        logger.info(
            f"RoadService initialized - Route: OSM, POI: {settings.poi_provider.upper()}"
        )

    @property
    def segmentation_service(self) -> RouteSegmentationService:
        """Get or create the segmentation service."""
        if self._segmentation_service is None:
            self._segmentation_service = RouteSegmentationService()
        return self._segmentation_service

    @property
    def quality_service(self) -> POIQualityService:
        """Get or create the quality service."""
        if self._quality_service is None:
            self._quality_service = POIQualityService()
        return self._quality_service

    @property
    def milestone_factory(self) -> MilestoneFactory:
        """Get or create the milestone factory."""
        if self._milestone_factory is None:
            self._milestone_factory = MilestoneFactory(
                geo_provider=self.geo_provider,
                quality_service=self.quality_service,
            )
        return self._milestone_factory

    @property
    def poi_search_service(self) -> POISearchService:
        """Get or create the POI search service."""
        if self._poi_search_service is None:
            self._poi_search_service = POISearchService(
                geo_provider=self.geo_provider,
                poi_provider=self.poi_provider,
                milestone_factory=self.milestone_factory,
                quality_service=self.quality_service,
            )
        return self._poi_search_service

    # ========================================================================
    # UTILITY METHODS
    # ========================================================================

    def _extract_city_name(self, location_string: str) -> str:
        """
        Extract city name from location string.

        Args:
            location_string: Location in format "City, State" (e.g., "Belo Horizonte, MG")

        Returns:
            City name (e.g., "Belo Horizonte")
        """
        return (
            location_string.split(",")[0].strip()
            if "," in location_string
            else location_string.strip()
        )

    def _geocode_and_validate(
        self, address: str, address_type: str = "location"
    ) -> GeoLocation:
        """
        Geocode an address and validate the result.

        Args:
            address: Address string to geocode
            address_type: Type of address for error messages

        Returns:
            GeoLocation object

        Raises:
            ValueError: If geocoding fails
        """
        logger.info(f"Geocoding {address_type}: {address}")
        location = run_async_safe(self.geo_provider.geocode(address))

        if not location:
            raise ValueError(f"Could not geocode {address_type}: {address}")

        logger.info(
            f"{address_type.capitalize()}: {address} -> "
            f"lat={location.latitude:.6f}, lon={location.longitude:.6f}"
        )

        return location

    def _log_route_info(self, route: Route):
        """Log detailed route information."""
        logger.info(f"Route calculated:")
        logger.info(f"  - Total distance: {route.total_distance:.1f} km")
        logger.info(f"  - Road names: {route.road_names}")
        logger.info(f"  - Geometry points: {len(route.geometry)}")

        if route.geometry:
            logger.info(
                f"  - First point: lat={route.geometry[0][0]:.6f}, "
                f"lon={route.geometry[0][1]:.6f}"
            )
            logger.info(
                f"  - Last point: lat={route.geometry[-1][0]:.6f}, "
                f"lon={route.geometry[-1][1]:.6f}"
            )

    def _log_milestone_statistics(self, milestones: List[RoadMilestone]):
        """Log statistics about found milestones."""
        milestones_with_city = len([m for m in milestones if m.city])
        logger.info(f"Milestones with city: {milestones_with_city}/{len(milestones)}")

        for milestone in milestones:
            city_info = f" ({milestone.city})" if milestone.city else ""
            logger.info(
                f"Milestone: {milestone.name}{city_info} "
                f"({milestone.type.value}) - dist={milestone.distance_from_origin_km:.1f}km"
            )

    # ========================================================================
    # MAIN PUBLIC METHODS
    # ========================================================================

    def generate_linear_map(
        self,
        origin: str,
        destination: str,
        road_id: Optional[str] = None,
        include_cities: bool = True,
        max_distance_from_road: float = 3000,
        max_detour_distance_km: float = 5.0,
        min_distance_from_origin_km: float = 0.0,  # Deprecated
        progress_callback: Optional[Callable[[float], None]] = None,
        segment_length_km: float = 1.0,
        user_id: Optional[str] = None,
    ) -> LinearMapResponse:
        """
        Generate a linear map of a route between origin and destination.

        This method:
        1. Geocodes origin and destination
        2. Calculates the route
        3. Processes route into linear segments
        4. Finds POI milestones along the route
        5. Assigns milestones to segments
        6. Enriches with Google Places data
        7. Optionally enriches with HERE data

        Args:
            origin: Starting point address
            destination: End point address
            road_id: Optional road identifier
            include_cities: Whether to include city markers
            max_distance_from_road: Maximum POI search radius in meters
            max_detour_distance_km: Maximum detour distance for distant POIs
            min_distance_from_origin_km: DEPRECATED - No longer used
            progress_callback: Callback for progress updates (0-100)
            segment_length_km: Target length for each segment
            user_id: Optional user ID to associate the map with

        Returns:
            LinearMapResponse with segments and milestones
        """
        logger.info(f"Starting linear map generation: {origin} -> {destination}")

        # Extract origin city for POI filtering
        origin_city = self._extract_city_name(origin)
        logger.info(f"Origin city extracted: {origin_city}")

        # Step 1: Geocode origin and destination
        origin_location = self._geocode_and_validate(origin, "origin")
        destination_location = self._geocode_and_validate(destination, "destination")

        # Step 2: Calculate route
        logger.info("Calculating route...")
        route = run_async_safe(
            self.geo_provider.calculate_route(origin_location, destination_location)
        )

        if not route:
            raise ValueError(f"Could not calculate route from {origin} to {destination}")

        self._log_route_info(route)

        # Step 3: Process route into linear segments
        linear_segments = self.segmentation_service.process_route_into_segments(
            route, segment_length_km
        )

        # Step 4: Find milestones along the route
        milestone_categories = self.milestone_factory.build_milestone_categories(
            include_cities
        )

        logger.info(
            f"Milestone categories requested: {[cat.value for cat in milestone_categories]}"
        )

        # Check if debug is enabled and create collector
        debug_collector: Optional[POIDebugDataCollector] = None
        try:
            if _is_debug_enabled_sync():
                debug_collector = POIDebugDataCollector()
                debug_collector.set_main_route_geometry(route.geometry)
                logger.info("POI debug enabled - collecting calculation data")
        except Exception as e:
            logger.warning(f"Error checking debug config: {e}")

        all_milestones = run_async_safe(
            self.poi_search_service.find_milestones(
                segments=linear_segments,
                categories=milestone_categories,
                max_distance_from_road=max_distance_from_road,
                max_detour_distance_km=max_detour_distance_km,
                exclude_cities=[origin_city],
                progress_callback=progress_callback,
                main_route=route,
                debug_collector=debug_collector,
            )
        )

        # Step 5: Sort and assign milestones to segments
        all_milestones.sort(key=lambda m: m.distance_from_origin_km)
        self.milestone_factory.assign_to_segments(linear_segments, all_milestones)

        # Step 6: Enrich with Google Places ratings
        try:
            from .google_places_service import enrich_milestones_sync

            all_milestones = enrich_milestones_sync(all_milestones)
            logger.info("Milestones enriched with Google Places data")
        except Exception as e:
            logger.warning(f"Error enriching with Google Places: {e}")

        # Create response
        linear_map = LinearMapResponse(
            origin=origin,
            destination=destination,
            total_length_km=route.total_distance,
            segments=linear_segments,
            milestones=all_milestones,
            road_id=road_id or f"route_{hash(origin + destination)}",
        )

        # Log final statistics
        logger.info(
            f"Linear map complete: {len(linear_segments)} segments, "
            f"{len(all_milestones)} milestones"
        )
        self._log_milestone_statistics(all_milestones)

        # Save linear map to database
        try:
            from .map_storage_service_db import save_map_sync

            map_id = save_map_sync(
                linear_map,
                user_id=user_id,
                debug_collector=debug_collector,
            )
            linear_map.id = map_id
        except Exception as e:
            logger.error(f"Error saving linear map: {e}")
            map_id = None

        # Step 7: HERE enrichment (only when POI_PROVIDER=osm and HERE_ENRICHMENT_ENABLED=true)
        settings = get_settings()
        if (
            map_id
            and settings.poi_provider.lower() == "osm"
            and settings.here_enrichment_enabled
            and settings.here_api_key
        ):
            try:
                from .here_enrichment_service import enrich_map_pois_with_here
                import asyncio
                from sqlalchemy.ext.asyncio import (
                    AsyncSession,
                    async_sessionmaker,
                    create_async_engine,
                )

                async def _enrich():
                    database_url = (
                        f"postgresql+asyncpg://{settings.postgres_user}:{settings.postgres_password}"
                        f"@{settings.postgres_host}:{settings.postgres_port}/{settings.postgres_database}"
                    )
                    engine = create_async_engine(
                        database_url,
                        pool_size=1,
                        max_overflow=0,
                        pool_pre_ping=True,
                    )
                    session_maker = async_sessionmaker(
                        engine,
                        class_=AsyncSession,
                        expire_on_commit=False,
                    )

                    try:
                        async with session_maker() as session:
                            try:
                                results = await enrich_map_pois_with_here(
                                    session=session,
                                    map_id=map_id,
                                    poi_types=[
                                        "gas_station",
                                        "restaurant",
                                        "hotel",
                                        "hospital",
                                        "pharmacy",
                                    ],
                                )
                                await session.commit()
                                matched = len([r for r in results if r.matched])
                                logger.info(
                                    f"HERE enrichment: {matched}/{len(results)} POIs enriched"
                                )
                            except Exception:
                                await session.rollback()
                                raise
                    finally:
                        await engine.dispose()

                asyncio.run(_enrich())
            except Exception as e:
                logger.warning(f"Error enriching with HERE: {e}")

        return linear_map

    def get_road_milestones(
        self,
        road_id: str,
        origin: Optional[str] = None,
        destination: Optional[str] = None,
        milestone_type: Optional[str] = None,
    ) -> List[RoadMilestoneResponse]:
        """
        Get milestones along a road.

        In a real implementation, this would query the database for milestones.
        For now, returns an empty list since we're not caching anymore.

        Args:
            road_id: Road identifier
            origin: Optional starting point filter
            destination: Optional end point filter
            milestone_type: Optional type filter

        Returns:
            List of RoadMilestoneResponse objects
        """
        return []

    def get_route_statistics(
        self,
        origin: str,
        destination: str,
        max_distance_from_road: float = 1000,
    ) -> RouteStatisticsResponse:
        """
        Generate detailed statistics for a route.

        Always searches for all POI types for comprehensive statistics.

        Args:
            origin: Starting point
            destination: End point
            max_distance_from_road: Maximum POI search distance

        Returns:
            RouteStatisticsResponse with complete statistics
        """
        from api.services.route_statistics_service import RouteStatisticsService

        stats_service = RouteStatisticsService(self)
        return stats_service.get_statistics(origin, destination, max_distance_from_road)

    # ========================================================================
    # ASYNC PUBLIC METHODS
    # ========================================================================

    async def geocode_location_async(
        self, address: str
    ) -> Optional[Tuple[float, float]]:
        """
        Geocode a location using the configured provider.

        Args:
            address: Address string to geocode

        Returns:
            Tuple of (latitude, longitude) or None if not found
        """
        try:
            location = await self.geo_provider.geocode(address)
            if location:
                return (location.latitude, location.longitude)
            return None
        except Exception as e:
            logger.error(f"Error geocoding '{address}': {e}")
            return None

    async def search_pois_async(
        self, location: Tuple[float, float], radius: float, categories: List[str]
    ) -> List[Dict[str, Any]]:
        """
        Search for POIs using the configured provider.

        Args:
            location: (latitude, longitude) tuple
            radius: Search radius in meters
            categories: List of POI categories to search for

        Returns:
            List of POI dictionaries
        """
        try:
            # Convert location to GeoLocation
            geo_location = GeoLocation(latitude=location[0], longitude=location[1])

            # Convert category strings to POICategory enums
            poi_categories = []
            for category in categories:
                try:
                    poi_categories.append(POICategory(category))
                except ValueError:
                    logger.warning(f"Unknown POI category: {category}")
                    continue

            if not poi_categories:
                return []

            # Search using the provider
            pois = await self.poi_provider.search_pois(
                location=geo_location,
                radius=radius,
                categories=poi_categories,
            )

            # Convert POIs to dictionaries
            result = []
            for poi in pois:
                result.append(
                    {
                        "id": poi.id,
                        "name": poi.name,
                        "lat": poi.location.latitude,
                        "lon": poi.location.longitude,
                        "category": poi.category.value,
                        "amenities": poi.amenities,
                        "rating": poi.rating,
                        "is_open": poi.is_open,
                        "phone": poi.phone,
                        "website": poi.website,
                        "tags": poi.provider_data.get("tags", poi.provider_data),
                    }
                )

            return result

        except Exception as e:
            logger.error(f"Error searching POIs: {e}")
            return []

    # ========================================================================
    # BACKWARD COMPATIBILITY METHODS
    # ========================================================================
    # These methods delegate to the new services but maintain backward compatibility
    # for any code that might be calling them directly.

    def _calculate_distance_meters(
        self, lat1: float, lon1: float, lat2: float, lon2: float
    ) -> float:
        """Calculate distance between two points using Haversine formula."""
        return calculate_distance_meters(lat1, lon1, lat2, lon2)

    def _interpolate_coordinate_at_distance(
        self,
        geometry: List[Tuple[float, float]],
        target_distance_km: float,
        total_distance_km: float,
    ) -> Tuple[float, float]:
        """Interpolate a coordinate at a specific distance along the route."""
        from api.utils.geo_utils import interpolate_coordinate_at_distance

        return interpolate_coordinate_at_distance(
            geometry, target_distance_km, total_distance_km
        )

    def _process_route_into_segments(
        self, route: Route, segment_length_km: float
    ) -> List[LinearRoadSegment]:
        """Process a route into linear segments."""
        return self.segmentation_service.process_route_into_segments(
            route, segment_length_km
        )

    def _extract_search_points_from_segments(
        self, segments: List[LinearRoadSegment]
    ) -> List[Tuple[Tuple[float, float], float]]:
        """Extract search points from segments."""
        return self.segmentation_service.extract_search_points_from_segments(segments)

    def _build_milestone_categories(self, include_cities: bool) -> List[POICategory]:
        """Build list of POI categories for milestone search."""
        return self.milestone_factory.build_milestone_categories(include_cities)

    def _assign_milestones_to_segments(
        self, segments: List[LinearRoadSegment], milestones: List[RoadMilestone]
    ):
        """Assign milestones to segments."""
        self.milestone_factory.assign_to_segments(segments, milestones)

    def _poi_category_to_milestone_type(self, category: POICategory):
        """Convert POI category to milestone type."""
        return self.milestone_factory.get_milestone_type(category)

    def _create_milestone_from_poi(
        self,
        poi,
        distance_from_origin: float,
        route_point: Tuple[float, float],
        junction_info=None,
    ) -> RoadMilestone:
        """Create a milestone from a POI."""
        return self.milestone_factory.create_from_poi(
            poi, distance_from_origin, route_point, junction_info
        )

    def _is_poi_abandoned(self, tags: Dict[str, Any]) -> bool:
        """Check if a POI is abandoned."""
        return self.quality_service.is_poi_abandoned(tags)

    def _calculate_poi_quality_score(self, tags: Dict[str, Any]) -> float:
        """Calculate quality score for a POI."""
        return self.quality_service.calculate_quality_score(tags)

    def _meets_quality_threshold(
        self, tags: Dict[str, Any], quality_score: float
    ) -> bool:
        """Check if POI meets quality threshold."""
        return self.quality_service.meets_quality_threshold(tags, quality_score)

    def _extract_amenities(self, tags: Dict[str, Any]) -> List[str]:
        """Extract amenities from POI tags."""
        return self.quality_service.extract_amenities(tags)

    def _format_opening_hours(
        self, opening_hours: Optional[Dict[str, str]]
    ) -> Optional[str]:
        """Format opening hours to string."""
        return self.quality_service.format_opening_hours(opening_hours)

    def _filter_excluded_cities(
        self, milestones: List[RoadMilestone], exclude_cities: List[str]
    ) -> List[RoadMilestone]:
        """Filter milestones by excluded cities."""
        return self.quality_service.filter_by_excluded_cities(milestones, exclude_cities)

    def _determine_poi_side(
        self,
        main_route_geometry: List[Tuple[float, float]],
        junction_point: Tuple[float, float],
        poi_location: Tuple[float, float],
        return_debug: bool = False,
    ):
        """Determine POI side relative to road."""
        return self.poi_search_service.determine_poi_side(
            main_route_geometry, junction_point, poi_location, return_debug
        )

    async def _enrich_milestones_with_cities(
        self, milestones: List[RoadMilestone]
    ) -> None:
        """Enrich milestones with city information."""
        await self.milestone_factory.enrich_with_cities(milestones)

    def _run_async_safe(self, coro):
        """Execute async coroutine safely."""
        return run_async_safe(coro)

    def _calculate_distance_along_route(
        self,
        geometry: List[Tuple[float, float]],
        target_point: Tuple[float, float],
    ) -> float:
        """Calculate distance along route to target point."""
        from api.utils.geo_utils import calculate_distance_along_route

        return calculate_distance_along_route(geometry, target_point)

    async def _find_milestones_from_segments(
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
        """Find milestones along the route (delegates to poi_search_service)."""
        return await self.poi_search_service.find_milestones(
            segments=segments,
            categories=categories,
            max_distance_from_road=max_distance_from_road,
            max_detour_distance_km=max_detour_distance_km,
            exclude_cities=exclude_cities,
            progress_callback=progress_callback,
            main_route=main_route,
            debug_collector=debug_collector,
        )
