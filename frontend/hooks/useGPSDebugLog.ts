/**
 * Hook for sending GPS debug logs (admin only).
 *
 * This hook automatically logs GPS position and POI distance data
 * when an admin user opens or refreshes the map page.
 * Logs are throttled to max 1 per 5 minutes per map.
 */

import { useCallback, useRef, useEffect } from 'react';
import { apiClient } from '@/lib/api';
import { getSessionId } from '@/lib/session-id';
import { POI, Milestone, GPSDebugPOIInfo, GPSDebugLogRequest } from '@/lib/types';

const THROTTLE_MINUTES = 5;
const THROTTLE_KEY_PREFIX = 'gps_debug_last_log_';

interface UseGPSDebugLogOptions {
  isAdmin: boolean;
  mapId: string | null;
  mapOrigin: string;
  mapDestination: string;
  userPosition: { lat: number; lon: number } | null;
  gpsAccuracy?: number;
  distanceTraveled: number | null;
  isOnRoute: boolean;
  distanceToRoute: number | null;
  pois: (POI | Milestone)[];
}

interface UseGPSDebugLogResult {
  sendDebugLog: () => Promise<void>;
  canSendLog: boolean;
  lastLogTime: Date | null;
}

/**
 * Get the distance to use for sorting/comparison (handles junction distances for detour POIs)
 */
function getEffectiveDistance(poi: POI | Milestone): number {
  if (poi.requires_detour && poi.junction_distance_km !== undefined) {
    return poi.junction_distance_km;
  }
  return poi.distance_from_origin_km;
}

/**
 * Convert POI to debug info format
 */
function poiToDebugInfo(poi: POI | Milestone, userDistanceKm: number): GPSDebugPOIInfo {
  const effectiveDistance = getEffectiveDistance(poi);
  return {
    id: poi.id,
    name: poi.name || poi.type,
    type: poi.type,
    distance_from_origin_km: effectiveDistance,
    relative_distance_km: effectiveDistance - userDistanceKm,
  };
}

export function useGPSDebugLog({
  isAdmin,
  mapId,
  mapOrigin,
  mapDestination,
  userPosition,
  gpsAccuracy,
  distanceTraveled,
  isOnRoute,
  distanceToRoute,
  pois,
}: UseGPSDebugLogOptions): UseGPSDebugLogResult {
  const lastLogTimeRef = useRef<Date | null>(null);
  const hasSentInitialLogRef = useRef(false);

  // Check if we can send a log (throttle check)
  const canSendLog = useCallback((): boolean => {
    if (!isAdmin || !mapId || !userPosition) {
      return false;
    }

    // Check local storage for last log time
    const throttleKey = `${THROTTLE_KEY_PREFIX}${mapId}`;
    const lastLogStr = localStorage.getItem(throttleKey);
    if (lastLogStr) {
      const lastLog = new Date(lastLogStr);
      const now = new Date();
      const diffMinutes = (now.getTime() - lastLog.getTime()) / 60000;
      if (diffMinutes < THROTTLE_MINUTES) {
        return false;
      }
    }

    return true;
  }, [isAdmin, mapId, userPosition]);

  // Send debug log
  const sendDebugLog = useCallback(async () => {
    if (!canSendLog() || !mapId || !userPosition || distanceTraveled === null) {
      return;
    }

    const userDistanceKm = distanceTraveled;

    // Sort POIs by effective distance
    const sortedPOIs = [...pois].sort((a, b) => getEffectiveDistance(a) - getEffectiveDistance(b));

    // Find POIs before and after current position
    const previousPOIs: GPSDebugPOIInfo[] = [];
    const nextPOIs: GPSDebugPOIInfo[] = [];

    for (const poi of sortedPOIs) {
      const effectiveDistance = getEffectiveDistance(poi);
      const relativeDistance = effectiveDistance - userDistanceKm;

      if (relativeDistance < -0.1) {
        // POI is behind user (passed)
        previousPOIs.push(poiToDebugInfo(poi, userDistanceKm));
      } else {
        // POI is ahead of user
        nextPOIs.push(poiToDebugInfo(poi, userDistanceKm));
      }
    }

    // Get last 2 previous POIs and first 5 next POIs
    const last2Previous = previousPOIs.slice(-2);
    const first5Next = nextPOIs.slice(0, 5);

    const logData: GPSDebugLogRequest = {
      map_id: mapId,
      map_origin: mapOrigin,
      map_destination: mapDestination,
      latitude: userPosition.lat,
      longitude: userPosition.lon,
      gps_accuracy: gpsAccuracy,
      distance_from_origin_km: distanceTraveled,
      is_on_route: isOnRoute,
      distance_to_route_m: distanceToRoute ?? undefined,
      previous_pois: last2Previous.length > 0 ? last2Previous : undefined,
      next_pois: first5Next.length > 0 ? first5Next : undefined,
      session_id: getSessionId(),
    };

    try {
      const response = await apiClient.createGPSDebugLog(logData);

      if (response.status === 'ok') {
        // Update local storage with current time
        const throttleKey = `${THROTTLE_KEY_PREFIX}${mapId}`;
        const now = new Date();
        localStorage.setItem(throttleKey, now.toISOString());
        lastLogTimeRef.current = now;

        console.log('[GPS Debug] Log sent successfully:', {
          lat: userPosition.lat.toFixed(5),
          lon: userPosition.lon.toFixed(5),
          distance: distanceTraveled?.toFixed(2),
          previousPOIs: last2Previous.length,
          nextPOIs: first5Next.length,
        });
      } else if (response.status === 'throttled') {
        console.log('[GPS Debug] Log throttled:', response.message);
      }
    } catch (error) {
      console.error('[GPS Debug] Error sending log:', error);
    }
  }, [
    canSendLog,
    mapId,
    mapOrigin,
    mapDestination,
    userPosition,
    gpsAccuracy,
    distanceTraveled,
    isOnRoute,
    distanceToRoute,
    pois,
  ]);

  // Auto-send log when GPS position is first obtained (and conditions are met)
  useEffect(() => {
    if (
      isAdmin &&
      mapId &&
      userPosition &&
      distanceTraveled !== null &&
      !hasSentInitialLogRef.current &&
      canSendLog()
    ) {
      hasSentInitialLogRef.current = true;
      sendDebugLog();
    }
  }, [isAdmin, mapId, userPosition, distanceTraveled, canSendLog, sendDebugLog]);

  // Get last log time from storage
  const getLastLogTime = useCallback((): Date | null => {
    if (!mapId) return null;
    const throttleKey = `${THROTTLE_KEY_PREFIX}${mapId}`;
    const lastLogStr = localStorage.getItem(throttleKey);
    return lastLogStr ? new Date(lastLogStr) : null;
  }, [mapId]);

  return {
    sendDebugLog,
    canSendLog: canSendLog(),
    lastLogTime: lastLogTimeRef.current || getLastLogTime(),
  };
}
