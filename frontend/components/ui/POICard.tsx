import React from 'react';
import { POI, Milestone } from '@/lib/types';

interface POICardProps {
  poi: POI | Milestone;
  onClick?: () => void;
}

// Helper function to get emoji for POI type
function getPoiEmoji(type: string): string {
  const emojiMap: Record<string, string> = {
    gas_station: '⛽',
    restaurant: '🍽️',
    fast_food: '🍔',
    cafe: '☕',
    hotel: '🏨',
    camping: '⛺',
    hospital: '🏥',
    toll_booth: '🛣️',
    rest_area: '🅿️',
    city: '🏙️',
    town: '🏘️',
    village: '🏡',
    police: '👮',
    intersection: '🔀',
    exit: '🚪',
    other: '📍'
  };
  return emojiMap[type] || '📍';
}

// Helper function to get display name for POI type
function getPoiTypeName(type: string): string {
  const typeNameMap: Record<string, string> = {
    gas_station: 'Posto',
    restaurant: 'Restaurante',
    fast_food: 'Fast Food',
    cafe: 'Café',
    hotel: 'Hotel',
    camping: 'Camping',
    hospital: 'Hospital',
    toll_booth: 'Pedágio',
    rest_area: 'Área de Descanso',
    city: 'Cidade',
    town: 'Vila',
    village: 'Povoado',
    police: 'Polícia',
    intersection: 'Cruzamento',
    exit: 'Saída',
    other: 'Outro'
  };
  return typeNameMap[type] || type;
}

export function POICard({ poi, onClick }: POICardProps) {
  const type = 'type' in poi ? poi.type : (poi as Milestone).type;
  const emoji = getPoiEmoji(type);
  const typeName = getPoiTypeName(type);
  const kmFormatted = poi.distance_from_origin_km.toFixed(1);

  return (
    <div
      className="bg-white border border-gray-200 rounded-lg p-4 hover:shadow-md transition-shadow cursor-pointer active:scale-[0.98] transition-transform"
      onClick={onClick}
    >
        <div className="flex items-start gap-3">
          {/* Icon/Emoji Section */}
          <div className="flex-shrink-0 text-4xl" role="img" aria-label={typeName}>
            {emoji}
          </div>

          {/* Main Content Section */}
          <div className="flex-1 min-w-0">
            {/* Header: Distance + Type */}
            <div className="flex items-center justify-between gap-2 mb-1">
              <span className="text-lg font-bold text-blue-600">
                {kmFormatted} km
              </span>
              <span className="text-sm text-gray-500">
                {typeName}
              </span>
            </div>

            {/* POI Name */}
            <h3 className="text-base font-semibold text-gray-900 mb-1 truncate">
              {poi.name || 'Nome não disponível'}
            </h3>

            {/* City */}
            <div className="text-sm text-gray-600 truncate">
              {poi.city || '-'}
            </div>
          </div>
        </div>
    </div>
  );
}
