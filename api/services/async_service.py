"""
Service for managing async operations with PostgreSQL storage.
"""

import asyncio
import logging
import threading
import uuid
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional, Union

from api.database.connection import get_session
from api.database.models.async_operation import AsyncOperation
from api.database.repositories.async_operation import AsyncOperationRepository
from api.models.road_models import AsyncOperationResponse, OperationStatus

logger = logging.getLogger(__name__)

# In-memory cache of active operations for quick access
_active_operations: Dict[str, AsyncOperationResponse] = {}


def _serialize_for_json(obj: Any) -> Any:
    """Recursively serialize objects for JSON storage in PostgreSQL JSONB columns.

    Handles datetime objects by converting them to ISO format strings.
    """
    if isinstance(obj, datetime):
        return obj.isoformat()
    elif isinstance(obj, dict):
        return {k: _serialize_for_json(v) for k, v in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return [_serialize_for_json(item) for item in obj]
    return obj


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
            current_phase=db_op.current_phase,
            estimated_completion=db_op.estimated_completion,
            result=db_op.result,
            error=db_op.error,
        )

    @staticmethod
    async def _create_operation_async(
        operation_type: str,
        user_id: Optional[str] = None,
        initial_result: Optional[dict] = None,
    ) -> AsyncOperationResponse:
        """Create a new operation in the database (async version)."""
        operation_id = str(uuid.uuid4())
        estimated_completion = datetime.now() + timedelta(minutes=5)

        async with get_session() as session:
            repo = AsyncOperationRepository(session)
            db_op = await repo.create_operation(
                operation_id=operation_id,
                operation_type=operation_type,
                estimated_completion=estimated_completion,
                user_id=user_id,
                initial_result=initial_result,
            )

            response = AsyncService._db_to_response(db_op)
            _active_operations[operation_id] = response
            return response

    @staticmethod
    async def create_operation(
        operation_type: str,
        user_id: Optional[str] = None,
        initial_result: Optional[dict] = None,
    ) -> AsyncOperationResponse:
        """
        Create a new async operation.

        Args:
            operation_type: Type of operation (e.g., "linear_map")
            user_id: ID of the user who requested the operation
            initial_result: Initial result data (e.g., origin/destination for display)

        Returns:
            AsyncOperationResponse object
        """
        return await AsyncService._create_operation_async(operation_type, user_id, initial_result)

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
    async def get_operation(operation_id: str) -> Optional[AsyncOperationResponse]:
        """
        Get an operation by its ID.

        Args:
            operation_id: Operation ID

        Returns:
            AsyncOperationResponse or None if not found
        """
        return await AsyncService._get_operation_async(operation_id)

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
        # Serialize datetime objects to ISO strings for JSONB storage
        serialized_result = _serialize_for_json(result)
        async with get_session() as session:
            repo = AsyncOperationRepository(session)
            await repo.complete_operation(operation_id=operation_id, result=serialized_result)

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
    async def list_operations(active_only: bool = True) -> List[AsyncOperationResponse]:
        """
        List async operations.

        Args:
            active_only: If True, only return in_progress operations

        Returns:
            List of operations
        """
        return await AsyncService._list_operations_async(active_only)

    @staticmethod
    def run_async(
        operation_id: str,
        function: Callable,
        *args,
        request_id: Optional[str] = None,
        **kwargs
    ) -> None:
        """
        Execute a function asynchronously in a background thread.

        Args:
            operation_id: Operation ID
            function: Function to execute
            request_id: Optional request ID for log tracking
            *args, **kwargs: Arguments for the function
        """
        from api.database.connection import create_standalone_engine, get_standalone_session
        from api.database.repositories.async_operation import AsyncOperationRepository
        from api.middleware.request_id import set_request_id

        def _worker():
            # Set request ID for this thread (for log tracking)
            if request_id:
                set_request_id(request_id)
            # Create a new event loop for this thread
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            # Create a standalone engine for this thread
            engine = create_standalone_engine()

            async def _update_progress_bg(progress: float, phase: Optional[str] = None):
                """Update progress using the thread's own database connection."""
                async with get_standalone_session(engine) as session:
                    repo = AsyncOperationRepository(session)
                    await repo.update_progress(
                        operation_id=operation_id,
                        progress_percent=progress,
                        estimated_completion=datetime.now() + timedelta(minutes=5 * (100 - progress) / 100),
                        current_phase=phase,
                    )
                # Update in-memory cache
                if operation_id in _active_operations:
                    _active_operations[operation_id].progress_percent = progress
                    if phase is not None:
                        _active_operations[operation_id].current_phase = phase

            async def _complete_operation_bg(result: Dict[str, Any]):
                """Complete operation using the thread's own database connection."""
                # Serialize datetime objects to ISO strings for JSONB storage
                serialized_result = _serialize_for_json(result)
                async with get_standalone_session(engine) as session:
                    repo = AsyncOperationRepository(session)
                    await repo.complete_operation(operation_id=operation_id, result=serialized_result)
                _active_operations.pop(operation_id, None)
                logger.info(f"Operation {operation_id} completed successfully")

            async def _fail_operation_bg(error: str):
                """Fail operation using the thread's own database connection."""
                async with get_standalone_session(engine) as session:
                    repo = AsyncOperationRepository(session)
                    await repo.fail_operation(operation_id=operation_id, error=error)
                _active_operations.pop(operation_id, None)
                logger.error(f"Operation {operation_id} failed: {error}")

            # Track last persisted progress to avoid excessive DB writes
            last_persisted_progress = [0.0]  # Use list to allow mutation in closure
            last_persisted_phase = [None]  # Track last phase to detect phase changes

            def _update_progress_sync(progress: float, phase: Optional[str] = None):
                """Sync wrapper for progress updates.

                Persists progress to database with throttling (only when progress
                changes by >= 5% OR phase changes). When called from within a running
                event loop (e.g., inside run_async_safe), schedules the update as a task.
                When called from sync context, uses run_until_complete.

                Args:
                    progress: Overall progress percentage (0-100)
                    phase: Current phase name (e.g., "geocoding", "poi_search")
                """
                # Always update in-memory cache (fast, sync)
                if operation_id in _active_operations:
                    _active_operations[operation_id].progress_percent = progress
                    _active_operations[operation_id].estimated_completion = (
                        datetime.now() + timedelta(minutes=5 * (100 - progress) / 100)
                    )
                    if phase is not None:
                        _active_operations[operation_id].current_phase = phase

                # Persist to DB if progress changed by >= 5% OR phase changed
                phase_changed = phase is not None and phase != last_persisted_phase[0]
                progress_changed = progress - last_persisted_progress[0] >= 5.0

                if not phase_changed and not progress_changed:
                    return

                last_persisted_progress[0] = progress
                if phase is not None:
                    last_persisted_phase[0] = phase

                # Persist to DB
                # We need to check if we're in the same thread/loop context
                try:
                    running_loop = asyncio.get_running_loop()
                    # We're inside an async context - check if it's our loop
                    if running_loop is loop:
                        # Same loop - schedule as task
                        asyncio.ensure_future(_update_progress_bg(progress, phase), loop=loop)
                    else:
                        # Different loop (e.g., inside run_async_safe's thread)
                        # Schedule on our main worker loop using thread-safe call
                        # Capture values in default args to avoid closure issues
                        def _schedule_update(p=progress, ph=phase):
                            asyncio.ensure_future(_update_progress_bg(p, ph), loop=loop)
                        loop.call_soon_threadsafe(_schedule_update)
                except RuntimeError:
                    # No running loop - we can use run_until_complete
                    try:
                        loop.run_until_complete(_update_progress_bg(progress, phase))
                    except Exception as e:
                        logger.warning(f"Failed to persist progress to DB: {e}")

            try:
                # Update to 5% to show it started (loop not running yet)
                loop.run_until_complete(_update_progress_bg(5))

                # Execute the function with progress callback
                result = function(
                    progress_callback=_update_progress_sync,
                    *args,
                    **kwargs
                )

                # Mark as completed
                loop.run_until_complete(_complete_operation_bg(result))
            except Exception as e:
                logger.error(f"Error in async operation {operation_id}: {str(e)}")
                try:
                    loop.run_until_complete(_fail_operation_bg(str(e)))
                except Exception as fail_error:
                    logger.error(f"Failed to mark operation as failed: {fail_error}")
            finally:
                # Clean up the engine and loop
                try:
                    loop.run_until_complete(engine.dispose())
                except Exception:
                    pass
                loop.close()

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
