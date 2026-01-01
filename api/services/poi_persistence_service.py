"""
POI Persistence Service.

Handles persisting POIs from geographic providers to the database.
"""
import logging
from typing import Dict, List, Optional, Set, Tuple
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from api.database.models.poi import POI as POIModel
from api.database.repositories.poi import POIRepository
from api.providers.models import POI as ProviderPOI, POICategory

logger = logging.getLogger(__name__)


def _extract_provider_info(poi: ProviderPOI) -> Tuple[str, str]:
    """
    Extract provider name and ID from a POI.

    The POI ID from providers follows the pattern "type/id" (e.g., "node/12345").

    Args:
        poi: POI from geographic provider

    Returns:
        Tuple of (provider_name, provider_id)
    """
    # Check provider_data for hints about the source
    provider_data = poi.provider_data or {}

    # HERE POIs have here_id in provider_data
    if provider_data.get("here_id"):
        return "here", provider_data["here_id"]

    # OSM POIs have IDs like "node/12345" or "way/67890"
    if "/" in poi.id and poi.id.split("/")[0] in ("node", "way", "relation"):
        return "osm", poi.id

    # Default to OSM with the raw ID
    return "osm", poi.id


def _poi_category_to_type(category: POICategory) -> str:
    """Convert POI category to milestone type string."""
    from api.models.road_models import MilestoneType

    mapping = {
        POICategory.GAS_STATION: MilestoneType.GAS_STATION,
        POICategory.FUEL: MilestoneType.GAS_STATION,
        POICategory.RESTAURANT: MilestoneType.RESTAURANT,
        POICategory.FOOD: MilestoneType.RESTAURANT,
        POICategory.HOTEL: MilestoneType.HOTEL,
        POICategory.LODGING: MilestoneType.HOTEL,
        POICategory.HOSPITAL: MilestoneType.HOSPITAL,
        POICategory.PHARMACY: MilestoneType.PHARMACY,
        POICategory.HEALTH: MilestoneType.HOSPITAL,
        POICategory.CITY: MilestoneType.CITY,
        POICategory.TOWN: MilestoneType.CITY,
        POICategory.SERVICES: MilestoneType.GAS_STATION,
    }

    milestone_type = mapping.get(category, MilestoneType.GAS_STATION)
    return milestone_type.value


def provider_poi_to_db_dict(poi: ProviderPOI) -> dict:
    """
    Convert a provider POI to a dictionary suitable for database insertion.

    Args:
        poi: POI from geographic provider

    Returns:
        Dictionary with POI data for database
    """
    provider, provider_id = _extract_provider_info(poi)

    # Extract quality data from provider_data
    provider_data = poi.provider_data or {}
    quality_score = provider_data.get('quality_score')
    quality_issues = provider_data.get('quality_issues', [])
    is_low_quality = provider_data.get('is_low_quality', False)

    return {
        "name": poi.name,
        "type": _poi_category_to_type(poi.category),
        "latitude": poi.location.latitude,
        "longitude": poi.location.longitude,
        "phone": poi.phone,
        "website": poi.website,
        "opening_hours": str(poi.opening_hours) if poi.opening_hours else None,
        "rating": poi.rating,
        "rating_count": poi.review_count,
        "amenities": poi.amenities or [],
        "tags": provider_data,
        "is_referenced": False,  # Will be set to True for POIs used in maps
        # Quality fields
        "quality_score": quality_score,
        "quality_issues": quality_issues,
        "is_low_quality": is_low_quality,
    }


async def persist_pois_batch(
    session: AsyncSession,
    pois: List[ProviderPOI],
    referenced_poi_ids: Optional[Set[str]] = None
) -> Dict[str, UUID]:
    """
    Persist a batch of POIs to the database.

    Args:
        session: Database session
        pois: List of POIs from geographic provider
        referenced_poi_ids: Set of provider POI IDs that are referenced by maps

    Returns:
        Dictionary mapping provider POI ID to database UUID
    """
    referenced_poi_ids = referenced_poi_ids or set()
    poi_repo = POIRepository(session)

    provider_to_db_id: Dict[str, UUID] = {}
    created_count = 0
    existing_count = 0

    for poi in pois:
        provider, provider_id = _extract_provider_info(poi)

        # Prepare data for database
        poi_data = provider_poi_to_db_dict(poi)

        # Check if this POI is referenced by a map
        is_referenced = poi.id in referenced_poi_ids
        poi_data["is_referenced"] = is_referenced

        try:
            db_poi, created = await poi_repo.get_or_create_by_provider_id(
                provider=provider,
                provider_id=provider_id,
                defaults=poi_data
            )

            provider_to_db_id[poi.id] = db_poi.id

            if created:
                created_count += 1
            else:
                existing_count += 1
                # Update is_referenced if POI is now used in a map
                if is_referenced and not db_poi.is_referenced:
                    db_poi.is_referenced = True

        except Exception as e:
            logger.error(f"Error persisting POI {poi.name}: {e}")
            continue

    await session.commit()

    logger.info(f"📦 POIs persistidos: {created_count} novos, {existing_count} existentes")

    return provider_to_db_id


async def mark_pois_as_referenced(
    session: AsyncSession,
    poi_ids: List[UUID]
) -> int:
    """
    Mark POIs as referenced by a map.

    Args:
        session: Database session
        poi_ids: List of database POI UUIDs

    Returns:
        Number of POIs updated
    """
    poi_repo = POIRepository(session)
    count = await poi_repo.bulk_mark_as_referenced(poi_ids)
    await session.commit()
    return count
