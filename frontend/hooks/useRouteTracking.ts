import { useMemo } from 'react';
import { Coordinates, RouteSegment, POI, Milestone } from '@/lib/types';
import { findNearestPointOnRoute, NearestPointResult } from '@/lib/geo-utils';

export interface RouteTrackingResult {
  // Whether the user is on the route (within threshold distance)
  isOnRoute: boolean;
  // Distance from user to the nearest point on the route (in meters)
  distanceToRoute: number | null;
  // Estimated distance traveled from origin (in km), null if not on route
  distanceTraveled: number | null;
  // The nearest point on the route
  nearestPoint: Coordinates | null;
  // Index of the next POI ahead (or null if none or not on route)
  nextPOIIndex: number | null;
  // Function to check if a POI has been passed
  isPOIPassed: (poi: POI | Milestone) => boolean;
}

export interface UseRouteTrackingOptions {
  // User's current position (real GPS or simulated)
  userPosition: Coordinates | null;
  // Route segments with geometry
  segments: RouteSegment[];
  // POIs sorted by distance from origin
  pois: (POI | Milestone)[];
  // Maximum distance (in meters) to consider "on route" (default 500m)
  onRouteThreshold?: number;
}

/**
 * Hook to track user's position along a route.
 * Determines if user is on route, calculates distance traveled,
 * and identifies which POIs have been passed.
 */
export function useRouteTracking({
  userPosition,
  segments,
  pois,
  onRouteThreshold = 500,
}: UseRouteTrackingOptions): RouteTrackingResult {
  // Find nearest point on route
  const nearestResult = useMemo<NearestPointResult | null>(() => {
    if (!userPosition || !segments || segments.length === 0) {
      return null;
    }
    const result = findNearestPointOnRoute(userPosition, segments, onRouteThreshold);
    // Debug: log tracking info
    if (typeof window !== 'undefined' && result) {
      console.log('[Tracking] User position:', userPosition);
      console.log('[Tracking] Distance to route:', result.distanceToRoute?.toFixed(0), 'm');
      console.log('[Tracking] Is on route:', result.isOnRoute);
      console.log('[Tracking] Distance from origin:', result.distanceFromOrigin?.toFixed(2), 'km');
    }
    return result;
  }, [userPosition, segments, onRouteThreshold]);

  // Sort POIs by distance and find the next one
  const sortedPois = useMemo(() => {
    return [...pois].sort((a, b) => {
      const distA = a.requires_detour && a.junction_distance_km !== undefined
        ? a.junction_distance_km
        : a.distance_from_origin_km;
      const distB = b.requires_detour && b.junction_distance_km !== undefined
        ? b.junction_distance_km
        : b.distance_from_origin_km;
      return distA - distB;
    });
  }, [pois]);

  // Find the index of the next POI ahead
  const nextPOIIndex = useMemo(() => {
    if (!nearestResult?.isOnRoute) return null;

    const distanceTraveled = nearestResult.distanceFromOrigin;

    for (let i = 0; i < sortedPois.length; i++) {
      const poi = sortedPois[i];
      const poiDistance = poi.requires_detour && poi.junction_distance_km !== undefined
        ? poi.junction_distance_km
        : poi.distance_from_origin_km;

      if (poiDistance > distanceTraveled) {
        return i;
      }
    }

    return null; // All POIs have been passed
  }, [nearestResult, sortedPois]);

  // Function to check if a POI has been passed
  const isPOIPassed = useMemo(() => {
    return (poi: POI | Milestone): boolean => {
      // If not on route, nothing is considered "passed"
      if (!nearestResult?.isOnRoute) return false;

      const distanceTraveled = nearestResult.distanceFromOrigin;
      const poiDistance = poi.requires_detour && poi.junction_distance_km !== undefined
        ? poi.junction_distance_km
        : poi.distance_from_origin_km;

      // POI is passed if its distance is less than user's traveled distance
      // We add a small buffer (100m = 0.1km) to avoid flickering at boundaries
      return poiDistance < distanceTraveled - 0.1;
    };
  }, [nearestResult]);

  return {
    isOnRoute: nearestResult?.isOnRoute ?? false,
    distanceToRoute: nearestResult?.distanceToRoute ?? null,
    distanceTraveled: nearestResult?.isOnRoute ? nearestResult.distanceFromOrigin : null,
    nearestPoint: nearestResult?.nearestPoint ?? null,
    nextPOIIndex,
    isPOIPassed,
  };
}
