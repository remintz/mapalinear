"""
CacheEntry SQLAlchemy model.
"""
from datetime import datetime

from sqlalchemy import Index, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from api.database.connection import Base


class CacheEntry(Base):
    """
    Cache entry model for storing geographic data cache.

    This replaces the existing cache_entries table but maintains
    the same schema for compatibility with the existing cache system.
    """

    __tablename__ = "cache_entries"

    key: Mapped[str] = mapped_column(String(500), primary_key=True)
    data: Mapped[dict] = mapped_column(JSONB, nullable=False)
    provider: Mapped[str] = mapped_column(String(50), index=True)
    operation: Mapped[str] = mapped_column(String(50), index=True)
    params: Mapped[dict] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(default=func.now())
    expires_at: Mapped[datetime] = mapped_column(index=True)
    hit_count: Mapped[int] = mapped_column(default=0)

    # Indexes for efficient queries
    __table_args__ = (
        Index("idx_cache_operation_expires", "operation", "expires_at"),
        Index("idx_cache_provider_operation", "provider", "operation"),
    )

    def __repr__(self) -> str:
        return f"<CacheEntry(key='{self.key[:50]}...', provider='{self.provider}', operation='{self.operation}')>"

    def is_expired(self) -> bool:
        """Check if the cache entry has expired."""
        return datetime.now() > self.expires_at
