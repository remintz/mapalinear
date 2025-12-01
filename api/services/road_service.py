import uuid
from typing import List, Optional, Dict, Any, Tuple, Callable
import logging
import math

from api.models.road_models import (
    LinearMapResponse,
    LinearRoadSegment,
    RoadMilestone,
    RoadMilestoneResponse,
    SavedMapResponse,
    MilestoneType,
    Coordinates,
)
from api.providers.base import GeoProvider
from api.providers.models import GeoLocation, Route, POI, POICategory

# Usar logger centralizado
logger = logging.getLogger(__name__)

class RoadService:
    def __init__(self, geo_provider: Optional[GeoProvider] = None):
        """Initialize RoadService with a geographic data provider."""
        if geo_provider is None:
            # Use the default provider from the manager
            from ..providers import create_provider
            geo_provider = create_provider()
        
        self.geo_provider = geo_provider

    # ========================================================================
    # UTILITY METHODS
    # ========================================================================
    
    def _run_async_safe(self, coro):
        """
        Execute async coroutine safely, handling both running and non-running event loops.
        
        This helper allows calling async provider methods from sync contexts.
        """
        import asyncio
        
        try:
            # Try to get the event loop for this thread
            loop = asyncio.get_event_loop()
            
            # Check if the loop is running
            if loop.is_running():
                # If loop is already running (e.g., in async context), 
                # we need to run in a new thread
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(asyncio.run, coro)
                    return future.result()
            else:
                # Loop exists but not running - run the coroutine in it
                return loop.run_until_complete(coro)
        except RuntimeError:
            # No event loop in this thread, create and use a new one
            return asyncio.run(coro)
    
    def _extract_city_name(self, location_string: str) -> str:
        """
        Extract city name from location string.
        
        Args:
            location_string: Location in format "City, State" (e.g., "Belo Horizonte, MG")
            
        Returns:
            City name (e.g., "Belo Horizonte")
        """
        return location_string.split(',')[0].strip() if ',' in location_string else location_string.strip()
    
    def _geocode_and_validate(self, address: str, address_type: str = "location") -> GeoLocation:
        """
        Geocode an address and validate the result.
        
        Args:
            address: Address string to geocode
            address_type: Type of address for error messages ("origin", "destination", etc.)
            
        Returns:
            GeoLocation object
            
        Raises:
            ValueError: If geocoding fails
        """
        logger.info(f"🛣️ Geocodificando {address_type}: {address}")
        location = self._run_async_safe(self.geo_provider.geocode(address))
        
        if not location:
            raise ValueError(f"Could not geocode {address_type}: {address}")
        
        logger.info(f"🛣️ {address_type.capitalize()}: {address} → "
                   f"lat={location.latitude:.6f}, lon={location.longitude:.6f}")
        
        return location
    
    def _log_route_info(self, route: Route):
        """Log detailed route information."""
        logger.info(f"🛣️ Rota calculada:")
        logger.info(f"🛣️ - Distância total: {route.total_distance:.1f} km")
        logger.info(f"🛣️ - Nomes das estradas: {route.road_names}")
        logger.info(f"🛣️ - Pontos na geometria: {len(route.geometry)}")
        
        if route.geometry:
            logger.info(f"🛣️ - Primeiro ponto: lat={route.geometry[0][0]:.6f}, "
                       f"lon={route.geometry[0][1]:.6f}")
            logger.info(f"🛣️ - Último ponto: lat={route.geometry[-1][0]:.6f}, "
                       f"lon={route.geometry[-1][1]:.6f}")
    
    def _build_milestone_categories(
        self,
        include_cities: bool
    ) -> List[POICategory]:
        """
        Build list of all POI categories. Always includes all POI types for comprehensive search.
        Frontend will filter which ones to display.

        Returns:
            List of POICategory enums
        """
        categories = []

        # Always include all POI types
        categories.extend([
            POICategory.GAS_STATION,
            POICategory.FUEL,
            POICategory.RESTAURANT,
            POICategory.FOOD,
            POICategory.HOTEL,
            POICategory.LODGING,
            POICategory.CAMPING,
            POICategory.HOSPITAL
        ])

        # Cities/services based on parameter
        if include_cities:
            categories.extend([POICategory.SERVICES])

        return categories
    
    def _assign_milestones_to_segments(
        self,
        segments: List[LinearRoadSegment],
        milestones: List[RoadMilestone]
    ):
        """
        Assign milestones to their respective segments based on distance.
        
        Modifies segments in-place.
        """
        for segment in segments:
            segment.milestones = [
                milestone for milestone in milestones
                if segment.start_distance_km <= milestone.distance_from_origin_km <= segment.end_distance_km
            ]
            segment.milestones.sort(key=lambda m: m.distance_from_origin_km)
    
    def _log_milestone_statistics(self, milestones: List[RoadMilestone]):
        """Log statistics about found milestones."""
        milestones_with_city = len([m for m in milestones if m.city])
        logger.info(f"🏙️ Milestones com cidade: {milestones_with_city}/{len(milestones)}")
        
        for milestone in milestones:
            city_info = f" ({milestone.city})" if milestone.city else ""
            logger.info(f"🎯 Milestone: {milestone.name}{city_info} "
                       f"({milestone.type.value}) - dist={milestone.distance_from_origin_km:.1f}km")
    



    def generate_linear_map(
        self,
        origin: str,
        destination: str,
        road_id: Optional[str] = None,
        include_cities: bool = True,
        max_distance_from_road: float = 3000,
        min_distance_from_origin_km: float = 0.0,  # Deprecated - kept for backwards compatibility
        progress_callback: Optional[Callable[[float], None]] = None,
        segment_length_km: float = 1.0
    ) -> LinearMapResponse:
        """
        Generate a linear map of a route between origin and destination.
        
        This method:
        1. Geocodes origin and destination
        2. Calculates the route
        3. Processes route into linear segments
        4. Finds POI milestones along the route
        5. Assigns milestones to segments
        
        Args:
            min_distance_from_origin_km: DEPRECATED - No longer used. POIs are filtered by city name instead.
        
        Returns:
            LinearMapResponse with segments and milestones
        """
        logger.info(f"🛣️ Iniciando geração de mapa linear: {origin} → {destination}")
        
        # Extract origin city for POI filtering
        origin_city = self._extract_city_name(origin)
        logger.info(f"🏙️ Cidade de origem extraída: {origin_city}")
        
        # Step 1: Geocode origin and destination
        origin_location = self._geocode_and_validate(origin, "origem")
        destination_location = self._geocode_and_validate(destination, "destino")
        
        # Step 2: Calculate route
        logger.info(f"🛣️ Calculando rota entre os pontos...")
        route = self._run_async_safe(
            self.geo_provider.calculate_route(origin_location, destination_location)
        )
        
        if not route:
            raise ValueError(f"Could not calculate route from {origin} to {destination}")
        
        self._log_route_info(route)
        
        # Step 3: Process route into linear segments
        linear_segments = self._process_route_into_segments(route, segment_length_km)
        
        # Step 4: Find milestones along the route (always search all POI types)
        milestone_categories = self._build_milestone_categories(include_cities)
        
        logger.info(f"🛣️ Categorias de milestone solicitadas: "
                   f"{[cat.value for cat in milestone_categories]}")

        all_milestones = self._run_async_safe(self._find_milestones_from_segments(
            linear_segments,
            milestone_categories,
            max_distance_from_road,
            exclude_cities=[origin_city],
            progress_callback=progress_callback,
            main_route=route
        ))
        
        # Step 5: Sort and assign milestones to segments
        all_milestones.sort(key=lambda m: m.distance_from_origin_km)
        self._assign_milestones_to_segments(linear_segments, all_milestones)

        # Step 6: Enrich restaurants and hotels with Google Places ratings
        try:
            from .google_places_service import enrich_milestones_sync
            all_milestones = enrich_milestones_sync(all_milestones)
            logger.info("✅ Milestones enriquecidos com dados do Google Places")
        except Exception as e:
            logger.warning(f"⚠️ Erro ao enriquecer milestones com Google Places: {e}")

        # Create response
        linear_map = LinearMapResponse(
            origin=origin,
            destination=destination,
            total_length_km=route.total_distance,
            segments=linear_segments,
            milestones=all_milestones,
            road_id=road_id or f"route_{hash(origin + destination)}"
        )
        
        # Log final statistics
        logger.info(f"🛣️ Mapa linear concluído: {len(linear_segments)} segmentos, "
                   f"{len(all_milestones)} milestones")
        self._log_milestone_statistics(all_milestones)

        # Note: Cache is automatically persisted to PostgreSQL, no manual save needed

        # Save linear map to database
        try:
            from .map_storage_service_db import save_map_sync
            save_map_sync(linear_map)
        except Exception as e:
            logger.error(f"Erro ao salvar mapa linear no banco: {e}")

        return linear_map

    def _process_route_into_segments(self, route: Route, segment_length_km: float) -> List[LinearRoadSegment]:
        """
        Process a unified Route object into linear road segments.
        """
        linear_segments = []
        total_distance = route.total_distance
        
        # Create segments based on the specified segment length
        current_distance = 0.0
        segment_id = 1
        
        while current_distance < total_distance:
            start_distance = current_distance
            end_distance = min(current_distance + segment_length_km, total_distance)
            
            # Calculate start and end coordinates by interpolating along the route geometry
            start_coord = self._interpolate_coordinate_at_distance(route.geometry, start_distance, total_distance)
            end_coord = self._interpolate_coordinate_at_distance(route.geometry, end_distance, total_distance)
            
            # Get primary road name from route
            road_name = route.road_names[0] if route.road_names else "Unnamed Road"
            
            segment = LinearRoadSegment(
                id=f"segment_{segment_id}",
                name=road_name,
                start_distance_km=start_distance,
                end_distance_km=end_distance,
                length_km=end_distance - start_distance,
                start_coordinates=Coordinates(latitude=start_coord[0], longitude=start_coord[1]),
                end_coordinates=Coordinates(latitude=end_coord[0], longitude=end_coord[1]),
                milestones=[]
            )
            
            linear_segments.append(segment)
            current_distance = end_distance
            segment_id += 1
        
        logger.info(f"Created {len(linear_segments)} linear segments from route")
        return linear_segments
    
    def _interpolate_coordinate_at_distance(self, geometry: List[Tuple[float, float]], 
                                          target_distance_km: float, total_distance_km: float) -> Tuple[float, float]:
        """
        Interpolate a coordinate at a specific distance along the route geometry.
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

    # ========================================================================
    # POI/MILESTONE HELPER METHODS
    # ========================================================================
    
    def _extract_search_points_from_segments(
        self,
        segments: List[LinearRoadSegment]
    ) -> List[Tuple[Tuple[float, float], float]]:
        """
        Extract search points from segment start/end coordinates.
        
        Returns:
            List of tuples: ((lat, lon), distance_from_origin)
        """
        search_points = []
        
        for segment in segments:
            # Add segment start point
            if segment.start_coordinates:
                search_points.append((
                    (segment.start_coordinates.latitude, segment.start_coordinates.longitude),
                    segment.start_distance_km
                ))
            
            # Add segment end point (only for last segment to avoid duplicates)
            if segment.end_coordinates and segment == segments[-1]:
                search_points.append((
                    (segment.end_coordinates.latitude, segment.end_coordinates.longitude),
                    segment.end_distance_km
                ))
        
        logger.info(f"🔍 Gerados {len(search_points)} pontos de busca a partir dos segmentos")
        return search_points
    
    def _create_milestone_from_poi(
        self,
        poi: POI,
        distance_from_origin: float,
        route_point: Tuple[float, float],
        junction_info: Optional[Tuple[float, Tuple[float, float], float, str]] = None
    ) -> RoadMilestone:
        """
        Create a RoadMilestone from a POI object.

        Args:
            poi: POI object from provider
            distance_from_origin: Distance from route origin in km
            route_point: (lat, lon) of the route point near this POI
            junction_info: Optional tuple of (junction_distance_km, junction_coords, access_route_distance_km, side) for distant POIs

        Returns:
            RoadMilestone object
        """
        # Determine milestone type - check if it's a place (city/town/village) first
        milestone_type = None
        if poi.provider_data and 'osm_tags' in poi.provider_data:
            osm_tags = poi.provider_data['osm_tags']
            place_type = osm_tags.get('place', '')
            if place_type == 'city':
                milestone_type = MilestoneType.CITY
            elif place_type == 'town':
                milestone_type = MilestoneType.TOWN
            elif place_type == 'village':
                milestone_type = MilestoneType.VILLAGE

        # If not a place, use category mapping
        if not milestone_type:
            milestone_type = self._poi_category_to_milestone_type(poi.category)

        # Calculate distance from POI to route point
        distance_from_road = self._calculate_distance_meters(
            poi.location.latitude, poi.location.longitude,
            route_point[0], route_point[1]
        )

        # Extract city from POI tags (quick, no API call)
        city = None
        if poi.provider_data:
            # For cities and towns, the city field is the place name itself
            if milestone_type in [MilestoneType.CITY, MilestoneType.TOWN]:
                city = poi.name  # The place name is the city name
            # For villages, city should be the municipality name (from tags or reverse geocoding)
            elif milestone_type == MilestoneType.VILLAGE:
                # Try to extract municipality from OSM tags
                osm_tags = poi.provider_data.get('osm_tags', {})
                city = (osm_tags.get('addr:city') or
                       osm_tags.get('is_in:city') or
                       osm_tags.get('is_in') or
                       poi.provider_data.get('addr:city') or
                       poi.provider_data.get('address:city') or
                       poi.provider_data.get('addr:municipality'))
                # If no city found in tags, reverse geocoding will fill it later
            else:
                # For other POIs (gas stations, restaurants, etc), try to extract city from address tags
                city = (poi.provider_data.get('addr:city') or
                       poi.provider_data.get('address:city') or
                       poi.provider_data.get('addr:municipality'))
            if city:
                logger.debug(f"🏙️ POI {poi.name}: cidade '{city}' extraída das tags OSM")
        
        # Extract quality_score from provider_data
        quality_score = None
        if poi.provider_data:
            quality_score = poi.provider_data.get('quality_score')

        # Process junction information for distant POIs
        requires_detour = distance_from_road > 500  # POIs > 500m require detour
        junction_distance_km = None
        junction_coordinates = None
        access_route_distance_m = distance_from_road  # Default to straight-line distance
        poi_side = "center"  # Default side

        if junction_info:
            junction_distance_km, junction_coords, access_route_distance_km, side = junction_info

            # If distance from junction to POI is < 0.1km, treat as roadside POI
            if access_route_distance_km < 0.1:
                logger.debug(f"📍 POI {poi.name} está praticamente na rodovia "
                           f"(distância do entroncamento={access_route_distance_km:.2f}km < 0.1km), "
                           f"sem necessidade de sinalização de desvio")
                requires_detour = False
                junction_distance_km = None
                junction_coordinates = None
            else:
                junction_coordinates = Coordinates(
                    latitude=junction_coords[0],
                    longitude=junction_coords[1]
                )
                # Use access route distance instead of straight-line distance
                access_route_distance_m = access_route_distance_km * 1000
                poi_side = side  # Use calculated side (left or right)
                logger.debug(f"🛣️ POI {poi.name} requer desvio: entroncamento no km {junction_distance_km:.1f}, "
                            f"distância pela rota={access_route_distance_km:.2f}km, lado={side}")

        return RoadMilestone(
            id=poi.id,
            name=poi.name,
            type=milestone_type,
            coordinates=Coordinates(
                latitude=poi.location.latitude,
                longitude=poi.location.longitude
            ),
            distance_from_origin_km=distance_from_origin,
            distance_from_road_meters=access_route_distance_m,
            side=poi_side,
            tags=poi.provider_data,
            city=city,
            operator=poi.subcategory,
            brand=poi.subcategory,
            opening_hours=self._format_opening_hours(poi.opening_hours),
            phone=poi.phone,
            website=poi.website,
            amenities=poi.amenities,
            quality_score=quality_score,
            # New fields for junction information
            junction_distance_km=junction_distance_km,
            junction_coordinates=junction_coordinates,
            requires_detour=requires_detour
        )
    
    async def _enrich_milestones_with_cities(self, milestones: List[RoadMilestone]):
        """
        Enrich milestones with city information via reverse geocoding.
        
        Only geocodes milestones that don't already have city information.
        Modifies milestones in-place.
        """
        milestones_without_city = [m for m in milestones if not m.city]
        logger.info(f"🌍 Fazendo reverse geocoding para obter cidades...")
        logger.info(f"🌍 {len(milestones_without_city)} POIs precisam de reverse geocoding")
        
        for milestone in milestones_without_city:
            try:
                reverse_loc = await self.geo_provider.reverse_geocode(
                    milestone.coordinates.latitude,
                    milestone.coordinates.longitude,
                    poi_name=milestone.name
                )
                if reverse_loc and reverse_loc.city:
                    milestone.city = reverse_loc.city
                    logger.debug(f"🌍 {milestone.name}: {reverse_loc.city}")
            except Exception as e:
                logger.debug(f"Could not reverse geocode {milestone.name}: {e}")
        
        cities_found = len([m for m in milestones if m.city])
        logger.info(f"🌍 Reverse geocoding concluído: "
                   f"{cities_found}/{len(milestones)} POIs com cidade identificada")
    
    def _filter_excluded_cities(
        self,
        milestones: List[RoadMilestone],
        exclude_cities_filtered: List[str]
    ) -> List[RoadMilestone]:
        """
        Filter out milestones in excluded cities.
        
        Args:
            milestones: List of milestones to filter
            exclude_cities_filtered: List of normalized city names to exclude
            
        Returns:
            Filtered list of milestones
        """
        if not exclude_cities_filtered:
            return milestones
        
        milestones_before_filter = len(milestones)
        
        # Debug: log cities found in milestones
        milestone_cities = set([m.city for m in milestones if m.city])
        logger.debug(f"🏙️ Cidades únicas encontradas nos POIs: {milestone_cities}")
        logger.debug(f"🚫 Cidade(s) a filtrar: {exclude_cities_filtered}")
        
        # Show some examples before filtering
        examples_to_filter = [
            m for m in milestones
            if m.city and m.city.strip().lower() in exclude_cities_filtered
        ][:3]
        
        if examples_to_filter:
            logger.debug(f"📝 Exemplos de POIs que serão filtrados:")
            for m in examples_to_filter:
                logger.debug(f"   - {m.name} em {m.city}")
        
        # Filter
        filtered_milestones = [
            m for m in milestones
            if not m.city or m.city.strip().lower() not in exclude_cities_filtered
        ]
        
        filtered_count = milestones_before_filter - len(filtered_milestones)
        if filtered_count > 0:
            logger.info(f"🚫 Removidos {filtered_count} POIs da cidade de origem: "
                       f"{exclude_cities_filtered}")
        else:
            logger.warning(f"⚠️ Nenhum POI foi filtrado. "
                          f"Cidade de origem '{exclude_cities_filtered}' não encontrada nos POIs")
        
        return filtered_milestones

    async def _find_milestones_from_segments(
        self,
        segments: List[LinearRoadSegment],
        categories: List[POICategory],
        max_distance_from_road: float,
        exclude_cities: Optional[List[Optional[str]]] = None,
        progress_callback: Optional[Callable[[float], None]] = None,
        main_route: Optional[Route] = None
    ) -> List[RoadMilestone]:
        """
        Find POI milestones along the route using segment start/end points.
        
        This method:
        1. Extracts search points from segments
        2. Searches for POIs around each point
        3. Converts POIs to milestones
        4. For distant POIs (>500m), calculates junction point
        5. Enriches with city information
        6. Filters excluded cities
        
        Returns:
            List of RoadMilestone objects
        """
        logger.info(f"🔍 Iniciando busca de milestones usando {len(segments)} segmentos")
        logger.info(f"🔍 Categorias: {[cat.value for cat in categories]}")
        logger.info(f"🔍 Parâmetros: max_distance={max_distance_from_road}m")
        
        # Normalize excluded cities
        exclude_cities_filtered = [city.strip().lower() for city in (exclude_cities or []) if city]
        if exclude_cities_filtered:
            logger.info(f"🚫 Cidades a excluir: {exclude_cities_filtered}")
        
        # Extract search points from segments
        search_points = self._extract_search_points_from_segments(segments)
        total_points = len(search_points)

        # Statistics
        milestones = []
        total_errors = 0
        total_requests = 0
        consecutive_errors = 0
        pois_abandoned_no_junction = 0

        for i, (point, distance_from_origin) in enumerate(search_points):
            # Update progress based on points processed
            # Progress goes from 10% to 90% during POI search (leaving 10% for enrichment and filtering)
            if progress_callback:
                progress = round(10.0 + (i / total_points) * 80.0)
                progress_callback(progress)
            logger.debug(f"🔍 Ponto {i}: lat={point[0]:.6f}, lon={point[1]:.6f}, "
                        f"dist={distance_from_origin:.1f}km")
            total_requests += 1
            
            try:
                # Search for POIs around this point
                pois = await self.geo_provider.search_pois(
                    location=GeoLocation(latitude=point[0], longitude=point[1]),
                    radius=max_distance_from_road,
                    categories=categories,
                    limit=20
                )
                
                logger.info(f"📍 Ponto {i}: {len(pois)} POIs encontrados")
                consecutive_errors = 0  # Reset on success
                
                # Convert POIs to milestones
                converted_count = 0
                duplicates_count = 0
                abandoned_count = 0
                
                for j, poi in enumerate(pois):
                    try:
                        # Check if POI already exists (already processed with junction if needed)
                        if any(m.id == poi.id for m in milestones):
                            duplicates_count += 1
                            logger.debug(f"⏭️  Ignorando POI duplicado: {poi.name}")
                            continue

                        # Validate POI category
                        if not isinstance(poi.category, POICategory):
                            logger.error(f"🔍 POI {j}: categoria inválida! "
                                       f"Valor: {poi.category}, tipo: {type(poi.category)}")
                            continue

                        # Calculate distance from POI to search point
                        poi_distance_from_road = self._calculate_distance_meters(
                            poi.location.latitude, poi.location.longitude,
                            point[0], point[1]
                        )

                        junction_info = None
                        
                        # For distant POIs (>500m), calculate junction point
                        if poi_distance_from_road > 500 and main_route:
                            logger.debug(f"🛣️ POI afastado detectado: {poi.name} "
                                       f"({poi_distance_from_road:.0f}m da estrada)")
                            
                            junction_info = await self._calculate_junction_for_distant_poi(
                                poi=poi,
                                search_point=point,
                                search_point_distance_km=distance_from_origin,
                                main_route=main_route
                            )
                            
                            if not junction_info:
                                # Abandon POI if no junction found
                                logger.info(f"🚫 POI abandonado (sem entroncamento): {poi.name} "
                                          f"({poi_distance_from_road:.0f}m da estrada)")
                                pois_abandoned_no_junction += 1
                                abandoned_count += 1
                                continue

                        # Create milestone
                        milestone = self._create_milestone_from_poi(
                            poi, 
                            distance_from_origin, 
                            point,
                            junction_info
                        )
                        milestones.append(milestone)
                        converted_count += 1
                        logger.debug(f"✅ {milestone.name} ({milestone.type.value})")
                        
                    except Exception as e:
                        logger.error(f"🔍 Erro convertendo POI {j}: {e}")
                        logger.error(f"🔍 POI detalhes: nome={getattr(poi, 'name', 'N/A')}, "
                                   f"categoria={getattr(poi, 'category', 'N/A')}")
                        import traceback
                        logger.error(f"🔍 Traceback: {traceback.format_exc()}")
                        continue

                if converted_count > 0 or duplicates_count > 0 or abandoned_count > 0:
                    logger.debug(f"📍 Ponto {i}: {converted_count} novos, "
                                f"{duplicates_count} duplicatas, {abandoned_count} abandonados")
                
            except Exception as e:
                total_errors += 1
                consecutive_errors += 1
                logger.error(f"🔍 Erro buscando POIs no ponto {i}: {e}")
                
                # Fail fast criteria
                if consecutive_errors >= 5:
                    logger.error(f"Too many consecutive POI search failures ({consecutive_errors}). "
                               f"All endpoints may be down.")
                    raise RuntimeError(
                        f"POI search failed: {consecutive_errors} consecutive failures. "
                        f"All Overpass endpoints may be unavailable. Last error: {e}"
                    )
                
                if total_requests >= 5:
                    error_rate = total_errors / total_requests
                    if error_rate > 0.9:
                        logger.error(f"POI search failure rate too high ({error_rate:.1%}). "
                                   f"Systemic issue detected.")
                        raise RuntimeError(
                            f"POI search failed: {error_rate:.1%} of requests failed. "
                            f"Systemic issue detected. Last error: {e}"
                        )
                
                continue
        
        # Log final statistics
        if total_requests > 0:
            error_rate = total_errors / total_requests
            if error_rate > 0:
                logger.warning(f"POI search completed with {error_rate:.1%} error rate "
                             f"({total_errors}/{total_requests} failed)")
            if error_rate > 0.5:
                logger.warning(f"High error rate detected. Consider checking Overpass API status.")
        
        logger.info(f"🎯 RESULTADO FINAL: {len(milestones)} milestones encontrados ao longo da rota")
        
        if pois_abandoned_no_junction > 0:
            logger.info(f"🚫 POIs abandonados por falta de entroncamento: {pois_abandoned_no_junction}")

        # Update progress - POI search completed (90%)
        if progress_callback:
            progress_callback(90)

        # Enrich milestones with cities (reverse geocoding)
        await self._enrich_milestones_with_cities(milestones)

        # Update progress - enrichment completed (95%)
        if progress_callback:
            progress_callback(95)
        
        # Filter out POIs in excluded cities
        milestones = self._filter_excluded_cities(milestones, exclude_cities_filtered)
        
        # Log final results
        self._log_milestone_statistics(milestones)
        
        return milestones

    def _poi_category_to_milestone_type(self, category: POICategory) -> MilestoneType:
        """
        Convert POI category to milestone type.
        """
        mapping = {
            POICategory.GAS_STATION: MilestoneType.GAS_STATION,
            POICategory.FUEL: MilestoneType.GAS_STATION,
            POICategory.RESTAURANT: MilestoneType.RESTAURANT,
            POICategory.FOOD: MilestoneType.RESTAURANT,
            POICategory.HOTEL: MilestoneType.HOTEL,
            POICategory.LODGING: MilestoneType.HOTEL,
            POICategory.CAMPING: MilestoneType.CAMPING,
            POICategory.HOSPITAL: MilestoneType.HOSPITAL,
            POICategory.SERVICES: MilestoneType.OTHER,
            POICategory.PARKING: MilestoneType.OTHER,
        }
        return mapping.get(category, MilestoneType.OTHER)
    
    def _format_opening_hours(self, opening_hours: Optional[Dict[str, str]]) -> Optional[str]:
        """
        Format opening hours dict to string.
        """
        if not opening_hours:
            return None
        
        # Simple format: "Mon-Fri: 8:00-18:00, Sat: 9:00-17:00"
        formatted = []
        for day, hours in opening_hours.items():
            formatted.append(f"{day}: {hours}")
        
        return ", ".join(formatted)
    
    
    def get_road_milestones(
        self, 
        road_id: str, 
        origin: Optional[str] = None, 
        destination: Optional[str] = None, 
        milestone_type: Optional[str] = None
    ) -> List[RoadMilestoneResponse]:
        """
        Obtém marcos importantes ao longo de uma estrada.
        """
        # In a real implementation, this would query the database for milestones
        # For now, we'll return an empty list since we're not caching anymore
        return []
    
    def _is_poi_abandoned(self, tags: Dict[str, Any]) -> bool:
        """
        Verifica se um POI está abandonado ou fora de uso.
        
        Args:
            tags: Tags do provider geográfico
            
        Returns:
            True se o POI deve ser excluído por estar abandonado
        """
        abandonment_indicators = [
            'abandoned', 'disused', 'demolished', 'razed', 'removed', 
            'ruins', 'former', 'closed', 'destroyed'
        ]
        
        # Verifica tags diretas de abandono
        for indicator in abandonment_indicators:
            if tags.get(indicator) in ['yes', 'true', '1']:
                return True
            # Verifica prefixos (ex: abandoned:amenity=fuel)
            for key in tags.keys():
                if key.startswith(f"{indicator}:"):
                    return True
        
        # Verifica status específicos
        if tags.get('opening_hours') in ['closed', 'no']:
            return True
            
        return False
    
    def _calculate_poi_quality_score(self, tags: Dict[str, Any]) -> float:
        """
        Calcula um score de qualidade para um POI baseado na completude dos dados.
        
        Args:
            tags: Tags do provider geográfico
            
        Returns:
            Score de 0.0 a 1.0, onde 1.0 é melhor qualidade
        """
        score = 0.0
        max_score = 7.0  # Número de critérios de qualidade
        
        # Critério 1: Tem nome
        if tags.get('name'):
            score += 1.0
        
        # Critério 2: Tem operator ou brand
        if tags.get('operator') or tags.get('brand'):
            score += 1.0
        
        # Critério 3: Tem telefone
        if tags.get('phone') or tags.get('contact:phone'):
            score += 1.0
        
        # Critério 4: Tem horário de funcionamento
        if tags.get('opening_hours'):
            score += 1.0
        
        # Critério 5: Tem website
        if tags.get('website') or tags.get('contact:website'):
            score += 1.0
        
        # Critério 6: Para restaurantes, tem tipo de culinária
        if tags.get('amenity') == 'restaurant' and tags.get('cuisine'):
            score += 1.0
        elif tags.get('amenity') != 'restaurant':
            score += 1.0  # Não penalizar não-restaurantes
            
        # Critério 7: Tem endereço estruturado
        if any(tags.get(f'addr:{field}') for field in ['street', 'housenumber', 'city']):
            score += 1.0
        
        return score / max_score
    
    def _meets_quality_threshold(self, tags: Dict[str, Any], quality_score: float) -> bool:
        """
        Verifica se um POI atende ao threshold mínimo de qualidade.
        
        Args:
            tags: Tags do provider geográfico
            quality_score: Score de qualidade calculado
            
        Returns:
            True se o POI deve ser incluído
        """
        amenity = tags.get('amenity')
        barrier = tags.get('barrier')
        
        # Para postos de gasolina, exigir nome OU brand OU operator
        if amenity == 'fuel':
            if not (tags.get('name') or tags.get('brand') or tags.get('operator')):
                return False
            return quality_score >= 0.3  # Threshold mais baixo para postos
        
        # Para estabelecimentos de alimentação, exigir nome
        food_amenities = ['restaurant', 'fast_food', 'cafe', 'bar', 'pub', 'food_court', 'ice_cream']
        food_shops = ['bakery']
        
        if amenity in food_amenities or tags.get('shop') in food_shops:
            if not tags.get('name'):
                return False
            return quality_score >= 0.4  # Threshold médio para estabelecimentos de alimentação
        
        # Para pedágios, sempre incluir (mesmo sem nome)
        if barrier == 'toll_booth':
            return True
        
        # Para outros tipos, threshold padrão
        return quality_score >= 0.3
    
    def _extract_amenities(self, tags: Dict[str, Any]) -> List[str]:
        """
        Extrai lista de comodidades/amenidades de um POI baseado nas tags do provider.
        
        Args:
            tags: Tags do provider geográfico
            
        Returns:
            Lista de amenidades encontradas
        """
        amenities = []
        
        # Mapeamento de tags do provider para amenidades legíveis
        amenity_mappings = {
            # Conectividade
            'internet_access': {'wifi', 'internet'},
            'wifi': {'wifi'},
            
            # Estacionamento
            'parking': {'estacionamento'},
            'parking:fee': {'estacionamento pago'},
            
            # Acessibilidade
            'wheelchair': {'acessível'},
            
            # Pagamento
            'payment:cash': {'dinheiro'},
            'payment:cards': {'cartão'},
            'payment:contactless': {'contactless'},
            'payment:credit_cards': {'cartão de crédito'},
            'payment:debit_cards': {'cartão de débito'},
            
            # Combustível específico
            'fuel:diesel': {'diesel'},
            'fuel:octane_91': {'gasolina comum'},
            'fuel:octane_95': {'gasolina aditivada'},
            'fuel:lpg': {'GNV'},
            'fuel:ethanol': {'etanol'},
            
            # Serviços
            'toilets': {'banheiro'},
            'shower': {'chuveiro'},
            'restaurant': {'restaurante'},
            'cafe': {'café'},
            'shop': {'loja'},
            'atm': {'caixa eletrônico'},
            'car_wash': {'lava-jato'},
            'compressed_air': {'calibragem'},
            'vacuum_cleaner': {'aspirador'},
            
            # Outros
            'outdoor_seating': {'área externa'},
            'air_conditioning': {'ar condicionado'},
            'takeaway': {'delivery'},
            'delivery': {'delivery'},
            'drive_through': {'drive-thru'},
        }
        
        # Verifica cada tag e adiciona as amenidades correspondentes
        for tag_key, tag_value in tags.items():
            # Normaliza o valor da tag
            if isinstance(tag_value, str):
                tag_value = tag_value.lower()
            
            # Verifica se a tag indica presença da amenidade
            if tag_value in ['yes', 'true', '1', 'available']:
                if tag_key in amenity_mappings:
                    amenities.extend(amenity_mappings[tag_key])
                elif tag_key.startswith('payment:') and tag_key in amenity_mappings:
                    amenities.extend(amenity_mappings[tag_key])
        
        # Amenidades especiais baseadas no tipo
        amenity_type = tags.get('amenity')
        if amenity_type == 'fuel':
            # Para postos, assumir algumas amenidades básicas se não especificadas
            if not any('banheiro' in a for a in amenities) and tags.get('toilets') != 'no':
                amenities.append('banheiro')
        
        # Amenidades baseadas em horário
        opening_hours = tags.get('opening_hours', '')
        if '24/7' in opening_hours or 'Mo-Su 00:00-24:00' in opening_hours:
            amenities.append('24h')
        
        # Remove duplicatas e ordena
        amenities = sorted(list(set(amenities)))
        
        return amenities
    
    def get_route_statistics(
        self,
        origin: str,
        destination: str,
        max_distance_from_road: float = 1000
    ) -> 'RouteStatisticsResponse':
        """
        Gera estatísticas detalhadas de uma rota.
        Sempre busca todos os tipos de POI para estatísticas completas.

        Args:
            origin: Ponto de origem
            destination: Ponto de destino
            max_distance_from_road: Distância máxima da estrada para considerar POIs

        Returns:
            Estatísticas completas da rota
        """
        from api.models.road_models import (
            RouteStatisticsResponse, POIStatistics, RouteStopRecommendation
        )

        # Gerar mapa linear para obter dados (sempre busca todos os POI)
        linear_map = self.generate_linear_map(
            origin=origin,
            destination=destination,
            include_cities=True,
            max_distance_from_road=max_distance_from_road
        )
        
        # Calcular estatísticas por tipo de POI
        poi_stats = []
        all_milestones = []
        
        # Coletar todos os milestones de todos os segmentos
        for segment in linear_map.segments:
            all_milestones.extend(segment.milestones)
        
        # Agrupar por tipo
        poi_types = {}
        for milestone in all_milestones:
            if milestone.type.value not in poi_types:
                poi_types[milestone.type.value] = []
            poi_types[milestone.type.value].append(milestone)
        
        # Calcular estatísticas para cada tipo
        for poi_type, milestones in poi_types.items():
            if poi_type == "city":  # Pular cidades nas estatísticas
                continue
                
            if len(milestones) > 1:
                # Calcular distância média entre POIs
                distances = []
                sorted_milestones = sorted(milestones, key=lambda m: m.distance_from_origin_km)
                for i in range(1, len(sorted_milestones)):
                    distance = sorted_milestones[i].distance_from_origin_km - sorted_milestones[i-1].distance_from_origin_km
                    distances.append(distance)
                
                avg_distance = sum(distances) / len(distances) if distances else 0
            else:
                avg_distance = linear_map.total_length_km
            
            # Calcular densidade por 100km
            density = (len(milestones) / linear_map.total_length_km) * 100 if linear_map.total_length_km > 0 else 0
            
            poi_stats.append(POIStatistics(
                type=poi_type,
                total_count=len(milestones),
                average_distance_km=avg_distance,
                density_per_100km=density
            ))
        
        # Gerar recomendações de paradas
        recommendations = self._generate_stop_recommendations(all_milestones, linear_map.total_length_km)
        
        # Calcular tempo estimado (assumindo 80 km/h de média)
        estimated_time = linear_map.total_length_km / 80.0
        
        # Métricas de qualidade dos dados
        quality_metrics = self._calculate_quality_metrics(all_milestones)
        
        return RouteStatisticsResponse(
            route_info={
                "origin": origin,
                "destination": destination,
                "road_refs": [seg.ref for seg in linear_map.segments if seg.ref],
                "segment_count": len(linear_map.segments)
            },
            total_length_km=linear_map.total_length_km,
            estimated_travel_time_hours=estimated_time,
            poi_statistics=poi_stats,
            recommendations=recommendations,
            quality_metrics=quality_metrics
        )
    
    def _generate_stop_recommendations(
        self, 
        milestones: List['RoadMilestone'], 
        total_length_km: float
    ) -> List['RouteStopRecommendation']:
        """
        Gera recomendações de paradas estratégicas baseadas nos POIs disponíveis.
        """
        from api.models.road_models import RouteStopRecommendation
        
        recommendations = []
        
        # Filtrar apenas POIs úteis para paradas
        useful_milestones = [m for m in milestones if m.type.value in ['gas_station', 'restaurant']]
        useful_milestones.sort(key=lambda m: m.distance_from_origin_km)
        
        # Recomendações baseadas em distância (a cada 200km aproximadamente)
        last_recommended_km = 0
        for milestone in useful_milestones:
            distance_from_last = milestone.distance_from_origin_km - last_recommended_km
            
            # Se passou mais de 150km desde a última recomendação, considerar esta parada
            if distance_from_last >= 150:
                services = []
                reason = ""
                duration = 15  # minutos padrão
                
                if milestone.type.value == 'gas_station':
                    services.append("Combustível")
                    reason = "Reabastecimento recomendado"
                    duration = 10
                    
                if milestone.type.value == 'restaurant':
                    services.append("Alimentação")
                    reason = "Parada para refeição"
                    duration = 30
                
                # Verificar se há outros POIs próximos (até 5km)
                nearby_pois = [
                    m for m in useful_milestones 
                    if abs(m.distance_from_origin_km - milestone.distance_from_origin_km) <= 5
                    and m != milestone
                ]
                
                for nearby in nearby_pois:
                    if nearby.type.value == 'gas_station' and "Combustível" not in services:
                        services.append("Combustível")
                    elif nearby.type.value == 'restaurant' and "Alimentação" not in services:
                        services.append("Alimentação")
                
                if len(services) > 1:
                    reason = "Parada estratégica - múltiplos serviços"
                    duration = 20
                
                # Adicionar amenidades do POI principal
                if milestone.amenities:
                    services.extend(milestone.amenities[:3])  # Limitar a 3 amenidades extras
                
                recommendations.append(RouteStopRecommendation(
                    distance_km=milestone.distance_from_origin_km,
                    reason=reason,
                    available_services=list(set(services)),  # Remove duplicatas
                    recommended_duration_minutes=duration
                ))
                
                last_recommended_km = milestone.distance_from_origin_km
        
        return recommendations[:5]  # Limitar a 5 recomendações
    
    def _calculate_quality_metrics(self, milestones: List['RoadMilestone']) -> Dict[str, Any]:
        """
        Calcula métricas de qualidade dos dados dos POIs.
        """
        if not milestones:
            return {"overall_quality": 0.0, "data_completeness": 0.0}
        
        total_quality = sum(m.quality_score or 0 for m in milestones)
        average_quality = total_quality / len(milestones)
        
        # Calcular completude dos dados
        fields_to_check = ['phone', 'opening_hours', 'website', 'operator', 'brand']
        completeness_scores = []
        
        for milestone in milestones:
            filled_fields = sum(1 for field in fields_to_check if getattr(milestone, field, None))
            completeness = filled_fields / len(fields_to_check)
            completeness_scores.append(completeness)
        
        average_completeness = sum(completeness_scores) / len(completeness_scores)
        
        return {
            "overall_quality": round(average_quality, 2),
            "data_completeness": round(average_completeness, 2),
            "total_pois_analyzed": len(milestones),
            "pois_with_phone": len([m for m in milestones if m.phone]),
            "pois_with_hours": len([m for m in milestones if m.opening_hours]),
            "pois_with_website": len([m for m in milestones if m.website])
        }

    async def geocode_location_async(self, address: str) -> Optional[Tuple[float, float]]:
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
        self, 
        location: Tuple[float, float], 
        radius: float, 
        categories: List[str]
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
            from ..providers.models import GeoLocation, POICategory
            
            # Convert location to GeoLocation
            geo_location = GeoLocation(latitude=location[0], longitude=location[1])
            
            # Convert category strings to POICategory enums
            poi_categories = []
            for category in categories:
                try:
                    poi_categories.append(POICategory(category))
                except ValueError:
                    # Skip unknown categories
                    logger.warning(f"Unknown POI category: {category}")
                    continue
            
            if not poi_categories:
                return []
            
            # Search using the provider
            pois = await self.geo_provider.search_pois(
                location=geo_location,
                radius=radius,
                categories=poi_categories
            )
            
            # Convert POIs back to dictionaries for compatibility
            result = []
            for poi in pois:
                result.append({
                    'id': poi.id,
                    'name': poi.name,
                    'lat': poi.location.latitude,
                    'lon': poi.location.longitude,
                    'category': poi.category.value,
                    'amenities': poi.amenities,
                    'rating': poi.rating,
                    'is_open': poi.is_open,
                    'phone': poi.phone,
                    'website': poi.website,
                    'tags': poi.provider_data.get('tags', poi.provider_data)
                })
            
            return result
            
        except Exception as e:
            logger.error(f"Error searching POIs: {e}")
            return []
    
    def _calculate_distance_meters(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """
        Calculate the distance between two points using Haversine formula.
        
        Args:
            lat1, lon1: First point coordinates
            lat2, lon2: Second point coordinates
            
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
        
        a = (math.sin(dlat/2) * math.sin(dlat/2) + 
             math.cos(lat1_rad) * math.cos(lat2_rad) * 
             math.sin(dlon/2) * math.sin(dlon/2))
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        
        # Earth radius in meters
        R = 6371000  
        distance = R * c
        
        return distance

    def _calculate_distance_along_route(
        self, 
        geometry: List[Tuple[float, float]], 
        target_point: Tuple[float, float]
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
        min_distance = float('inf')
        closest_segment_idx = 0
        
        for i in range(len(geometry) - 1):
            # Calculate distance from target to this segment
            seg_start = geometry[i]
            seg_end = geometry[i + 1]
            
            # Distance to segment midpoint (simplified)
            midpoint = ((seg_start[0] + seg_end[0]) / 2, (seg_start[1] + seg_end[1]) / 2)
            dist = self._calculate_distance_meters(
                target_point[0], target_point[1],
                midpoint[0], midpoint[1]
            )
            
            if dist < min_distance:
                min_distance = dist
                closest_segment_idx = i
        
        # Calculate cumulative distance up to the closest segment
        cumulative_distance = 0.0
        for i in range(closest_segment_idx):
            cumulative_distance += self._calculate_distance_meters(
                geometry[i][0], geometry[i][1],
                geometry[i + 1][0], geometry[i + 1][1]
            )
        
        # Convert to km
        return cumulative_distance / 1000.0

    def _calculate_distance_from_point_to_end(
        self,
        geometry: List[Tuple[float, float]],
        start_point: Tuple[float, float]
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
        min_distance = float('inf')
        closest_segment_idx = 0
        projection_point = start_point
        
        for i in range(len(geometry) - 1):
            seg_start = geometry[i]
            seg_end = geometry[i + 1]
            
            # Calculate projection of start_point onto this segment
            # For simplicity, we'll use the midpoint approach like in the original method
            midpoint = ((seg_start[0] + seg_end[0]) / 2, (seg_start[1] + seg_end[1]) / 2)
            dist = self._calculate_distance_meters(
                start_point[0], start_point[1],
                midpoint[0], midpoint[1]
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
            cumulative_distance += self._calculate_distance_meters(
                geometry[i][0], geometry[i][1],
                geometry[i + 1][0], geometry[i + 1][1]
            )
        
        # Also add the distance from the start_point to the projection_point
        cumulative_distance += self._calculate_distance_meters(
            start_point[0], start_point[1],
            projection_point[0], projection_point[1]
        )
        
        # Convert to km
        return cumulative_distance / 1000.0

    def _determine_poi_side(
        self,
        main_route_geometry: List[Tuple[float, float]],
        junction_point: Tuple[float, float],
        poi_location: Tuple[float, float]
    ) -> str:
        """
        Determine if POI is on the left or right side of the road.
        
        Uses cross product to determine the side relative to the road direction.
        
        Args:
            main_route_geometry: Main route geometry as list of (lat, lon) tuples
            junction_point: Junction coordinates (lat, lon)
            poi_location: POI coordinates (lat, lon)
            
        Returns:
            'left' or 'right'
        """
        # Find the segment in main route closest to junction point
        min_distance = float('inf')
        segment_idx = 0
        
        for i in range(len(main_route_geometry) - 1):
            seg_start = main_route_geometry[i]
            seg_end = main_route_geometry[i + 1]
            midpoint = ((seg_start[0] + seg_end[0]) / 2, (seg_start[1] + seg_end[1]) / 2)
            
            dist = self._calculate_distance_meters(
                junction_point[0], junction_point[1],
                midpoint[0], midpoint[1]
            )
            
            if dist < min_distance:
                min_distance = dist
                segment_idx = i
        
        # Get the road direction vector at junction
        seg_start = main_route_geometry[segment_idx]
        seg_end = main_route_geometry[segment_idx + 1]
        
        # Vector from segment start to end (road direction)
        road_vector = (seg_end[1] - seg_start[1], seg_end[0] - seg_start[0])  # (dx, dy)
        
        # Vector from junction to POI
        poi_vector = (poi_location[1] - junction_point[1], poi_location[0] - junction_point[0])  # (dx, dy)
        
        # Cross product in 2D: road_vector x poi_vector
        # If positive: POI is to the left (counter-clockwise)
        # If negative: POI is to the right (clockwise)
        cross_product = road_vector[0] * poi_vector[1] - road_vector[1] * poi_vector[0]
        
        side = 'left' if cross_product > 0 else 'right'
        
        logger.debug(f"🧭 Determinando lado do POI: road_vector={road_vector}, "
                    f"poi_vector={poi_vector}, cross_product={cross_product:.2f} → {side}")
        
        return side

    def _find_route_intersection(
        self,
        main_route_geometry: List[Tuple[float, float]],
        access_route_geometry: List[Tuple[float, float]],
        tolerance_meters: float = 100.0
    ) -> Optional[Tuple[Tuple[float, float], float]]:
        """
        Find the intersection point between main route and access route.
        
        This method finds the LAST point where the access route is still
        on/near the main route before deviating to reach the POI.
        This represents the true junction/exit point.
        
        Args:
            main_route_geometry: Main route geometry [(lat, lon), ...]
            access_route_geometry: Access route to POI [(lat, lon), ...]
            tolerance_meters: Maximum distance to consider points as "on the route"
            
        Returns:
            Tuple of (junction_point, junction_distance_km) or None if no intersection found
        """
        if not main_route_geometry or not access_route_geometry:
            return None
        
        # Strategy: Iterate through access route from start to end
        # Find the LAST point that is still close to the main route
        # This is where the driver exits the main route to reach the POI
        
        last_intersection_point = None
        last_intersection_on_main = None
        
        # Check each point in access route from start to end
        for i, access_point in enumerate(access_route_geometry):
            # Find the closest point on main route to this access point
            min_distance = float('inf')
            closest_main_point = None
            
            for main_point in main_route_geometry:
                distance = self._calculate_distance_meters(
                    access_point[0], access_point[1],
                    main_point[0], main_point[1]
                )
                
                if distance < min_distance:
                    min_distance = distance
                    closest_main_point = main_point
            
            # If this access point is close enough to main route, it's still on the route
            if min_distance < tolerance_meters and closest_main_point:
                last_intersection_point = access_point
                last_intersection_on_main = closest_main_point
            else:
                # Access route has deviated from main route
                # If we found at least one intersection before, use the last one
                if last_intersection_on_main:
                    logger.debug(f"🔍 Rota de acesso se desviou da principal no ponto {i}")
                    break
        
        if last_intersection_on_main:
            # Calculate distance along main route to the junction point
            junction_distance_km = self._calculate_distance_along_route(
                main_route_geometry, last_intersection_on_main
            )
            logger.debug(f"🔍 Entroncamento final: lat={last_intersection_on_main[0]:.6f}, "
                        f"lon={last_intersection_on_main[1]:.6f}, km={junction_distance_km:.1f}")
            return (last_intersection_on_main, junction_distance_km)
        
        return None

    async def _calculate_junction_for_distant_poi(
        self,
        poi: POI,
        search_point: Tuple[float, float],
        search_point_distance_km: float,
        main_route: Route
    ) -> Optional[Tuple[float, Tuple[float, float], float, str]]:
        """
        Calculate the junction/exit point for a distant POI.

        For POIs that are far from the road (>500m), this calculates where
        the driver needs to exit the main route to reach the POI.

        Args:
            poi: The POI object
            search_point: The search point on main route closest to POI (lat, lon)
            search_point_distance_km: Distance of search point from origin
            main_route: The complete main route object with geometry

        Returns:
            Tuple of (junction_distance_km, junction_coordinates, access_route_distance_km, side) or None if not found
            where side is 'left' or 'right'
        """
        # Calculate distance from POI to search point
        poi_distance_from_road_m = self._calculate_distance_meters(
            poi.location.latitude, poi.location.longitude,
            search_point[0], search_point[1]
        )
        
        # Determine lookback distance based on POI distance
        # Further POIs might have junctions further back
        poi_distance_km = poi_distance_from_road_m / 1000.0
        lookback_km = min(20.0, max(5.0, poi_distance_km * 2))
        
        logger.debug(f"🔍 Calculando entroncamento para {poi.name}: "
                    f"distância da estrada={poi_distance_km:.1f}km, lookback={lookback_km:.1f}km")
        
        # Find lookback point on main route
        lookback_distance_km = max(0, search_point_distance_km - lookback_km)
        
        # Interpolate lookback point on main route geometry
        lookback_point = self._interpolate_coordinate_at_distance(
            main_route.geometry,
            lookback_distance_km,
            main_route.total_distance
        )
        
        logger.debug(f"🔍 Ponto lookback: lat={lookback_point[0]:.6f}, lon={lookback_point[1]:.6f}, "
                    f"distância={lookback_distance_km:.1f}km")
        
        try:
            # Calculate route from lookback point to POI
            access_route = await self.geo_provider.calculate_route(
                GeoLocation(latitude=lookback_point[0], longitude=lookback_point[1]),
                GeoLocation(latitude=poi.location.latitude, longitude=poi.location.longitude)
            )
            
            if not access_route or not access_route.geometry:
                logger.debug(f"⚠️ Não foi possível calcular rota de acesso para {poi.name}")
                return None
            
            logger.debug(f"🔍 Rota de acesso calculada: {len(access_route.geometry)} pontos, "
                        f"{access_route.total_distance:.1f}km")
            
            # Find intersection between access route and main route
            intersection = self._find_route_intersection(
                main_route.geometry,
                access_route.geometry,
                tolerance_meters=150.0  # Allow 150m tolerance
            )
            
            if intersection:
                junction_coords, junction_distance = intersection

                # Calculate distance along access route from junction to POI
                # Use the new method that calculates from junction point to end of route
                access_route_distance_km = self._calculate_distance_from_point_to_end(
                    access_route.geometry,
                    junction_coords
                )

                # Determine which side of the road the POI is on
                poi_location = (poi.location.latitude, poi.location.longitude)
                side = self._determine_poi_side(
                    main_route.geometry,
                    junction_coords,
                    poi_location
                )

                logger.info(f"✅ Entroncamento encontrado para {poi.name}: "
                           f"km {junction_distance:.1f} "
                           f"(lat={junction_coords[0]:.6f}, lon={junction_coords[1]:.6f}), "
                           f"distância do entroncamento ao POI={access_route_distance_km:.1f}km, "
                           f"lado={side}")
                return (junction_distance, junction_coords, access_route_distance_km, side)
            else:
                logger.debug(f"⚠️ Nenhuma interseção encontrada entre rota principal e rota de acesso para {poi.name}")
                return None
                
        except Exception as e:
            logger.error(f"❌ Erro calculando entroncamento para {poi.name}: {e}")
            return None
