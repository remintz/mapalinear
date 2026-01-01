"""
Async utility functions for safe execution of coroutines.

This module provides helpers for running async code from synchronous contexts,
handling event loop conflicts that can occur in various execution environments.
"""

import asyncio
import concurrent.futures
from typing import Any, Coroutine


def run_async_safe(coro: Coroutine) -> Any:
    """
    Execute async coroutine safely, handling both running and non-running event loops.

    This helper allows calling async provider methods from sync contexts.
    It handles three scenarios:
    1. No event loop exists - creates a new one with asyncio.run()
    2. Event loop exists but not running - uses run_until_complete()
    3. Event loop is already running - runs in a separate thread

    Args:
        coro: The coroutine to execute

    Returns:
        The result of the coroutine execution
    """
    try:
        # Try to get the event loop for this thread
        loop = asyncio.get_event_loop()

        # Check if the loop is running
        if loop.is_running():
            # If loop is already running (e.g., in async context),
            # we need to run in a new thread
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, coro)
                return future.result()
        else:
            # Loop exists but not running - run the coroutine in it
            return loop.run_until_complete(coro)
    except RuntimeError:
        # No event loop in this thread, create and use a new one
        return asyncio.run(coro)
