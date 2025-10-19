import React from 'react';
import { POI, Milestone } from '@/lib/types';
import { POICard } from './POICard';

interface POIFeedProps {
  pois: (POI | Milestone)[];
  onPOIClick?: (poi: POI | Milestone) => void;
  emptyMessage?: string;
}

export function POIFeed({ pois, onPOIClick, emptyMessage = 'Nenhum POI encontrado' }: POIFeedProps) {
  if (pois.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-12 px-4 text-center">
        <div className="text-6xl mb-4">📍</div>
        <p className="text-gray-500 text-lg">{emptyMessage}</p>
      </div>
    );
  }

  return (
    <div className="space-y-3 pb-20">
      {pois.map((poi) => (
        <POICard
          key={poi.id}
          poi={poi}
          onClick={() => onPOIClick?.(poi)}
        />
      ))}
    </div>
  );
}
