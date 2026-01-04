import React, { useEffect, useRef, useMemo } from 'react';
import { POI, Milestone } from '@/lib/types';
import { POICard } from './POICard';
import { useAnalytics } from '@/hooks/useAnalytics';

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
}

export function POIFeed({
  pois,
  onPOIClick,
  emptyMessage = 'Nenhum ponto de interesse encontrado',
  isPOIPassed,
  nextPOIIndex,
  autoScroll = true,
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

  return (
    <div ref={containerRef} className="space-y-3 pb-20">
      {sortedPois.map((poi, index) => {
        const isPassed = isPOIPassed ? isPOIPassed(poi) : false;
        const isNext = nextPOIIndex === index;

        return (
          <div
            key={poi.id}
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
        );
      })}
    </div>
  );
}
