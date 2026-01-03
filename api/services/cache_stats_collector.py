"""
Cache statistics collector for per-map-generation tracking.

This module provides a collector that tracks cache hits/misses
for a single map generation operation, allowing summary display
at the end of the generation process.
"""

import logging
import threading
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Dict, Optional, Generator

logger = logging.getLogger(__name__)

# Thread-local storage for the current stats collector
_thread_local = threading.local()


@dataclass
class CacheStatsCollector:
    """
    Collects cache hit/miss statistics for a single map generation.

    This collector is instantiated for each map generation and passed
    through the services to track cache usage per operation type.
    """

    _hits_by_operation: Dict[str, int] = field(default_factory=dict)
    _misses_by_operation: Dict[str, int] = field(default_factory=dict)

    def record_hit(self, operation: str) -> None:
        """Record a cache hit for the given operation type."""
        if operation not in self._hits_by_operation:
            self._hits_by_operation[operation] = 0
        self._hits_by_operation[operation] += 1

    def record_miss(self, operation: str) -> None:
        """Record a cache miss for the given operation type."""
        if operation not in self._misses_by_operation:
            self._misses_by_operation[operation] = 0
        self._misses_by_operation[operation] += 1

    def get_summary(self) -> Dict[str, Dict[str, int]]:
        """
        Get summary of cache statistics by operation.

        Returns:
            Dictionary with operation names as keys and
            {hits, misses, total, hit_rate} as values.
        """
        # Get all unique operations
        all_operations = set(self._hits_by_operation.keys()) | set(self._misses_by_operation.keys())

        summary = {}
        for operation in sorted(all_operations):
            hits = self._hits_by_operation.get(operation, 0)
            misses = self._misses_by_operation.get(operation, 0)
            total = hits + misses
            hit_rate = (hits / total * 100) if total > 0 else 0

            summary[operation] = {
                "hits": hits,
                "misses": misses,
                "total": total,
                "hit_rate": round(hit_rate, 1)
            }

        return summary

    def get_totals(self) -> Dict[str, int]:
        """
        Get total cache statistics across all operations.

        Returns:
            Dictionary with total hits, misses, total, and hit_rate.
        """
        total_hits = sum(self._hits_by_operation.values())
        total_misses = sum(self._misses_by_operation.values())
        total = total_hits + total_misses
        hit_rate = (total_hits / total * 100) if total > 0 else 0

        return {
            "hits": total_hits,
            "misses": total_misses,
            "total": total,
            "hit_rate": round(hit_rate, 1)
        }

    def log_summary(self) -> None:
        """Log a summary of cache statistics."""
        summary = self.get_summary()
        totals = self.get_totals()

        if not summary:
            logger.info("📊 Cache: No cache operations recorded")
            return

        logger.info("📊 Cache Statistics Summary:")
        logger.info(f"   {'Operation':<20} {'Hits':>6} {'Misses':>6} {'Total':>6} {'Hit Rate':>8}")
        logger.info(f"   {'-'*20} {'-'*6} {'-'*6} {'-'*6} {'-'*8}")

        for operation, stats in summary.items():
            logger.info(
                f"   {operation:<20} {stats['hits']:>6} {stats['misses']:>6} "
                f"{stats['total']:>6} {stats['hit_rate']:>7.1f}%"
            )

        logger.info(f"   {'-'*20} {'-'*6} {'-'*6} {'-'*6} {'-'*8}")
        logger.info(
            f"   {'TOTAL':<20} {totals['hits']:>6} {totals['misses']:>6} "
            f"{totals['total']:>6} {totals['hit_rate']:>7.1f}%"
        )


def get_current_collector() -> Optional[CacheStatsCollector]:
    """Get the current cache stats collector for this thread, if any."""
    return getattr(_thread_local, 'collector', None)


def set_current_collector(collector: Optional[CacheStatsCollector]) -> None:
    """Set the current cache stats collector for this thread."""
    _thread_local.collector = collector


@contextmanager
def cache_stats_context() -> Generator[CacheStatsCollector, None, None]:
    """
    Context manager that creates and manages a cache stats collector.

    Usage:
        with cache_stats_context() as stats:
            # ... do cache operations ...
            stats.log_summary()
    """
    collector = CacheStatsCollector()
    previous = get_current_collector()
    set_current_collector(collector)
    try:
        yield collector
    finally:
        set_current_collector(previous)


def record_cache_hit(operation: str) -> None:
    """Record a cache hit for the current collector, if any."""
    collector = get_current_collector()
    if collector:
        collector.record_hit(operation)


def record_cache_miss(operation: str) -> None:
    """Record a cache miss for the current collector, if any."""
    collector = get_current_collector()
    if collector:
        collector.record_miss(operation)
