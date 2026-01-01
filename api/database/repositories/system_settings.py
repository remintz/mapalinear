"""Repository for system settings operations."""

from datetime import datetime
from typing import Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.database.models.system_settings import SystemSettings


# Default settings with their descriptions
DEFAULT_SETTINGS = {
    "poi_search_radius_km": {
        "value": "5",
        "description": "Raio de busca de pontos de interesse em km (1-20)"
    },
    "duplicate_map_tolerance_km": {
        "value": "10",
        "description": "Tolerância em km para detectar mapas duplicados (1-50)"
    },
    "poi_debug_enabled": {
        "value": "true",
        "description": "Habilitar coleta de dados de debug para POIs (true/false)"
    }
}


class SystemSettingsRepository:
    """Repository for system settings CRUD operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get(self, key: str) -> Optional[SystemSettings]:
        """Get a setting by key."""
        result = await self.session.execute(
            select(SystemSettings).where(SystemSettings.key == key)
        )
        return result.scalar_one_or_none()

    async def get_value(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """Get just the value of a setting, with optional default."""
        setting = await self.get(key)
        if setting:
            return setting.value
        # Check if there's a default in DEFAULT_SETTINGS
        if key in DEFAULT_SETTINGS:
            return DEFAULT_SETTINGS[key]["value"]
        return default

    async def get_all(self) -> List[SystemSettings]:
        """Get all settings."""
        result = await self.session.execute(select(SystemSettings))
        return list(result.scalars().all())

    async def get_all_as_dict(self) -> Dict[str, str]:
        """Get all settings as a dictionary."""
        settings = await self.get_all()
        result = {}

        # Start with defaults
        for key, config in DEFAULT_SETTINGS.items():
            result[key] = config["value"]

        # Override with saved values
        for setting in settings:
            result[setting.key] = setting.value

        return result

    async def set(
        self,
        key: str,
        value: str,
        description: Optional[str] = None,
        updated_by: Optional[str] = None
    ) -> SystemSettings:
        """Set a setting value (create or update)."""
        setting = await self.get(key)

        if setting:
            setting.value = value
            setting.updated_at = datetime.utcnow()
            if updated_by:
                setting.updated_by = updated_by
            if description:
                setting.description = description
        else:
            # Use default description if not provided
            if description is None and key in DEFAULT_SETTINGS:
                description = DEFAULT_SETTINGS[key]["description"]

            setting = SystemSettings(
                key=key,
                value=value,
                description=description,
                updated_by=updated_by
            )
            self.session.add(setting)

        await self.session.flush()
        await self.session.refresh(setting)
        return setting

    async def delete(self, key: str) -> bool:
        """Delete a setting by key."""
        setting = await self.get(key)
        if setting:
            await self.session.delete(setting)
            await self.session.flush()
            return True
        return False

    async def ensure_defaults(self) -> None:
        """Ensure all default settings exist in the database."""
        for key, config in DEFAULT_SETTINGS.items():
            existing = await self.get(key)
            if not existing:
                await self.set(
                    key=key,
                    value=config["value"],
                    description=config["description"]
                )
