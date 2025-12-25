'use client';

import React, { useEffect, useState, useMemo, use } from 'react';
import dynamic from 'next/dynamic';
import { Button } from '@/components/ui/Button';
import { ArrowLeft, Loader2, MapPin, Navigation, Route } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import Link from 'next/link';
import { apiClient } from '@/lib/api';
import { RouteSearchResponse } from '@/lib/types';
import { useGeolocation } from '@/hooks/useGeolocation';

// Support both coordinate formats from API
interface CoordinatePoint {
  lat?: number;
  lon?: number;
  latitude?: number;
  longitude?: number;
}

// Dynamic import for Leaflet components (no SSR)
const RouteMapView = dynamic(() => import('./RouteMapView'), {
  ssr: false,
  loading: () => (
    <div className="h-full flex items-center justify-center bg-gray-100">
      <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
    </div>
  ),
});

interface PageProps {
  params: Promise<{ mapId: string }>;
}

export default function MapViewPage({ params }: PageProps) {
  const resolvedParams = use(params);
  const { mapId } = resolvedParams;

  const [routeData, setRouteData] = useState<RouteSearchResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Get user's current location
  const { position: userPosition } = useGeolocation();

  useEffect(() => {
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
  }, [mapId]);

  // Extract all coordinates from segments' geometry
  const routeCoordinates = useMemo((): CoordinatePoint[] => {
    if (!routeData?.segments) return [];

    const coords: CoordinatePoint[] = [];
    for (const segment of routeData.segments) {
      if (segment.geometry && segment.geometry.length > 0) {
        // Use full geometry - cast to CoordinatePoint to support both formats
        coords.push(...(segment.geometry as CoordinatePoint[]));
      } else if (segment.start_coordinates && segment.end_coordinates) {
        // Fallback to start/end coordinates
        coords.push(segment.start_coordinates as CoordinatePoint);
        coords.push(segment.end_coordinates as CoordinatePoint);
      }
    }
    return coords;
  }, [routeData]);

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <Loader2 className="h-8 w-8 animate-spin text-blue-600 mx-auto mb-4" />
          <p className="text-gray-600">Carregando mapa...</p>
        </div>
      </div>
    );
  }

  if (error || !routeData) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center p-4">
        <div className="text-center max-w-md">
          <div className="text-6xl mb-4">!</div>
          <h2 className="text-xl font-bold text-gray-900 mb-2">Erro ao carregar mapa</h2>
          <p className="text-sm text-gray-600 mb-4">{error || 'Mapa não encontrado'}</p>
          <Link href="/maps">
            <Button>
              <ArrowLeft className="h-4 w-4 mr-2" />
              Voltar aos Mapas
            </Button>
          </Link>
        </div>
      </div>
    );
  }

  const totalDistance = routeData.total_length_km ?? routeData.total_distance_km ?? 0;

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col">
      {/* Header */}
      <header className="sticky top-0 z-20 bg-white border-b border-gray-200 shadow-sm">
        <div className="max-w-6xl mx-auto px-4 py-3">
          <div className="flex items-center gap-3">
            <Link href="/maps" className="text-blue-600 hover:text-blue-700">
              <ArrowLeft className="h-5 w-5" />
            </Link>
            <div className="flex-1 min-w-0">
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
                  {routeCoordinates.length} pontos
                </span>
                {routeData.segments && (
                  <Badge variant="secondary" className="text-xs">
                    {routeData.segments.length} segmentos
                  </Badge>
                )}
              </div>
            </div>
            <Link href={`/map?mapId=${mapId}`}>
              <Button size="sm" variant="outline">
                <Navigation className="h-4 w-4 mr-1" />
                Mapa Linear
              </Button>
            </Link>
          </div>
        </div>
      </header>

      {/* Map Container */}
      <main className="flex-1 relative">
        {routeCoordinates.length > 0 ? (
          <RouteMapView
            coordinates={routeCoordinates}
            origin={routeData.origin}
            destination={routeData.destination}
            userPosition={userPosition ? { lat: userPosition.lat, lon: userPosition.lon } : undefined}
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
  );
}
