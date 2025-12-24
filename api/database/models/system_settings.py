"""System settings model for storing application configuration."""

from datetime import datetime
from sqlalchemy import Column, String, Integer, DateTime, Text
from api.database.connection import Base


class SystemSettings(Base):
    """Stores system-wide configuration settings."""

    __tablename__ = "system_settings"

    key = Column(String(100), primary_key=True, nullable=False)
    value = Column(Text, nullable=False)
    description = Column(Text, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    updated_by = Column(String(255), nullable=True)

    def __repr__(self) -> str:
        return f"<SystemSettings(key={self.key}, value={self.value})>"
