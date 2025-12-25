'use client';

import React, { useEffect, useMemo } from 'react';
import { MapContainer, TileLayer, Polyline, Marker, Popup, useMap } from 'react-leaflet';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';

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
}

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

export default function RouteMapView({ coordinates, origin, destination, userPosition }: RouteMapViewProps) {
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
      </MapContainer>
    </div>
  );
}
