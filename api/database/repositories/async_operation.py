"""
Repository for async operations.
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional

from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from api.database.models.async_operation import AsyncOperation
from api.database.repositories.base import BaseRepository


class AsyncOperationRepository(BaseRepository[AsyncOperation]):
    """Repository for managing async operations."""

    def __init__(self, session: AsyncSession):
        super().__init__(session, AsyncOperation)

    async def create_operation(
        self,
        operation_id: str,
        operation_type: str,
        estimated_completion: Optional[datetime] = None,
        user_id: Optional[str] = None,
        initial_result: Optional[dict] = None,
    ) -> AsyncOperation:
        """
        Create a new async operation.

        Args:
            operation_id: Unique operation ID
            operation_type: Type of operation (e.g., "linear_map")
            estimated_completion: Estimated completion time
            user_id: ID of the user who requested the operation
            initial_result: Initial result data (e.g., origin/destination for display during progress)

        Returns:
            Created AsyncOperation instance
        """
        operation = AsyncOperation(
            id=operation_id,
            operation_type=operation_type,
            status="in_progress",
            progress_percent=0.0,
            estimated_completion=estimated_completion,
            user_id=user_id,
            result=initial_result,
        )
        return await self.create(operation)

    async def get_by_operation_id(self, operation_id: str) -> Optional[AsyncOperation]:
        """
        Get an operation by its ID.

        Args:
            operation_id: Operation UUID string

        Returns:
            AsyncOperation instance or None if not found
        """
        result = await self.session.execute(
            select(AsyncOperation).where(AsyncOperation.id == operation_id)
        )
        return result.scalar_one_or_none()

    async def update_progress(
        self,
        operation_id: str,
        progress_percent: float,
        estimated_completion: Optional[datetime] = None,
    ) -> bool:
        """
        Update operation progress.

        Args:
            operation_id: Operation ID
            progress_percent: New progress percentage (0-100)
            estimated_completion: Updated estimated completion time

        Returns:
            True if updated, False if operation not found
        """
        values = {"progress_percent": progress_percent}
        if estimated_completion is not None:
            values["estimated_completion"] = estimated_completion

        result = await self.session.execute(
            update(AsyncOperation)
            .where(AsyncOperation.id == operation_id)
            .where(AsyncOperation.status == "in_progress")
            .values(**values)
        )
        return result.rowcount > 0

    async def complete_operation(
        self,
        operation_id: str,
        result: Dict,
    ) -> bool:
        """
        Mark an operation as completed with its result.

        Args:
            operation_id: Operation ID
            result: Operation result data

        Returns:
            True if updated, False if operation not found
        """
        result_update = await self.session.execute(
            update(AsyncOperation)
            .where(AsyncOperation.id == operation_id)
            .values(
                status="completed",
                progress_percent=100.0,
                completed_at=func.now(),
                estimated_completion=None,
                result=result,
            )
        )
        return result_update.rowcount > 0

    async def fail_operation(
        self,
        operation_id: str,
        error: str,
    ) -> bool:
        """
        Mark an operation as failed.

        Args:
            operation_id: Operation ID
            error: Error message

        Returns:
            True if updated, False if operation not found
        """
        result = await self.session.execute(
            update(AsyncOperation)
            .where(AsyncOperation.id == operation_id)
            .values(
                status="failed",
                completed_at=func.now(),
                estimated_completion=None,
                error=error,
            )
        )
        return result.rowcount > 0

    async def list_operations(
        self,
        active_only: bool = True,
        operation_type: Optional[str] = None,
        limit: int = 100,
    ) -> List[AsyncOperation]:
        """
        List async operations.

        Args:
            active_only: If True, only return in_progress operations
            operation_type: Filter by operation type
            limit: Maximum number of operations to return

        Returns:
            List of AsyncOperation instances
        """
        query = select(AsyncOperation)

        if active_only:
            query = query.where(AsyncOperation.status == "in_progress")

        if operation_type:
            query = query.where(AsyncOperation.operation_type == operation_type)

        query = query.order_by(AsyncOperation.started_at.desc()).limit(limit)

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def cleanup_old_operations(self, max_age_hours: int = 24) -> int:
        """
        Remove old completed/failed operations.

        Args:
            max_age_hours: Maximum age in hours for operations to keep

        Returns:
            Number of deleted operations
        """
        cutoff_time = datetime.now() - timedelta(hours=max_age_hours)

        result = await self.session.execute(
            delete(AsyncOperation)
            .where(AsyncOperation.status.in_(["completed", "failed"]))
            .where(AsyncOperation.started_at < cutoff_time)
        )
        return result.rowcount

    async def cleanup_stale_operations(self, stale_hours: int = 2) -> int:
        """
        Mark stale in_progress operations as failed and remove them.

        Operations that have been in_progress for too long are likely stuck.

        Args:
            stale_hours: Hours after which an in_progress operation is considered stale

        Returns:
            Number of operations marked as failed
        """
        cutoff_time = datetime.now() - timedelta(hours=stale_hours)

        # First, mark stale operations as failed
        result = await self.session.execute(
            update(AsyncOperation)
            .where(AsyncOperation.status == "in_progress")
            .where(AsyncOperation.started_at < cutoff_time)
            .values(
                status="failed",
                completed_at=func.now(),
                error="Operation timed out (stale)",
            )
        )
        return result.rowcount

    async def get_stats(self, operation_type: Optional[str] = None) -> Dict:
        """
        Get statistics about async operations.

        Args:
            operation_type: Filter by operation type

        Returns:
            Dictionary with operation statistics
        """
        from sqlalchemy import func

        # Count by status
        query = select(
            AsyncOperation.status,
            func.count(AsyncOperation.id).label("count"),
        )

        if operation_type:
            query = query.where(AsyncOperation.operation_type == operation_type)

        query = query.group_by(AsyncOperation.status)

        result = await self.session.execute(query)

        stats = {"in_progress": 0, "completed": 0, "failed": 0, "total": 0}
        for row in result.all():
            stats[row.status] = row.count
            stats["total"] += row.count

        return stats

    async def list_all_operations(
        self,
        status: Optional[str] = None,
        operation_type: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[AsyncOperation]:
        """
        List all operations with user information for admin views.

        Args:
            status: Filter by status (in_progress, completed, failed)
            operation_type: Filter by operation type
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of AsyncOperation instances with user relationship loaded
        """
        from sqlalchemy.orm import selectinload

        query = select(AsyncOperation).options(selectinload(AsyncOperation.user))

        if status:
            query = query.where(AsyncOperation.status == status)

        if operation_type:
            query = query.where(AsyncOperation.operation_type == operation_type)

        query = query.order_by(AsyncOperation.started_at.desc()).offset(skip).limit(limit)

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def count_operations(
        self,
        status: Optional[str] = None,
        operation_type: Optional[str] = None,
    ) -> int:
        """
        Count operations with optional filters.

        Args:
            status: Filter by status
            operation_type: Filter by operation type

        Returns:
            Count of matching operations
        """
        from sqlalchemy import func

        query = select(func.count(AsyncOperation.id))

        if status:
            query = query.where(AsyncOperation.status == status)

        if operation_type:
            query = query.where(AsyncOperation.operation_type == operation_type)

        result = await self.session.execute(query)
        return result.scalar() or 0
