"""
Database-backed service for storing and managing saved linear maps.

This service handles:
- Saving linear maps to PostgreSQL database
- Loading saved maps
- Listing user's maps (via user_maps association)
- Listing all available maps (for browsing)
- Adopting existing maps
- Unlinking maps from user (soft delete)
- Permanently deleting maps (admin only)

Maps are now global/shared - multiple users can have the same map in their collection.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from api.database.models.map import Map
from api.database.models.map_poi import MapPOI
from api.database.models.poi import POI
from api.database.models.route_segment import RouteSegment
from api.database.models.user_map import UserMap
from api.database.repositories import MapPOIRepository, MapRepository, POIRepository
from api.database.repositories.user_map import UserMapRepository
from api.providers.base import GeoProvider
from api.services.map_assembly_service import MapAssemblyService
from api.services.poi_debug_service import POIDebugDataCollector, POIDebugService
from api.models.road_models import (
    Coordinates,
    LinearMapResponse,
    LinearRoadSegment,
    MilestoneType,
    RoadMilestone,
    SavedMapResponse,
)

logger = logging.getLogger(__name__)


class MapStorageServiceDB:
    """Service for managing saved linear maps in database."""

    def __init__(self, session: AsyncSession):
        """
        Initialize the map storage service with a database session.

        Args:
            session: SQLAlchemy async session (injected via FastAPI Depends)
        """
        self.session = session
        self.map_repo = MapRepository(session)
        self.poi_repo = POIRepository(session)
        self.map_poi_repo = MapPOIRepository(session)
        self.user_map_repo = UserMapRepository(session)
        # Lazy-loaded repositories for segment operations
        self._map_segment_repo = None
        self._route_segment_repo = None

    @property
    def map_segment_repo(self):
        """Lazy-load MapSegmentRepository."""
        if self._map_segment_repo is None:
            from api.database.repositories.map_segment import MapSegmentRepository
            self._map_segment_repo = MapSegmentRepository(self.session)
        return self._map_segment_repo

    @property
    def route_segment_repo(self):
        """Lazy-load RouteSegmentRepository."""
        if self._route_segment_repo is None:
            from api.database.repositories.route_segment import RouteSegmentRepository
            self._route_segment_repo = RouteSegmentRepository(self.session)
        return self._route_segment_repo

    async def save_map(
        self,
        linear_map: LinearMapResponse,
        geo_provider: GeoProvider,
        user_id: Optional[UUID] = None,
        debug_collector: Optional[POIDebugDataCollector] = None,
        route_segments_data: Optional[List[Tuple[RouteSegment, bool]]] = None,
        route_geometry: Optional[List[Tuple[float, float]]] = None,
        route_total_km: Optional[float] = None,
    ) -> str:
        """
        Save a linear map to database and associate with user if provided.

        Args:
            linear_map: The linear map to save
            geo_provider: Geographic provider for access route calculation
            user_id: Optional user ID to associate the map with (creator)
            debug_collector: Optional debug data collector with POI debug info
            route_segments_data: Optional list of (RouteSegment, is_new) tuples
            route_geometry: Optional full route geometry for junction calculation
            route_total_km: Optional total route length in km

        Returns:
            The ID of the saved map
        """
        try:
            # Convert LinearMapResponse to Map model
            map_id = UUID(linear_map.id) if linear_map.id else uuid4()

            # Serialize segments to JSONB
            segments_data = [self._segment_to_dict(seg) for seg in linear_map.segments]

            # Create metadata
            metadata = {
                "road_refs": self._extract_road_refs(linear_map.segments),
                "creation_date": linear_map.creation_date.isoformat(),
            }

            # Create Map record (without user_id - maps are now global)
            db_map = Map(
                id=map_id,
                origin=linear_map.origin,
                destination=linear_map.destination,
                total_length_km=linear_map.total_length_km,
                road_id=linear_map.road_id,
                segments=segments_data,
                metadata_=metadata,
                created_at=linear_map.creation_date,
                updated_at=datetime.now(),
                created_by_user_id=user_id,  # Track who created it
            )
            await self.map_repo.create(db_map)

            # Create user-map association if user provided
            if user_id:
                await self.user_map_repo.add_map_to_user(
                    user_id=user_id, map_id=map_id, is_creator=True
                )

            # Use MapAssemblyService to create MapSegments and MapPOIs
            milestone_to_map_poi: Dict[str, UUID] = {}
            if not route_segments_data or not route_geometry or not route_total_km:
                raise ValueError(
                    "route_segments_data, route_geometry, and route_total_km are required"
                )

            # Extract just the RouteSegments (not the is_new flag)
            route_segments = [seg for seg, _ in route_segments_data]

            # Extract origin city name for POI filtering
            origin_city = self._extract_city_name(linear_map.origin)

            assembly_service = MapAssemblyService(self.session, geo_provider)
            num_segments, num_pois, milestone_to_map_poi = await assembly_service.assemble_map(
                map_id=map_id,
                segments=route_segments,
                route_geometry=route_geometry,
                route_total_km=route_total_km,
                debug_collector=debug_collector,
                origin_city=origin_city,
            )
            logger.info(
                f"Assembled map with {num_segments} segments and {num_pois} POIs"
            )

            # Persist debug data if collector provided
            if debug_collector and milestone_to_map_poi:
                try:
                    debug_service = POIDebugService(self.session)
                    count = await debug_service.persist_debug_data(
                        map_id=map_id,
                        poi_id_to_map_poi_id=milestone_to_map_poi,
                        collector=debug_collector,
                    )
                    if count > 0:
                        logger.info(f"Persistidos {count} registros de debug para mapa {map_id}")
                except Exception as e:
                    logger.warning(f"Erro ao persistir dados de debug: {e}")
                    # Don't fail the map save if debug persistence fails

            logger.info(
                f"Mapa linear salvo no banco: {linear_map.origin} -> {linear_map.destination} (ID: {map_id})"
            )
            return str(map_id)

        except Exception as e:
            logger.error(f"Erro ao salvar mapa no banco: {e}")
            raise

    async def load_map(
        self, map_id: str, user_id: Optional[UUID] = None
    ) -> Optional[LinearMapResponse]:
        """
        Load a saved map from database.

        Args:
            map_id: ID of the map to load
            user_id: Optional user ID to verify access (via user_maps)

        Returns:
            The loaded linear map, or None if not found/not accessible
        """
        try:
            map_uuid = UUID(map_id)

            # If user_id provided, verify user has access to this map
            if user_id:
                has_access = await self.user_map_repo.user_has_map(user_id, map_uuid)
                if not has_access:
                    logger.warning(
                        f"User {user_id} does not have access to map {map_id}"
                    )
                    return None

            db_map = await self.map_repo.get_by_id_with_pois(map_uuid)

            if not db_map:
                logger.warning(f"Mapa nao encontrado: {map_id}")
                return None

            # Load POIs with details
            map_pois = await self.map_poi_repo.get_pois_for_map(
                map_uuid, include_poi_details=True
            )

            # Convert segments from JSONB
            segments = [self._dict_to_segment(seg_data) for seg_data in db_map.segments]

            # Convert POIs to milestones
            milestones = [self._map_poi_to_milestone(map_poi) for map_poi in map_pois]

            # Get creation date from metadata or created_at
            creation_date = db_map.created_at
            if db_map.metadata_ and "creation_date" in db_map.metadata_:
                creation_date = datetime.fromisoformat(
                    db_map.metadata_["creation_date"]
                )

            linear_map = LinearMapResponse(
                id=str(db_map.id),
                origin=db_map.origin,
                destination=db_map.destination,
                total_length_km=db_map.total_length_km,
                road_id=db_map.road_id or "",
                segments=segments,
                milestones=milestones,
                creation_date=creation_date,
            )

            logger.info(
                f"Mapa carregado: {linear_map.origin} -> {linear_map.destination}"
            )
            return linear_map

        except ValueError as e:
            logger.warning(f"Erro de valor ao carregar mapa {map_id}: {e}")
            return None
        except Exception as e:
            logger.error(f"Erro ao carregar mapa {map_id}: {e}", exc_info=True)
            return None

    async def list_user_maps(self, user_id: UUID) -> List[SavedMapResponse]:
        """
        List all maps associated with a user (via user_maps).

        Args:
            user_id: User UUID

        Returns:
            List of saved map metadata, sorted by added_at (newest first)
        """
        try:
            # Get user's map associations
            user_maps = await self.user_map_repo.get_user_maps(user_id, limit=100)
            saved_maps = []

            for user_map in user_maps:
                db_map = user_map.map

                # Count POIs for this map
                pois = await self.map_poi_repo.get_pois_for_map(db_map.id)

                # Extract road refs from metadata
                road_refs = []
                if db_map.metadata_ and "road_refs" in db_map.metadata_:
                    road_refs = db_map.metadata_["road_refs"]

                # Get creation date
                creation_date = db_map.created_at
                if db_map.metadata_ and "creation_date" in db_map.metadata_:
                    try:
                        creation_date = datetime.fromisoformat(
                            db_map.metadata_["creation_date"]
                        )
                    except (ValueError, TypeError):
                        pass

                saved_map = SavedMapResponse(
                    id=str(db_map.id),
                    name=None,
                    origin=db_map.origin,
                    destination=db_map.destination,
                    total_length_km=db_map.total_length_km,
                    creation_date=creation_date,
                    road_refs=road_refs,
                    milestone_count=len(pois),
                )
                saved_maps.append(saved_map)

            logger.info(f"Listados {len(saved_maps)} mapas para usuario {user_id}")
            return saved_maps

        except Exception as e:
            logger.error(f"Erro ao listar mapas do usuario: {e}")
            return []

    async def list_available_maps(
        self,
        skip: int = 0,
        limit: int = 100,
        origin: Optional[str] = None,
        destination: Optional[str] = None,
    ) -> List[SavedMapResponse]:
        """
        List all available maps for browsing.

        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            origin: Optional origin filter (partial match)
            destination: Optional destination filter (partial match)

        Returns:
            List of available maps
        """
        try:
            if origin or destination:
                # Search by location
                search_term = origin or destination or ""
                maps = await self.map_repo.search_by_location(search_term, limit=limit)
            else:
                maps = await self.map_repo.get_all_maps(skip=skip, limit=limit)

            saved_maps = []

            for db_map in maps:
                # Count POIs for this map
                pois = await self.map_poi_repo.get_pois_for_map(db_map.id)

                # Count users with this map
                user_count = await self.user_map_repo.get_map_user_count(db_map.id)

                # Extract road refs from metadata
                road_refs = []
                if db_map.metadata_ and "road_refs" in db_map.metadata_:
                    road_refs = db_map.metadata_["road_refs"]

                # Get creation date
                creation_date = db_map.created_at
                if db_map.metadata_ and "creation_date" in db_map.metadata_:
                    try:
                        creation_date = datetime.fromisoformat(
                            db_map.metadata_["creation_date"]
                        )
                    except (ValueError, TypeError):
                        pass

                saved_map = SavedMapResponse(
                    id=str(db_map.id),
                    name=None,
                    origin=db_map.origin,
                    destination=db_map.destination,
                    total_length_km=db_map.total_length_km,
                    creation_date=creation_date,
                    road_refs=road_refs,
                    milestone_count=len(pois),
                )
                saved_maps.append(saved_map)

            logger.info(f"Listados {len(saved_maps)} mapas disponiveis")
            return saved_maps

        except Exception as e:
            logger.error(f"Erro ao listar mapas disponiveis: {e}")
            return []

    async def get_suggested_maps(
        self,
        limit: int = 10,
        user_lat: Optional[float] = None,
        user_lon: Optional[float] = None,
    ) -> List[SavedMapResponse]:
        """
        Get suggested maps for the create page.

        Returns a small number of maps, optionally sorted by proximity to user's location.
        If lat/lon provided, maps with origin near the user are prioritized.

        Args:
            limit: Maximum number of maps to return
            user_lat: User's latitude (optional)
            user_lon: User's longitude (optional)

        Returns:
            List of suggested maps
        """
        import math

        def haversine_distance(
            lat1: float, lon1: float, lat2: float, lon2: float
        ) -> float:
            """Calculate distance in km between two points."""
            R = 6371  # Earth radius in km
            phi1 = math.radians(lat1)
            phi2 = math.radians(lat2)
            delta_phi = math.radians(lat2 - lat1)
            delta_lambda = math.radians(lon2 - lon1)
            a = (
                math.sin(delta_phi / 2) ** 2
                + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
            )
            c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
            return R * c

        try:
            # Get more maps than needed so we can sort and filter
            maps = await self.map_repo.get_all_maps(skip=0, limit=limit * 3)

            saved_maps = []
            maps_with_distance = []

            for db_map in maps:
                # Count POIs for this map
                pois = await self.map_poi_repo.get_pois_for_map(db_map.id)

                # Extract road refs from metadata
                road_refs = []
                if db_map.metadata_ and "road_refs" in db_map.metadata_:
                    road_refs = db_map.metadata_["road_refs"]

                # Get creation date
                creation_date = db_map.created_at
                if db_map.metadata_ and "creation_date" in db_map.metadata_:
                    try:
                        creation_date = datetime.fromisoformat(
                            db_map.metadata_["creation_date"]
                        )
                    except (ValueError, TypeError):
                        pass

                saved_map = SavedMapResponse(
                    id=str(db_map.id),
                    name=None,
                    origin=db_map.origin,
                    destination=db_map.destination,
                    total_length_km=db_map.total_length_km,
                    creation_date=creation_date,
                    road_refs=road_refs,
                    milestone_count=len(pois),
                )

                # Calculate distance if user location provided and segments available
                distance = float("inf")
                if user_lat is not None and user_lon is not None and db_map.segments:
                    try:
                        # Get first segment's start point
                        first_segment = db_map.segments[0]
                        if (
                            isinstance(first_segment, dict)
                            and "coordinates" in first_segment
                        ):
                            coords = first_segment["coordinates"]
                            if coords and len(coords) > 0:
                                first_point = coords[0]
                                if len(first_point) >= 2:
                                    # OSRM returns [lon, lat]
                                    origin_lon, origin_lat = (
                                        first_point[0],
                                        first_point[1],
                                    )
                                    distance = haversine_distance(
                                        user_lat, user_lon, origin_lat, origin_lon
                                    )
                    except (KeyError, IndexError, TypeError) as e:
                        logger.debug(
                            f"Could not get coordinates for map {db_map.id}: {e}"
                        )

                maps_with_distance.append((saved_map, distance))

            # Sort by distance if user location provided
            if user_lat is not None and user_lon is not None:
                maps_with_distance.sort(key=lambda x: x[1])

            # Take only the requested limit
            saved_maps = [m[0] for m in maps_with_distance[:limit]]

            logger.info(f"Sugeridos {len(saved_maps)} mapas")
            return saved_maps

        except Exception as e:
            logger.error(f"Erro ao obter mapas sugeridos: {e}")
            return []

    async def adopt_map(self, map_id: str, user_id: UUID) -> bool:
        """
        Add an existing map to user's collection.

        Args:
            map_id: ID of the map to adopt
            user_id: User UUID

        Returns:
            True if adopted successfully, False if map not found or already adopted
        """
        try:
            map_uuid = UUID(map_id)

            # Check if map exists
            map_exists = await self.map_repo.exists(map_uuid)
            if not map_exists:
                logger.warning(f"Map not found for adoption: {map_id}")
                return False

            # Check if user already has this map
            already_has = await self.user_map_repo.user_has_map(user_id, map_uuid)
            if already_has:
                logger.info(f"User {user_id} already has map {map_id}")
                return True  # Already has it, consider success

            # Add map to user's collection
            await self.user_map_repo.add_map_to_user(
                user_id=user_id, map_id=map_uuid, is_creator=False
            )

            logger.info(f"User {user_id} adopted map {map_id}")
            return True

        except ValueError:
            logger.warning(f"Invalid map ID for adoption: {map_id}")
            return False
        except Exception as e:
            logger.error(f"Error adopting map {map_id}: {e}")
            return False

    async def unlink_map(self, map_id: str, user_id: UUID) -> bool:
        """
        Remove map from user's collection (does NOT delete the map).

        Args:
            map_id: ID of the map to unlink
            user_id: User UUID

        Returns:
            True if unlinked successfully, False if not found
        """
        try:
            map_uuid = UUID(map_id)

            removed = await self.user_map_repo.remove_map_from_user(user_id, map_uuid)

            if removed:
                logger.info(f"User {user_id} unlinked map {map_id}")
            else:
                logger.warning(f"Map {map_id} not in user {user_id}'s collection")

            return removed

        except ValueError:
            logger.warning(f"Invalid map ID for unlink: {map_id}")
            return False
        except Exception as e:
            logger.error(f"Error unlinking map {map_id}: {e}")
            return False

    async def delete_map_permanently(self, map_id: str) -> bool:
        """
        Permanently delete a map from database (admin only).
        This removes the map and all associated user_maps entries.
        Also decrements usage_count on associated RouteSegments.

        Args:
            map_id: ID of the map to delete

        Returns:
            True if deleted successfully, False otherwise
        """
        try:
            map_uuid = UUID(map_id)

            # Get segment IDs before deletion to decrement their usage counts
            segment_ids = await self.map_segment_repo.get_segment_ids_for_map(map_uuid)

            # Decrement usage count for all segments used by this map
            if segment_ids:
                await self.route_segment_repo.bulk_decrement_usage(segment_ids)
                logger.info(
                    f"Decremented usage_count for {len(segment_ids)} segments "
                    f"(map {map_id})"
                )

            # Delete the map (cascades to MapSegments, MapPOIs, etc.)
            deleted = await self.map_repo.delete_by_id(map_uuid)

            if deleted:
                logger.info(f"Map permanently deleted: {map_id}")
            else:
                logger.warning(f"Map not found for permanent deletion: {map_id}")

            return deleted

        except ValueError:
            logger.warning(f"Invalid map ID for deletion: {map_id}")
            return False
        except Exception as e:
            logger.error(f"Error permanently deleting map {map_id}: {e}")
            return False

    async def user_has_map(self, user_id: UUID, map_id: str) -> bool:
        """
        Check if user has a map in their collection.

        Args:
            user_id: User UUID
            map_id: Map ID string

        Returns:
            True if user has the map, False otherwise
        """
        try:
            map_uuid = UUID(map_id)
            return await self.user_map_repo.user_has_map(user_id, map_uuid)
        except ValueError:
            return False

    async def map_exists(self, map_id: str) -> bool:
        """
        Check if a map exists.

        Args:
            map_id: ID of the map to check

        Returns:
            True if map exists, False otherwise
        """
        try:
            map_uuid = UUID(map_id)
            return await self.map_repo.exists(map_uuid)
        except ValueError:
            return False

    # Legacy method - kept for backwards compatibility during migration
    async def list_maps(self, user_id: Optional[UUID] = None) -> List[SavedMapResponse]:
        """
        List maps. If user_id provided, lists user's maps. Otherwise lists recent maps.

        DEPRECATED: Use list_user_maps() or list_available_maps() instead.
        """
        if user_id:
            return await self.list_user_maps(user_id)
        return await self.list_available_maps(limit=100)

    # Legacy method - kept for backwards compatibility during migration
    async def delete_map(self, map_id: str, user_id: Optional[UUID] = None) -> bool:
        """
        Delete/unlink a map.

        DEPRECATED: Use unlink_map() for users or delete_map_permanently() for admins.
        """
        if user_id:
            return await self.unlink_map(map_id, user_id)
        return await self.delete_map_permanently(map_id)

    # Helper methods for conversion

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

    def _segment_to_dict(self, segment: LinearRoadSegment) -> dict:
        """Convert LinearRoadSegment to dict for JSONB storage."""
        return segment.model_dump(mode="json")

    def _dict_to_segment(self, data: dict) -> LinearRoadSegment:
        """Convert dict from JSONB to LinearRoadSegment."""
        return LinearRoadSegment(**data)

    def _map_poi_to_milestone(self, map_poi: MapPOI) -> RoadMilestone:
        """Convert MapPOI + POI to RoadMilestone."""
        poi = map_poi.poi

        # Build junction coordinates if available
        junction_coordinates = None
        if map_poi.junction_lat is not None and map_poi.junction_lon is not None:
            junction_coordinates = Coordinates(
                latitude=map_poi.junction_lat, longitude=map_poi.junction_lon
            )

        # Mapping for POI types that don't exist directly in MilestoneType
        poi_type_mapping = {
            "food": MilestoneType.RESTAURANT,
            "fuel": MilestoneType.GAS_STATION,
            "lodging": MilestoneType.HOTEL,
        }

        # Safely convert POI type to MilestoneType
        poi_type = poi.type
        if poi_type in poi_type_mapping:
            milestone_type = poi_type_mapping[poi_type]
        else:
            try:
                milestone_type = MilestoneType(poi_type)
            except ValueError:
                # Type not in MilestoneType enum - use OTHER as fallback
                logger.debug(
                    f"Unknown POI type '{poi_type}' for POI {poi.id}, using OTHER"
                )
                milestone_type = MilestoneType.OTHER

        return RoadMilestone(
            id=str(poi.id),
            name=poi.name,
            type=milestone_type,
            coordinates=Coordinates(latitude=poi.latitude, longitude=poi.longitude),
            distance_from_origin_km=map_poi.distance_from_origin_km,
            distance_from_road_meters=map_poi.distance_from_road_meters,
            side=map_poi.side,
            tags=poi.tags or {},
            city=poi.city,
            operator=poi.operator,
            brand=poi.brand,
            opening_hours=poi.opening_hours,
            phone=poi.phone,
            website=poi.website,
            cuisine=poi.cuisine,
            amenities=poi.amenities or [],
            quality_score=map_poi.quality_score,
            rating=poi.rating,
            rating_count=poi.rating_count,
            google_maps_uri=poi.google_maps_uri,
            junction_distance_km=map_poi.junction_distance_km,
            junction_coordinates=junction_coordinates,
            requires_detour=map_poi.requires_detour,
        )

    def _find_segment_index(
        self, distance_km: float, segments: List[LinearRoadSegment]
    ) -> Optional[int]:
        """Find which segment a POI belongs to based on distance."""
        for i, segment in enumerate(segments):
            if segment.start_distance_km <= distance_km <= segment.end_distance_km:
                return i
        return None

    def _extract_road_refs(self, segments: List[LinearRoadSegment]) -> List[str]:
        """Extract unique road references from segments."""
        refs = set()
        for segment in segments:
            if segment.ref:
                refs.add(segment.ref)
        return list(refs)


# Sync wrappers for use in background tasks and sync contexts


def _create_standalone_session():
    """
    Create a completely standalone async session with its own engine.
    This avoids event loop conflicts when called from sync contexts.
    """
    from sqlalchemy.ext.asyncio import (
        AsyncSession,
        async_sessionmaker,
        create_async_engine,
    )

    from api.providers.settings import get_settings

    settings = get_settings()
    database_url = (
        f"postgresql+asyncpg://{settings.postgres_user}:{settings.postgres_password}"
        f"@{settings.postgres_host}:{settings.postgres_port}/{settings.postgres_database}"
    )

    # Create a fresh engine for this sync operation
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

    return engine, session_maker


def save_map_sync(
    linear_map: LinearMapResponse,
    geo_provider: GeoProvider,
    user_id: Optional[str] = None,
    debug_collector: Optional[POIDebugDataCollector] = None,
    route_segments_data: Optional[List[Tuple[Any, bool]]] = None,
    route_geometry: Optional[List[Tuple[float, float]]] = None,
    route_total_km: Optional[float] = None,
) -> str:
    """
    Sync wrapper for saving a map to the database.
    Use this from sync contexts (like RoadService.generate_linear_map).

    Args:
        linear_map: The linear map to save
        geo_provider: Geographic provider for access route calculation
        user_id: Optional user ID to associate the map with (as creator)
        debug_collector: Optional debug data collector with POI debug info
        route_segments_data: Optional list of (RouteSegment, is_new) tuples
        route_geometry: Optional full route geometry for junction calculation
        route_total_km: Optional total route length in km

    Returns:
        The ID of the saved map
    """
    import asyncio
    from uuid import UUID as PyUUID

    async def _save():
        engine, session_maker = _create_standalone_session()
        try:
            async with session_maker() as session:
                try:
                    storage = MapStorageServiceDB(session)
                    # Convert string user_id to UUID if provided
                    uuid_user_id = PyUUID(user_id) if user_id else None
                    result = await storage.save_map(
                        linear_map,
                        geo_provider=geo_provider,
                        user_id=uuid_user_id,
                        debug_collector=debug_collector,
                        route_segments_data=route_segments_data,
                        route_geometry=route_geometry,
                        route_total_km=route_total_km,
                    )
                    await session.commit()
                    return result
                except Exception:
                    await session.rollback()
                    raise
        finally:
            await engine.dispose()

    # Run in a new event loop
    return asyncio.run(_save())


def delete_map_sync(map_id: str) -> bool:
    """
    Sync wrapper for permanently deleting a map from the database.
    Use this from sync contexts (like background tasks).

    Args:
        map_id: ID of the map to delete

    Returns:
        True if deleted successfully, False otherwise
    """
    import asyncio

    async def _delete():
        engine, session_maker = _create_standalone_session()
        try:
            async with session_maker() as session:
                try:
                    storage = MapStorageServiceDB(session)
                    result = await storage.delete_map_permanently(map_id)
                    await session.commit()
                    return result
                except Exception:
                    await session.rollback()
                    raise
        finally:
            await engine.dispose()

    # Run in a new event loop
    return asyncio.run(_delete())


async def replace_map_data_async(
    original_map_id: str,
    temp_map_id: str,
    session: AsyncSession
) -> bool:
    """
    Replace the data of an original map with data from a temporary map.

    This is used for map regeneration with segment versioning to:
    1. Keep the original map ID (preserving user associations)
    2. Update the map with fresh data from the regenerated temporary map
    3. Handle segment versioning (old segments have usage decremented,
       new segments are moved to the original map)
    4. Delete the temporary map

    Args:
        original_map_id: ID of the original map to update
        temp_map_id: ID of the temporary map with new data
        session: Database session

    Returns:
        True if successful, False otherwise
    """
    from sqlalchemy import update, delete
    from api.database.models.poi_debug_data import POIDebugData
    from api.database.models.map_segment import MapSegment
    from api.database.repositories.route_segment import RouteSegmentRepository

    try:
        original_uuid = UUID(original_map_id)
        temp_uuid = UUID(temp_map_id)

        storage = MapStorageServiceDB(session)
        route_segment_repo = RouteSegmentRepository(session)

        # 1. Load the temporary map to get its data
        temp_map = await storage.map_repo.get_by_id(temp_uuid)
        if not temp_map:
            logger.error(f"Temporary map {temp_map_id} not found")
            return False

        original_map = await storage.map_repo.get_by_id(original_uuid)
        if not original_map:
            logger.error(f"Original map {original_map_id} not found")
            return False

        # 2. Get old segment IDs from original map (for usage count decrement)
        old_segment_ids = await storage.map_segment_repo.get_segment_ids_for_map(
            original_uuid
        )
        logger.info(f"Found {len(old_segment_ids)} old segments to decrement usage")

        # 3. Decrement usage_count for old segments
        # These segments may become orphans if no other map uses them
        if old_segment_ids:
            await route_segment_repo.bulk_decrement_usage(old_segment_ids)
            logger.info(f"Decremented usage for {len(old_segment_ids)} old segments")

        # 4. Delete old data from original map
        from api.database.repositories.poi_debug_data import POIDebugDataRepository
        debug_repo = POIDebugDataRepository(session)

        deleted_debug = await debug_repo.delete_by_map(original_uuid)
        logger.info(f"Deleted {deleted_debug} debug entries from original map")

        deleted_pois = await storage.map_poi_repo.delete_all_for_map(original_uuid)
        logger.info(f"Deleted {deleted_pois} MapPOI entries from original map")

        # 5. Delete old MapSegments from original map
        deleted_map_segments = await storage.map_segment_repo.delete_by_map(original_uuid)
        logger.info(f"Deleted {deleted_map_segments} MapSegment entries from original map")

        # 6. Update original map metadata with temp map data
        original_map.total_length_km = temp_map.total_length_km
        original_map.segments = temp_map.segments
        original_map.metadata_ = temp_map.metadata_
        original_map.updated_at = datetime.now()
        await session.flush()
        logger.info(f"Updated original map metadata")

        # 7. Move MapSegments from temp to original (new versioned segments)
        await session.execute(
            update(MapSegment)
            .where(MapSegment.map_id == temp_uuid)
            .values(map_id=original_uuid)
        )
        logger.info(f"Moved MapSegment entries from temp to original")

        # 8. Move MapPOI entries from temp to original (update map_id)
        await session.execute(
            update(MapPOI)
            .where(MapPOI.map_id == temp_uuid)
            .values(map_id=original_uuid)
        )
        logger.info(f"Moved MapPOI entries from temp to original")

        # 9. Move POIDebugData entries from temp to original (update map_id)
        await session.execute(
            update(POIDebugData)
            .where(POIDebugData.map_id == temp_uuid)
            .values(map_id=original_uuid)
        )
        logger.info(f"Moved POIDebugData entries from temp to original")

        # 10. Delete the temporary map (now empty)
        await storage.map_repo.delete_by_id(temp_uuid)
        logger.info(f"Deleted temporary map {temp_map_id}")

        logger.info(
            f"Successfully replaced map data with versioned segments: {original_map_id}"
        )
        return True

    except Exception as e:
        logger.error(f"Error replacing map data: {e}")
        raise


def replace_map_data_sync(original_map_id: str, temp_map_id: str) -> bool:
    """
    Sync wrapper for replacing map data.
    Use this from sync contexts (like background tasks).

    Args:
        original_map_id: ID of the original map to update
        temp_map_id: ID of the temporary map with new data

    Returns:
        True if successful, False otherwise
    """
    import asyncio

    async def _replace():
        engine, session_maker = _create_standalone_session()
        try:
            async with session_maker() as session:
                try:
                    result = await replace_map_data_async(
                        original_map_id, temp_map_id, session
                    )
                    await session.commit()
                    return result
                except Exception:
                    await session.rollback()
                    raise
        finally:
            await engine.dispose()

    return asyncio.run(_replace())
