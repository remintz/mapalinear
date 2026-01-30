import { Coordinates, RouteSegment } from './types';

// Earth radius in meters
const EARTH_RADIUS_M = 6371000;

/**
 * Normalize coordinates to { lat, lon } format.
 * Handles both { lat, lon } and { latitude, longitude } formats.
 */
interface AnyCoordinates {
  lat?: number;
  lon?: number;
  latitude?: number;
  longitude?: number;
}

function normalizeCoords(coords: AnyCoordinates): Coordinates {
  return {
    lat: coords.lat ?? coords.latitude ?? 0,
    lon: coords.lon ?? coords.longitude ?? 0,
  };
}

/**
 * Convert degrees to radians
 */
function toRadians(degrees: number): number {
  return degrees * (Math.PI / 180);
}

/**
 * Calculate the Haversine distance between two points in meters
 */
export function haversineDistance(
  point1: AnyCoordinates,
  point2: AnyCoordinates
): number {
  const p1 = normalizeCoords(point1);
  const p2 = normalizeCoords(point2);
  const lat1 = toRadians(p1.lat);
  const lat2 = toRadians(p2.lat);
  const deltaLat = toRadians(p2.lat - p1.lat);
  const deltaLon = toRadians(p2.lon - p1.lon);

  const a =
    Math.sin(deltaLat / 2) * Math.sin(deltaLat / 2) +
    Math.cos(lat1) * Math.cos(lat2) * Math.sin(deltaLon / 2) * Math.sin(deltaLon / 2);

  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));

  return EARTH_RADIUS_M * c;
}

/**
 * Calculate the distance from a point to a line segment.
 * Returns the perpendicular distance if the projection falls on the segment,
 * otherwise returns the distance to the nearest endpoint.
 */
export function pointToSegmentDistance(
  point: AnyCoordinates,
  segmentStart: AnyCoordinates,
  segmentEnd: AnyCoordinates
): { distance: number; nearestPoint: Coordinates; fraction: number } {
  const p = normalizeCoords(point);
  const start = normalizeCoords(segmentStart);
  const end = normalizeCoords(segmentEnd);

  const dx = end.lon - start.lon;
  const dy = end.lat - start.lat;

  // If segment has zero length, return distance to the point
  if (dx === 0 && dy === 0) {
    return {
      distance: haversineDistance(p, start),
      nearestPoint: start,
      fraction: 0,
    };
  }

  // Calculate the projection of the point onto the line
  const t = Math.max(
    0,
    Math.min(
      1,
      ((p.lon - start.lon) * dx + (p.lat - start.lat) * dy) /
        (dx * dx + dy * dy)
    )
  );

  const nearestPoint: Coordinates = {
    lon: start.lon + t * dx,
    lat: start.lat + t * dy,
  };

  return {
    distance: haversineDistance(p, nearestPoint),
    nearestPoint,
    fraction: t,
  };
}

/**
 * Result of finding the nearest point on a route
 */
export interface NearestPointResult {
  // Distance from user to the nearest point on the route (in meters)
  distanceToRoute: number;
  // The nearest point on the route
  nearestPoint: Coordinates;
  // Estimated distance from origin at the nearest point (in km)
  distanceFromOrigin: number;
  // Index of the segment where the nearest point is
  segmentIndex: number;
  // Whether the user is considered "on route" (within threshold)
  isOnRoute: boolean;
}

/**
 * Get the start distance for a segment (handles both new and legacy formats).
 */
function getSegmentStartKm(segment: RouteSegment): number {
  // New format: distance_from_origin_km is the primary field
  if (segment.distance_from_origin_km !== undefined) {
    return segment.distance_from_origin_km;
  }
  // Legacy format fallback
  return segment.start_distance_km ?? 0;
}

/**
 * Get the length for a segment (handles both new and legacy formats).
 */
function getSegmentLengthKm(segment: RouteSegment): number {
  // New format: length_km is the primary field
  if (segment.length_km !== undefined) {
    return segment.length_km;
  }
  // Legacy format fallback
  return segment.distance_km ?? 0;
}

/**
 * Get start coordinates for a segment (handles both new and legacy formats).
 */
function getSegmentStartCoords(segment: RouteSegment): Coordinates {
  // New format: start_lat/start_lon are the primary fields
  if (segment.start_lat !== undefined && segment.start_lon !== undefined) {
    return { lat: segment.start_lat, lon: segment.start_lon };
  }
  // Legacy format fallback
  if (segment.start_coordinates) {
    return normalizeCoords(segment.start_coordinates);
  }
  // Last resort: use first geometry point
  if (segment.geometry && segment.geometry.length > 0) {
    return normalizeCoords(segment.geometry[0]);
  }
  return { lat: 0, lon: 0 };
}

/**
 * Get end coordinates for a segment (handles both new and legacy formats).
 */
function getSegmentEndCoords(segment: RouteSegment): Coordinates {
  // New format: end_lat/end_lon are the primary fields
  if (segment.end_lat !== undefined && segment.end_lon !== undefined) {
    return { lat: segment.end_lat, lon: segment.end_lon };
  }
  // Legacy format fallback
  if (segment.end_coordinates) {
    return normalizeCoords(segment.end_coordinates);
  }
  // Last resort: use last geometry point
  if (segment.geometry && segment.geometry.length > 0) {
    return normalizeCoords(segment.geometry[segment.geometry.length - 1]);
  }
  return { lat: 0, lon: 0 };
}

/**
 * Find the nearest point on the route to the user's position.
 * Uses the geometry from route segments for accurate calculation.
 *
 * @param userPosition - Current user position
 * @param segments - Route segments with geometry
 * @param onRouteThreshold - Maximum distance (in meters) to consider "on route" (default 500m)
 */
export function findNearestPointOnRoute(
  userPosition: Coordinates,
  segments: RouteSegment[],
  onRouteThreshold: number = 500
): NearestPointResult | null {
  if (!segments || segments.length === 0) {
    return null;
  }

  let nearestResult: NearestPointResult | null = null;
  let minDistance = Infinity;

  for (let segIdx = 0; segIdx < segments.length; segIdx++) {
    const segment = segments[segIdx];
    const geometry = segment.geometry;

    // Get segment properties using helper functions
    const segmentStartKm = getSegmentStartKm(segment);
    const segmentLengthKm = getSegmentLengthKm(segment);

    // If segment has geometry, use it for precise calculation
    if (geometry && geometry.length >= 2) {
      // Calculate total length of this segment's geometry for interpolation
      let segmentCumulativeDistance = 0;
      const segmentDistances: number[] = [0];

      for (let i = 1; i < geometry.length; i++) {
        segmentCumulativeDistance += haversineDistance(geometry[i - 1], geometry[i]);
        segmentDistances.push(segmentCumulativeDistance);
      }

      // Check each line segment within the geometry
      for (let i = 0; i < geometry.length - 1; i++) {
        const result = pointToSegmentDistance(userPosition, geometry[i], geometry[i + 1]);

        if (result.distance < minDistance) {
          minDistance = result.distance;

          // Interpolate within this geometry segment
          const distanceAlongGeometry = segmentDistances[i] +
            result.fraction * (segmentDistances[i + 1] - segmentDistances[i]);
          const fractionOfSegment = segmentCumulativeDistance > 0
            ? distanceAlongGeometry / segmentCumulativeDistance
            : 0;

          const distanceFromOrigin = segmentStartKm + fractionOfSegment * segmentLengthKm;

          nearestResult = {
            distanceToRoute: result.distance,
            nearestPoint: result.nearestPoint,
            distanceFromOrigin,
            segmentIndex: segIdx,
            isOnRoute: result.distance <= onRouteThreshold,
          };
        }
      }
    } else {
      // Fallback: use start/end coordinates
      const startCoords = getSegmentStartCoords(segment);
      const endCoords = getSegmentEndCoords(segment);
      const result = pointToSegmentDistance(userPosition, startCoords, endCoords);

      if (result.distance < minDistance) {
        minDistance = result.distance;

        const distanceFromOrigin = segmentStartKm + result.fraction * segmentLengthKm;

        nearestResult = {
          distanceToRoute: result.distance,
          nearestPoint: result.nearestPoint,
          distanceFromOrigin,
          segmentIndex: segIdx,
          isOnRoute: result.distance <= onRouteThreshold,
        };
      }
    }
  }

  return nearestResult;
}

/**
 * Get all geometry points from route segments as a flat array with cumulative distances.
 * Useful for simulation along the route.
 */
export interface RoutePoint {
  coordinates: Coordinates;
  distanceFromOrigin: number; // in km
}

export function getRoutePoints(segments: RouteSegment[]): RoutePoint[] {
  const points: RoutePoint[] = [];

  for (const segment of segments) {
    const geometry = segment.geometry;
    const startKm = getSegmentStartKm(segment);
    const lengthKm = getSegmentLengthKm(segment);

    if (geometry && geometry.length >= 2) {
      // Calculate cumulative distances within segment
      let cumulativeDistance = 0;
      const segmentDistances: number[] = [0];

      for (let i = 1; i < geometry.length; i++) {
        cumulativeDistance += haversineDistance(geometry[i - 1], geometry[i]);
        segmentDistances.push(cumulativeDistance);
      }

      const totalSegmentDistance = cumulativeDistance;

      // Add each point with its distance from origin
      for (let i = 0; i < geometry.length; i++) {
        const fractionOfSegment = totalSegmentDistance > 0
          ? segmentDistances[i] / totalSegmentDistance
          : 0;
        const distanceFromOrigin = startKm + fractionOfSegment * lengthKm;

        // Avoid duplicates at segment boundaries
        if (points.length === 0 ||
            points[points.length - 1].distanceFromOrigin < distanceFromOrigin - 0.001) {
          points.push({
            coordinates: normalizeCoords(geometry[i]),
            distanceFromOrigin,
          });
        }
      }
    } else {
      // Fallback: use start/end coordinates
      const startCoords = getSegmentStartCoords(segment);
      const endCoords = getSegmentEndCoords(segment);

      if (points.length === 0 ||
          points[points.length - 1].distanceFromOrigin < startKm - 0.001) {
        points.push({
          coordinates: startCoords,
          distanceFromOrigin: startKm,
        });
      }
      points.push({
        coordinates: endCoords,
        distanceFromOrigin: startKm + lengthKm,
      });
    }
  }

  return points;
}

/**
 * Interpolate a position along the route at a given distance from origin.
 *
 * @param routePoints - Array of route points with distances
 * @param distanceKm - Distance from origin in km
 */
export function interpolateRoutePosition(
  routePoints: RoutePoint[],
  distanceKm: number
): Coordinates | null {
  if (routePoints.length === 0) return null;
  if (distanceKm <= routePoints[0].distanceFromOrigin) {
    return routePoints[0].coordinates;
  }
  if (distanceKm >= routePoints[routePoints.length - 1].distanceFromOrigin) {
    return routePoints[routePoints.length - 1].coordinates;
  }

  // Find the two points to interpolate between
  for (let i = 0; i < routePoints.length - 1; i++) {
    const p1 = routePoints[i];
    const p2 = routePoints[i + 1];

    if (distanceKm >= p1.distanceFromOrigin && distanceKm <= p2.distanceFromOrigin) {
      const segmentLength = p2.distanceFromOrigin - p1.distanceFromOrigin;
      if (segmentLength === 0) return p1.coordinates;

      const fraction = (distanceKm - p1.distanceFromOrigin) / segmentLength;

      return {
        lat: p1.coordinates.lat + fraction * (p2.coordinates.lat - p1.coordinates.lat),
        lon: p1.coordinates.lon + fraction * (p2.coordinates.lon - p1.coordinates.lon),
      };
    }
  }

  return null;
}
