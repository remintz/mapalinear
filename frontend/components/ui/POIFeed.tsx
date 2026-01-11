import React, { useEffect, useRef, useMemo } from 'react';
import { POI, Milestone } from '@/lib/types';
import { POICard } from './POICard';
import { useAnalytics } from '@/hooks/useAnalytics';

interface TrackingInfo {
  isOnRoute: boolean;
  distanceTraveled: number | null;
  nextPOI: (POI | Milestone) | null;
}

interface POIFeedProps {
  pois: (POI | Milestone)[];
  onPOIClick?: (poi: POI | Milestone) => void;
  emptyMessage?: string;
  // Function to check if a POI has been passed
  isPOIPassed?: (poi: POI | Milestone) => boolean;
  // Index of the next POI ahead (for highlighting)
  nextPOIIndex?: number | null;
  // Whether to auto-scroll to the next POI
  autoScroll?: boolean;
  // Tracking info to show progress bar between passed and upcoming POIs
  trackingInfo?: TrackingInfo;
}

export function POIFeed({
  pois,
  onPOIClick,
  emptyMessage = 'Nenhum ponto de interesse encontrado',
  isPOIPassed,
  nextPOIIndex,
  autoScroll = true,
  trackingInfo,
}: POIFeedProps) {
  const { trackPOIClick } = useAnalytics();

  // Refs for each POI card for scrolling
  const poiRefs = useRef<Map<number, HTMLDivElement>>(new Map());
  const containerRef = useRef<HTMLDivElement>(null);
  const lastScrolledIndex = useRef<number | null>(null);

  // Sort POIs by distance from origin
  const sortedPois = useMemo(() => {
    return [...pois].sort((a, b) => {
      const distanceA = a.requires_detour && a.junction_distance_km !== undefined
        ? a.junction_distance_km
        : a.distance_from_origin_km;
      const distanceB = b.requires_detour && b.junction_distance_km !== undefined
        ? b.junction_distance_km
        : b.distance_from_origin_km;
      return distanceA - distanceB;
    });
  }, [pois]);

  // Auto-scroll to next POI when it changes
  useEffect(() => {
    if (!autoScroll || nextPOIIndex === null || nextPOIIndex === undefined) {
      return;
    }

    // Only scroll if the index has changed
    if (lastScrolledIndex.current === nextPOIIndex) {
      return;
    }

    const element = poiRefs.current.get(nextPOIIndex);
    if (element) {
      // Scroll the element into view with some offset from the top
      element.scrollIntoView({
        behavior: 'smooth',
        block: 'center',
      });
      lastScrolledIndex.current = nextPOIIndex;
    }
  }, [nextPOIIndex, autoScroll]);

  // Reset scroll tracking when POIs change significantly
  useEffect(() => {
    lastScrolledIndex.current = null;
  }, [pois.length]);

  if (pois.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-12 px-4 text-center">
        <div className="text-6xl mb-4">📍</div>
        <p className="text-gray-500 text-lg">{emptyMessage}</p>
      </div>
    );
  }

  // Calculate next POI distance text
  const getNextPOIDistanceText = () => {
    if (!trackingInfo?.nextPOI || trackingInfo.distanceTraveled === null) {
      return 'Todos os POIs passados';
    }

    const nextPoi = trackingInfo.nextPOI;
    if (nextPoi.requires_detour && nextPoi.junction_distance_km !== undefined) {
      // POI requires detour - show distance to junction + detour distance
      const distToJunction = nextPoi.junction_distance_km - trackingInfo.distanceTraveled;
      const detourDist = (nextPoi.distance_from_road_meters || 0) / 1000;
      return `Proximo POI em ${distToJunction.toFixed(1)} + ${detourDist.toFixed(1)} km`;
    } else {
      // POI on route - show simple distance
      const dist = (nextPoi.distance_from_origin_km || 0) - trackingInfo.distanceTraveled;
      return `Proximo POI em ${dist.toFixed(1)} km`;
    }
  };

  // Render tracking status bar
  const renderTrackingBar = () => {
    if (!trackingInfo?.isOnRoute || trackingInfo.distanceTraveled === null) {
      return null;
    }

    return (
      <div className="p-3 bg-green-50 border border-green-200 rounded-lg">
        <div className="flex items-center justify-between text-sm">
          <span className="text-green-700 font-medium">
            Distancia percorrida: {trackingInfo.distanceTraveled.toFixed(1)} km
          </span>
          <span className="text-green-600">
            {getNextPOIDistanceText()}
          </span>
        </div>
      </div>
    );
  };

  return (
    <div ref={containerRef} className="space-y-3 pb-20">
      {sortedPois.map((poi, index) => {
        const isPassed = isPOIPassed ? isPOIPassed(poi) : false;
        const isNext = nextPOIIndex === index;

        // Show tracking bar just before the next POI (between passed and upcoming)
        const showTrackingBar = isNext && trackingInfo?.isOnRoute;

        return (
          <React.Fragment key={poi.id}>
            {showTrackingBar && renderTrackingBar()}
            <div
              ref={(el) => {
                if (el) {
                  poiRefs.current.set(index, el);
                } else {
                  poiRefs.current.delete(index);
                }
              }}
            >
              <POICard
                poi={poi}
                onClick={() => {
                  trackPOIClick(poi.id, poi.name, poi.type);
                  onPOIClick?.(poi);
                }}
                isPassed={isPassed}
                isNext={isNext}
              />
            </div>
          </React.Fragment>
        );
      })}
      {/* Show tracking bar at the end if all POIs are passed */}
      {trackingInfo?.isOnRoute && nextPOIIndex === null && renderTrackingBar()}
    </div>
  );
}
