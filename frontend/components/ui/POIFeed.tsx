import React from 'react';
import { POI, Milestone } from '@/lib/types';
import { POICard } from './POICard';

interface POIFeedProps {
  pois: (POI | Milestone)[];
  onPOIClick?: (poi: POI | Milestone) => void;
  emptyMessage?: string;
}

export function POIFeed({ pois, onPOIClick, emptyMessage = 'Nenhum ponto de interesse encontrado' }: POIFeedProps) {
  if (pois.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-12 px-4 text-center">
        <div className="text-6xl mb-4">📍</div>
        <p className="text-gray-500 text-lg">{emptyMessage}</p>
      </div>
    );
  }

  // Sort POIs by distance from origin
  // For POIs with junction (requires_detour), use junction_distance_km
  // For regular POIs, use distance_from_origin_km
  const sortedPois = [...pois].sort((a, b) => {
    const distanceA = a.requires_detour && a.junction_distance_km !== undefined
      ? a.junction_distance_km
      : a.distance_from_origin_km;
    const distanceB = b.requires_detour && b.junction_distance_km !== undefined
      ? b.junction_distance_km
      : b.distance_from_origin_km;
    return distanceA - distanceB;
  });

  return (
    <div className="space-y-3 pb-20">
      {sortedPois.map((poi) => (
        <POICard
          key={poi.id}
          poi={poi}
          onClick={() => onPOIClick?.(poi)}
        />
      ))}
    </div>
  );
}
