import React, { useEffect, useRef, useMemo, useState } from 'react';
import { POI, Milestone } from '@/lib/types';
import { POICard } from './POICard';
import { useAnalytics } from '@/hooks/useAnalytics';
import { ChevronDown, ChevronUp } from 'lucide-react';

interface TrackingInfo {
  isOnRoute: boolean;
  distanceTraveled: number | null;
  distanceToRoute: number | null;
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

  // State for accordion (passed POIs collapsed by default)
  const [isPassedExpanded, setIsPassedExpanded] = useState(false);

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

  // Separate passed and upcoming POIs (must be before any conditional returns)
  const isTrackingActive = trackingInfo?.isOnRoute ?? false;
  const { passedPois, upcomingPois } = useMemo(() => {
    if (!isPOIPassed || !isTrackingActive || pois.length === 0) {
      return { passedPois: [] as { poi: POI | Milestone; index: number }[], upcomingPois: sortedPois.map((poi, index) => ({ poi, index })) };
    }

    const passed: { poi: POI | Milestone; index: number }[] = [];
    const upcoming: { poi: POI | Milestone; index: number }[] = [];

    sortedPois.forEach((poi, index) => {
      if (isPOIPassed(poi)) {
        passed.push({ poi, index });
      } else {
        upcoming.push({ poi, index });
      }
    });

    return { passedPois: passed, upcomingPois: upcoming };
  }, [sortedPois, isPOIPassed, isTrackingActive, pois.length]);

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
    if (!trackingInfo || trackingInfo.distanceToRoute === null) {
      return null;
    }

    // Check if user is far from route (more than 500m)
    const isFarFromRoute = trackingInfo.distanceToRoute > 500;

    if (isFarFromRoute) {
      return (
        <div className="p-3 bg-yellow-50 border border-yellow-300 rounded-lg">
          <div className="flex items-center justify-center text-sm">
            <span className="text-yellow-700 font-medium">
              Voce esta a {(trackingInfo.distanceToRoute / 1000).toFixed(1)} km da rota
            </span>
          </div>
        </div>
      );
    }

    // On route - show green bar with progress
    if (trackingInfo.distanceTraveled === null) {
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

  // Render a single POI card
  const renderPOICard = (poi: POI | Milestone, index: number, isPassed: boolean, isNext: boolean) => (
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
        distanceTraveled={trackingInfo?.isOnRoute ? trackingInfo.distanceTraveled : null}
      />
    </div>
  );

  // If tracking is active and there are passed POIs, show accordion layout
  const hasPassedPois = passedPois.length > 0 && trackingInfo?.isOnRoute;

  // Check if location is not available (no tracking info or not on route)
  const isLocationUnavailable = !trackingInfo || trackingInfo.distanceToRoute === null;

  return (
    <div ref={containerRef} className="space-y-3 pb-20">
      {/* Location unavailable banner */}
      {isLocationUnavailable && (
        <div className="p-3 bg-blue-50 border border-blue-200 rounded-lg">
          <div className="flex items-center gap-2 text-sm text-blue-700">
            <span className="text-lg">📍</span>
            <span>
              Habilite a localização para ver sua posição no mapa e os POIs já passados.
            </span>
          </div>
        </div>
      )}

      {/* Passed POIs Accordion */}
      {hasPassedPois && (
        <div className="border border-gray-200 rounded-lg overflow-hidden">
          <button
            onClick={() => setIsPassedExpanded(!isPassedExpanded)}
            className="w-full px-4 py-3 bg-gray-50 hover:bg-gray-100 transition-colors flex items-center justify-between"
          >
            <span className="text-sm font-medium text-gray-600">
              POIs passados ({passedPois.length})
            </span>
            {isPassedExpanded ? (
              <ChevronUp className="w-4 h-4 text-gray-500" />
            ) : (
              <ChevronDown className="w-4 h-4 text-gray-500" />
            )}
          </button>
          {isPassedExpanded && (
            <div className="p-3 space-y-3 bg-gray-50/50">
              {passedPois.map(({ poi, index }) => (
                <React.Fragment key={poi.id}>
                  {renderPOICard(poi, index, true, false)}
                </React.Fragment>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Tracking Bar - between passed and upcoming (or warning when far from route) */}
      {trackingInfo?.distanceToRoute !== null && renderTrackingBar()}

      {/* Upcoming POIs (or all POIs when not tracking) */}
      {upcomingPois.map(({ poi, index }) => {
        const isPassed = isPOIPassed ? isPOIPassed(poi) : false;
        const isNext = nextPOIIndex === index;
        return (
          <React.Fragment key={poi.id}>
            {renderPOICard(poi, index, isPassed, isNext)}
          </React.Fragment>
        );
      })}
    </div>
  );
}
