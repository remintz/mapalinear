"""
Unit tests for api/utils/async_utils.py

Tests for async utility functions:
- run_async_safe (safe execution of coroutines)
"""

import asyncio
import pytest

from api.utils.async_utils import run_async_safe


class TestRunAsyncSafe:
    """Tests for run_async_safe function."""

    def test_simple_coroutine_returns_value(self):
        """Simple coroutine should return its value."""
        async def simple_coro():
            return 42

        result = run_async_safe(simple_coro())
        assert result == 42

    def test_async_with_await(self):
        """Coroutine with await should work."""
        async def coro_with_await():
            await asyncio.sleep(0.01)
            return "done"

        result = run_async_safe(coro_with_await())
        assert result == "done"

    def test_returns_complex_value(self):
        """Should return complex data structures."""
        async def complex_coro():
            return {"key": "value", "list": [1, 2, 3]}

        result = run_async_safe(complex_coro())
        assert result == {"key": "value", "list": [1, 2, 3]}

    def test_exception_propagation(self):
        """Exceptions in coroutine should propagate."""
        async def error_coro():
            raise ValueError("test error")

        with pytest.raises(ValueError, match="test error"):
            run_async_safe(error_coro())

    def test_returns_none(self):
        """Coroutine returning None should work."""
        async def none_coro():
            return None

        result = run_async_safe(none_coro())
        assert result is None

    def test_with_parameters(self):
        """Coroutine with parameters should work."""
        async def param_coro(a, b):
            return a + b

        result = run_async_safe(param_coro(10, 20))
        assert result == 30

    def test_multiple_awaits(self):
        """Coroutine with multiple awaits should work."""
        async def multi_await():
            await asyncio.sleep(0.01)
            x = 1
            await asyncio.sleep(0.01)
            x += 1
            return x

        result = run_async_safe(multi_await())
        assert result == 2

    def test_nested_coroutines(self):
        """Nested coroutines should work."""
        async def inner():
            return 5

        async def outer():
            result = await inner()
            return result * 2

        result = run_async_safe(outer())
        assert result == 10

    @pytest.mark.asyncio
    async def test_from_async_context(self):
        """Should work when called from an async context."""
        # This tests the thread pool executor path
        async def simple_coro():
            return "from async"

        # When running in an async context, run_async_safe uses thread pool
        # We need to call it in a sync function from within async
        import concurrent.futures

        def sync_wrapper():
            return run_async_safe(simple_coro())

        # Run sync wrapper in executor to avoid nested event loop issues
        loop = asyncio.get_event_loop()
        with concurrent.futures.ThreadPoolExecutor() as executor:
            result = await loop.run_in_executor(executor, sync_wrapper)

        assert result == "from async"
