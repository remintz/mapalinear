'use client';

import React, { useEffect, useState, useMemo } from 'react';
import dynamic from 'next/dynamic';
import { X, Loader2, MapPin, Route, Calendar } from 'lucide-react';
import { Button } from '@/components/ui/Button';
import { apiClient } from '@/lib/api';
import { RouteSearchResponse, POI, Milestone } from '@/lib/types';
import { useGeolocation } from '@/hooks/useGeolocation';

// Support both coordinate formats from API
interface CoordinatePoint {
  lat?: number;
  lon?: number;
  latitude?: number;
  longitude?: number;
}

// Dynamic import for Leaflet components (no SSR)
const RouteMapView = dynamic(() => import('@/app/map/view/[mapId]/RouteMapView'), {
  ssr: false,
  loading: () => (
    <div className="h-full flex items-center justify-center bg-gray-100">
      <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
    </div>
  ),
});

interface RouteMapModalProps {
  mapId: string;
  isOpen: boolean;
  onClose: () => void;
  filteredPOIs?: (POI | Milestone)[];
}

export default function RouteMapModal({ mapId, isOpen, onClose, filteredPOIs }: RouteMapModalProps) {
  const [routeData, setRouteData] = useState<RouteSearchResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Get user's current location
  const { position: userPosition } = useGeolocation();

  useEffect(() => {
    if (!isOpen || !mapId) return;

    async function loadMap() {
      try {
        setLoading(true);
        setError(null);
        const data = await apiClient.getMap(mapId);
        setRouteData(data);
      } catch (err) {
        console.error('Error loading map:', err);
        setError(err instanceof Error ? err.message : 'Erro ao carregar o mapa');
      } finally {
        setLoading(false);
      }
    }
    loadMap();
  }, [mapId, isOpen]);

  // Close on Escape key
  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onClose();
      }
    };

    if (isOpen) {
      document.addEventListener('keydown', handleEscape);
      // Prevent body scroll when modal is open
      document.body.style.overflow = 'hidden';
    }

    return () => {
      document.removeEventListener('keydown', handleEscape);
      document.body.style.overflow = 'unset';
    };
  }, [isOpen, onClose]);

  // Extract all coordinates from segments' geometry
  const routeCoordinates = useMemo((): CoordinatePoint[] => {
    if (!routeData?.segments) return [];

    const coords: CoordinatePoint[] = [];
    for (const segment of routeData.segments) {
      if (segment.geometry && segment.geometry.length > 0) {
        coords.push(...(segment.geometry as CoordinatePoint[]));
      } else if (segment.start_coordinates && segment.end_coordinates) {
        coords.push(segment.start_coordinates as CoordinatePoint);
        coords.push(segment.end_coordinates as CoordinatePoint);
      }
    }
    return coords;
  }, [routeData]);

  if (!isOpen) return null;

  const totalDistance = routeData?.total_length_km ?? routeData?.total_distance_km ?? 0;

  return (
    <div className="fixed inset-0 z-50 bg-black bg-opacity-50">
      <div className="fixed inset-0 bg-white flex flex-col">
        {/* Header */}
        <header className="sticky top-0 z-20 bg-white border-b border-gray-200 shadow-sm">
          <div className="max-w-6xl mx-auto px-4 py-3">
            <div className="flex items-center gap-3">
              <div className="flex-1 min-w-0">
                {loading ? (
                  <div className="flex items-center gap-2">
                    <Loader2 className="h-4 w-4 animate-spin text-blue-600" />
                    <span className="text-gray-600">Carregando...</span>
                  </div>
                ) : routeData ? (
                  <>
                    <h1 className="text-lg font-bold text-gray-900 truncate">
                      {routeData.origin} → {routeData.destination}
                    </h1>
                    <div className="flex flex-wrap items-center gap-2 text-xs text-gray-600">
                      <span className="flex items-center gap-1">
                        <Route className="h-3 w-3" />
                        {totalDistance.toFixed(1)} km
                      </span>
                      <span className="flex items-center gap-1">
                        <MapPin className="h-3 w-3" />
                        {filteredPOIs?.length ?? 0} POIs
                      </span>
                      {(routeData.created_at || routeData.creation_date) && (
                        <span className="flex items-center gap-1">
                          <Calendar className="h-3 w-3" />
                          {new Date(routeData.created_at || routeData.creation_date || '').toLocaleDateString('pt-BR')}
                        </span>
                      )}
                    </div>
                  </>
                ) : (
                  <span className="text-gray-600">Mapa OSM</span>
                )}
              </div>
              <button
                onClick={onClose}
                className="p-2 hover:bg-gray-100 rounded-full transition-colors"
                aria-label="Fechar"
              >
                <X className="h-6 w-6 text-gray-600" />
              </button>
            </div>
          </div>
        </header>

        {/* Map Container */}
        <main className="flex-1 relative">
          {loading ? (
            <div className="h-full flex items-center justify-center bg-gray-100">
              <div className="text-center">
                <Loader2 className="h-8 w-8 animate-spin text-blue-600 mx-auto mb-4" />
                <p className="text-gray-600">Carregando mapa...</p>
              </div>
            </div>
          ) : error || !routeData ? (
            <div className="h-full flex items-center justify-center bg-gray-100 p-4">
              <div className="text-center max-w-md">
                <div className="text-6xl mb-4">!</div>
                <h2 className="text-xl font-bold text-gray-900 mb-2">Erro ao carregar mapa</h2>
                <p className="text-sm text-gray-600 mb-4">{error || 'Mapa não encontrado'}</p>
                <Button onClick={onClose}>Fechar</Button>
              </div>
            </div>
          ) : routeCoordinates.length > 0 ? (
            <RouteMapView
              coordinates={routeCoordinates}
              origin={routeData.origin}
              destination={routeData.destination}
              userPosition={userPosition ? { lat: userPosition.lat, lon: userPosition.lon } : undefined}
              pois={filteredPOIs}
            />
          ) : (
            <div className="h-full flex items-center justify-center bg-gray-100">
              <div className="text-center">
                <MapPin className="h-12 w-12 text-gray-400 mx-auto mb-4" />
                <p className="text-gray-600">Sem dados de rota disponíveis</p>
              </div>
            </div>
          )}
        </main>
      </div>
    </div>
  );
}
