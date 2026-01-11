"""
Tests for progress phases module.
"""

import pytest

from api.services.progress_phases import (
    MapGenerationPhase,
    PhaseConfig,
    PHASE_CONFIGS,
    get_phase_config,
    calculate_overall_progress,
    ProgressReporter,
)


class TestMapGenerationPhase:
    """Tests for MapGenerationPhase enum."""

    def test_all_phases_defined(self):
        """All expected phases should be defined."""
        expected_phases = [
            "geocoding",
            "route_calculation",
            "segment_processing",
            "poi_search",
            "map_creation",
            "saving",
            "enrichment",
            "finalizing",
        ]
        actual_phases = [phase.value for phase in MapGenerationPhase]
        assert actual_phases == expected_phases

    def test_phase_values_are_strings(self):
        """Phase values should be strings."""
        for phase in MapGenerationPhase:
            assert isinstance(phase.value, str)


class TestPhaseConfigs:
    """Tests for phase configuration."""

    def test_all_phases_have_config(self):
        """Every phase should have a configuration."""
        for phase in MapGenerationPhase:
            assert phase in PHASE_CONFIGS
            config = PHASE_CONFIGS[phase]
            assert isinstance(config, PhaseConfig)

    def test_phases_are_contiguous(self):
        """Phase ranges should be contiguous (no gaps)."""
        phases_in_order = [
            MapGenerationPhase.GEOCODING,
            MapGenerationPhase.ROUTE_CALCULATION,
            MapGenerationPhase.SEGMENT_PROCESSING,
            MapGenerationPhase.POI_SEARCH,
            MapGenerationPhase.MAP_CREATION,
            MapGenerationPhase.SAVING,
            MapGenerationPhase.ENRICHMENT,
            MapGenerationPhase.FINALIZING,
        ]

        for i in range(len(phases_in_order) - 1):
            current_config = PHASE_CONFIGS[phases_in_order[i]]
            next_config = PHASE_CONFIGS[phases_in_order[i + 1]]
            assert current_config.end_percent == next_config.start_percent, (
                f"Gap between {phases_in_order[i].value} and {phases_in_order[i + 1].value}"
            )

    def test_phases_cover_0_to_100(self):
        """Phases should cover the full 0-100% range."""
        first_phase = PHASE_CONFIGS[MapGenerationPhase.GEOCODING]
        last_phase = PHASE_CONFIGS[MapGenerationPhase.FINALIZING]

        assert first_phase.start_percent == 0
        assert last_phase.end_percent == 100

    def test_each_phase_has_positive_range(self):
        """Each phase should have end > start."""
        for phase, config in PHASE_CONFIGS.items():
            assert config.end_percent > config.start_percent, (
                f"Phase {phase.value} has invalid range: {config.start_percent}-{config.end_percent}"
            )

    def test_each_phase_has_description(self):
        """Each phase should have a Portuguese description."""
        for phase, config in PHASE_CONFIGS.items():
            assert config.description_pt, f"Phase {phase.value} missing description"
            assert isinstance(config.description_pt, str)


class TestGetPhaseConfig:
    """Tests for get_phase_config function."""

    def test_returns_correct_config(self):
        """Should return the correct config for a phase."""
        config = get_phase_config(MapGenerationPhase.POI_SEARCH)
        assert config.phase == MapGenerationPhase.POI_SEARCH
        assert config.start_percent == 25
        assert config.end_percent == 70

    def test_raises_for_invalid_phase(self):
        """Should raise KeyError for invalid phase."""
        with pytest.raises(KeyError):
            get_phase_config("invalid_phase")


class TestCalculateOverallProgress:
    """Tests for calculate_overall_progress function."""

    def test_at_phase_start(self):
        """0% phase progress should return phase start percent."""
        result = calculate_overall_progress(MapGenerationPhase.GEOCODING, 0)
        assert result == 0

        result = calculate_overall_progress(MapGenerationPhase.POI_SEARCH, 0)
        assert result == 25

    def test_at_phase_end(self):
        """100% phase progress should return phase end percent."""
        result = calculate_overall_progress(MapGenerationPhase.GEOCODING, 100)
        assert result == 10

        result = calculate_overall_progress(MapGenerationPhase.POI_SEARCH, 100)
        assert result == 70

    def test_at_phase_midpoint(self):
        """50% phase progress should return midpoint of phase range."""
        # POI_SEARCH is 25-70%, midpoint is 47.5%
        result = calculate_overall_progress(MapGenerationPhase.POI_SEARCH, 50)
        assert result == 47.5

    def test_poi_search_phase_range(self):
        """POI_SEARCH phase should cover 25-70% (45 percentage points)."""
        # At 0%: 25%
        assert calculate_overall_progress(MapGenerationPhase.POI_SEARCH, 0) == 25
        # At 25%: 25 + 0.25 * 45 = 36.25%
        assert calculate_overall_progress(MapGenerationPhase.POI_SEARCH, 25) == 36.25
        # At 50%: 25 + 0.5 * 45 = 47.5%
        assert calculate_overall_progress(MapGenerationPhase.POI_SEARCH, 50) == 47.5
        # At 75%: 25 + 0.75 * 45 = 58.75%
        assert calculate_overall_progress(MapGenerationPhase.POI_SEARCH, 75) == 58.75
        # At 100%: 70%
        assert calculate_overall_progress(MapGenerationPhase.POI_SEARCH, 100) == 70


class TestProgressReporter:
    """Tests for ProgressReporter class."""

    def test_report_calls_callback(self):
        """report() should call the update callback with overall progress and phase."""
        calls = []

        def callback(progress: float, phase: str):
            calls.append((progress, phase))

        reporter = ProgressReporter(update_callback=callback)
        reporter.report(MapGenerationPhase.GEOCODING, 50)

        assert len(calls) == 1
        assert calls[0] == (5.0, "geocoding")  # 50% of 0-10% = 5%

    def test_report_without_callback(self):
        """report() should not fail without a callback."""
        reporter = ProgressReporter(update_callback=None)
        # Should not raise
        reporter.report(MapGenerationPhase.GEOCODING, 50)

    def test_start_phase(self):
        """start_phase() should report 0% progress for the phase."""
        calls = []

        def callback(progress: float, phase: str):
            calls.append((progress, phase))

        reporter = ProgressReporter(update_callback=callback)
        reporter.start_phase(MapGenerationPhase.POI_SEARCH)

        assert len(calls) == 1
        assert calls[0] == (25.0, "poi_search")  # Start of POI_SEARCH

    def test_complete_phase(self):
        """complete_phase() should report 100% progress for the phase."""
        calls = []

        def callback(progress: float, phase: str):
            calls.append((progress, phase))

        reporter = ProgressReporter(update_callback=callback)
        reporter.complete_phase(MapGenerationPhase.POI_SEARCH)

        assert len(calls) == 1
        assert calls[0] == (70.0, "poi_search")  # End of POI_SEARCH

    def test_full_workflow(self):
        """Test a typical workflow through multiple phases."""
        calls = []

        def callback(progress: float, phase: str):
            calls.append((progress, phase))

        reporter = ProgressReporter(update_callback=callback)

        # Simulate geocoding
        reporter.start_phase(MapGenerationPhase.GEOCODING)
        reporter.report(MapGenerationPhase.GEOCODING, 50)
        reporter.complete_phase(MapGenerationPhase.GEOCODING)

        # Simulate route calculation
        reporter.start_phase(MapGenerationPhase.ROUTE_CALCULATION)
        reporter.complete_phase(MapGenerationPhase.ROUTE_CALCULATION)

        assert calls == [
            (0.0, "geocoding"),
            (5.0, "geocoding"),
            (10.0, "geocoding"),
            (10.0, "route_calculation"),
            (20.0, "route_calculation"),
        ]

    def test_poi_search_segment_progress(self):
        """Test POI search phase with segment-by-segment progress."""
        calls = []

        def callback(progress: float, phase: str):
            calls.append((progress, phase))

        reporter = ProgressReporter(update_callback=callback)

        # Simulate processing 5 segments
        reporter.start_phase(MapGenerationPhase.POI_SEARCH)
        for i in range(5):
            segment_progress = ((i + 1) / 5) * 100
            reporter.report(MapGenerationPhase.POI_SEARCH, segment_progress)

        # Check progress increases correctly
        assert calls[0] == (25.0, "poi_search")  # Start at 25%
        assert calls[-1] == (70.0, "poi_search")  # End at 70%

        # All intermediate values should be in order
        progresses = [c[0] for c in calls]
        assert progresses == sorted(progresses)
