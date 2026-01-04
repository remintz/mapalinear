import React from 'react';
import {
  Play,
  Pause,
  Square,
  SkipBack,
  Navigation,
  Gauge,
  MapPin,
  AlertCircle
} from 'lucide-react';
import { SimulationState, SimulationControls as SimulationControlsType } from '@/hooks/useRouteSimulation';
import { useAnalytics } from '@/hooks/useAnalytics';
import { EventType } from '@/lib/analytics-types';

interface SimulationControlsProps {
  state: SimulationState;
  controls: SimulationControlsType;
  isOnRoute: boolean;
  distanceToRoute: number | null;
  mapId?: string;
  className?: string;
}

const SPEED_OPTIONS = [40, 60, 80, 100, 120];

export function SimulationControls({
  state,
  controls,
  isOnRoute,
  distanceToRoute,
  mapId,
  className = '',
}: SimulationControlsProps) {
  const { trackEvent } = useAnalytics();
  const { isActive, isPlaying, distanceKm, totalDistanceKm, speedKmH, progressPercent } = state;

  const handleStart = () => {
    trackEvent(EventType.ROUTE_TRACKING_START, { map_id: mapId, mode: 'simulation' });
    controls.start();
  };

  const handleStop = () => {
    trackEvent(EventType.ROUTE_TRACKING_STOP, {
      map_id: mapId,
      mode: 'simulation',
      distance_traveled_km: distanceKm,
      progress_percent: progressPercent,
    });
    controls.stop();
  };

  // If simulation is not active, show the start button
  if (!isActive) {
    return (
      <div className={`bg-white border border-gray-200 rounded-lg shadow-lg p-4 ${className}`}>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Navigation className="w-5 h-5 text-blue-600" />
            <span className="text-sm font-medium text-gray-700">Modo Simulacao</span>
          </div>
          <button
            onClick={handleStart}
            className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors text-sm font-medium"
          >
            <Play className="w-4 h-4" />
            Iniciar
          </button>
        </div>
        <p className="text-xs text-gray-500 mt-2">
          Simule o percurso para testar a visualizacao de POIs
        </p>
      </div>
    );
  }

  return (
    <div className={`bg-white border border-gray-200 rounded-lg shadow-lg ${className}`}>
      {/* Header with status */}
      <div className="px-4 py-3 border-b border-gray-100">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Navigation className="w-5 h-5 text-blue-600" />
            <span className="text-sm font-medium text-gray-700">Simulacao Ativa</span>
          </div>
          <button
            onClick={handleStop}
            className="flex items-center gap-1 px-2 py-1 text-red-600 hover:bg-red-50 rounded transition-colors text-xs"
            title="Parar simulacao"
          >
            <Square className="w-3 h-3" />
            Parar
          </button>
        </div>

        {/* Route status indicator */}
        <div className="mt-2 flex items-center gap-2">
          {isOnRoute ? (
            <div className="flex items-center gap-1 text-green-600 text-xs">
              <MapPin className="w-3 h-3" />
              <span>Na rota</span>
            </div>
          ) : (
            <div className="flex items-center gap-1 text-orange-500 text-xs">
              <AlertCircle className="w-3 h-3" />
              <span>
                Fora da rota
                {distanceToRoute && ` (${(distanceToRoute / 1000).toFixed(1)}km)`}
              </span>
            </div>
          )}
        </div>
      </div>

      {/* Progress bar */}
      <div className="px-4 py-3">
        <div className="flex items-center justify-between text-xs text-gray-500 mb-1">
          <span>{distanceKm.toFixed(1)} km</span>
          <span>{totalDistanceKm.toFixed(1)} km</span>
        </div>
        <div
          className="relative w-full h-2 bg-gray-200 rounded-full cursor-pointer"
          onClick={(e) => {
            const rect = e.currentTarget.getBoundingClientRect();
            const percent = ((e.clientX - rect.left) / rect.width) * 100;
            controls.jumpToPercent(percent);
          }}
        >
          <div
            className="absolute top-0 left-0 h-full bg-blue-600 rounded-full transition-all duration-100"
            style={{ width: `${progressPercent}%` }}
          />
          {/* Draggable thumb */}
          <div
            className="absolute top-1/2 -translate-y-1/2 w-4 h-4 bg-white border-2 border-blue-600 rounded-full shadow-md cursor-grab active:cursor-grabbing"
            style={{ left: `calc(${progressPercent}% - 8px)` }}
          />
        </div>
      </div>

      {/* Controls */}
      <div className="px-4 py-3 border-t border-gray-100">
        <div className="flex items-center justify-between">
          {/* Play/Pause and Reset */}
          <div className="flex items-center gap-2">
            <button
              onClick={controls.reset}
              className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
              title="Voltar ao inicio"
            >
              <SkipBack className="w-5 h-5 text-gray-600" />
            </button>

            <button
              onClick={controls.togglePlay}
              className="p-3 bg-blue-600 text-white rounded-full hover:bg-blue-700 transition-colors"
              title={isPlaying ? 'Pausar' : 'Continuar'}
            >
              {isPlaying ? (
                <Pause className="w-5 h-5" />
              ) : (
                <Play className="w-5 h-5 ml-0.5" />
              )}
            </button>
          </div>

          {/* Speed control */}
          <div className="flex items-center gap-2">
            <Gauge className="w-4 h-4 text-gray-400" />
            <div className="flex items-center bg-gray-100 rounded-lg p-1">
              {SPEED_OPTIONS.map((speed) => (
                <button
                  key={speed}
                  onClick={() => controls.setSpeed(speed)}
                  className={`px-2 py-1 text-xs rounded transition-colors ${
                    speedKmH === speed
                      ? 'bg-blue-600 text-white'
                      : 'text-gray-600 hover:bg-gray-200'
                  }`}
                >
                  {speed}
                </button>
              ))}
            </div>
            <span className="text-xs text-gray-500">km/h</span>
          </div>
        </div>
      </div>
    </div>
  );
}
