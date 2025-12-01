"""
Database module for MapaLinear.

Provides SQLAlchemy async database connection, models, and repositories.
"""
from api.database.connection import (
    Base,
    close_db,
    get_db,
    get_engine,
    get_session,
    get_session_maker,
    init_db,
)
from api.database.repositories import (
    BaseRepository,
    CacheRepository,
    MapPOIRepository,
    MapRepository,
    POIRepository,
)

__all__ = [
    # Connection
    "Base",
    "get_engine",
    "get_session",
    "get_session_maker",
    "get_db",
    "init_db",
    "close_db",
    # Repositories
    "BaseRepository",
    "MapRepository",
    "POIRepository",
    "MapPOIRepository",
    "CacheRepository",
]
