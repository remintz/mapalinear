"""
Database-backed service for storing and managing saved linear maps.

This service handles:
- Saving linear maps to PostgreSQL database
- Loading saved maps
- Listing all saved maps
- Deleting saved maps

It uses SQLAlchemy repositories for database operations.
"""

import logging
from datetime import datetime
from typing import List, Optional
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from api.database.models.map import Map
from api.database.models.map_poi import MapPOI
from api.database.models.poi import POI
from api.database.repositories import MapPOIRepository, MapRepository, POIRepository
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

    async def save_map(self, linear_map: LinearMapResponse) -> str:
        """
        Save a linear map to database.

        Args:
            linear_map: The linear map to save

        Returns:
            The ID of the saved map
        """
        try:
            # Convert LinearMapResponse to Map model
            map_id = UUID(linear_map.id) if linear_map.id else uuid4()

            # Serialize segments to JSONB
            segments_data = [
                self._segment_to_dict(seg) for seg in linear_map.segments
            ]

            # Create metadata
            metadata = {
                "road_refs": self._extract_road_refs(linear_map.segments),
                "creation_date": linear_map.creation_date.isoformat(),
            }

            # Create Map record
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
            )
            await self.map_repo.create(db_map)

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
                    logger.debug(f"Skipping duplicate POI in map: {milestone.name} (poi_id={poi.id})")
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

    async def load_map(self, map_id: str) -> Optional[LinearMapResponse]:
        """
        Load a saved map from database.

        Args:
            map_id: ID of the map to load

        Returns:
            The loaded linear map, or None if not found
        """
        try:
            map_uuid = UUID(map_id)
            db_map = await self.map_repo.get_by_id(map_uuid)

            if not db_map:
                logger.warning(f"Mapa nao encontrado: {map_id}")
                return None

            # Load POIs with details
            map_pois = await self.map_poi_repo.get_pois_for_map(
                map_uuid, include_poi_details=True
            )

            # Convert segments from JSONB
            segments = [
                self._dict_to_segment(seg_data) for seg_data in db_map.segments
            ]

            # Convert POIs to milestones
            milestones = [
                self._map_poi_to_milestone(map_poi) for map_poi in map_pois
            ]

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

    async def list_maps(self) -> List[SavedMapResponse]:
        """
        List all saved maps (metadata only).

        Returns:
            List of saved map metadata, sorted by creation date (newest first)
        """
        try:
            # Get recent maps
            maps = await self.map_repo.get_recent(limit=100)
            saved_maps = []

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
                saved_maps.append(saved_map)

            logger.info(f"Listados {len(saved_maps)} mapas salvos")
            return saved_maps

        except Exception as e:
            logger.error(f"Erro ao listar mapas: {e}")
            return []

    async def delete_map(self, map_id: str) -> bool:
        """
        Delete a saved map from database.

        Args:
            map_id: ID of the map to delete

        Returns:
            True if deleted successfully, False otherwise
        """
        try:
            map_uuid = UUID(map_id)
            deleted = await self.map_repo.delete_by_id(map_uuid)

            if deleted:
                logger.info(f"Mapa deletado: {map_id}")
            else:
                logger.warning(f"Mapa nao encontrado para deletar: {map_id}")

            return deleted

        except ValueError:
            logger.warning(f"ID de mapa invalido: {map_id}")
            return False
        except Exception as e:
            logger.error(f"Erro ao deletar mapa {map_id}: {e}")
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


def save_map_sync(linear_map: LinearMapResponse) -> str:
    """
    Sync wrapper for saving a map to the database.
    Use this from sync contexts (like RoadService.generate_linear_map).

    Args:
        linear_map: The linear map to save

    Returns:
        The ID of the saved map
    """
    import asyncio

    async def _save():
        engine, session_maker = _create_standalone_session()
        try:
            async with session_maker() as session:
                try:
                    storage = MapStorageServiceDB(session)
                    result = await storage.save_map(linear_map)
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
    Sync wrapper for deleting a map from the database.
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
                    result = await storage.delete_map(map_id)
                    await session.commit()
                    return result
                except Exception:
                    await session.rollback()
                    raise
        finally:
            await engine.dispose()

    # Run in a new event loop
    return asyncio.run(_delete())
