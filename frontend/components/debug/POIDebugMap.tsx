'use client';

import React, { useMemo, useEffect } from 'react';
import { MapContainer, TileLayer, Polyline, Marker, Popup, useMap } from 'react-leaflet';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import { POIDebugData } from '@/lib/types';

interface POIDebugMapProps {
  debugData: POIDebugData;
}

// Create POI marker icon
const createPOIIcon = () => {
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
    ">P</div>`,
    className: '',
    iconSize: [32, 32],
    iconAnchor: [16, 16],
  });
};

// Create junction marker icon
const createJunctionIcon = () => {
  return L.divIcon({
    html: `<div style="
      background-color: #f59e0b;
      color: white;
      border: 3px solid white;
      border-radius: 50%;
      width: 28px;
      height: 28px;
      display: flex;
      align-items: center;
      justify-content: center;
      font-weight: bold;
      font-size: 12px;
      box-shadow: 0 2px 6px rgba(0,0,0,0.35);
    ">J</div>`,
    className: '',
    iconSize: [28, 28],
    iconAnchor: [14, 14],
  });
};

// Create lookback marker icon
const createLookbackIcon = () => {
  return L.divIcon({
    html: `<div style="
      background-color: #8b5cf6;
      color: white;
      border: 3px solid white;
      border-radius: 50%;
      width: 24px;
      height: 24px;
      display: flex;
      align-items: center;
      justify-content: center;
      font-weight: bold;
      font-size: 10px;
      box-shadow: 0 2px 6px rgba(0,0,0,0.35);
    ">L</div>`,
    className: '',
    iconSize: [24, 24],
    iconAnchor: [12, 12],
  });
};

// Component to fit bounds
function FitBounds({ positions }: { positions: [number, number][] }) {
  const map = useMap();

  useEffect(() => {
    if (positions.length > 0) {
      const bounds = L.latLngBounds(positions);
      map.fitBounds(bounds, { padding: [50, 50] });
    }
  }, [positions, map]);

  return null;
}

export default function POIDebugMap({ debugData }: POIDebugMapProps) {
  const poiIcon = useMemo(() => createPOIIcon(), []);
  const junctionIcon = useMemo(() => createJunctionIcon(), []);
  const lookbackIcon = useMemo(() => createLookbackIcon(), []);

  // Collect all positions for bounds
  const allPositions = useMemo((): [number, number][] => {
    const positions: [number, number][] = [];

    // POI position
    positions.push([debugData.poi_lat, debugData.poi_lon]);

    // Junction position
    if (debugData.junction_lat && debugData.junction_lon) {
      positions.push([debugData.junction_lat, debugData.junction_lon]);
    }

    // Main route segment
    if (debugData.main_route_segment) {
      debugData.main_route_segment.forEach(p => {
        positions.push([p[0], p[1]]);
      });
    }

    // Access route
    if (debugData.access_route_geometry) {
      debugData.access_route_geometry.forEach(p => {
        positions.push([p[0], p[1]]);
      });
    }

    // Lookback point
    if (debugData.lookback_data?.lookback_point) {
      positions.push([debugData.lookback_data.lookback_point.lat, debugData.lookback_data.lookback_point.lon]);
    }

    return positions;
  }, [debugData]);

  const center = useMemo((): [number, number] => {
    // Center on junction if available, otherwise on POI
    if (debugData.junction_lat && debugData.junction_lon) {
      return [debugData.junction_lat, debugData.junction_lon];
    }
    return [debugData.poi_lat, debugData.poi_lon];
  }, [debugData]);

  return (
    <div className="relative">
      <div className="h-[400px] rounded-lg overflow-hidden border border-gray-300">
        <MapContainer
        center={center}
        zoom={14}
        style={{ height: '100%', width: '100%' }}
      >
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />

        <FitBounds positions={allPositions} />

        {/* Main route segment (blue) */}
        {debugData.main_route_segment && debugData.main_route_segment.length >= 2 && (
          <Polyline
            positions={debugData.main_route_segment.map(p => [p[0], p[1]] as [number, number])}
            color="#3b82f6"
            weight={6}
            opacity={0.8}
          >
            <Popup>Segmento da Rota Principal</Popup>
          </Polyline>
        )}

        {/* Access route (green dashed) */}
        {debugData.access_route_geometry && debugData.access_route_geometry.length >= 2 && (
          <Polyline
            positions={debugData.access_route_geometry.map(p => [p[0], p[1]] as [number, number])}
            color="#22c55e"
            weight={4}
            opacity={0.9}
            dashArray="10, 10"
          >
            <Popup>
              Rota de Acesso: {debugData.access_route_distance_km?.toFixed(2)} km
            </Popup>
          </Polyline>
        )}

        {/* Lookback marker */}
        {debugData.lookback_data?.lookback_point && (
          <Marker
            position={[debugData.lookback_data.lookback_point.lat, debugData.lookback_data.lookback_point.lon]}
            icon={lookbackIcon}
          >
            <Popup>
              <div className="text-sm">
                <p className="font-bold text-purple-600">Ponto de Lookback</p>
                <p>Distancia: {debugData.lookback_data.lookback_distance_km?.toFixed(2)} km da origem</p>
                <p className="text-xs text-gray-500">Inicio da busca de rota de acesso</p>
              </div>
            </Popup>
          </Marker>
        )}

        {/* Junction marker */}
        {debugData.junction_lat && debugData.junction_lon && (
          <Marker
            position={[debugData.junction_lat, debugData.junction_lon]}
            icon={junctionIcon}
          >
            <Popup>
              <div className="text-sm">
                <p className="font-bold text-amber-600">Ponto de Juncao</p>
                <p>Distancia: {debugData.junction_distance_km?.toFixed(2)} km da origem</p>
              </div>
            </Popup>
          </Marker>
        )}

        {/* POI marker */}
        <Marker position={[debugData.poi_lat, debugData.poi_lon]} icon={poiIcon}>
          <Popup>
            <div className="text-sm">
              <p className="font-bold text-red-600">{debugData.poi_name}</p>
              <p>Tipo: {debugData.poi_type}</p>
              <p>Lado: <span className={debugData.final_side === 'left' ? 'text-blue-600' : debugData.final_side === 'right' ? 'text-green-600' : 'text-gray-600'}>
                {debugData.final_side === 'left' ? 'ESQUERDA' : debugData.final_side === 'right' ? 'DIREITA' : 'CENTRO'}
              </span></p>
              {debugData.requires_detour && (
                <p className="text-amber-600">Requer Desvio</p>
              )}
            </div>
          </Popup>
        </Marker>
      </MapContainer>
      </div>

      {/* Legend */}
      <div className="absolute bottom-2 left-2 bg-white/95 rounded-lg shadow-md p-2 text-xs z-[1000]">
        <div className="font-semibold mb-1 text-gray-700">Legenda:</div>
        <div className="flex flex-col gap-1">
          <div className="flex items-center gap-2">
            <div className="w-4 h-1 bg-blue-500 rounded"></div>
            <span>Rota Principal</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-4 h-1 bg-green-500 rounded" style={{backgroundImage: 'repeating-linear-gradient(90deg, #22c55e 0, #22c55e 3px, transparent 3px, transparent 6px)'}}></div>
            <span>Rota de Acesso</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-4 h-4 bg-purple-500 rounded-full text-white text-[8px] flex items-center justify-center font-bold">L</div>
            <span>Lookback</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-4 h-4 bg-amber-500 rounded-full text-white text-[8px] flex items-center justify-center font-bold">J</div>
            <span>Junction</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-4 h-4 bg-red-500 rounded-full text-white text-[8px] flex items-center justify-center font-bold">P</div>
            <span>POI</span>
          </div>
        </div>
      </div>
    </div>
  );
}
