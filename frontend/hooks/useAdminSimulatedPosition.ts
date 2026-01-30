import { useState, useEffect, useCallback } from 'react';

const ADMIN_SIMULATED_POSITION_KEY = 'mapalinear_admin_simulated_position';

export interface AdminSimulatedPosition {
  lat: number;
  lon: number;
  timestamp: number;
}

export interface UseAdminSimulatedPositionResult {
  position: AdminSimulatedPosition | null;
  setPosition: (lat: number, lon: number) => void;
  clearPosition: () => void;
  isActive: boolean;
}

/**
 * Hook for managing an admin-set simulated GPS position.
 * This is used for debugging purposes to simulate the user's location
 * without using real GPS or the route simulation.
 *
 * The position is stored in sessionStorage and persists across page refreshes
 * but is cleared when the browser session ends.
 */
export function useAdminSimulatedPosition(): UseAdminSimulatedPositionResult {
  const [position, setPositionState] = useState<AdminSimulatedPosition | null>(null);

  // Load position from sessionStorage on mount
  useEffect(() => {
    try {
      const stored = sessionStorage.getItem(ADMIN_SIMULATED_POSITION_KEY);
      if (stored) {
        const parsed = JSON.parse(stored) as AdminSimulatedPosition;
        setPositionState(parsed);
      }
    } catch (error) {
      console.error('Error loading admin simulated position:', error);
      sessionStorage.removeItem(ADMIN_SIMULATED_POSITION_KEY);
    }
  }, []);

  const setPosition = useCallback((lat: number, lon: number) => {
    const newPosition: AdminSimulatedPosition = {
      lat,
      lon,
      timestamp: Date.now(),
    };
    setPositionState(newPosition);
    sessionStorage.setItem(ADMIN_SIMULATED_POSITION_KEY, JSON.stringify(newPosition));
  }, []);

  const clearPosition = useCallback(() => {
    setPositionState(null);
    sessionStorage.removeItem(ADMIN_SIMULATED_POSITION_KEY);
  }, []);

  return {
    position,
    setPosition,
    clearPosition,
    isActive: position !== null,
  };
}
