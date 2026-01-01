"""
Route Statistics Service - Generate statistics and recommendations for routes.

This service handles:
- Calculating POI distribution statistics
- Generating stop recommendations
- Calculating quality metrics
"""

from typing import Any, Dict, List, TYPE_CHECKING

from api.models.road_models import (
    POIStatistics,
    RoadMilestone,
    RouteStatisticsResponse,
    RouteStopRecommendation,
)

if TYPE_CHECKING:
    from api.services.road_service import RoadService


class RouteStatisticsService:
    """
    Service for generating route statistics and recommendations.

    This service analyzes POI distribution along a route and provides
    insights and recommendations for optimal stops.
    """

    def __init__(self, road_service: "RoadService"):
        """
        Initialize the Route Statistics Service.

        Args:
            road_service: RoadService instance for map generation
        """
        self.road_service = road_service

    def get_statistics(
        self,
        origin: str,
        destination: str,
        max_distance_from_road: float = 1000,
    ) -> RouteStatisticsResponse:
        """
        Generate detailed statistics for a route.

        Always searches for all POI types for comprehensive statistics.

        Args:
            origin: Starting point
            destination: End point
            max_distance_from_road: Maximum POI search distance

        Returns:
            RouteStatisticsResponse with complete statistics
        """
        # Generate linear map to get data
        linear_map = self.road_service.generate_linear_map(
            origin=origin,
            destination=destination,
            include_cities=True,
            max_distance_from_road=max_distance_from_road,
        )

        # Calculate statistics by POI type
        poi_stats = []
        all_milestones: List[RoadMilestone] = []

        # Collect all milestones from segments
        for segment in linear_map.segments:
            all_milestones.extend(segment.milestones)

        # Group by type
        poi_types: Dict[str, List[RoadMilestone]] = {}
        for milestone in all_milestones:
            type_value = milestone.type.value
            if type_value not in poi_types:
                poi_types[type_value] = []
            poi_types[type_value].append(milestone)

        # Calculate statistics for each type
        for poi_type, milestones in poi_types.items():
            if poi_type == "city":  # Skip cities in statistics
                continue

            if len(milestones) > 1:
                # Calculate average distance between POIs
                distances = []
                sorted_milestones = sorted(
                    milestones, key=lambda m: m.distance_from_origin_km
                )
                for i in range(1, len(sorted_milestones)):
                    distance = (
                        sorted_milestones[i].distance_from_origin_km
                        - sorted_milestones[i - 1].distance_from_origin_km
                    )
                    distances.append(distance)

                avg_distance = sum(distances) / len(distances) if distances else 0
            else:
                avg_distance = linear_map.total_length_km

            # Calculate density per 100km
            density = (
                (len(milestones) / linear_map.total_length_km) * 100
                if linear_map.total_length_km > 0
                else 0
            )

            poi_stats.append(
                POIStatistics(
                    type=poi_type,
                    total_count=len(milestones),
                    average_distance_km=avg_distance,
                    density_per_100km=density,
                )
            )

        # Generate stop recommendations
        recommendations = self.generate_stop_recommendations(
            all_milestones, linear_map.total_length_km
        )

        # Calculate estimated time (assuming 80 km/h average)
        estimated_time = linear_map.total_length_km / 80.0

        # Quality metrics
        quality_metrics = self.calculate_quality_metrics(all_milestones)

        return RouteStatisticsResponse(
            route_info={
                "origin": origin,
                "destination": destination,
                "road_refs": [seg.ref for seg in linear_map.segments if seg.ref],
                "segment_count": len(linear_map.segments),
            },
            total_length_km=linear_map.total_length_km,
            estimated_travel_time_hours=estimated_time,
            poi_statistics=poi_stats,
            recommendations=recommendations,
            quality_metrics=quality_metrics,
        )

    def generate_stop_recommendations(
        self, milestones: List[RoadMilestone], total_length_km: float
    ) -> List[RouteStopRecommendation]:
        """
        Generate strategic stop recommendations based on available POIs.

        Args:
            milestones: List of all milestones
            total_length_km: Total route length

        Returns:
            List of recommended stops
        """
        recommendations = []

        # Filter useful POIs for stops
        useful_milestones = [
            m for m in milestones if m.type.value in ["gas_station", "restaurant"]
        ]
        useful_milestones.sort(key=lambda m: m.distance_from_origin_km)

        # Recommend stops approximately every 150-200km
        last_recommended_km = 0
        for milestone in useful_milestones:
            distance_from_last = milestone.distance_from_origin_km - last_recommended_km

            # If more than 150km since last recommendation
            if distance_from_last >= 150:
                services = []
                reason = ""
                duration = 15  # default minutes

                if milestone.type.value == "gas_station":
                    services.append("Combustível")
                    reason = "Reabastecimento recomendado"
                    duration = 10

                if milestone.type.value == "restaurant":
                    services.append("Alimentação")
                    reason = "Parada para refeição"
                    duration = 30

                # Check for nearby POIs (within 5km)
                nearby_pois = [
                    m
                    for m in useful_milestones
                    if abs(m.distance_from_origin_km - milestone.distance_from_origin_km)
                    <= 5
                    and m != milestone
                ]

                for nearby in nearby_pois:
                    if (
                        nearby.type.value == "gas_station"
                        and "Combustível" not in services
                    ):
                        services.append("Combustível")
                    elif (
                        nearby.type.value == "restaurant"
                        and "Alimentação" not in services
                    ):
                        services.append("Alimentação")

                if len(services) > 1:
                    reason = "Parada estratégica - múltiplos serviços"
                    duration = 20

                # Add POI amenities
                if milestone.amenities:
                    services.extend(milestone.amenities[:3])

                recommendations.append(
                    RouteStopRecommendation(
                        distance_km=milestone.distance_from_origin_km,
                        reason=reason,
                        available_services=list(set(services)),
                        recommended_duration_minutes=duration,
                    )
                )

                last_recommended_km = milestone.distance_from_origin_km

        return recommendations[:5]  # Limit to 5 recommendations

    def calculate_quality_metrics(
        self, milestones: List[RoadMilestone]
    ) -> Dict[str, Any]:
        """
        Calculate quality metrics for POI data.

        Args:
            milestones: List of all milestones

        Returns:
            Dictionary with quality metrics
        """
        if not milestones:
            return {"overall_quality": 0.0, "data_completeness": 0.0}

        total_quality = sum(m.quality_score or 0 for m in milestones)
        average_quality = total_quality / len(milestones)

        # Calculate data completeness
        fields_to_check = ["phone", "opening_hours", "website", "operator", "brand"]
        completeness_scores = []

        for milestone in milestones:
            filled_fields = sum(
                1 for field in fields_to_check if getattr(milestone, field, None)
            )
            completeness = filled_fields / len(fields_to_check)
            completeness_scores.append(completeness)

        average_completeness = sum(completeness_scores) / len(completeness_scores)

        return {
            "overall_quality": round(average_quality, 2),
            "data_completeness": round(average_completeness, 2),
            "total_pois_analyzed": len(milestones),
            "pois_with_phone": len([m for m in milestones if m.phone]),
            "pois_with_hours": len([m for m in milestones if m.opening_hours]),
            "pois_with_website": len([m for m in milestones if m.website]),
        }
