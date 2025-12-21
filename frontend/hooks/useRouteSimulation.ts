import { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import { Coordinates, RouteSegment } from '@/lib/types';
import { getRoutePoints, interpolateRoutePosition, RoutePoint } from '@/lib/geo-utils';

export interface SimulationState {
  // Whether simulation is active
  isActive: boolean;
  // Whether simulation is currently playing
  isPlaying: boolean;
  // Current simulated position
  position: Coordinates | null;
  // Current distance from origin (in km)
  distanceKm: number;
  // Total route distance (in km)
  totalDistanceKm: number;
  // Current simulation speed (km/h)
  speedKmH: number;
  // Progress as percentage (0-100)
  progressPercent: number;
}

export interface SimulationControls {
  // Start/activate simulation
  start: () => void;
  // Stop/deactivate simulation (returns to real GPS)
  stop: () => void;
  // Play/resume simulation
  play: () => void;
  // Pause simulation
  pause: () => void;
  // Toggle play/pause
  togglePlay: () => void;
  // Set simulation speed in km/h
  setSpeed: (kmH: number) => void;
  // Jump to a specific distance (in km)
  jumpTo: (distanceKm: number) => void;
  // Jump to a specific percentage (0-100)
  jumpToPercent: (percent: number) => void;
  // Reset to beginning of route
  reset: () => void;
}

export interface UseRouteSimulationOptions {
  // Route segments with geometry
  segments: RouteSegment[];
  // Total route distance in km
  totalDistanceKm: number;
  // Initial simulation speed in km/h (default: 80)
  initialSpeedKmH?: number;
  // Update interval in ms (default: 100)
  updateIntervalMs?: number;
}

export interface UseRouteSimulationResult {
  state: SimulationState;
  controls: SimulationControls;
}

/**
 * Hook to simulate movement along a route.
 * Provides controls for play/pause, speed adjustment, and jumping to specific points.
 */
export function useRouteSimulation({
  segments,
  totalDistanceKm,
  initialSpeedKmH = 80,
  updateIntervalMs = 100,
}: UseRouteSimulationOptions): UseRouteSimulationResult {
  const [isActive, setIsActive] = useState(false);
  const [isPlaying, setIsPlaying] = useState(false);
  const [distanceKm, setDistanceKm] = useState(0);
  const [speedKmH, setSpeedKmH] = useState(initialSpeedKmH);

  // Ref for interval to avoid stale closures
  const intervalRef = useRef<NodeJS.Timeout | null>(null);
  const speedRef = useRef(speedKmH);
  speedRef.current = speedKmH;

  // Pre-compute route points for interpolation
  const routePoints = useMemo<RoutePoint[]>(() => {
    const points = getRoutePoints(segments);
    // Debug: log route points info
    if (typeof window !== 'undefined') {
      console.log('[Simulation] Segments count:', segments.length);
      console.log('[Simulation] Route points count:', points.length);
      if (segments.length > 0) {
        console.log('[Simulation] First segment:', {
          id: segments[0].id,
          hasGeometry: !!(segments[0].geometry && segments[0].geometry.length > 0),
          geometryLength: segments[0].geometry?.length || 0,
          start_distance_km: segments[0].start_distance_km,
          end_distance_km: segments[0].end_distance_km,
        });
      }
      if (points.length > 0) {
        console.log('[Simulation] First point:', points[0]);
        console.log('[Simulation] Last point:', points[points.length - 1]);
      }
    }
    return points;
  }, [segments]);

  // Calculate current position based on distance
  const position = useMemo<Coordinates | null>(() => {
    if (!isActive || routePoints.length === 0) return null;
    return interpolateRoutePosition(routePoints, distanceKm);
  }, [isActive, routePoints, distanceKm]);

  // Calculate progress percentage
  const progressPercent = useMemo(() => {
    if (totalDistanceKm <= 0) return 0;
    return Math.min(100, (distanceKm / totalDistanceKm) * 100);
  }, [distanceKm, totalDistanceKm]);

  // Clean up interval on unmount
  useEffect(() => {
    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
    };
  }, []);

  // Handle play/pause state changes
  useEffect(() => {
    if (isActive && isPlaying) {
      // Calculate distance increment per update
      // speed is km/h, interval is in ms
      // distancePerInterval = (speed * intervalMs) / (3600 * 1000) km
      intervalRef.current = setInterval(() => {
        setDistanceKm((current) => {
          const increment = (speedRef.current * updateIntervalMs) / 3600000;
          const newDistance = current + increment;

          // Stop at end of route
          if (newDistance >= totalDistanceKm) {
            setIsPlaying(false);
            return totalDistanceKm;
          }

          return newDistance;
        });
      }, updateIntervalMs);

      return () => {
        if (intervalRef.current) {
          clearInterval(intervalRef.current);
          intervalRef.current = null;
        }
      };
    } else {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
    }
  }, [isActive, isPlaying, updateIntervalMs, totalDistanceKm]);

  // Control functions
  const start = useCallback(() => {
    setIsActive(true);
    setDistanceKm(0);
    setIsPlaying(false);
  }, []);

  const stop = useCallback(() => {
    setIsActive(false);
    setIsPlaying(false);
    setDistanceKm(0);
  }, []);

  const play = useCallback(() => {
    if (isActive) {
      setIsPlaying(true);
    }
  }, [isActive]);

  const pause = useCallback(() => {
    setIsPlaying(false);
  }, []);

  const togglePlay = useCallback(() => {
    if (!isActive) {
      setIsActive(true);
      setIsPlaying(true);
    } else {
      setIsPlaying((prev) => !prev);
    }
  }, [isActive]);

  const setSpeedControl = useCallback((kmH: number) => {
    setSpeedKmH(Math.max(10, Math.min(200, kmH)));
  }, []);

  const jumpTo = useCallback((km: number) => {
    setDistanceKm(Math.max(0, Math.min(totalDistanceKm, km)));
  }, [totalDistanceKm]);

  const jumpToPercent = useCallback((percent: number) => {
    const km = (Math.max(0, Math.min(100, percent)) / 100) * totalDistanceKm;
    setDistanceKm(km);
  }, [totalDistanceKm]);

  const reset = useCallback(() => {
    setDistanceKm(0);
    setIsPlaying(false);
  }, []);

  return {
    state: {
      isActive,
      isPlaying,
      position,
      distanceKm,
      totalDistanceKm,
      speedKmH,
      progressPercent,
    },
    controls: {
      start,
      stop,
      play,
      pause,
      togglePlay,
      setSpeed: setSpeedControl,
      jumpTo,
      jumpToPercent,
      reset,
    },
  };
}
