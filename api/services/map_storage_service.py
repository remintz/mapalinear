"""
Service for storing and managing saved linear maps.

This service handles:
- Saving linear maps to disk
- Loading saved maps
- Listing all saved maps
- Deleting saved maps
- Regenerating maps
"""

import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import List, Optional
from uuid import uuid4

from ..models.road_models import LinearMapResponse, SavedMapResponse

logger = logging.getLogger(__name__)


class MapStorageService:
    """Service for managing saved linear maps on disk."""

    def __init__(self, storage_dir: Optional[str] = None):
        """
        Initialize the map storage service.

        Args:
            storage_dir: Directory to store maps. Defaults to 'saved_maps' in project root.
        """
        if storage_dir is None:
            # Get project root (3 levels up from this file)
            project_root = Path(__file__).parent.parent.parent
            storage_dir = project_root / "saved_maps"

        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"📁 Map storage initialized at: {self.storage_dir}")

    def save_map(self, linear_map: LinearMapResponse) -> str:
        """
        Save a linear map to disk.

        Args:
            linear_map: The linear map to save

        Returns:
            The ID of the saved map
        """
        map_id = linear_map.id
        file_path = self.storage_dir / f"{map_id}.json"

        try:
            # Convert to dict for JSON serialization
            map_data = linear_map.model_dump(mode='json')

            # Save to file with pretty formatting
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(map_data, f, indent=2, ensure_ascii=False)

            logger.info(f"💾 Mapa linear salvo: {linear_map.origin} → {linear_map.destination} (ID: {map_id})")
            return map_id

        except Exception as e:
            logger.error(f"❌ Erro ao salvar mapa {map_id}: {e}")
            raise

    def load_map(self, map_id: str) -> Optional[LinearMapResponse]:
        """
        Load a saved map from disk.

        Args:
            map_id: ID of the map to load

        Returns:
            The loaded linear map, or None if not found
        """
        file_path = self.storage_dir / f"{map_id}.json"

        if not file_path.exists():
            logger.warning(f"⚠️ Mapa não encontrado: {map_id}")
            return None

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                map_data = json.load(f)

            # Parse dates properly
            if 'creation_date' in map_data and isinstance(map_data['creation_date'], str):
                map_data['creation_date'] = datetime.fromisoformat(map_data['creation_date'].replace('Z', '+00:00'))

            linear_map = LinearMapResponse(**map_data)
            logger.info(f"📂 Mapa carregado: {linear_map.origin} → {linear_map.destination}")
            return linear_map

        except Exception as e:
            logger.error(f"❌ Erro ao carregar mapa {map_id}: {e}")
            return None

    def list_maps(self) -> List[SavedMapResponse]:
        """
        List all saved maps (metadata only).

        Returns:
            List of saved map metadata, sorted by creation date (newest first)
        """
        saved_maps = []

        try:
            # Find all JSON files in storage directory
            for file_path in self.storage_dir.glob("*.json"):
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        map_data = json.load(f)

                    # Parse creation date
                    creation_date = map_data.get('creation_date')
                    if isinstance(creation_date, str):
                        creation_date = datetime.fromisoformat(creation_date.replace('Z', '+00:00'))
                    elif creation_date is None:
                        creation_date = datetime.now()

                    # Extract road refs from milestones or segments if available
                    road_refs = []
                    # Could extract from segments or milestones if we track road names

                    # Create metadata response
                    saved_map = SavedMapResponse(
                        id=map_data.get('id', file_path.stem),
                        name=None,  # Could be added in future
                        origin=map_data.get('origin', 'Unknown'),
                        destination=map_data.get('destination', 'Unknown'),
                        total_length_km=map_data.get('total_length_km', 0.0),
                        creation_date=creation_date,
                        road_refs=road_refs,
                        milestone_count=len(map_data.get('milestones', []))
                    )

                    saved_maps.append(saved_map)

                except Exception as e:
                    logger.warning(f"⚠️ Erro ao processar {file_path.name}: {e}")
                    continue

            # Sort by creation date, newest first
            saved_maps.sort(key=lambda m: m.creation_date, reverse=True)

            logger.info(f"📋 Listados {len(saved_maps)} mapas salvos")
            return saved_maps

        except Exception as e:
            logger.error(f"❌ Erro ao listar mapas: {e}")
            return []

    def delete_map(self, map_id: str) -> bool:
        """
        Delete a saved map from disk.

        Args:
            map_id: ID of the map to delete

        Returns:
            True if deleted successfully, False otherwise
        """
        file_path = self.storage_dir / f"{map_id}.json"

        if not file_path.exists():
            logger.warning(f"⚠️ Mapa não encontrado para deletar: {map_id}")
            return False

        try:
            file_path.unlink()
            logger.info(f"🗑️ Mapa deletado: {map_id}")
            return True

        except Exception as e:
            logger.error(f"❌ Erro ao deletar mapa {map_id}: {e}")
            return False

    def map_exists(self, map_id: str) -> bool:
        """
        Check if a map exists.

        Args:
            map_id: ID of the map to check

        Returns:
            True if map exists, False otherwise
        """
        file_path = self.storage_dir / f"{map_id}.json"
        return file_path.exists()


# Global instance
_storage_service: Optional[MapStorageService] = None


def get_storage_service() -> MapStorageService:
    """Get the global map storage service instance."""
    global _storage_service
    if _storage_service is None:
        _storage_service = MapStorageService()
    return _storage_service
