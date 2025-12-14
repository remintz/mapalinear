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
        If POI exists, updates rating fields if new data is available.

        Args:
            osm_id: OpenStreetMap ID
            defaults: Default values for creating a new POI

        Returns:
            Tuple of (POI instance, created flag)
        """
        existing = await self.get_by_osm_id(osm_id)
        if existing:
            # Update rating fields if new data is available
            updated = False
            if defaults.get("rating") is not None and existing.rating is None:
                existing.rating = defaults["rating"]
                updated = True
            if defaults.get("rating_count") is not None and existing.rating_count is None:
                existing.rating_count = defaults["rating_count"]
                updated = True
            if defaults.get("google_maps_uri") and not existing.google_maps_uri:
                existing.google_maps_uri = defaults["google_maps_uri"]
                updated = True
            # Also update city if missing
            if defaults.get("city") and not existing.city:
                existing.city = defaults["city"]
                updated = True

            if updated:
                await self.session.flush()

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

    async def get_by_here_id(self, here_id: str) -> Optional[POI]:
        """
        Get a POI by its HERE ID.

        Args:
            here_id: HERE Maps place ID

        Returns:
            POI instance or None if not found
        """
        result = await self.session.execute(
            select(POI).where(POI.here_id == here_id)
        )
        return result.scalar_one_or_none()

    async def find_not_enriched_by_here(
        self, poi_types: Optional[List[str]] = None, limit: int = 100
    ) -> List[POI]:
        """
        Find POIs that have not been enriched by HERE Maps.

        Args:
            poi_types: Optional list of POI types to filter
            limit: Maximum number of results

        Returns:
            List of POIs not yet enriched by HERE
        """
        from sqlalchemy import not_
        from sqlalchemy.dialects.postgresql import JSONB

        # Filter POIs where enriched_by does not contain 'here_maps'
        conditions = [
            not_(POI.enriched_by.contains(["here_maps"]))
        ]

        if poi_types:
            conditions.append(POI.type.in_(poi_types))

        result = await self.session.execute(
            select(POI)
            .where(and_(*conditions))
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_or_create_by_provider_id(
        self,
        provider: str,
        provider_id: str,
        defaults: dict
    ) -> tuple[POI, bool]:
        """
        Get an existing POI by provider ID (osm_id or here_id) or create a new one.

        Args:
            provider: Provider name ('osm' or 'here')
            provider_id: Provider-specific ID
            defaults: Default values for creating a new POI

        Returns:
            Tuple of (POI instance, created flag)
        """
        # Look up by appropriate provider ID
        if provider == "osm":
            existing = await self.get_by_osm_id(provider_id)
        elif provider == "here":
            existing = await self.get_by_here_id(provider_id)
        else:
            existing = None

        if existing:
            return existing, False

        # Create new POI with provider-specific ID
        poi_data = {**defaults, "primary_provider": provider}
        if provider == "osm":
            poi_data["osm_id"] = provider_id
        elif provider == "here":
            poi_data["here_id"] = provider_id

        poi = POI(**poi_data)
        await self.create(poi)
        return poi, True

    async def mark_as_referenced(self, poi_id: UUID) -> None:
        """
        Mark a POI as referenced by a map.

        Args:
            poi_id: POI UUID
        """
        poi = await self.get(poi_id)
        if poi and not poi.is_referenced:
            poi.is_referenced = True
            await self.session.flush()

    async def bulk_mark_as_referenced(self, poi_ids: List[UUID]) -> int:
        """
        Mark multiple POIs as referenced.

        Args:
            poi_ids: List of POI UUIDs

        Returns:
            Number of POIs updated
        """
        from sqlalchemy import update

        result = await self.session.execute(
            update(POI)
            .where(and_(POI.id.in_(poi_ids), POI.is_referenced == False))
            .values(is_referenced=True)
        )
        await self.session.flush()
        return result.rowcount

    async def find_unreferenced(self, limit: int = 100) -> List[POI]:
        """
        Find POIs that are not referenced by any map.

        Args:
            limit: Maximum number of results

        Returns:
            List of unreferenced POIs
        """
        result = await self.session.execute(
            select(POI)
            .where(POI.is_referenced == False)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def find_referenced_not_enriched(
        self,
        enrichment_provider: str,
        poi_types: Optional[List[str]] = None,
        limit: int = 100
    ) -> List[POI]:
        """
        Find referenced POIs that haven't been enriched by a specific provider.

        Args:
            enrichment_provider: Provider name (e.g., 'google_places', 'here_maps')
            poi_types: Optional list of POI types to filter
            limit: Maximum number of results

        Returns:
            List of POIs needing enrichment
        """
        from sqlalchemy import not_

        conditions = [
            POI.is_referenced == True,
            not_(POI.enriched_by.contains([enrichment_provider]))
        ]

        if poi_types:
            conditions.append(POI.type.in_(poi_types))

        result = await self.session.execute(
            select(POI)
            .where(and_(*conditions))
            .limit(limit)
        )
        return list(result.scalars().all())

    async def update_with_here_data(
        self,
        poi: POI,
        here_id: str,
        here_data: dict,
        phone: Optional[str] = None,
        website: Optional[str] = None,
        opening_hours: Optional[str] = None,
    ) -> POI:
        """
        Update a POI with HERE Maps data.

        Args:
            poi: POI instance to update
            here_id: HERE Maps place ID
            here_data: Structured HERE data (address, references, categories)
            phone: Phone number (optional)
            website: Website URL (optional)
            opening_hours: Opening hours string (optional)

        Returns:
            Updated POI instance
        """
        from datetime import datetime

        poi.here_id = here_id
        poi.here_data = here_data

        # Only update contact info if not already present
        if phone and not poi.phone:
            poi.phone = phone
        if website and not poi.website:
            poi.website = website
        if opening_hours and not poi.opening_hours:
            poi.opening_hours = opening_hours

        # Mark as enriched by HERE
        poi.add_enrichment("here_maps")

        await self.session.flush()
        return poi
