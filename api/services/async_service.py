"""
Service for managing async operations with PostgreSQL storage.
"""

import asyncio
import logging
import threading
import uuid
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional

from api.database.connection import get_session
from api.database.models.async_operation import AsyncOperation
from api.database.repositories.async_operation import AsyncOperationRepository
from api.models.road_models import AsyncOperationResponse, OperationStatus

logger = logging.getLogger(__name__)

# In-memory cache of active operations for quick access
_active_operations: Dict[str, AsyncOperationResponse] = {}


class AsyncService:
    """Service for managing async operations stored in PostgreSQL."""

    @staticmethod
    def _db_to_response(db_op: AsyncOperation) -> AsyncOperationResponse:
        """Convert database model to response model."""
        return AsyncOperationResponse(
            operation_id=db_op.id,
            type=db_op.operation_type,
            status=OperationStatus(db_op.status),
            started_at=db_op.started_at,
            progress_percent=db_op.progress_percent,
            estimated_completion=db_op.estimated_completion,
            result=db_op.result,
            error=db_op.error,
        )

    @staticmethod
    async def _create_operation_async(operation_type: str) -> AsyncOperationResponse:
        """Create a new operation in the database (async version)."""
        operation_id = str(uuid.uuid4())
        estimated_completion = datetime.now() + timedelta(minutes=5)

        async with get_session() as session:
            repo = AsyncOperationRepository(session)
            db_op = await repo.create_operation(
                operation_id=operation_id,
                operation_type=operation_type,
                estimated_completion=estimated_completion,
            )

            response = AsyncService._db_to_response(db_op)
            _active_operations[operation_id] = response
            return response

    @staticmethod
    async def create_operation(operation_type: str) -> AsyncOperationResponse:
        """
        Create a new async operation.

        Args:
            operation_type: Type of operation (e.g., "linear_map")

        Returns:
            AsyncOperationResponse object
        """
        return await AsyncService._create_operation_async(operation_type)

    @staticmethod
    async def _get_operation_async(operation_id: str) -> Optional[AsyncOperationResponse]:
        """Get an operation from the database (async version)."""
        # Check in-memory cache first
        if operation_id in _active_operations:
            return _active_operations[operation_id]

        async with get_session() as session:
            repo = AsyncOperationRepository(session)
            db_op = await repo.get_by_operation_id(operation_id)

            if db_op is None:
                return None

            response = AsyncService._db_to_response(db_op)

            # Cache active operations
            if response.status == OperationStatus.IN_PROGRESS:
                _active_operations[operation_id] = response

            return response

    @staticmethod
    def get_operation(operation_id: str) -> Optional[AsyncOperationResponse]:
        """
        Get an operation by its ID.

        Args:
            operation_id: Operation ID

        Returns:
            AsyncOperationResponse or None if not found
        """
        # Check in-memory cache first (sync access)
        if operation_id in _active_operations:
            return _active_operations[operation_id]

        try:
            loop = asyncio.get_running_loop()
            future = asyncio.run_coroutine_threadsafe(
                AsyncService._get_operation_async(operation_id),
                loop
            )
            return future.result(timeout=10)
        except RuntimeError:
            return asyncio.run(AsyncService._get_operation_async(operation_id))

    @staticmethod
    async def _update_progress_async(
        operation_id: str,
        progress_percent: float,
        estimated_completion: Optional[datetime] = None
    ) -> None:
        """Update operation progress in database (async version)."""
        async with get_session() as session:
            repo = AsyncOperationRepository(session)
            await repo.update_progress(
                operation_id=operation_id,
                progress_percent=progress_percent,
                estimated_completion=estimated_completion,
            )

        # Update in-memory cache
        if operation_id in _active_operations:
            _active_operations[operation_id].progress_percent = progress_percent
            if estimated_completion:
                _active_operations[operation_id].estimated_completion = estimated_completion

    @staticmethod
    def update_progress(
        operation_id: str,
        progress_percent: float,
        estimated_completion: Optional[datetime] = None
    ) -> None:
        """
        Update operation progress.

        Args:
            operation_id: Operation ID
            progress_percent: Progress percentage (0-100)
            estimated_completion: Updated estimated completion time
        """
        try:
            loop = asyncio.get_running_loop()
            future = asyncio.run_coroutine_threadsafe(
                AsyncService._update_progress_async(
                    operation_id, progress_percent, estimated_completion
                ),
                loop
            )
            future.result(timeout=10)
        except RuntimeError:
            asyncio.run(
                AsyncService._update_progress_async(
                    operation_id, progress_percent, estimated_completion
                )
            )

    @staticmethod
    async def _complete_operation_async(operation_id: str, result: Dict[str, Any]) -> None:
        """Mark operation as completed in database (async version)."""
        async with get_session() as session:
            repo = AsyncOperationRepository(session)
            await repo.complete_operation(operation_id=operation_id, result=result)

        # Remove from in-memory cache
        _active_operations.pop(operation_id, None)
        logger.info(f"Operation {operation_id} completed successfully")

    @staticmethod
    def complete_operation(operation_id: str, result: Dict[str, Any]) -> None:
        """
        Mark an operation as completed.

        Args:
            operation_id: Operation ID
            result: Operation result data
        """
        try:
            loop = asyncio.get_running_loop()
            future = asyncio.run_coroutine_threadsafe(
                AsyncService._complete_operation_async(operation_id, result),
                loop
            )
            future.result(timeout=10)
        except RuntimeError:
            asyncio.run(AsyncService._complete_operation_async(operation_id, result))

    @staticmethod
    async def _fail_operation_async(operation_id: str, error: str) -> None:
        """Mark operation as failed in database (async version)."""
        async with get_session() as session:
            repo = AsyncOperationRepository(session)
            await repo.fail_operation(operation_id=operation_id, error=error)

        # Remove from in-memory cache
        _active_operations.pop(operation_id, None)
        logger.error(f"Operation {operation_id} failed: {error}")

    @staticmethod
    def fail_operation(operation_id: str, error: str) -> None:
        """
        Mark an operation as failed.

        Args:
            operation_id: Operation ID
            error: Error message
        """
        try:
            loop = asyncio.get_running_loop()
            future = asyncio.run_coroutine_threadsafe(
                AsyncService._fail_operation_async(operation_id, error),
                loop
            )
            future.result(timeout=10)
        except RuntimeError:
            asyncio.run(AsyncService._fail_operation_async(operation_id, error))

    @staticmethod
    async def _list_operations_async(active_only: bool = True) -> List[AsyncOperationResponse]:
        """List operations from database (async version)."""
        async with get_session() as session:
            repo = AsyncOperationRepository(session)
            db_ops = await repo.list_operations(active_only=active_only)
            return [AsyncService._db_to_response(op) for op in db_ops]

    @staticmethod
    def list_operations(active_only: bool = True) -> List[AsyncOperationResponse]:
        """
        List async operations.

        Args:
            active_only: If True, only return in_progress operations

        Returns:
            List of operations
        """
        try:
            loop = asyncio.get_running_loop()
            future = asyncio.run_coroutine_threadsafe(
                AsyncService._list_operations_async(active_only),
                loop
            )
            return future.result(timeout=10)
        except RuntimeError:
            return asyncio.run(AsyncService._list_operations_async(active_only))

    @staticmethod
    def run_async(
        operation_id: str,
        function: Callable,
        *args,
        **kwargs
    ) -> None:
        """
        Execute a function asynchronously in a background thread.

        Args:
            operation_id: Operation ID
            function: Function to execute
            *args, **kwargs: Arguments for the function
        """
        def _update_progress(progress: float):
            AsyncService.update_progress(
                operation_id,
                progress,
                estimated_completion=datetime.now() + timedelta(minutes=5 * (100 - progress) / 100)
            )

        def _worker():
            # Create a new event loop for this thread
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            try:
                # Update to 5% to show it started
                _update_progress(5)

                # Execute the function with progress callback
                result = function(
                    progress_callback=_update_progress,
                    *args,
                    **kwargs
                )

                # Mark as completed
                AsyncService.complete_operation(operation_id, result)
            except Exception as e:
                logger.error(f"Error in async operation {operation_id}: {str(e)}")
                AsyncService.fail_operation(operation_id, str(e))

        # Start background thread
        thread = threading.Thread(target=_worker)
        thread.daemon = True
        thread.start()

        logger.info(f"Async operation {operation_id} started in background")

    @staticmethod
    async def cleanup_old_operations(max_age_hours: int = 24) -> int:
        """
        Remove old completed/failed operations from the database.

        Args:
            max_age_hours: Maximum age in hours for operations to keep

        Returns:
            Number of operations removed
        """
        async with get_session() as session:
            repo = AsyncOperationRepository(session)

            # First, mark stale in_progress operations as failed
            stale_count = await repo.cleanup_stale_operations(stale_hours=2)
            if stale_count > 0:
                logger.info(f"Marked {stale_count} stale operations as failed")

            # Then, remove old completed/failed operations
            removed_count = await repo.cleanup_old_operations(max_age_hours=max_age_hours)
            logger.info(f"Removed {removed_count} old operations")

            return removed_count + stale_count

    @staticmethod
    def cleanup_old_operations_sync(max_age_hours: int = 24) -> int:
        """
        Synchronous wrapper for cleanup_old_operations.

        Args:
            max_age_hours: Maximum age in hours for operations to keep

        Returns:
            Number of operations removed
        """
        try:
            loop = asyncio.get_running_loop()
            future = asyncio.run_coroutine_threadsafe(
                AsyncService.cleanup_old_operations(max_age_hours),
                loop
            )
            return future.result(timeout=30)
        except RuntimeError:
            return asyncio.run(AsyncService.cleanup_old_operations(max_age_hours))
