"""
Municipalities router for IBGE data.

Provides endpoints to fetch Brazilian municipalities from IBGE API with caching.
"""

import logging
from typing import List, Optional

import httpx
from fastapi import APIRouter, Query, HTTPException

from api.models.municipality_models import Municipality, MunicipalityListResponse
from api.providers.cache import UnifiedCache, CacheKey
from api.providers.base import ProviderType

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/municipalities", tags=["municipalities"])

# Cache instance
cache = UnifiedCache()

# IBGE API endpoint
IBGE_API_URL = "https://servicodados.ibge.gov.br/api/v1/localidades/municipios"


async def fetch_municipalities_from_ibge() -> List[Municipality]:
    """
    Fetch all municipalities from IBGE API.

    Returns:
        List of Municipality objects
    """
    logger.info("Fetching municipalities from IBGE API...")

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(IBGE_API_URL)
        response.raise_for_status()
        data = response.json()

    municipalities = []
    for item in data:
        try:
            # Extract UF from nested structure (defensive parsing)
            microrregiao = item.get("microrregiao") or {}
            mesorregiao = microrregiao.get("mesorregiao") or {}
            uf_data = mesorregiao.get("UF") or {}
            uf = uf_data.get("sigla", "")

            if not uf:
                logger.debug(f"Municipality without UF: {item.get('nome', 'unknown')}")
                continue

            municipalities.append(Municipality(
                id=item["id"],
                nome=item["nome"],
                uf=uf
            ))
        except (KeyError, TypeError, AttributeError) as e:
            logger.warning(f"Failed to parse municipality: {item.get('nome', 'unknown')}: {e}")
            continue

    # Sort by name for better UX
    municipalities.sort(key=lambda m: (m.uf, m.nome))

    logger.info(f"Fetched {len(municipalities)} municipalities from IBGE")
    return municipalities


@router.get("", response_model=List[Municipality])
async def list_municipalities(
    uf: Optional[str] = Query(None, description="Filter by state code (e.g., SP, RJ)")
) -> List[Municipality]:
    """
    Get list of Brazilian municipalities.

    Data is fetched from IBGE API and cached for 7 days.
    Optionally filter by state code (UF).
    """
    # Check cache first
    cache_params = {"all": True}
    cached_data = await cache.get(
        provider=ProviderType.IBGE,
        operation="municipalities",
        params=cache_params
    )

    if cached_data:
        logger.debug("Municipalities cache hit")
        municipalities = [Municipality(**m) if isinstance(m, dict) else m for m in cached_data]
    else:
        logger.debug("Municipalities cache miss, fetching from IBGE")
        try:
            municipalities = await fetch_municipalities_from_ibge()

            # Store in cache
            await cache.set(
                provider=ProviderType.IBGE,
                operation="municipalities",
                params=cache_params,
                data=[m.model_dump() for m in municipalities]
            )
        except httpx.HTTPError as e:
            logger.error(f"Failed to fetch municipalities from IBGE: {e}")
            raise HTTPException(
                status_code=503,
                detail="Failed to fetch municipalities from IBGE. Please try again later."
            )

    # Filter by UF if provided
    if uf:
        uf_upper = uf.upper()
        municipalities = [m for m in municipalities if m.uf == uf_upper]

    return municipalities


@router.get("/stats")
async def municipalities_stats():
    """Get statistics about cached municipalities."""
    cache_params = {"all": True}
    cached_data = await cache.get(
        provider=ProviderType.IBGE,
        operation="municipalities",
        params=cache_params
    )

    if not cached_data:
        return {"cached": False, "total": 0, "states": 0}

    municipalities = [Municipality(**m) if isinstance(m, dict) else m for m in cached_data]
    states = set(m.uf for m in municipalities)

    return {
        "cached": True,
        "total": len(municipalities),
        "states": len(states)
    }
