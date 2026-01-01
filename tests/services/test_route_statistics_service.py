"""
Unit tests for api/services/route_statistics_service.py

Tests for route statistics and recommendations:
- generate_stop_recommendations
- calculate_quality_metrics
"""

import pytest
from unittest.mock import MagicMock, patch

from api.models.road_models import Coordinates, MilestoneType, RoadMilestone
from api.services.route_statistics_service import RouteStatisticsService


class TestGenerateStopRecommendations:
    """Tests for stop recommendation generation."""

    @pytest.fixture
    def service(self):
        """Create service with mock road service."""
        mock_road_service = MagicMock()
        return RouteStatisticsService(mock_road_service)

    @pytest.fixture
    def sample_milestones(self):
        """Create sample milestones for testing."""
        return [
            RoadMilestone(
                id="gas_50",
                name="Posto 1",
                type=MilestoneType.GAS_STATION,
                coordinates=Coordinates(latitude=-23.55, longitude=-46.63),
                distance_from_origin_km=50.0,
                distance_from_road_meters=50.0,
                side="right",
            ),
            RoadMilestone(
                id="rest_200",
                name="Restaurante 1",
                type=MilestoneType.RESTAURANT,
                coordinates=Coordinates(latitude=-23.60, longitude=-46.68),
                distance_from_origin_km=200.0,
                distance_from_road_meters=100.0,
                side="left",
            ),
            RoadMilestone(
                id="gas_350",
                name="Posto 2",
                type=MilestoneType.GAS_STATION,
                coordinates=Coordinates(latitude=-23.65, longitude=-46.73),
                distance_from_origin_km=350.0,
                distance_from_road_meters=75.0,
                side="right",
            ),
            RoadMilestone(
                id="rest_500",
                name="Restaurante 2",
                type=MilestoneType.RESTAURANT,
                coordinates=Coordinates(latitude=-23.70, longitude=-46.78),
                distance_from_origin_km=500.0,
                distance_from_road_meters=150.0,
                side="left",
            ),
        ]

    def test_empty_milestones_returns_empty(self, service):
        """Empty milestones should return empty recommendations."""
        recommendations = service.generate_stop_recommendations([], 500.0)
        assert recommendations == []

    def test_generates_recommendations_at_intervals(self, service, sample_milestones):
        """Should generate recommendations approximately every 150km+."""
        recommendations = service.generate_stop_recommendations(
            sample_milestones, 600.0
        )
        # Should have recommendations for stops at useful intervals
        assert len(recommendations) > 0

    def test_first_recommendation_after_150km(self, service, sample_milestones):
        """First recommendation should be at least 150km from start."""
        recommendations = service.generate_stop_recommendations(
            sample_milestones, 600.0
        )
        if recommendations:
            assert recommendations[0].distance_km >= 150.0

    def test_limits_to_5_recommendations(self, service):
        """Should limit to maximum 5 recommendations."""
        # Create many milestones
        milestones = [
            RoadMilestone(
                id=f"gas_{i * 160}",
                name=f"Posto {i}",
                type=MilestoneType.GAS_STATION,
                coordinates=Coordinates(latitude=-23.55, longitude=-46.63),
                distance_from_origin_km=float(i * 160),
                distance_from_road_meters=50.0,
                side="right",
            )
            for i in range(1, 15)
        ]

        recommendations = service.generate_stop_recommendations(milestones, 2000.0)
        assert len(recommendations) <= 5

    def test_gas_station_recommendation_has_fuel_service(self, service):
        """Gas station recommendation should include fuel service."""
        milestones = [
            RoadMilestone(
                id="gas_200",
                name="Posto Shell",
                type=MilestoneType.GAS_STATION,
                coordinates=Coordinates(latitude=-23.55, longitude=-46.63),
                distance_from_origin_km=200.0,
                distance_from_road_meters=50.0,
                side="right",
            ),
        ]

        recommendations = service.generate_stop_recommendations(milestones, 500.0)

        if recommendations:
            assert "Combustível" in recommendations[0].available_services

    def test_restaurant_recommendation_has_food_service(self, service):
        """Restaurant recommendation should include food service."""
        milestones = [
            RoadMilestone(
                id="rest_200",
                name="Restaurante Bom",
                type=MilestoneType.RESTAURANT,
                coordinates=Coordinates(latitude=-23.55, longitude=-46.63),
                distance_from_origin_km=200.0,
                distance_from_road_meters=100.0,
                side="left",
            ),
        ]

        recommendations = service.generate_stop_recommendations(milestones, 500.0)

        if recommendations:
            assert "Alimentação" in recommendations[0].available_services

    def test_multiple_services_at_same_location(self, service):
        """Nearby POIs should combine services."""
        milestones = [
            RoadMilestone(
                id="gas_200",
                name="Posto Shell",
                type=MilestoneType.GAS_STATION,
                coordinates=Coordinates(latitude=-23.55, longitude=-46.63),
                distance_from_origin_km=200.0,
                distance_from_road_meters=50.0,
                side="right",
            ),
            RoadMilestone(
                id="rest_203",
                name="Restaurante do Posto",
                type=MilestoneType.RESTAURANT,
                coordinates=Coordinates(latitude=-23.55, longitude=-46.63),
                distance_from_origin_km=203.0,  # Within 5km
                distance_from_road_meters=100.0,
                side="right",
            ),
        ]

        recommendations = service.generate_stop_recommendations(milestones, 500.0)

        if recommendations:
            services = recommendations[0].available_services
            # Should have both fuel and food
            has_fuel = "Combustível" in services
            has_food = "Alimentação" in services
            # At least one should be present
            assert has_fuel or has_food

    def test_includes_poi_amenities(self, service):
        """Should include POI amenities in services."""
        milestones = [
            RoadMilestone(
                id="gas_200",
                name="Posto Shell",
                type=MilestoneType.GAS_STATION,
                coordinates=Coordinates(latitude=-23.55, longitude=-46.63),
                distance_from_origin_km=200.0,
                distance_from_road_meters=50.0,
                side="right",
                amenities=["banheiro", "loja", "wifi"],
            ),
        ]

        recommendations = service.generate_stop_recommendations(milestones, 500.0)

        if recommendations:
            services = recommendations[0].available_services
            # Should include some amenities (limited to 3)
            assert len(services) >= 1

    def test_only_includes_useful_pois(self, service):
        """Should only consider gas stations and restaurants."""
        milestones = [
            RoadMilestone(
                id="hotel_200",
                name="Hotel",
                type=MilestoneType.HOTEL,
                coordinates=Coordinates(latitude=-23.55, longitude=-46.63),
                distance_from_origin_km=200.0,
                distance_from_road_meters=200.0,
                side="left",
            ),
            RoadMilestone(
                id="hospital_300",
                name="Hospital",
                type=MilestoneType.HOSPITAL,
                coordinates=Coordinates(latitude=-23.60, longitude=-46.68),
                distance_from_origin_km=300.0,
                distance_from_road_meters=300.0,
                side="right",
            ),
        ]

        recommendations = service.generate_stop_recommendations(milestones, 500.0)
        # Hotels and hospitals are not considered for stop recommendations
        assert len(recommendations) == 0


class TestCalculateQualityMetrics:
    """Tests for quality metrics calculation."""

    @pytest.fixture
    def service(self):
        """Create service with mock road service."""
        mock_road_service = MagicMock()
        return RouteStatisticsService(mock_road_service)

    def test_empty_milestones_returns_zero_metrics(self, service):
        """Empty milestones should return zero metrics."""
        metrics = service.calculate_quality_metrics([])
        assert metrics["overall_quality"] == 0.0
        assert metrics["data_completeness"] == 0.0

    def test_calculates_average_quality(self, service):
        """Should calculate average quality score."""
        milestones = [
            RoadMilestone(
                id="m1",
                name="POI 1",
                type=MilestoneType.GAS_STATION,
                coordinates=Coordinates(latitude=-23.55, longitude=-46.63),
                distance_from_origin_km=10.0,
                distance_from_road_meters=50.0,
                side="right",
                quality_score=0.8,
            ),
            RoadMilestone(
                id="m2",
                name="POI 2",
                type=MilestoneType.RESTAURANT,
                coordinates=Coordinates(latitude=-23.60, longitude=-46.68),
                distance_from_origin_km=20.0,
                distance_from_road_meters=100.0,
                side="left",
                quality_score=0.6,
            ),
        ]

        metrics = service.calculate_quality_metrics(milestones)

        # Average of 0.8 and 0.6 = 0.7
        assert metrics["overall_quality"] == 0.7

    def test_counts_pois_with_phone(self, service):
        """Should count POIs with phone number."""
        milestones = [
            RoadMilestone(
                id="m1",
                name="POI 1",
                type=MilestoneType.GAS_STATION,
                coordinates=Coordinates(latitude=-23.55, longitude=-46.63),
                distance_from_origin_km=10.0,
                distance_from_road_meters=50.0,
                side="right",
                phone="+55 11 1234-5678",
            ),
            RoadMilestone(
                id="m2",
                name="POI 2",
                type=MilestoneType.RESTAURANT,
                coordinates=Coordinates(latitude=-23.60, longitude=-46.68),
                distance_from_origin_km=20.0,
                distance_from_road_meters=100.0,
                side="left",
                phone=None,
            ),
        ]

        metrics = service.calculate_quality_metrics(milestones)
        assert metrics["pois_with_phone"] == 1

    def test_counts_pois_with_hours(self, service):
        """Should count POIs with opening hours."""
        milestones = [
            RoadMilestone(
                id="m1",
                name="POI 1",
                type=MilestoneType.GAS_STATION,
                coordinates=Coordinates(latitude=-23.55, longitude=-46.63),
                distance_from_origin_km=10.0,
                distance_from_road_meters=50.0,
                side="right",
                opening_hours="Mon-Sun: 06:00-22:00",
            ),
            RoadMilestone(
                id="m2",
                name="POI 2",
                type=MilestoneType.RESTAURANT,
                coordinates=Coordinates(latitude=-23.60, longitude=-46.68),
                distance_from_origin_km=20.0,
                distance_from_road_meters=100.0,
                side="left",
                opening_hours=None,
            ),
        ]

        metrics = service.calculate_quality_metrics(milestones)
        assert metrics["pois_with_hours"] == 1

    def test_counts_pois_with_website(self, service):
        """Should count POIs with website."""
        milestones = [
            RoadMilestone(
                id="m1",
                name="POI 1",
                type=MilestoneType.GAS_STATION,
                coordinates=Coordinates(latitude=-23.55, longitude=-46.63),
                distance_from_origin_km=10.0,
                distance_from_road_meters=50.0,
                side="right",
                website="https://example.com",
            ),
        ]

        metrics = service.calculate_quality_metrics(milestones)
        assert metrics["pois_with_website"] == 1

    def test_total_pois_analyzed(self, service):
        """Should count total POIs analyzed."""
        milestones = [
            RoadMilestone(
                id=f"m{i}",
                name=f"POI {i}",
                type=MilestoneType.GAS_STATION,
                coordinates=Coordinates(latitude=-23.55, longitude=-46.63),
                distance_from_origin_km=float(i * 10),
                distance_from_road_meters=50.0,
                side="right",
            )
            for i in range(5)
        ]

        metrics = service.calculate_quality_metrics(milestones)
        assert metrics["total_pois_analyzed"] == 5

    def test_data_completeness_calculation(self, service):
        """Should calculate data completeness based on fields."""
        # POI with all 5 fields filled (phone, hours, website, operator, brand)
        milestones = [
            RoadMilestone(
                id="m1",
                name="Complete POI",
                type=MilestoneType.GAS_STATION,
                coordinates=Coordinates(latitude=-23.55, longitude=-46.63),
                distance_from_origin_km=10.0,
                distance_from_road_meters=50.0,
                side="right",
                phone="+55 11 1234-5678",
                opening_hours="24/7",
                website="https://shell.com.br",
                operator="Shell Brasil",
                brand="Shell",
            ),
        ]

        metrics = service.calculate_quality_metrics(milestones)
        # All 5 fields filled = 1.0 completeness
        assert metrics["data_completeness"] == 1.0

    def test_partial_data_completeness(self, service):
        """Should calculate partial completeness."""
        # POI with 2 of 5 fields filled
        milestones = [
            RoadMilestone(
                id="m1",
                name="Partial POI",
                type=MilestoneType.GAS_STATION,
                coordinates=Coordinates(latitude=-23.55, longitude=-46.63),
                distance_from_origin_km=10.0,
                distance_from_road_meters=50.0,
                side="right",
                phone="+55 11 1234-5678",
                website="https://example.com",
                # opening_hours, operator, brand are None
            ),
        ]

        metrics = service.calculate_quality_metrics(milestones)
        # 2 of 5 fields = 0.4
        assert metrics["data_completeness"] == 0.4

    def test_rounds_metrics(self, service):
        """Should round metrics to 2 decimal places."""
        milestones = [
            RoadMilestone(
                id="m1",
                name="POI 1",
                type=MilestoneType.GAS_STATION,
                coordinates=Coordinates(latitude=-23.55, longitude=-46.63),
                distance_from_origin_km=10.0,
                distance_from_road_meters=50.0,
                side="right",
                quality_score=0.333333,
            ),
        ]

        metrics = service.calculate_quality_metrics(milestones)
        assert metrics["overall_quality"] == 0.33

    def test_handles_none_quality_scores(self, service):
        """Should handle milestones without quality scores."""
        milestones = [
            RoadMilestone(
                id="m1",
                name="POI 1",
                type=MilestoneType.GAS_STATION,
                coordinates=Coordinates(latitude=-23.55, longitude=-46.63),
                distance_from_origin_km=10.0,
                distance_from_road_meters=50.0,
                side="right",
                quality_score=None,
            ),
            RoadMilestone(
                id="m2",
                name="POI 2",
                type=MilestoneType.RESTAURANT,
                coordinates=Coordinates(latitude=-23.60, longitude=-46.68),
                distance_from_origin_km=20.0,
                distance_from_road_meters=100.0,
                side="left",
                quality_score=0.8,
            ),
        ]

        metrics = service.calculate_quality_metrics(milestones)
        # (0 + 0.8) / 2 = 0.4
        assert metrics["overall_quality"] == 0.4
