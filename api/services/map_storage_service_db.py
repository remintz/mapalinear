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
from typing import List, Optional, Tuple
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from api.database.models.map import Map
from api.database.models.map_poi import MapPOI
from api.database.models.poi import POI
from api.database.models.user_map import UserMap
from api.database.repositories import MapPOIRepository, MapRepository, POIRepository
from api.database.repositories.user_map import UserMapRepository
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

    async def save_map(
        self, linear_map: LinearMapResponse, user_id: Optional[UUID] = None
    ) -> str:
        """
        Save a linear map to database and associate with user if provided.

        Args:
            linear_map: The linear map to save
            user_id: Optional user ID to associate the map with (creator)

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

            # Process milestones as POIs
            # Track POI IDs already added to this map to avoid duplicates
            added_poi_ids: set = set()

            for milestone in linear_map.milestones:
                # Get or create POI
                poi_data = self._milestone_to_poi_dict(milestone)
                osm_id = poi_data.pop("osm_id", None)

                if osm_id:
                    poi, created = await self.poi_repo.get_or_create_by_osm_id(
                        osm_id, poi_data
                    )
                else:
                    # No OSM ID, create new POI
                    poi = POI(**poi_data)
                    await self.poi_repo.create(poi)

                # Skip if this POI was already added to this map
                if poi.id in added_poi_ids:
                    logger.debug(
                        f"Skipping duplicate POI in map: {milestone.name} (poi_id={poi.id})"
                    )
                    continue
                added_poi_ids.add(poi.id)

                # Create MapPOI relationship
                map_poi = MapPOI(
                    map_id=map_id,
                    poi_id=poi.id,
                    segment_index=self._find_segment_index(
                        milestone.distance_from_origin_km, linear_map.segments
                    ),
                    distance_from_origin_km=milestone.distance_from_origin_km,
                    distance_from_road_meters=milestone.distance_from_road_meters,
                    side=milestone.side,
                    junction_distance_km=milestone.junction_distance_km,
                    junction_lat=(
                        milestone.junction_coordinates.latitude
                        if milestone.junction_coordinates
                        else None
                    ),
                    junction_lon=(
                        milestone.junction_coordinates.longitude
                        if milestone.junction_coordinates
                        else None
                    ),
                    requires_detour=milestone.requires_detour,
                    quality_score=milestone.quality_score,
                )
                await self.map_poi_repo.create(map_poi)

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

        except ValueError:
            logger.warning(f"ID de mapa invalido: {map_id}")
            return None
        except Exception as e:
            logger.error(f"Erro ao carregar mapa {map_id}: {e}")
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

        Args:
            map_id: ID of the map to delete

        Returns:
            True if deleted successfully, False otherwise
        """
        try:
            map_uuid = UUID(map_id)
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

    def _segment_to_dict(self, segment: LinearRoadSegment) -> dict:
        """Convert LinearRoadSegment to dict for JSONB storage."""
        return segment.model_dump(mode="json")

    def _dict_to_segment(self, data: dict) -> LinearRoadSegment:
        """Convert dict from JSONB to LinearRoadSegment."""
        return LinearRoadSegment(**data)

    def _milestone_to_poi_dict(self, milestone: RoadMilestone) -> dict:
        """Convert RoadMilestone to POI dict."""
        # Extract OSM ID from tags if available
        osm_id = milestone.tags.get("osm_id") or milestone.tags.get("id")
        if osm_id and not isinstance(osm_id, str):
            osm_id = str(osm_id)

        return {
            "osm_id": osm_id,
            "name": milestone.name,
            "type": milestone.type.value,
            "latitude": milestone.coordinates.latitude,
            "longitude": milestone.coordinates.longitude,
            "city": milestone.city,
            "operator": milestone.operator,
            "brand": milestone.brand,
            "opening_hours": milestone.opening_hours,
            "phone": milestone.phone,
            "website": milestone.website,
            "cuisine": milestone.cuisine,
            "amenities": milestone.amenities,
            "tags": milestone.tags,
            "rating": milestone.rating,
            "rating_count": milestone.rating_count,
            "google_maps_uri": milestone.google_maps_uri,
        }

    def _map_poi_to_milestone(self, map_poi: MapPOI) -> RoadMilestone:
        """Convert MapPOI + POI to RoadMilestone."""
        poi = map_poi.poi

        # Build junction coordinates if available
        junction_coordinates = None
        if map_poi.junction_lat is not None and map_poi.junction_lon is not None:
            junction_coordinates = Coordinates(
                latitude=map_poi.junction_lat, longitude=map_poi.junction_lon
            )

        return RoadMilestone(
            id=str(poi.id),
            name=poi.name,
            type=MilestoneType(poi.type),
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


def save_map_sync(linear_map: LinearMapResponse, user_id: Optional[str] = None) -> str:
    """
    Sync wrapper for saving a map to the database.
    Use this from sync contexts (like RoadService.generate_linear_map).

    Args:
        linear_map: The linear map to save
        user_id: Optional user ID to associate the map with (as creator)

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
                    result = await storage.save_map(linear_map, user_id=uuid_user_id)
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
