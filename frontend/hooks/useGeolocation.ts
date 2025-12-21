import { useState, useEffect, useCallback } from 'react';

export interface GeoPosition {
  lat: number;
  lon: number;
  accuracy?: number;
  timestamp: number;
}

export interface UseGeolocationOptions {
  enableHighAccuracy?: boolean;
  timeout?: number;
  maximumAge?: number;
  // If provided, uses this position instead of real GPS
  simulatedPosition?: { lat: number; lon: number } | null;
}

export interface UseGeolocationResult {
  position: GeoPosition | null;
  error: string | null;
  isLoading: boolean;
  isSimulated: boolean;
  isSupported: boolean;
  requestPermission: () => void;
}

export function useGeolocation(options: UseGeolocationOptions = {}): UseGeolocationResult {
  const {
    enableHighAccuracy = true,
    timeout = 10000,
    maximumAge = 0,
    simulatedPosition = null,
  } = options;

  const [position, setPosition] = useState<GeoPosition | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isSupported, setIsSupported] = useState(true);

  // Handle simulated position
  useEffect(() => {
    if (simulatedPosition) {
      setPosition({
        lat: simulatedPosition.lat,
        lon: simulatedPosition.lon,
        accuracy: 10, // Simulated accuracy
        timestamp: Date.now(),
      });
      setIsLoading(false);
      setError(null);
    }
  }, [simulatedPosition]);

  // Request permission and start watching position
  const requestPermission = useCallback(() => {
    if (simulatedPosition) {
      // Don't request real GPS if simulating
      return;
    }

    if (!navigator.geolocation) {
      setIsSupported(false);
      setError('Geolocalização não suportada neste navegador');
      setIsLoading(false);
      return;
    }

    setIsLoading(true);
    setError(null);

    const watchId = navigator.geolocation.watchPosition(
      (pos) => {
        setPosition({
          lat: pos.coords.latitude,
          lon: pos.coords.longitude,
          accuracy: pos.coords.accuracy,
          timestamp: pos.timestamp,
        });
        setIsLoading(false);
        setError(null);
      },
      (err) => {
        setIsLoading(false);
        switch (err.code) {
          case err.PERMISSION_DENIED:
            setError('Permissão de localização negada');
            break;
          case err.POSITION_UNAVAILABLE:
            setError('Localização indisponível');
            break;
          case err.TIMEOUT:
            setError('Tempo esgotado ao obter localização');
            break;
          default:
            setError('Erro ao obter localização');
        }
      },
      {
        enableHighAccuracy,
        timeout,
        maximumAge,
      }
    );

    return () => {
      navigator.geolocation.clearWatch(watchId);
    };
  }, [simulatedPosition, enableHighAccuracy, timeout, maximumAge]);

  // Auto-request permission on mount if not simulating
  useEffect(() => {
    if (!simulatedPosition) {
      const cleanup = requestPermission();
      return cleanup;
    }
  }, [simulatedPosition, requestPermission]);

  return {
    position,
    error,
    isLoading: simulatedPosition ? false : isLoading,
    isSimulated: !!simulatedPosition,
    isSupported,
    requestPermission,
  };
}
