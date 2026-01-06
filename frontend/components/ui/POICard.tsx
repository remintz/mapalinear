import React from 'react';
import { POI, Milestone } from '@/lib/types';
import {
  Fuel, Utensils, Coffee, Bed, Tent, Hospital, Ticket,
  Building2, Home, MapPin, Shield, Signpost, LogOut,
  UtensilsCrossed, ParkingCircle, Star, ExternalLink
} from 'lucide-react';

interface POICardProps {
  poi: POI | Milestone;
  onClick?: () => void;
  // Whether this POI has been passed (user is ahead of it)
  isPassed?: boolean;
  // Whether this is the next POI ahead
  isNext?: boolean;
}

// Helper function to get icon for POI type
function getPoiIcon(type: string): React.ElementType {
  const iconMap: Record<string, React.ElementType> = {
    gas_station: Fuel,
    restaurant: Utensils,
    fast_food: UtensilsCrossed,
    cafe: Coffee,
    hotel: Bed,
    camping: Tent,
    hospital: Hospital,
    toll_booth: Ticket,
    rest_area: ParkingCircle,
    city: Building2,
    town: Home,
    village: Home,
    police: Shield,
    intersection: Signpost,
    exit: LogOut,
    other: MapPin
  };
  return iconMap[type] || MapPin;
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

// Helper function to render star rating
function StarRating({ rating, count }: { rating: number; count?: number }) {
  const fullStars = Math.floor(rating);
  const hasHalfStar = rating - fullStars >= 0.5;

  return (
    <div className="flex items-center gap-1">
      <div className="flex items-center">
        {[...Array(5)].map((_, i) => (
          <Star
            key={i}
            className={`w-3.5 h-3.5 ${
              i < fullStars
                ? 'text-yellow-400 fill-yellow-400'
                : i === fullStars && hasHalfStar
                ? 'text-yellow-400 fill-yellow-400/50'
                : 'text-gray-300'
            }`}
          />
        ))}
      </div>
      <span className="text-sm font-medium text-zinc-700">{rating.toFixed(1)}</span>
      {count != null && (
        <span className="text-xs text-zinc-500">({count.toLocaleString('pt-BR')})</span>
      )}
    </div>
  );
}

// Helper function to get friendly name when POI has generic/type name
function getFriendlyPoiName(name: string | null | undefined, type: string): string {
  // List of generic names from OSM that should be replaced
  const genericNames = [
    'fuel', 'gas_station', 'restaurant', 'cafe', 'fast_food', 'food_court', 'hotel',
    'camping', 'hospital', 'toll_booth', 'rest_area', 'city', 'town',
    'village', 'police', 'motel', 'guest_house', 'hostel', 'pharmacy',
    'atm', 'bank', 'parking', 'post_office', 'convenience', 'supermarket'
  ];

  // Friendly names mapping for common POI types
  const friendlyNames: Record<string, string> = {
    fuel: 'Posto de Combustível',
    gas_station: 'Posto de Combustível',
    restaurant: 'Restaurante',
    cafe: 'Café',
    fast_food: 'Lanchonete',
    food_court: 'Praça de Alimentação',
    hotel: 'Hotel',
    motel: 'Motel',
    guest_house: 'Pousada',
    hostel: 'Hostel',
    camping: 'Área de Camping',
    hospital: 'Hospital',
    pharmacy: 'Farmácia',
    toll_booth: 'Pedágio',
    rest_area: 'Área de Descanso',
    city: 'Cidade',
    town: 'Vila',
    village: 'Povoado',
    police: 'Delegacia',
    atm: 'Caixa Eletrônico',
    bank: 'Banco',
    parking: 'Estacionamento',
    post_office: 'Correios',
    convenience: 'Conveniência',
    supermarket: 'Supermercado'
  };

  // If no name provided or name is empty
  if (!name || name.trim() === '') {
    return friendlyNames[type] || getPoiTypeName(type);
  }

  // Check if name is a generic type name (case insensitive)
  const nameLower = name.toLowerCase().trim();
  if (genericNames.includes(nameLower)) {
    return friendlyNames[nameLower] || friendlyNames[type] || getPoiTypeName(type);
  }

  // Return original name if it's specific
  return name;
}

export function POICard({ poi, onClick, isPassed = false, isNext = false }: POICardProps) {
  const type = 'type' in poi ? poi.type : (poi as Milestone).type;
  const Icon = getPoiIcon(type);
  const typeName = getPoiTypeName(type);

  // Check if POI requires detour (has junction information)
  const hasJunction = poi.requires_detour && poi.junction_distance_km !== undefined;

  // Use junction_distance_km for POIs with detour, otherwise use distance_from_origin_km
  const displayDistance = hasJunction ? poi.junction_distance_km! : poi.distance_from_origin_km;
  const kmFormatted = displayDistance.toFixed(1);

  // Get direction arrow based on POI side
  const directionArrow = poi.side === 'left' ? '←' : poi.side === 'right' ? '→' : '🔀';

  // Check if POI has Google Maps link
  const hasGoogleMapsLink = !!poi.google_maps_uri;

  // Handle card click - open Google Maps if available
  const handleClick = () => {
    if (poi.google_maps_uri) {
      window.open(poi.google_maps_uri, '_blank', 'noopener,noreferrer');
    } else if (onClick) {
      onClick();
    }
  };

  // Build card classes based on state
  const cardClasses = [
    'rounded-lg p-4 transition-all cursor-pointer active:scale-[0.98]',
    // Base styles - different for passed vs active
    isPassed
      ? 'bg-gray-50 border border-gray-100 opacity-50'
      : 'bg-white border border-gray-200 hover:shadow-md',
    // Next POI highlight
    isNext && !isPassed
      ? 'ring-2 ring-blue-500 ring-offset-2 border-blue-300'
      : '',
    // Google Maps link hover
    hasGoogleMapsLink && !isPassed ? 'hover:border-blue-300' : '',
  ].filter(Boolean).join(' ');

  return (
    <div
      className={cardClasses}
      onClick={handleClick}
    >
      <div className="flex items-start gap-3">
        {/* Icon Section */}
        <div className="flex-shrink-0 w-10 h-10 rounded-full bg-zinc-100 flex items-center justify-center text-zinc-600">
          <Icon className="w-5 h-5" />
        </div>

        {/* Main Content Section */}
        <div className="flex-1 min-w-0">
          {/* Header: Distance + Type */}
          <div className="flex items-center justify-between gap-2 mb-1">
            <div className="flex items-center gap-2">
              <span className="text-lg font-bold text-zinc-900">
                {kmFormatted} km
              </span>
              {hasJunction && (
                <span className="text-xs text-zinc-500 flex items-center gap-1">
                  <span>{directionArrow}</span>
                  <span>{((poi.distance_from_road_meters || 0) / 1000).toFixed(1)}km</span>
                </span>
              )}
            </div>
            <div className="flex items-center gap-1">
              {hasGoogleMapsLink && (
                <ExternalLink className="w-3.5 h-3.5 text-blue-500" />
              )}
              <span className="text-xs font-medium text-zinc-500 uppercase tracking-wide">
                {typeName}
              </span>
            </div>
          </div>

          {/* POI Name */}
          <h3 className="text-base font-semibold text-zinc-800 mb-1 truncate">
            {getFriendlyPoiName(poi.name, type)}
          </h3>

          {/* Rating (if available) */}
          {poi.rating && (
            <div className="mb-1">
              <StarRating rating={poi.rating} count={poi.rating_count} />
            </div>
          )}

          {/* City */}
          <div className="text-sm text-zinc-500 truncate flex items-center gap-1">
            <MapPin className="w-3 h-3" />
            {poi.city || '-'}
          </div>
        </div>
      </div>
    </div>
  );
}
