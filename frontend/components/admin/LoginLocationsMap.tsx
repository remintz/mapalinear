'use client';

import React, { useEffect, useMemo } from 'react';
import { MapContainer, TileLayer, Marker, Popup, useMap } from 'react-leaflet';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import { LoginLocation } from '@/lib/types';
import { Smartphone, Monitor, Tablet } from 'lucide-react';

interface LoginLocationsMapProps {
  locations: LoginLocation[];
}

// Create marker icon based on device type
const createLoginIcon = (deviceType: string | null) => {
  let emoji = '📍';
  let color = '#3b82f6';

  switch (deviceType) {
    case 'mobile':
      emoji = '📱';
      color = '#22c55e';
      break;
    case 'tablet':
      emoji = '📲';
      color = '#8b5cf6';
      break;
    case 'desktop':
      emoji = '💻';
      color = '#3b82f6';
      break;
  }

  return L.divIcon({
    html: `<div style="
      background-color: ${color};
      color: white;
      border: 2px solid white;
      border-radius: 50%;
      width: 28px;
      height: 28px;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 14px;
      box-shadow: 0 2px 6px rgba(0,0,0,0.35);
    ">${emoji}</div>`,
    className: '',
    iconSize: [28, 28],
    iconAnchor: [14, 14],
  });
};

// Component to fit map bounds to all markers
function MapBounds({ locations }: { locations: LoginLocation[] }) {
  const map = useMap();

  useEffect(() => {
    if (locations.length === 0) return;

    const latLngs = locations
      .filter(loc => loc.latitude && loc.longitude)
      .map(loc => [loc.latitude, loc.longitude] as [number, number]);

    if (latLngs.length === 0) return;

    if (latLngs.length === 1) {
      map.setView(latLngs[0], 10);
    } else {
      const bounds = L.latLngBounds(latLngs);
      map.fitBounds(bounds, { padding: [50, 50] });
    }
  }, [locations, map]);

  return null;
}

const DeviceIcon = ({ type }: { type: string | null }) => {
  switch (type) {
    case 'mobile':
      return <Smartphone className="h-4 w-4 text-green-600" />;
    case 'tablet':
      return <Tablet className="h-4 w-4 text-purple-600" />;
    default:
      return <Monitor className="h-4 w-4 text-blue-600" />;
  }
};

// Default center (Brazil)
const DEFAULT_CENTER: [number, number] = [-15.7801, -47.9292];

export default function LoginLocationsMap({ locations }: LoginLocationsMapProps) {
  // Calculate center from locations
  const center = useMemo((): [number, number] => {
    if (locations.length === 0) return DEFAULT_CENTER;

    const validLocations = locations.filter(loc => loc.latitude && loc.longitude);
    if (validLocations.length === 0) return DEFAULT_CENTER;

    const avgLat = validLocations.reduce((sum, loc) => sum + loc.latitude, 0) / validLocations.length;
    const avgLon = validLocations.reduce((sum, loc) => sum + loc.longitude, 0) / validLocations.length;

    return [avgLat, avgLon];
  }, [locations]);

  // Create icons cache
  const icons = useMemo(() => ({
    mobile: createLoginIcon('mobile'),
    tablet: createLoginIcon('tablet'),
    desktop: createLoginIcon('desktop'),
    default: createLoginIcon(null),
  }), []);

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleString('pt-BR', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  return (
    <div className="h-[500px] w-full rounded-lg overflow-hidden border border-gray-200">
      <MapContainer
        center={center}
        zoom={4}
        style={{ height: '100%', width: '100%' }}
        className="z-0"
      >
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />

        <MapBounds locations={locations} />

        {locations.map((location, index) => {
          if (!location.latitude || !location.longitude) return null;

          const icon = icons[location.device_type as keyof typeof icons] || icons.default;

          return (
            <Marker
              key={`login-${index}-${location.created_at}`}
              position={[location.latitude, location.longitude]}
              icon={icon}
            >
              <Popup>
                <div className="text-sm min-w-[180px]">
                  <div className="flex items-center gap-2 font-bold text-gray-900 mb-2">
                    <DeviceIcon type={location.device_type} />
                    <span>Login</span>
                  </div>

                  {location.user_name && (
                    <p className="text-gray-700">{location.user_name}</p>
                  )}

                  {location.user_email && (
                    <p className="text-gray-500 text-xs">{location.user_email}</p>
                  )}

                  <p className="text-gray-400 text-xs mt-2">
                    {formatDate(location.created_at)}
                  </p>

                  <p className="text-gray-400 text-xs capitalize">
                    {location.device_type || 'Desconhecido'}
                  </p>
                </div>
              </Popup>
            </Marker>
          );
        })}
      </MapContainer>
    </div>
  );
}
