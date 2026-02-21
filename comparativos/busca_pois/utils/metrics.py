"""
Metrics utilities for comparing POI search results.
"""

from typing import List, Dict, Any
from collections import defaultdict

from providers.base import POIResult


def compare_results(
    results_by_provider: Dict[str, List[POIResult]]
) -> Dict[str, Any]:
    """
    Compare results from multiple providers.
    
    Args:
        results_by_provider: Dict mapping provider name to list of results
        
    Returns:
        Comparison metrics
    """
    comparison = {}
    
    for provider, results in results_by_provider.items():
        # Group by category
        by_category = defaultdict(list)
        for poi in results:
            by_category[poi.category].append(poi)
        
        # Calculate stats
        comparison[provider] = {
            "total": len(results),
            "by_category": {cat: len(pois) for cat, pois in by_category.items()},
            "unique_ids": set(poi.id for poi in results),
            "with_phone": sum(1 for poi in results if poi.phone),
            "with_website": sum(1 for poi in results if poi.website),
            "with_rating": sum(1 for poi in results if poi.rating),
            "with_address": sum(1 for poi in results if poi.address),
        }
    
    # Calculate overlaps
    if len(comparison) > 1:
        providers = list(comparison.keys())
        for i, p1 in enumerate(providers):
            for p2 in providers[i+1:]:
                ids1 = comparison[p1]["unique_ids"]
                ids2 = comparison[p2]["unique_ids"]
                overlap = ids1.intersection(ids2)
                comparison[f"{p1}_vs_{p2}_overlap"] = len(overlap)
    
    return comparison


def calculate_category_stats(
    results_by_provider: Dict[str, List[POIResult]]
) -> Dict[str, Dict[str, int]]:
    """
    Calculate statistics by category for each provider.
    
    Returns:
        {provider: {category: count}}
    """
    stats = {}
    
    for provider, results in results_by_provider.items():
        category_counts = defaultdict(int)
        for poi in results:
            category_counts[poi.category] += 1
        stats[provider] = dict(category_counts)
    
    return stats


def generate_summary(
    results_by_provider: Dict[str, List[POIResult]],
    timing_stats: Dict[str, Dict[str, Any]]
) -> str:
    """
    Generate a text summary of the comparison.
    
    Args:
        results_by_provider: Results from each provider
        timing_stats: Timing statistics
        
    Returns:
        Formatted summary string
    """
    lines = []
    
    # Summary table
    lines.append("| Provider | Total POIs | Tempo Médio | Com Telefone | Com Website |")
    lines.append("|----------|------------|-------------|--------------|-------------|")
    
    for provider, results in results_by_provider.items():
        stats = timing_stats.get(provider, {})
        avg_time = stats.get("avg_time_per_request_seconds", 0)
        
        with_phone = sum(1 for poi in results if poi.phone)
        with_website = sum(1 for poi in results if poi.website)
        
        lines.append(
            f"| {provider:8} | {len(results):10} | {avg_time:9.3f}s | {with_phone:12} | {with_website:11} |"
        )
    
    return "\n".join(lines)


def calculate_data_quality_score(results: List[POIResult]) -> float:
    """
    Calculate data quality score based on completeness.
    
    Args:
        results: List of POI results
        
    Returns:
        Quality score 0-100
    """
    if not results:
        return 0.0
    
    total = len(results)
    scores = []
    
    for poi in results:
        # Check each field
        fields = 0
        if poi.name and poi.name != "Sem nome":
            fields += 1
        if poi.phone:
            fields += 1
        if poi.website:
            fields += 1
        if poi.address:
            fields += 1
        if poi.rating:
            fields += 1
        
        # Each field is worth 20 points
        scores.append(fields * 20)
    
    return sum(scores) / len(scores)


def find_duplicates(
    results: List[POIResult],
    distance_threshold_m: float = 50
) -> List[List[POIResult]]:
    """
    Find potential duplicate POIs based on location proximity.
    
    Args:
        results: List of POI results
        distance_threshold_m: Distance threshold in meters
        
    Returns:
        List of duplicate groups
    """
    from utils.geometry import calculate_distance_meters
    
    duplicates = []
    processed = set()
    
    for i, poi1 in enumerate(results):
        if poi1.id in processed:
            continue
        
        group = [poi1]
        
        for j, poi2 in enumerate(results[i+1:], i+1):
            if poi2.id in processed:
                continue
            
            # Check distance
            dist = calculate_distance_meters(
                poi1.latitude, poi1.longitude,
                poi2.latitude, poi2.longitude
            )
            
            if dist < distance_threshold_m:
                group.append(poi2)
                processed.add(poi2.id)
        
        if len(group) > 1:
            duplicates.append(group)
            processed.add(poi1.id)
    
    return duplicates