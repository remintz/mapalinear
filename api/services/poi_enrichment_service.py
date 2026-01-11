"""
POI Enrichment Service - Centralized POI data enrichment.

This service handles enrichment of POIs with external data sources:
- Google Places: Ratings for restaurants, hotels, cafes, etc.
- HERE Maps: Contact info (phone, website, hours) for various POI types.

The service provides both sync and async interfaces and handles all
database session management internally.
"""

import asyncio
import logging
from typing import List, Optional

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from api.providers.settings import get_settings

logger = logging.getLogger(__name__)


def _create_async_engine_and_session():
    """
    Create a standalone async engine and session maker.

    Returns:
        Tuple of (engine, session_maker)
    """
    settings = get_settings()
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
    return engine, session_maker


async def _run_with_session(async_func):
    """
    Run an async function with a managed database session.

    Args:
        async_func: Async function that takes a session parameter

    Returns:
        Result of the async function
    """
    engine, session_maker = _create_async_engine_and_session()
    try:
        async with session_maker() as session:
            try:
                result = await async_func(session)
                await session.commit()
                return result
            except Exception:
                await session.rollback()
                raise
    finally:
        await engine.dispose()


def enrich_map_with_google_places_sync(map_id: str) -> int:
    """
    Enrich POIs in a map with Google Places data (sync version).

    This is a convenience wrapper that runs the async enrichment
    in a new event loop.

    Args:
        map_id: Map UUID string

    Returns:
        Number of POIs enriched
    """
    settings = get_settings()

    # Early exit checks
    if not settings.google_places_enabled:
        logger.debug("Google Places enrichment is disabled (GOOGLE_PLACES_ENABLED=false)")
        return 0
    if not settings.google_places_api_key:
        logger.warning(
            "Google Places enrichment skipped: GOOGLE_PLACES_API_KEY not configured. "
            "Add GOOGLE_PLACES_API_KEY to .env to enable restaurant/hotel ratings."
        )
        return 0

    async def _enrich(session: AsyncSession) -> int:
        from api.services.google_places_service import enrich_map_pois_with_google_places
        return await enrich_map_pois_with_google_places(session, map_id)

    try:
        return asyncio.run(_run_with_session(_enrich))
    except Exception as e:
        logger.warning(f"Error enriching with Google Places: {e}")
        return 0


def enrich_map_with_here_sync(
    map_id: str,
    poi_types: Optional[List[str]] = None,
) -> int:
    """
    Enrich POIs in a map with HERE Maps data (sync version).

    This is a convenience wrapper that runs the async enrichment
    in a new event loop.

    Args:
        map_id: Map UUID string
        poi_types: Optional list of POI types to enrich

    Returns:
        Number of POIs enriched
    """
    settings = get_settings()

    # Early exit checks
    if settings.poi_provider.lower() != "osm":
        logger.debug("HERE enrichment only applies when POI_PROVIDER=osm")
        return 0
    if not settings.here_enrichment_enabled:
        logger.debug("HERE enrichment is disabled (HERE_ENRICHMENT_ENABLED=false)")
        return 0
    if not settings.here_api_key:
        logger.warning(
            "HERE enrichment skipped: HERE_API_KEY not configured. "
            "Add HERE_API_KEY to .env to enable contact info enrichment."
        )
        return 0

    if poi_types is None:
        poi_types = [
            "gas_station",
            "restaurant",
            "hotel",
            "hospital",
            "pharmacy",
        ]

    async def _enrich(session: AsyncSession) -> int:
        from api.services.here_enrichment_service import enrich_map_pois_with_here
        results = await enrich_map_pois_with_here(
            session=session,
            map_id=map_id,
            poi_types=poi_types,
        )
        matched = len([r for r in results if r.matched])
        logger.info(f"HERE enrichment: {matched}/{len(results)} POIs enriched")
        return matched

    try:
        return asyncio.run(_run_with_session(_enrich))
    except Exception as e:
        logger.warning(f"Error enriching with HERE: {e}")
        return 0


def enrich_map_pois(map_id: str) -> dict:
    """
    Enrich all POIs in a map with available external data sources.

    This is the main entry point for POI enrichment. It will:
    1. Enrich with Google Places (if enabled and configured)
    2. Enrich with HERE Maps (if enabled and configured)

    Args:
        map_id: Map UUID string

    Returns:
        Dict with enrichment results:
        {
            "google_places_enriched": int,
            "here_enriched": int,
            "total_enriched": int,
        }
    """
    google_count = enrich_map_with_google_places_sync(map_id)
    here_count = enrich_map_with_here_sync(map_id)

    return {
        "google_places_enriched": google_count,
        "here_enriched": here_count,
        "total_enriched": google_count + here_count,
    }
