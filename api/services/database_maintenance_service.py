"""
Database maintenance service for cleaning up orphaned data and ensuring consistency.
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional

from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from api.database.models.poi import POI
from api.database.models.map_poi import MapPOI
from api.database.models.map import Map
from api.database.models.async_operation import AsyncOperation

logger = logging.getLogger(__name__)


@dataclass
class MaintenanceStats:
    """Statistics from a maintenance run."""
    orphan_pois_found: int = 0
    orphan_pois_deleted: int = 0
    is_referenced_fixed: int = 0
    stale_operations_cleaned: int = 0
    execution_time_ms: int = 0


@dataclass
class DatabaseStats:
    """Current database statistics."""
    total_pois: int = 0
    referenced_pois: int = 0
    unreferenced_pois: int = 0
    total_maps: int = 0
    total_map_pois: int = 0
    pending_operations: int = 0
    stale_operations: int = 0


class DatabaseMaintenanceService:
    """Service for database maintenance and cleanup operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_database_stats(self) -> DatabaseStats:
        """
        Get current database statistics.

        Returns:
            DatabaseStats with counts of various entities.
        """
        # Count total POIs
        total_pois_result = await self.session.execute(
            select(func.count(POI.id))
        )
        total_pois = total_pois_result.scalar() or 0

        # Count referenced POIs
        referenced_pois_result = await self.session.execute(
            select(func.count(POI.id)).where(POI.is_referenced == True)
        )
        referenced_pois = referenced_pois_result.scalar() or 0

        # Count unreferenced POIs
        unreferenced_pois = total_pois - referenced_pois

        # Count total maps
        total_maps_result = await self.session.execute(
            select(func.count(Map.id))
        )
        total_maps = total_maps_result.scalar() or 0

        # Count total map-POI relationships
        total_map_pois_result = await self.session.execute(
            select(func.count(MapPOI.id))
        )
        total_map_pois = total_map_pois_result.scalar() or 0

        # Count pending operations
        pending_ops_result = await self.session.execute(
            select(func.count(AsyncOperation.id))
            .where(AsyncOperation.status == "in_progress")
        )
        pending_operations = pending_ops_result.scalar() or 0

        # Count stale operations (in_progress for more than 2 hours)
        from datetime import timedelta
        stale_cutoff = datetime.now() - timedelta(hours=2)
        stale_ops_result = await self.session.execute(
            select(func.count(AsyncOperation.id))
            .where(AsyncOperation.status == "in_progress")
            .where(AsyncOperation.started_at < stale_cutoff)
        )
        stale_operations = stale_ops_result.scalar() or 0

        return DatabaseStats(
            total_pois=total_pois,
            referenced_pois=referenced_pois,
            unreferenced_pois=unreferenced_pois,
            total_maps=total_maps,
            total_map_pois=total_map_pois,
            pending_operations=pending_operations,
            stale_operations=stale_operations,
        )

    async def find_orphan_poi_ids(self) -> List[str]:
        """
        Find POI IDs that are not referenced by any MapPOI.

        Returns:
            List of orphan POI UUIDs as strings.
        """
        # Subquery to get all POI IDs that have at least one MapPOI
        referenced_subquery = select(MapPOI.poi_id).distinct()

        # Find POIs not in the referenced set
        result = await self.session.execute(
            select(POI.id).where(~POI.id.in_(referenced_subquery))
        )
        return [str(poi_id) for poi_id in result.scalars().all()]

    async def delete_orphan_pois(self, dry_run: bool = True) -> int:
        """
        Delete POIs that are not referenced by any map.

        Args:
            dry_run: If True, only count but don't delete.

        Returns:
            Number of POIs deleted (or would be deleted in dry run).
        """
        # Get orphan POI IDs
        orphan_ids = await self.find_orphan_poi_ids()
        count = len(orphan_ids)

        if count == 0:
            logger.info("No orphan POIs found")
            return 0

        if dry_run:
            logger.info(f"Dry run: would delete {count} orphan POIs")
            return count

        # Delete orphan POIs
        from uuid import UUID
        orphan_uuids = [UUID(oid) for oid in orphan_ids]

        result = await self.session.execute(
            delete(POI).where(POI.id.in_(orphan_uuids))
        )
        await self.session.commit()

        deleted = result.rowcount
        logger.info(f"Deleted {deleted} orphan POIs")
        return deleted

    async def fix_is_referenced_flags(self, dry_run: bool = True) -> int:
        """
        Fix is_referenced flags that are incorrect.

        - POIs that have MapPOI references should have is_referenced=True
        - POIs that don't have MapPOI references should have is_referenced=False

        Args:
            dry_run: If True, only count but don't fix.

        Returns:
            Number of POIs fixed (or would be fixed in dry run).
        """
        # Find POIs that should be referenced but aren't marked
        referenced_subquery = select(MapPOI.poi_id).distinct()

        # Count POIs marked as not referenced but actually are
        should_be_true_result = await self.session.execute(
            select(func.count(POI.id))
            .where(POI.id.in_(referenced_subquery))
            .where(POI.is_referenced == False)
        )
        should_be_true = should_be_true_result.scalar() or 0

        # Count POIs marked as referenced but actually aren't
        should_be_false_result = await self.session.execute(
            select(func.count(POI.id))
            .where(~POI.id.in_(referenced_subquery))
            .where(POI.is_referenced == True)
        )
        should_be_false = should_be_false_result.scalar() or 0

        total_fixes = should_be_true + should_be_false

        if total_fixes == 0:
            logger.info("All is_referenced flags are correct")
            return 0

        if dry_run:
            logger.info(
                f"Dry run: would fix {total_fixes} is_referenced flags "
                f"({should_be_true} should be True, {should_be_false} should be False)"
            )
            return total_fixes

        # Fix POIs that should be referenced
        if should_be_true > 0:
            await self.session.execute(
                update(POI)
                .where(POI.id.in_(referenced_subquery))
                .where(POI.is_referenced == False)
                .values(is_referenced=True)
            )

        # Fix POIs that should not be referenced
        if should_be_false > 0:
            await self.session.execute(
                update(POI)
                .where(~POI.id.in_(referenced_subquery))
                .where(POI.is_referenced == True)
                .values(is_referenced=False)
            )

        await self.session.commit()

        logger.info(f"Fixed {total_fixes} is_referenced flags")
        return total_fixes

    async def cleanup_stale_operations(self) -> int:
        """
        Mark stale in_progress operations as failed.

        Returns:
            Number of operations marked as failed.
        """
        from datetime import timedelta
        stale_cutoff = datetime.now() - timedelta(hours=2)

        result = await self.session.execute(
            update(AsyncOperation)
            .where(AsyncOperation.status == "in_progress")
            .where(AsyncOperation.started_at < stale_cutoff)
            .values(
                status="failed",
                completed_at=datetime.now(),
                error="Operation timed out (stale) - cleaned by maintenance",
            )
        )
        await self.session.commit()

        count = result.rowcount
        if count > 0:
            logger.info(f"Marked {count} stale operations as failed")
        return count

    async def run_full_maintenance(self, dry_run: bool = True) -> MaintenanceStats:
        """
        Run all maintenance tasks.

        Args:
            dry_run: If True, only report what would be done.

        Returns:
            MaintenanceStats with results.
        """
        start_time = datetime.now()
        stats = MaintenanceStats()

        logger.info(f"Starting database maintenance (dry_run={dry_run})")

        # Get initial orphan count
        orphan_ids = await self.find_orphan_poi_ids()
        stats.orphan_pois_found = len(orphan_ids)

        # Delete orphan POIs
        stats.orphan_pois_deleted = await self.delete_orphan_pois(dry_run=dry_run)

        # Fix is_referenced flags
        stats.is_referenced_fixed = await self.fix_is_referenced_flags(dry_run=dry_run)

        # Cleanup stale operations (always run, not affected by dry_run)
        stats.stale_operations_cleaned = await self.cleanup_stale_operations()

        end_time = datetime.now()
        stats.execution_time_ms = int((end_time - start_time).total_seconds() * 1000)

        logger.info(
            f"Maintenance completed in {stats.execution_time_ms}ms: "
            f"orphans={stats.orphan_pois_deleted}, "
            f"flags_fixed={stats.is_referenced_fixed}, "
            f"stale_ops={stats.stale_operations_cleaned}"
        )

        return stats
