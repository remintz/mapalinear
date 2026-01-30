'use client';

import React, { useEffect, useMemo } from 'react';
import { MapContainer, TileLayer, Polyline, Marker, Popup, useMap, useMapEvents } from 'react-leaflet';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import { POI, Milestone } from '@/lib/types';
import { getFriendlyPoiName } from '@/components/ui/POICard';

// Support both coordinate formats from API
interface CoordinatePoint {
  lat?: number;
  lon?: number;
  latitude?: number;
  longitude?: number;
}

interface UserPosition {
  lat: number;
  lon: number;
}

interface RouteMapViewProps {
  coordinates: CoordinatePoint[];
  origin: string;
  destination: string;
  userPosition?: UserPosition;
  pois?: (POI | Milestone)[];
  // Admin features for setting simulated position
  isAdmin?: boolean;
  isSettingPosition?: boolean;
  onPositionSet?: (lat: number, lon: number) => void;
  adminSimulatedPosition?: { lat: number; lon: number } | null;
}

// POI type configuration with colors and icons
const POI_CONFIG: Record<string, { color: string; icon: string; label: string }> = {
  gas_station: { color: '#f59e0b', icon: '⛽', label: 'Posto' },
  restaurant: { color: '#ef4444', icon: '🍽️', label: 'Restaurante' },
  fast_food: { color: '#ef4444', icon: '🍔', label: 'Fast Food' },
  cafe: { color: '#ef4444', icon: '☕', label: 'Cafe' },
  hotel: { color: '#8b5cf6', icon: '🏨', label: 'Hotel' },
  camping: { color: '#22c55e', icon: '⛺', label: 'Camping' },
  hospital: { color: '#dc2626', icon: '🏥', label: 'Hospital' },
  toll_booth: { color: '#6b7280', icon: '💰', label: 'Pedagio' },
  city: { color: '#3b82f6', icon: '🏙️', label: 'Cidade' },
  town: { color: '#60a5fa', icon: '🏘️', label: 'Vila' },
  village: { color: '#93c5fd', icon: '🏡', label: 'Povoado' },
  rest_area: { color: '#14b8a6', icon: '🅿️', label: 'Area de descanso' },
  police: { color: '#1d4ed8', icon: '👮', label: 'Policia' },
  default: { color: '#6b7280', icon: '📍', label: 'POI' },
};

// Create POI icon based on type
const createPOIIcon = (type: string) => {
  const config = POI_CONFIG[type] || POI_CONFIG.default;

  return L.divIcon({
    html: `<div style="
      background-color: ${config.color};
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
    ">${config.icon}</div>`,
    className: '',
    iconSize: [28, 28],
    iconAnchor: [14, 14],
  });
};

// Helper to extract lat/lon from either format
function getLat(coord: CoordinatePoint): number {
  return coord.lat ?? coord.latitude ?? 0;
}

function getLon(coord: CoordinatePoint): number {
  return coord.lon ?? coord.longitude ?? 0;
}

// Component to fit map bounds to route
function MapBounds({ coordinates }: { coordinates: CoordinatePoint[] }) {
  const map = useMap();

  useEffect(() => {
    if (coordinates.length === 0) return;

    const latLngs = coordinates
      .filter(c => getLat(c) !== 0 || getLon(c) !== 0)
      .map(c => [getLat(c), getLon(c)] as [number, number]);

    if (latLngs.length === 0) return;

    const bounds = L.latLngBounds(latLngs);
    map.fitBounds(bounds, { padding: [50, 50] });
  }, [coordinates, map]);

  return null;
}

// Component to handle map clicks for setting admin simulated position
function MapClickHandler({
  isActive,
  onPositionSet,
}: {
  isActive: boolean;
  onPositionSet?: (lat: number, lon: number) => void;
}) {
  useMapEvents({
    click: (e) => {
      if (isActive && onPositionSet) {
        onPositionSet(e.latlng.lat, e.latlng.lng);
      }
    },
  });

  return null;
}

// Create custom marker icons
const createStartIcon = () => {
  return L.divIcon({
    html: `<div style="
      background-color: #22c55e;
      color: white;
      border: 3px solid white;
      border-radius: 50%;
      width: 32px;
      height: 32px;
      display: flex;
      align-items: center;
      justify-content: center;
      font-weight: bold;
      font-size: 14px;
      box-shadow: 0 2px 6px rgba(0,0,0,0.35);
    ">A</div>`,
    className: '',
    iconSize: [32, 32],
    iconAnchor: [16, 16],
  });
};

const createEndIcon = () => {
  return L.divIcon({
    html: `<div style="
      background-color: #ef4444;
      color: white;
      border: 3px solid white;
      border-radius: 50%;
      width: 32px;
      height: 32px;
      display: flex;
      align-items: center;
      justify-content: center;
      font-weight: bold;
      font-size: 14px;
      box-shadow: 0 2px 6px rgba(0,0,0,0.35);
    ">B</div>`,
    className: '',
    iconSize: [32, 32],
    iconAnchor: [16, 16],
  });
};

const createUserIcon = () => {
  return L.divIcon({
    html: `<div style="
      position: relative;
      width: 24px;
      height: 24px;
    ">
      <div style="
        position: absolute;
        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%);
        background-color: #3b82f6;
        border: 3px solid white;
        border-radius: 50%;
        width: 16px;
        height: 16px;
        box-shadow: 0 2px 6px rgba(0,0,0,0.35);
      "></div>
      <div style="
        position: absolute;
        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%);
        background-color: rgba(59, 130, 246, 0.3);
        border-radius: 50%;
        width: 24px;
        height: 24px;
        animation: pulse 2s infinite;
      "></div>
      <style>
        @keyframes pulse {
          0% { transform: translate(-50%, -50%) scale(1); opacity: 1; }
          100% { transform: translate(-50%, -50%) scale(2); opacity: 0; }
        }
      </style>
    </div>`,
    className: '',
    iconSize: [24, 24],
    iconAnchor: [12, 12],
  });
};

// Admin simulated position marker - orange/yellow to distinguish from real position
const createAdminSimulatedIcon = () => {
  return L.divIcon({
    html: `<div style="
      position: relative;
      width: 28px;
      height: 28px;
    ">
      <div style="
        position: absolute;
        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%);
        background-color: #f59e0b;
        border: 3px solid white;
        border-radius: 50%;
        width: 18px;
        height: 18px;
        box-shadow: 0 2px 6px rgba(0,0,0,0.35);
      "></div>
      <div style="
        position: absolute;
        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%);
        background-color: rgba(245, 158, 11, 0.3);
        border-radius: 50%;
        width: 28px;
        height: 28px;
        animation: pulse-admin 2s infinite;
      "></div>
      <style>
        @keyframes pulse-admin {
          0% { transform: translate(-50%, -50%) scale(1); opacity: 1; }
          100% { transform: translate(-50%, -50%) scale(2); opacity: 0; }
        }
      </style>
    </div>`,
    className: '',
    iconSize: [28, 28],
    iconAnchor: [14, 14],
  });
};

export default function RouteMapView({
  coordinates,
  origin,
  destination,
  userPosition,
  pois,
  isAdmin = false,
  isSettingPosition = false,
  onPositionSet,
  adminSimulatedPosition,
}: RouteMapViewProps) {
  // Convert coordinates to Leaflet format [lat, lng]
  const routePositions = useMemo((): [number, number][] => {
    return coordinates
      .filter(c => getLat(c) !== 0 || getLon(c) !== 0)
      .map(c => [getLat(c), getLon(c)] as [number, number]);
  }, [coordinates]);

  // Calculate center
  const center = useMemo((): [number, number] => {
    if (routePositions.length === 0) return [-15.7801, -47.9292]; // Default: Brasília

    return routePositions[0];
  }, [routePositions]);

  // Get start and end positions
  const startPosition = routePositions[0];
  const endPosition = routePositions[routePositions.length - 1];

  const startIcon = useMemo(() => createStartIcon(), []);
  const endIcon = useMemo(() => createEndIcon(), []);
  const userIcon = useMemo(() => createUserIcon(), []);
  const adminSimulatedIcon = useMemo(() => createAdminSimulatedIcon(), []);

  return (
    <div className="h-full w-full absolute inset-0">
      <MapContainer
        center={center}
        zoom={10}
        style={{ height: '100%', width: '100%' }}
        className="z-0"
      >
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />

        <MapBounds coordinates={coordinates} />

        {/* Admin click handler for setting simulated position */}
        {isAdmin && (
          <MapClickHandler
            isActive={isSettingPosition}
            onPositionSet={onPositionSet}
          />
        )}

        {/* Route polyline */}
        {routePositions.length >= 2 && (
          <Polyline
            positions={routePositions}
            color="#3b82f6"
            weight={5}
            opacity={0.8}
          />
        )}

        {/* Start marker */}
        {startPosition && (
          <Marker position={startPosition} icon={startIcon}>
            <Popup>
              <div className="text-sm">
                <p className="font-bold text-green-600">Origem</p>
                <p className="text-gray-700">{origin}</p>
              </div>
            </Popup>
          </Marker>
        )}

        {/* End marker */}
        {endPosition && (
          <Marker position={endPosition} icon={endIcon}>
            <Popup>
              <div className="text-sm">
                <p className="font-bold text-red-600">Destino</p>
                <p className="text-gray-700">{destination}</p>
              </div>
            </Popup>
          </Marker>
        )}

        {/* User position marker */}
        {userPosition && (
          <Marker position={[userPosition.lat, userPosition.lon]} icon={userIcon}>
            <Popup>
              <div className="text-sm">
                <p className="font-bold text-blue-600">Sua localização</p>
              </div>
            </Popup>
          </Marker>
        )}

        {/* Admin simulated position marker */}
        {adminSimulatedPosition && (
          <Marker
            position={[adminSimulatedPosition.lat, adminSimulatedPosition.lon]}
            icon={adminSimulatedIcon}
          >
            <Popup>
              <div className="text-sm">
                <p className="font-bold text-amber-600">Posição simulada (Admin)</p>
                <p className="text-xs text-gray-500">
                  {adminSimulatedPosition.lat.toFixed(6)}, {adminSimulatedPosition.lon.toFixed(6)}
                </p>
              </div>
            </Popup>
          </Marker>
        )}

        {/* POI markers */}
        {pois && pois.map((poi, index) => {
          const coords = poi.coordinates as CoordinatePoint | undefined;
          const lat = coords?.lat ?? coords?.latitude;
          const lon = coords?.lon ?? coords?.longitude;
          if (!lat || !lon) return null;

          const config = POI_CONFIG[poi.type] || POI_CONFIG.default;
          const poiIcon = createPOIIcon(poi.type);

          return (
            <Marker
              key={poi.id || `poi-${index}`}
              position={[lat, lon]}
              icon={poiIcon}
            >
              <Popup>
                <div className="text-sm min-w-[150px]">
                  <p className="font-bold text-black">
                    {config.icon} {getFriendlyPoiName(poi.name, poi.type)}
                  </p>
                  <p className="text-gray-600 text-xs mt-1">
                    {config.label} - {poi.distance_from_origin_km?.toFixed(1)} km
                  </p>
                  {poi.brand && !['yes', 'no', 'true', 'false'].includes(poi.brand.toLowerCase()) && (
                    <p className="text-gray-500 text-xs">{poi.brand}</p>
                  )}
                  {poi.city && (
                    <p className="text-gray-500 text-xs">{poi.city}</p>
                  )}
                </div>
              </Popup>
            </Marker>
          );
        })}
      </MapContainer>
    </div>
  );
}
