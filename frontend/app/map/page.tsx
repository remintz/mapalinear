'use client';

import React, { useState, useEffect, useMemo, Suspense } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import { Button, Card, CardContent } from '@/components/ui';
import { MapPin, Bug, Loader2, Menu, Download, X, Fuel, Utensils, Bed, Tent, Hospital, Ticket, Building2, Home, FileText, MapPinned, WifiOff } from 'lucide-react';
import Link from 'next/link';
import { toast } from 'sonner';
import { useSession } from 'next-auth/react';
import { POIFeed } from '@/components/ui/POIFeed';
import { POIFilters } from '@/components/ui/POIFilters';
import { SimulationControls } from '@/components/ui/SimulationControls';
import { apiClient } from '@/lib/api';
import { useRouteSimulation } from '@/hooks/useRouteSimulation';
import { useRouteTracking } from '@/hooks/useRouteTracking';
import { useGeolocation } from '@/hooks/useGeolocation';
import { useAdminSimulatedPosition } from '@/hooks/useAdminSimulatedPosition';
import { useAnalytics } from '@/hooks/useAnalytics';
import { EventType } from '@/lib/analytics-types';
import { RouteSegment, Milestone } from '@/lib/types';
import { ReportProblemButton } from '@/components/reports/ReportProblemButton';
import RouteMapModal from '@/components/RouteMapModal';
import { useOfflineMap } from '@/hooks/useOfflineMap';
import { useOfflineContext } from '@/components/providers/OfflineProvider';

interface RouteSearchResponse {
  origin: string;
  destination: string;
  total_distance_km: number;
  segments: RouteSegment[];
  pois: Milestone[];  // Using Milestone type since POIs come from milestones
  milestones: Milestone[];
}

const SIMULATE_USER_KEY = 'mapalinear_simulate_user';

function MapPageContent() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const { data: session } = useSession();
  const isActualAdmin = session?.user?.isAdmin ?? false;
  const { trackEvent, trackMapEvent, trackPageView, trackPerformance } = useAnalytics();

  // State for simulating regular user (set via Admin page)
  const [isSimulatingUser, setIsSimulatingUser] = useState(false);

  // Initialize from sessionStorage on mount
  useEffect(() => {
    const stored = sessionStorage.getItem(SIMULATE_USER_KEY);
    if (stored === 'true') {
      setIsSimulatingUser(true);
    }
  }, []);

  // Effective admin status (false when simulating user)
  const isAdmin = isActualAdmin && !isSimulatingUser;

  const mapId = searchParams.get('mapId');
  const operationId = searchParams.get('operationId');
  const { isOnline } = useOfflineContext();

  // Map loading: API when online, IndexedDB when offline
  const offlineMap = useOfflineMap(mapId);

  const [data, setData] = useState<RouteSearchResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [progressMessage, setProgressMessage] = useState<string>('Carregando mapa...');
  const [progressPercent, setProgressPercent] = useState<number>(0);
  const [isExporting, setIsExporting] = useState(false);
  const [isAdminMenuOpen, setIsAdminMenuOpen] = useState(false);
  const [osmMapOpen, setOsmMapOpen] = useState(false);

  // Active filters stored as a Set of filter IDs
  const [activeFilters, setActiveFilters] = useState<Set<string>>(
    new Set(['gas_station', 'restaurant', 'hotel', 'camping', 'hospital', 'toll_booth', 'city', 'town', 'village'])
  );

  // Sync offlineMap state into local state (for mapId loads)
  useEffect(() => {
    if (!mapId) return;
    // Don't override if operationId is being used
    if (operationId) return;

    if (offlineMap.isLoading) {
      setIsLoading(true);
      setProgressMessage('Carregando mapa salvo...');
      return;
    }

    if (offlineMap.error) {
      setError(offlineMap.error);
      setIsLoading(false);
      return;
    }

    if (offlineMap.data) {
      const routeData: RouteSearchResponse = {
        origin: offlineMap.data.origin,
        destination: offlineMap.data.destination,
        total_distance_km: offlineMap.data.total_distance_km,
        segments: offlineMap.data.segments,
        pois: offlineMap.data.milestones,
        milestones: offlineMap.data.milestones,
      };
      setData(routeData);
      setIsLoading(false);

      // Track map view
      trackPageView('/map');
      trackMapEvent('linear_map_view', {
        map_id: mapId,
        origin: offlineMap.data.origin,
        destination: offlineMap.data.destination,
        total_distance_km: offlineMap.data.total_distance_km,
        is_offline: !isOnline,
      });
    }
  }, [mapId, operationId, offlineMap.data, offlineMap.isLoading, offlineMap.error, isOnline, trackPageView, trackMapEvent]);

  // Monitor async operation if operationId is provided
  useEffect(() => {
    if (operationId && !mapId) {
      let pollingInterval: NodeJS.Timeout | null = null;

      const pollOperationStatus = async () => {
        try {
          const operation = await apiClient.getOperationStatus(operationId);

          // Update progress
          setProgressPercent(operation.progress_percent || 0);
          if (operation.progress_percent <= 30) {
            setProgressMessage('Consultando OpenStreetMap...');
          } else if (operation.progress_percent <= 60) {
            setProgressMessage('Processando rota...');
          } else if (operation.progress_percent <= 90) {
            setProgressMessage('Buscando pontos de interesse...');
          } else {
            setProgressMessage('Finalizando...');
          }

          // Check if completed
          if (operation.status === 'completed') {
            if (pollingInterval) {
              clearInterval(pollingInterval);
            }
            setIsLoading(false);
            setProgressMessage('Mapa criado');
            setProgressPercent(100);

            if (operation.result) {
              // Use milestones as the source of truth for POIs
              const milestones = operation.result.milestones || [];
              const routeData: RouteSearchResponse = {
                origin: operation.result.origin,
                destination: operation.result.destination,
                total_distance_km: operation.result.total_length_km || operation.result.total_distance_km || 0,
                segments: (operation.result.segments || []) as RouteSegment[],
                pois: milestones,
                milestones: milestones
              };
              setData(routeData);

              // Update URL to use mapId instead of operationId
              if (operation.result.id) {
                router.replace(`/map?mapId=${operation.result.id}`);
              }
            }
          } else if (operation.status === 'failed') {
            if (pollingInterval) {
              clearInterval(pollingInterval);
            }
            setIsLoading(false);
            setError(operation.error || 'Erro ao criar mapa');
            toast.error('Erro ao criar mapa');
          }
        } catch (error) {
          // apiClient handles 401 automatically and redirects to login
          console.error('Error polling operation:', error);
          if (pollingInterval) {
            clearInterval(pollingInterval);
          }
          setIsLoading(false);
          setError('Erro ao verificar status da operação');
          toast.error('Erro ao verificar status da operação');
        }
      };

      // Poll immediately and then every 2 seconds
      pollOperationStatus();
      pollingInterval = setInterval(pollOperationStatus, 2000);

      // Cleanup
      return () => {
        if (pollingInterval) {
          clearInterval(pollingInterval);
        }
      };
    }
  }, [operationId, mapId, router]);

  // Prepare filter options with counts
  const getFilterOptions = () => {
    if (!data?.pois) return [];

    const filters = [
      { id: 'gas_station', label: 'Postos', icon: Fuel },
      { id: 'restaurant', label: 'Restaurantes', icon: Utensils, includeTypes: ['restaurant', 'fast_food', 'cafe'] },
      { id: 'hotel', label: 'Hotéis', icon: Bed },
      { id: 'camping', label: 'Camping', icon: Tent },
      { id: 'hospital', label: 'Hospitais', icon: Hospital },
      { id: 'toll_booth', label: 'Pedágios', icon: Ticket },
      { id: 'city', label: 'Cidades', icon: Building2 },
      { id: 'town', label: 'Vilas', icon: Home },
      { id: 'village', label: 'Povoados', icon: Home },
    ];

    return filters.map(filter => ({
      ...filter,
      count: data.pois.filter(poi =>
        filter.includeTypes
          ? filter.includeTypes.includes(poi.type)
          : poi.type === filter.id
      ).length
    }));
  };

  // Filter POIs based on active filters
  const getFilteredPOIs = () => {
    if (!data?.pois) return [];

    return data.pois.filter((poi) => {
      // Check restaurants (includes multiple types)
      if (['restaurant', 'fast_food', 'cafe'].includes(poi.type)) {
        return activeFilters.has('restaurant');
      }
      // Check other types
      return activeFilters.has(poi.type);
    });
  };

  // Toggle filter
  const handleFilterToggle = (filterId: string) => {
    setActiveFilters(prev => {
      const newFilters = new Set(prev);
      if (newFilters.has(filterId)) {
        newFilters.delete(filterId);
      } else {
        newFilters.add(filterId);
      }
      return newFilters;
    });
  };

  const filterOptions = getFilterOptions();
  const filteredPOIs = getFilteredPOIs();

  // Route simulation hook
  const simulation = useRouteSimulation({
    segments: data?.segments || [],
    totalDistanceKm: data?.total_distance_km || 0,
    initialSpeedKmH: 80,
  });

  // Admin simulated position hook (set via OSM map click)
  const adminSimulatedPos = useAdminSimulatedPosition();

  // Real GPS hook (used when simulation is not active)
  const geoLocation = useGeolocation({
    simulatedPosition: simulation.state.isActive ? simulation.state.position : null,
  });

  // Determine current position (admin simulated > route simulation > real GPS)
  const currentPosition = useMemo(() => {
    // Priority 1: Admin simulated position (set via OSM map)
    if (adminSimulatedPos.isActive && adminSimulatedPos.position) {
      return { lat: adminSimulatedPos.position.lat, lon: adminSimulatedPos.position.lon };
    }
    // Priority 2: Route simulation
    if (simulation.state.isActive && simulation.state.position) {
      return simulation.state.position;
    }
    // Priority 3: Real GPS
    if (geoLocation.position) {
      return { lat: geoLocation.position.lat, lon: geoLocation.position.lon };
    }
    return null;
  }, [
    adminSimulatedPos.isActive,
    adminSimulatedPos.position,
    simulation.state.isActive,
    simulation.state.position,
    geoLocation.position,
  ]);

  // Route tracking hook
  // Using 1500m threshold because segments are linearized (~1km segments)
  // In curves, the real road can be far from the straight line between points
  const tracking = useRouteTracking({
    userPosition: currentPosition,
    segments: data?.segments || [],
    pois: filteredPOIs,
    onRouteThreshold: 1500, // 1.5km threshold for linearized segments
  });

  // Download files function
  const downloadFile = async (format: 'geojson' | 'gpx', routeData: RouteSearchResponse) => {
    setIsExporting(true);
    try {
      // Convert segments to ExportSegment format (ensure geometry is defined)
      const exportSegments = (routeData.segments || [])
        .filter(seg => seg.geometry && seg.geometry.length > 0)
        .map(seg => ({
          id: seg.id,
          name: seg.name,
          geometry: seg.geometry!,
          length_km: seg.length_km || seg.distance_km || 0
        }));

      // Convert POIs to ExportPOI format
      const exportPOIs = filteredPOIs.map(poi => ({
        id: poi.id,
        name: poi.name,
        type: poi.type,
        coordinates: poi.coordinates,
        distance_from_origin_km: poi.distance_from_origin_km,
        city: poi.city,
        brand: poi.brand,
        operator: poi.operator,
        opening_hours: poi.opening_hours
      }));

      const exportData = {
        origin: routeData.origin,
        destination: routeData.destination,
        total_distance_km: routeData.total_distance_km,
        segments: exportSegments,
        pois: exportPOIs
      };

      const blob = format === 'geojson'
        ? await apiClient.exportRouteAsGeoJSON(exportData)
        : await apiClient.exportRouteAsGPX(exportData);

      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;

      const filename = `rota_${routeData.origin.replace(/[^a-zA-Z0-9]/g, '_')}_${routeData.destination.replace(/[^a-zA-Z0-9]/g, '_')}.${format}`;

      a.download = filename;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);

      // Track export
      trackMapEvent(format === 'geojson' ? 'map_export_geojson' : 'map_export_gpx', {
        map_id: mapId,
        format,
      });
    } catch (error) {
      // apiClient handles 401 automatically and redirects to login
      console.error('Erro ao exportar:', error);
      toast.error(`Erro ao exportar ${format.toUpperCase()}`);
    } finally {
      setIsExporting(false);
    }
  };

  // Download PDF function - uses direct endpoint with mapId
  const downloadPDF = async () => {
    if (!mapId) {
      toast.error('Mapa não está salvo. Salve o mapa primeiro.');
      return;
    }

    setIsExporting(true);
    try {
      // Build types filter from active filters
      const typesParam = Array.from(activeFilters).join(',');

      const blob = await apiClient.exportMapToPDF(mapId, typesParam || undefined);
      const blobUrl = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = blobUrl;

      const filename = `pois_mapa.pdf`;

      a.download = filename;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(blobUrl);
      document.body.removeChild(a);

      // Track PDF export
      trackMapEvent(EventType.MAP_EXPORT_PDF, { map_id: mapId });
    } catch (error) {
      // apiClient handles 401 automatically and redirects to login
      console.error('Erro ao exportar PDF:', error);
      toast.error('Erro ao exportar PDF');
    } finally {
      setIsExporting(false);
    }
  };

  // Open web tools function
  const openWebTool = async (tool: 'umap' | 'overpass', routeData: RouteSearchResponse) => {
    try {
      // Convert segments to ExportSegment format
      const exportSegments = (routeData.segments || [])
        .filter(seg => seg.geometry && seg.geometry.length > 0)
        .map(seg => ({
          id: seg.id,
          name: seg.name,
          geometry: seg.geometry!,
          length_km: seg.length_km || seg.distance_km || 0
        }));

      // Convert POIs to ExportPOI format
      const exportPOIs = (routeData.pois || []).map(poi => ({
        id: poi.id,
        name: poi.name,
        type: poi.type,
        coordinates: poi.coordinates,
        distance_from_origin_km: poi.distance_from_origin_km,
        city: poi.city,
        brand: poi.brand,
        operator: poi.operator,
        opening_hours: poi.opening_hours
      }));

      const exportData = {
        origin: routeData.origin,
        destination: routeData.destination,
        total_distance_km: routeData.total_distance_km,
        segments: exportSegments,
        pois: exportPOIs
      };

      const urlData = await apiClient.getWebVisualizationURLs(exportData);
      const url = tool === 'umap' ? urlData.umap_url : urlData.overpass_turbo_url;

      window.open(url, '_blank');

      if (tool === 'umap') {
        toast.info('uMap aberto! Clique em "Importar dados" e carregue o arquivo GeoJSON baixado');
      } else {
        toast.info('Overpass Turbo aberto! Veja os pontos de interesse existentes na região da rota');
      }
    } catch (error) {
      // apiClient handles 401 automatically and redirects to login
      console.error('Erro ao abrir ferramenta web:', error);
      toast.error('Erro ao abrir ferramenta web');
    }
  };

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100">
        <div className="container mx-auto px-4 py-8">
          <div className="max-w-2xl mx-auto">
            <Card>
              <CardContent className="py-12">
                <div className="text-center space-y-4">
                  <Loader2 className="h-12 w-12 animate-spin text-blue-600 mx-auto" />
                  <div>
                    <p className="text-lg font-semibold text-gray-900">{progressMessage}</p>
                    {progressPercent > 0 && (
                      <div className="mt-4">
                        <div className="w-full bg-gray-200 rounded-full h-2">
                          <div
                            className="bg-blue-600 h-2 rounded-full transition-all duration-300"
                            style={{ width: `${progressPercent}%` }}
                          />
                        </div>
                        <p className="text-sm text-gray-600 mt-2">{Math.round(progressPercent)}%</p>
                      </div>
                    )}
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100">
        <div className="container mx-auto px-4 py-8">
          <div className="max-w-2xl mx-auto">
            <Card>
              <CardContent className="py-12">
                <div className="text-center space-y-4">
                  <div className="text-red-600">
                    <svg className="h-12 w-12 mx-auto" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                  </div>
                  <div>
                    <p className="text-lg font-semibold text-gray-900">Erro ao carregar mapa</p>
                    <p className="text-sm text-gray-600 mt-2">{error}</p>
                  </div>
                  <Button onClick={() => router.push('/search')}>
                    Criar Novo Mapa
                  </Button>
                </div>
              </CardContent>
            </Card>
          </div>
        </div>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100">
        <div className="container mx-auto px-4 py-8">
          <div className="max-w-2xl mx-auto">
            <Card>
              <CardContent className="py-12">
                <div className="text-center space-y-4">
                  <MapPin className="h-12 w-12 text-gray-400 mx-auto" />
                  <div>
                    <p className="text-lg font-semibold text-gray-900">Nenhum mapa para exibir</p>
                    <p className="text-sm text-gray-600 mt-2">Crie um novo mapa ou abra um mapa salvo</p>
                  </div>
                  <div className="flex gap-3 justify-center">
                    <Button onClick={() => router.push('/search')}>
                      Criar Novo Mapa
                    </Button>
                    <Button variant="outline" onClick={() => router.push('/maps')}>
                      Meus Mapas
                    </Button>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header - Responsive */}
      <header className="sticky top-0 z-20 bg-white border-b border-gray-200 shadow-sm">
        <div className="max-w-7xl mx-auto px-4 py-3">
          <div className="flex items-center justify-between">
            <div className="flex-1 min-w-0">
              <p className="text-sm text-gray-500">Rota</p>
              <p className="text-base font-semibold text-gray-900 truncate">
                {data.origin} → {data.destination}
              </p>
            </div>
            <div className="flex items-center gap-2 ml-4">
              <span className="text-sm font-medium text-zinc-900 bg-zinc-100 px-3 py-1 rounded-full whitespace-nowrap">
                {data.total_distance_km ? data.total_distance_km.toFixed(1) : '0.0'} km
              </span>
              {/* Offline indicator */}
              {!isOnline && (
                <span className="flex items-center gap-1 text-xs text-amber-600 bg-amber-50 px-2 py-1 rounded-full">
                  <WifiOff className="h-3 w-3" />
                  <span className="hidden sm:inline">offline</span>
                </span>
              )}
              {/* View Route on Map Button (needs network for tiles) */}
              {mapId && isOnline && (
                <button
                  onClick={() => {
                    setOsmMapOpen(true);
                    trackEvent(EventType.OSM_MAP_VIEW, { map_id: mapId });
                  }}
                  className="flex items-center gap-1.5 text-sm text-gray-600 hover:text-gray-900 px-3 py-1.5 rounded-lg hover:bg-gray-100 transition-colors border border-gray-200"
                  title="Ver rota no mapa"
                >
                  <MapPinned className="h-4 w-4" />
                  <span className="hidden sm:inline">Mapa</span>
                </button>
              )}
              {/* PDF Export Button (needs network) */}
              {isOnline && (
                <button
                  onClick={() => downloadPDF()}
                  disabled={isExporting || !mapId}
                  className="flex items-center gap-1.5 text-sm text-gray-600 hover:text-gray-900 px-3 py-1.5 rounded-lg hover:bg-gray-100 transition-colors border border-gray-200 disabled:opacity-50 disabled:cursor-not-allowed"
                  title={mapId ? "Exportar PDF" : "Salve o mapa para exportar PDF"}
                >
                  {isExporting ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    <FileText className="h-4 w-4" />
                  )}
                  <span className="hidden sm:inline">PDF</span>
                </button>
              )}
              {/* Desktop: Show options button in header (admin only) */}
              {isAdmin && (
                <button
                  onClick={() => setIsAdminMenuOpen(true)}
                  className="hidden lg:flex items-center gap-2 text-sm text-gray-600 hover:text-gray-900 px-3 py-1 rounded-lg hover:bg-gray-100 transition-colors"
                >
                  <Menu className="h-4 w-4" />
                  <span>Opções</span>
                </button>
              )}
            </div>
          </div>
        </div>
      </header>

      {/* Main Content - Responsive Layout */}
      <main className="max-w-7xl mx-auto px-4 py-4">
        {/* Desktop: Two columns layout */}
        <div className="lg:flex lg:gap-8">
          {/* Sidebar - Filters (Desktop: fixed left column) */}
          <aside className="lg:w-64 lg:flex-shrink-0">
            {/* POI Filters - Horizontal on mobile, vertical on desktop */}
            <div className="lg:sticky lg:top-20">
              <POIFilters
                filters={filterOptions}
                activeFilters={activeFilters}
                onFilterToggle={handleFilterToggle}
              />
            </div>
          </aside>

          {/* Content - POI Feed */}
          <div className="flex-1 lg:max-w-3xl">
            {/* Admin Simulated Position Banner */}
            {adminSimulatedPos.isActive && adminSimulatedPos.position && (
              <div className="mb-4 p-3 bg-amber-50 border border-amber-200 rounded-lg">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <div className="w-3 h-3 bg-amber-500 rounded-full animate-pulse" />
                    <div>
                      <p className="text-sm font-medium text-amber-800">
                        Posição Simulada (Admin)
                      </p>
                      <p className="text-xs text-amber-600">
                        {adminSimulatedPos.position.lat.toFixed(6)}, {adminSimulatedPos.position.lon.toFixed(6)}
                      </p>
                    </div>
                  </div>
                  <button
                    onClick={() => adminSimulatedPos.clearPosition()}
                    className="text-xs text-amber-700 hover:text-amber-900 underline"
                  >
                    Limpar
                  </button>
                </div>
              </div>
            )}

            {/* Simulation Controls - Only visible for admins */}
            {isAdmin && (
              <div className="mb-4">
                <SimulationControls
                  state={simulation.state}
                  controls={simulation.controls}
                  isOnRoute={tracking.isOnRoute}
                  distanceToRoute={tracking.distanceToRoute}
                  mapId={mapId || undefined}
                />
              </div>
            )}

            {/* POI Feed with tracking bar between passed and upcoming POIs */}
            <POIFeed
              pois={filteredPOIs}
              emptyMessage="Nenhum ponto de interesse com as categorias selecionadas"
              isPOIPassed={tracking.isPOIPassed}
              nextPOIIndex={tracking.nextPOIIndex}
              autoScroll={simulation.state.isActive || tracking.isOnRoute}
              trackingInfo={{
                isOnRoute: tracking.isOnRoute,
                distanceTraveled: tracking.distanceTraveled,
                distanceToRoute: tracking.distanceToRoute,
                nextPOI: tracking.nextPOI,
              }}
              locationInfo={{
                error: geoLocation.error,
                isLoading: geoLocation.isLoading,
                isSupported: geoLocation.isSupported,
                requestPermission: geoLocation.requestPermission,
              }}
            />

            {/* Debug Link - Mobile only (admin only) */}
            {isAdmin && (
              <div className="mt-8 pb-8 text-center lg:hidden">
                <button
                  onClick={() => setIsAdminMenuOpen(true)}
                  className="text-xs text-gray-400 hover:text-gray-600 underline"
                >
                  Opções avançadas
                </button>
              </div>
            )}
          </div>
        </div>
      </main>

      {/* Report Problem Button (needs network) */}
      {isOnline && <ReportProblemButton
        mapId={mapId || undefined}
        pois={filteredPOIs.map(poi => ({
          id: poi.id || String(Math.random()),
          name: poi.name || poi.type,
          type: poi.type,
          distance_from_origin_km: poi.distance_from_origin_km,
        }))}
        userLocation={currentPosition ? { lat: currentPosition.lat, lon: currentPosition.lon } : undefined}
      />}

      {/* Admin/Debug Slide-out Menu */}
      {isAdminMenuOpen && (
        <>
          {/* Backdrop */}
          <div
            className="fixed inset-0 bg-black bg-opacity-50 z-30"
            onClick={() => setIsAdminMenuOpen(false)}
          />

          {/* Slide-out Panel */}
          <div className="fixed top-0 right-0 bottom-0 w-full max-w-md bg-white shadow-xl z-40 overflow-y-auto">
            <div className="p-4">
              {/* Header */}
              <div className="flex items-center justify-between mb-6">
                <h2 className="text-xl font-bold text-gray-900">Opções Avançadas</h2>
                <button
                  onClick={() => setIsAdminMenuOpen(false)}
                  className="p-2 hover:bg-gray-100 rounded-full transition-colors"
                >
                  <X className="h-6 w-6 text-gray-600" />
                </button>
              </div>

              {/* Export Section */}
              <div className="mb-6">
                <h3 className="text-lg font-semibold text-gray-900 mb-3 flex items-center gap-2">
                  <Download className="h-5 w-5" />
                  Exportar Dados
                </h3>
                <div className="space-y-2">
                  <Button
                    onClick={() => {
                      downloadFile('geojson', data);
                      setIsAdminMenuOpen(false);
                    }}
                    disabled={isExporting}
                    className="w-full justify-start"
                    variant="outline"
                  >
                    <svg className="h-4 w-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                    </svg>
                    GeoJSON (uMap, QGIS)
                  </Button>
                  <Button
                    onClick={() => {
                      downloadFile('gpx', data);
                      setIsAdminMenuOpen(false);
                    }}
                    disabled={isExporting}
                    className="w-full justify-start"
                    variant="outline"
                  >
                    <svg className="h-4 w-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 20l-5.447-2.724A1 1 0 013 16.382V5.618a1 1 0 011.447-.894L9 7m0 13l6-3m-6 3V7m6 10l4.553 2.276A1 1 0 0021 18.382V7.618a1 1 0 00-.553-.894L15 4m0 13V4m0 0L9 7" />
                    </svg>
                    GPX (GPS, apps)
                  </Button>
                </div>
              </div>

              {/* Web Tools Section */}
              <div className="mb-6">
                <h3 className="text-lg font-semibold text-gray-900 mb-3">Ferramentas Web</h3>
                <div className="space-y-2">
                  <Button
                    onClick={() => {
                      openWebTool('umap', data);
                      setIsAdminMenuOpen(false);
                    }}
                    className="w-full justify-start"
                    variant="outline"
                  >
                    <svg className="h-4 w-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                    </svg>
                    Visualizar no uMap
                  </Button>
                  <Button
                    onClick={() => {
                      openWebTool('overpass', data);
                      setIsAdminMenuOpen(false);
                    }}
                    className="w-full justify-start"
                    variant="outline"
                  >
                    <svg className="h-4 w-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                    </svg>
                    Validar no Overpass Turbo
                  </Button>
                </div>
              </div>

              {/* Debug Section */}
              <div className="mb-6 pt-6 border-t border-gray-200">
                <h3 className="text-lg font-semibold text-gray-900 mb-3 flex items-center gap-2">
                  <Bug className="h-5 w-5" />
                  Debug
                </h3>
                <Link href="/debug-segments">
                  <Button
                    variant="outline"
                    className="w-full justify-start"
                    onClick={() => setIsAdminMenuOpen(false)}
                  >
                    <Bug className="h-4 w-4 mr-2" />
                    Ver Segmentos da Rota
                  </Button>
                </Link>
              </div>

              {/* Info Box */}
              <div className="mt-6 p-4 bg-blue-50 rounded-lg">
                <h4 className="font-medium text-blue-800 mb-2 text-sm">Dicas de Uso:</h4>
                <ul className="text-xs text-blue-700 space-y-1">
                  <li>• <strong>GeoJSON:</strong> Importar no uMap para visualização interativa</li>
                  <li>• <strong>GPX:</strong> Usar em apps de navegação GPS</li>
                </ul>
              </div>
            </div>
          </div>
        </>
      )}

      {/* OSM Map Modal */}
      {mapId && (
        <RouteMapModal
          mapId={mapId}
          isOpen={osmMapOpen}
          onClose={() => setOsmMapOpen(false)}
          filteredPOIs={filteredPOIs}
          isAdmin={isAdmin}
        />
      )}
    </div>
  );
}

export default function MapPage() {
  return (
    <Suspense fallback={
      <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 flex items-center justify-center">
        <div className="text-center">
          <Loader2 className="h-12 w-12 animate-spin text-blue-600 mx-auto" />
          <p className="mt-4 text-gray-600">Carregando...</p>
        </div>
      </div>
    }>
      <MapPageContent />
    </Suspense>
  );
}
