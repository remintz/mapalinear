"""
POI (Point of Interest) repository for database operations.
"""
from typing import List, Optional
from uuid import UUID

from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from api.database.models.poi import POI
from api.database.repositories.base import BaseRepository


class POIRepository(BaseRepository[POI]):
    """Repository for POI model operations."""

    def __init__(self, session: AsyncSession):
        """Initialize with session."""
        super().__init__(session, POI)

    async def get_by_osm_id(self, osm_id: str) -> Optional[POI]:
        """
        Get a POI by its OSM ID.

        Args:
            osm_id: OpenStreetMap ID

        Returns:
            POI instance or None if not found
        """
        result = await self.session.execute(
            select(POI).where(POI.osm_id == osm_id)
        )
        return result.scalar_one_or_none()

    async def find_by_type(
        self, poi_type: str, limit: int = 100
    ) -> List[POI]:
        """
        Find POIs by type.

        Args:
            poi_type: POI type (e.g., 'gas_station', 'restaurant')
            limit: Maximum number of results

        Returns:
            List of matching POIs
        """
        result = await self.session.execute(
            select(POI)
            .where(POI.type == poi_type)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def find_by_types(
        self, poi_types: List[str], limit: int = 100
    ) -> List[POI]:
        """
        Find POIs by multiple types.

        Args:
            poi_types: List of POI types
            limit: Maximum number of results

        Returns:
            List of matching POIs
        """
        result = await self.session.execute(
            select(POI)
            .where(POI.type.in_(poi_types))
            .limit(limit)
        )
        return list(result.scalars().all())

    async def find_by_city(
        self, city: str, limit: int = 100
    ) -> List[POI]:
        """
        Find POIs in a specific city.

        Args:
            city: City name
            limit: Maximum number of results

        Returns:
            List of POIs in the city
        """
        result = await self.session.execute(
            select(POI)
            .where(POI.city == city)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def find_by_brand(
        self, brand: str, limit: int = 100
    ) -> List[POI]:
        """
        Find POIs by brand.

        Args:
            brand: Brand name
            limit: Maximum number of results

        Returns:
            List of POIs with the brand
        """
        result = await self.session.execute(
            select(POI)
            .where(POI.brand == brand)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def search_by_name(
        self, name: str, limit: int = 100
    ) -> List[POI]:
        """
        Search POIs by name (case-insensitive partial match).

        Args:
            name: Name to search for
            limit: Maximum number of results

        Returns:
            List of matching POIs
        """
        search_pattern = f"%{name}%"
        result = await self.session.execute(
            select(POI)
            .where(POI.name.ilike(search_pattern))
            .limit(limit)
        )
        return list(result.scalars().all())

    async def find_in_bounding_box(
        self,
        min_lat: float,
        max_lat: float,
        min_lon: float,
        max_lon: float,
        poi_types: Optional[List[str]] = None,
        limit: int = 100
    ) -> List[POI]:
        """
        Find POIs within a geographic bounding box.

        Args:
            min_lat: Minimum latitude
            max_lat: Maximum latitude
            min_lon: Minimum longitude
            max_lon: Maximum longitude
            poi_types: Optional list of POI types to filter
            limit: Maximum number of results

        Returns:
            List of POIs within the bounding box
        """
        conditions = [
            POI.latitude >= min_lat,
            POI.latitude <= max_lat,
            POI.longitude >= min_lon,
            POI.longitude <= max_lon,
        ]

        if poi_types:
            conditions.append(POI.type.in_(poi_types))

        result = await self.session.execute(
            select(POI)
            .where(and_(*conditions))
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_or_create_by_osm_id(
        self, osm_id: str, defaults: dict
    ) -> tuple[POI, bool]:
        """
        Get an existing POI by OSM ID or create a new one.

        Args:
            osm_id: OpenStreetMap ID
            defaults: Default values for creating a new POI

        Returns:
            Tuple of (POI instance, created flag)
        """
        existing = await self.get_by_osm_id(osm_id)
        if existing:
            return existing, False

        # Create new POI
        poi = POI(osm_id=osm_id, **defaults)
        await self.create(poi)
        return poi, True

    async def bulk_get_or_create_by_osm_ids(
        self, poi_data: List[dict]
    ) -> List[POI]:
        """
        Bulk get or create POIs by OSM IDs.

        Args:
            poi_data: List of dicts with 'osm_id' and other POI fields

        Returns:
            List of POI instances (existing or newly created)
        """
        osm_ids = [p["osm_id"] for p in poi_data if p.get("osm_id")]

        # Get existing POIs
        existing_result = await self.session.execute(
            select(POI).where(POI.osm_id.in_(osm_ids))
        )
        existing_pois = {p.osm_id: p for p in existing_result.scalars().all()}

        result_pois = []
        for data in poi_data:
            osm_id = data.get("osm_id")
            if osm_id and osm_id in existing_pois:
                result_pois.append(existing_pois[osm_id])
            else:
                poi = POI(**data)
                self.session.add(poi)
                result_pois.append(poi)

        await self.session.flush()
        return result_pois
