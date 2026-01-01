'use client';

import { useEffect, useMemo } from 'react';
import { MapContainer, TileLayer, Marker, Popup, useMap } from 'react-leaflet';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';

// Fix Leaflet default icon issue
delete (L.Icon.Default.prototype as unknown as { _getIconUrl?: () => void })._getIconUrl;

interface POIDetailMapProps {
  latitude: number;
  longitude: number;
  name: string;
  type: string;
}

// Custom marker icon for POI
const createPOIIcon = (type: string) => {
  const colors: Record<string, string> = {
    gas_station: '#ef4444', // red
    restaurant: '#f97316', // orange
    hotel: '#8b5cf6', // purple
    hospital: '#10b981', // green
    toll_booth: '#6b7280', // gray
    rest_area: '#3b82f6', // blue
    city: '#1f2937', // dark gray
    town: '#374151', // gray
    village: '#4b5563', // gray
  };
  const color = colors[type] || '#3b82f6'; // blue default

  const icons: Record<string, string> = {
    gas_station: '⛽',
    restaurant: '🍽️',
    hotel: '🏨',
    hospital: '🏥',
    toll_booth: '🚧',
    rest_area: '🅿️',
    city: '🏙️',
    town: '🏘️',
    village: '🏡',
  };
  const icon = icons[type] || '📍';

  return L.divIcon({
    className: 'custom-marker',
    html: `<div style="
      background-color: ${color};
      width: 36px;
      height: 36px;
      border-radius: 50%;
      border: 3px solid white;
      box-shadow: 0 2px 6px rgba(0,0,0,0.3);
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 18px;
    ">${icon}</div>`,
    iconSize: [36, 36],
    iconAnchor: [18, 18],
    popupAnchor: [0, -18],
  });
};

// Component to fit map to POI location
function FitToPOI({ position }: { position: [number, number] }) {
  const map = useMap();
  useEffect(() => {
    map.setView(position, 16);
  }, [position, map]);
  return null;
}

export default function POIDetailMap({ latitude, longitude, name, type }: POIDetailMapProps) {
  const position: [number, number] = useMemo(
    () => [latitude, longitude],
    [latitude, longitude]
  );

  const icon = useMemo(() => createPOIIcon(type), [type]);

  return (
    <div className="relative w-full h-full min-h-[256px]">
      <MapContainer
        center={position}
        zoom={16}
        style={{ height: '100%', width: '100%' }}
      >
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        <FitToPOI position={position} />
        <Marker position={position} icon={icon}>
          <Popup>
            <div className="text-sm">
              <div className="font-semibold">{name}</div>
              <div className="text-gray-500">{type.replace(/_/g, ' ')}</div>
            </div>
          </Popup>
        </Marker>
      </MapContainer>
    </div>
  );
}
