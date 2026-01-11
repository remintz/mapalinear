"""
Progress phases configuration for map generation.

This module centralizes the definition of progress phases and their weights,
allowing both backend progress reporting and frontend phase display.

Note: Each async operation has its own phase/progress state stored in the
AsyncOperation model (current_phase field). This supports multiple concurrent
map generations by different users.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Callable, Optional


class MapGenerationPhase(str, Enum):
    """Phases of map generation process."""

    GEOCODING = "geocoding"
    ROUTE_CALCULATION = "route_calculation"
    SEGMENT_PROCESSING = "segment_processing"
    POI_SEARCH = "poi_search"
    MAP_CREATION = "map_creation"
    SAVING = "saving"
    ENRICHMENT = "enrichment"
    FINALIZING = "finalizing"


@dataclass(frozen=True)
class PhaseConfig:
    """Configuration for a progress phase."""

    phase: MapGenerationPhase
    start_percent: float  # Where this phase starts (0-100)
    end_percent: float  # Where this phase ends (0-100)
    description_pt: str  # Portuguese description for frontend


# Central configuration of all phases and their progress ranges
# The ranges must be contiguous and cover 0-100%
PHASE_CONFIGS: dict[MapGenerationPhase, PhaseConfig] = {
    MapGenerationPhase.GEOCODING: PhaseConfig(
        phase=MapGenerationPhase.GEOCODING,
        start_percent=0,
        end_percent=10,
        description_pt="Localizando enderecos",
    ),
    MapGenerationPhase.ROUTE_CALCULATION: PhaseConfig(
        phase=MapGenerationPhase.ROUTE_CALCULATION,
        start_percent=10,
        end_percent=20,
        description_pt="Calculando rota",
    ),
    MapGenerationPhase.SEGMENT_PROCESSING: PhaseConfig(
        phase=MapGenerationPhase.SEGMENT_PROCESSING,
        start_percent=20,
        end_percent=25,
        description_pt="Processando segmentos",
    ),
    MapGenerationPhase.POI_SEARCH: PhaseConfig(
        phase=MapGenerationPhase.POI_SEARCH,
        start_percent=25,
        end_percent=70,
        description_pt="Buscando pontos de interesse",
    ),
    MapGenerationPhase.MAP_CREATION: PhaseConfig(
        phase=MapGenerationPhase.MAP_CREATION,
        start_percent=70,
        end_percent=75,
        description_pt="Criando mapa",
    ),
    MapGenerationPhase.SAVING: PhaseConfig(
        phase=MapGenerationPhase.SAVING,
        start_percent=75,
        end_percent=85,
        description_pt="Salvando mapa",
    ),
    MapGenerationPhase.ENRICHMENT: PhaseConfig(
        phase=MapGenerationPhase.ENRICHMENT,
        start_percent=85,
        end_percent=95,
        description_pt="Enriquecendo dados",
    ),
    MapGenerationPhase.FINALIZING: PhaseConfig(
        phase=MapGenerationPhase.FINALIZING,
        start_percent=95,
        end_percent=100,
        description_pt="Finalizando",
    ),
}


def get_phase_config(phase: MapGenerationPhase) -> PhaseConfig:
    """Get configuration for a specific phase."""
    return PHASE_CONFIGS[phase]


def calculate_overall_progress(phase: MapGenerationPhase, phase_progress: float) -> float:
    """
    Calculate overall progress (0-100) from phase and progress within phase.

    Args:
        phase: Current phase
        phase_progress: Progress within the phase (0-100)

    Returns:
        Overall progress percentage (0-100)
    """
    config = PHASE_CONFIGS[phase]
    phase_range = config.end_percent - config.start_percent
    return config.start_percent + (phase_progress / 100.0 * phase_range)


class ProgressReporter:
    """
    Helper class to report progress with phase information.

    Each instance is tied to a specific operation (via callbacks).
    Multiple concurrent operations each have their own ProgressReporter instance.
    """

    def __init__(
        self,
        update_callback: Optional[Callable[[float, str], None]] = None,
    ):
        """
        Initialize the progress reporter for a specific operation.

        Args:
            update_callback: Callback that receives (overall_progress, phase_name)
                           This callback is responsible for updating the specific
                           operation's state in the database/cache.
        """
        self._update_callback = update_callback

    def report(self, phase: MapGenerationPhase, phase_progress: float) -> None:
        """
        Report progress for a specific phase.

        Args:
            phase: Current phase
            phase_progress: Progress within the phase (0-100)
        """
        if self._update_callback:
            overall = calculate_overall_progress(phase, phase_progress)
            self._update_callback(overall, phase.value)

    def start_phase(self, phase: MapGenerationPhase) -> None:
        """Start a new phase at 0% progress."""
        self.report(phase, 0)

    def complete_phase(self, phase: MapGenerationPhase) -> None:
        """Complete a phase at 100% progress."""
        self.report(phase, 100)
