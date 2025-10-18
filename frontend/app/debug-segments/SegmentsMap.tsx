'use client';

import React, { useEffect, useMemo } from 'react';
import { MapContainer, TileLayer, Polyline, Marker, Popup, useMap } from 'react-leaflet';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';

interface Segment {
  id: string;
  start_distance_km: number;
  end_distance_km: number;
  length_km: number;
  name: string;
  start_coordinates: {
    latitude: number;
    longitude: number;
  };
  end_coordinates: {
    latitude: number;
    longitude: number;
  };
}

interface SegmentsMapProps {
  segments: Segment[];
}

// Componente para ajustar o zoom do mapa
function MapBounds({ segments }: { segments: Segment[] }) {
  const map = useMap();

  useEffect(() => {
    if (segments.length === 0) return;

    // Coletar todas as coordenadas
    const allCoords = segments.flatMap(segment => [
      [segment.start_coordinates.latitude, segment.start_coordinates.longitude],
      [segment.end_coordinates.latitude, segment.end_coordinates.longitude]
    ]);

    // Criar bounds
    const bounds = L.latLngBounds(allCoords as [number, number][]);
    map.fitBounds(bounds, { padding: [50, 50] });
  }, [segments, map]);

  return null;
}

// Criar ícone personalizado para os marcadores
const createNumberIcon = (number: number, isStart: boolean) => {
  const color = isStart ? '#10b981' : '#ef4444'; // verde para início, vermelho para fim
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
      font-weight: bold;
      font-size: 12px;
      box-shadow: 0 2px 4px rgba(0,0,0,0.3);
    ">${number}</div>`,
    className: '',
    iconSize: [28, 28],
    iconAnchor: [14, 14]
  });
};

export default function SegmentsMap({ segments }: SegmentsMapProps) {
  // Calcular o centro do mapa
  const center = useMemo(() => {
    if (segments.length === 0) return [-23.5505, -46.6333]; // Default: São Paulo

    const firstSegment = segments[0];
    return [
      firstSegment.start_coordinates.latitude,
      firstSegment.start_coordinates.longitude
    ] as [number, number];
  }, [segments]);

  // Gerar cores diferentes para cada segmento
  const getSegmentColor = (index: number) => {
    const colors = [
      '#3b82f6', // blue-500
      '#8b5cf6', // violet-500
      '#ec4899', // pink-500
      '#f59e0b', // amber-500
      '#10b981', // emerald-500
      '#06b6d4', // cyan-500
    ];
    return colors[index % colors.length];
  };

  return (
    <div className="h-[600px] rounded-lg overflow-hidden border border-gray-300">
      <MapContainer
        center={center}
        zoom={8}
        style={{ height: '100%', width: '100%' }}
        className="z-0"
      >
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />

        <MapBounds segments={segments} />

        {/* Renderizar linhas para cada segmento */}
        {segments.map((segment, index) => {
          const positions: [number, number][] = [
            [segment.start_coordinates.latitude, segment.start_coordinates.longitude],
            [segment.end_coordinates.latitude, segment.end_coordinates.longitude]
          ];

          return (
            <React.Fragment key={segment.id}>
              {/* Linha do segmento */}
              <Polyline
                positions={positions}
                color={getSegmentColor(index)}
                weight={4}
                opacity={0.8}
              >
                <Popup>
                  <div className="text-sm">
                    <p className="font-bold">{segment.id}</p>
                    <p className="text-gray-600">{segment.name}</p>
                    <p className="mt-1">
                      Distância: {segment.start_distance_km.toFixed(2)} - {segment.end_distance_km.toFixed(2)} km
                    </p>
                    <p>Comprimento: {segment.length_km.toFixed(2)} km</p>
                  </div>
                </Popup>
              </Polyline>

              {/* Marcador no início do segmento */}
              <Marker
                position={positions[0]}
                icon={createNumberIcon(index + 1, true)}
              >
                <Popup>
                  <div className="text-sm">
                    <p className="font-bold text-green-600">Início: {segment.id}</p>
                    <p>KM {segment.start_distance_km.toFixed(2)}</p>
                    <p className="text-xs text-gray-500 mt-1">
                      ({segment.start_coordinates.latitude.toFixed(6)}, {segment.start_coordinates.longitude.toFixed(6)})
                    </p>
                  </div>
                </Popup>
              </Marker>

              {/* Marcador no fim do segmento */}
              <Marker
                position={positions[1]}
                icon={createNumberIcon(index + 1, false)}
              >
                <Popup>
                  <div className="text-sm">
                    <p className="font-bold text-red-600">Fim: {segment.id}</p>
                    <p>KM {segment.end_distance_km.toFixed(2)}</p>
                    <p className="text-xs text-gray-500 mt-1">
                      ({segment.end_coordinates.latitude.toFixed(6)}, {segment.end_coordinates.longitude.toFixed(6)})
                    </p>
                  </div>
                </Popup>
              </Marker>
            </React.Fragment>
          );
        })}
      </MapContainer>
    </div>
  );
}
