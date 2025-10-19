'use client';

import React, { useState, useEffect } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import { Button, Card, CardContent } from '@/components/ui';
import { MapPin, ArrowLeft, Bug, Loader2, Menu, Download, X } from 'lucide-react';
import Link from 'next/link';
import { toast } from 'sonner';
import { POIFeed } from '@/components/ui/POIFeed';
import { POIFilters } from '@/components/ui/POIFilters';

interface RouteSearchResponse {
  origin: string;
  destination: string;
  total_distance_km: number;
  segments: any[];
  pois: any[];
  milestones: any[];
}

export default function MapPage() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const mapId = searchParams.get('mapId');
  const operationId = searchParams.get('operationId');

  const [isLoading, setIsLoading] = useState(true);
  const [data, setData] = useState<RouteSearchResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [progressMessage, setProgressMessage] = useState<string>('Carregando mapa...');
  const [progressPercent, setProgressPercent] = useState<number>(0);
  const [isExporting, setIsExporting] = useState(false);
  const [isAdminMenuOpen, setIsAdminMenuOpen] = useState(false);

  // Active filters stored as a Set of filter IDs
  const [activeFilters, setActiveFilters] = useState<Set<string>>(
    new Set(['gas_station', 'restaurant', 'camping', 'toll_booth', 'city', 'town', 'village'])
  );

  const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001/api';

  // Load saved map if mapId is provided
  useEffect(() => {
    if (mapId) {
      const loadSavedMap = async () => {
        try {
          setIsLoading(true);
          setProgressMessage('Carregando mapa salvo...');

          const response = await fetch(`${API_URL}/maps/${mapId}`);

          if (!response.ok) {
            throw new Error('Erro ao carregar mapa salvo');
          }

          const savedMap = await response.json();

          // Transform saved map data to match RouteSearchResponse format
          const routeData = {
            origin: savedMap.origin,
            destination: savedMap.destination,
            total_distance_km: savedMap.total_length_km,
            segments: savedMap.segments || [],
            pois: savedMap.milestones || [],
            milestones: savedMap.milestones || []
          };

          setData(routeData);
          setIsLoading(false);
          toast.success('Mapa carregado com sucesso!');
        } catch (error) {
          console.error('Error loading saved map:', error);
          setError('Erro ao carregar mapa salvo');
          setIsLoading(false);
          toast.error('Erro ao carregar mapa salvo');
        }
      };

      loadSavedMap();
    }
  }, [mapId, API_URL]);

  // Monitor async operation if operationId is provided
  useEffect(() => {
    if (operationId && !mapId) {
      let pollingInterval: NodeJS.Timeout | null = null;

      const pollOperationStatus = async () => {
        try {
          const response = await fetch(`${API_URL}/operations/${operationId}`);

          if (!response.ok) {
            throw new Error('Erro ao verificar status da operação');
          }

          const operation = await response.json();

          // Update progress
          if (operation.progress) {
            setProgressMessage(operation.progress.message || 'Processando...');
            setProgressPercent(operation.progress.percentage || 0);
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
              const routeData = {
                id: operation.result.id,
                origin: operation.result.origin,
                destination: operation.result.destination,
                total_distance_km: operation.result.total_length_km || operation.result.total_distance_km,
                segments: operation.result.segments || [],
                pois: operation.result.milestones || operation.result.pois || [],
                milestones: operation.result.milestones || []
              };
              setData(routeData);
              toast.success('Mapa criado com sucesso!');

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
  }, [operationId, mapId, API_URL]);

  // Prepare filter options with counts
  const getFilterOptions = () => {
    if (!data?.pois) return [];

    const filters = [
      { id: 'gas_station', label: 'Postos', emoji: '⛽' },
      { id: 'restaurant', label: 'Restaurantes', emoji: '🍽️', includeTypes: ['restaurant', 'fast_food', 'cafe'] },
      { id: 'hotel', label: 'Hotéis', emoji: '🏨' },
      { id: 'camping', label: 'Camping', emoji: '⛺' },
      { id: 'hospital', label: 'Hospitais', emoji: '🏥' },
      { id: 'toll_booth', label: 'Pedágios', emoji: '🛣️' },
      { id: 'city', label: 'Cidades', emoji: '🏙️' },
      { id: 'town', label: 'Vilas', emoji: '🏘️' },
      { id: 'village', label: 'Povoados', emoji: '🏡' },
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

  // Download files function
  const downloadFile = async (format: 'geojson' | 'gpx', routeData: any) => {
    setIsExporting(true);
    try {
      const response = await fetch(`${API_URL}/export/${format}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          origin: routeData.origin,
          destination: routeData.destination,
          total_distance_km: routeData.total_distance_km,
          segments: routeData.segments || [],
          pois: filteredPOIs
        }),
      });

      if (!response.ok) {
        throw new Error(`Erro ao exportar ${format.toUpperCase()}`);
      }

      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;

      const contentDisposition = response.headers.get('Content-Disposition');
      const filename = contentDisposition
        ? contentDisposition.split('filename=')[1]?.replace(/"/g, '')
        : `rota_${routeData.origin.replace(/[^a-zA-Z0-9]/g, '_')}_${routeData.destination.replace(/[^a-zA-Z0-9]/g, '_')}.${format}`;

      a.download = filename;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);

      toast.success(`Arquivo ${format.toUpperCase()} baixado com sucesso!`);
    } catch (error) {
      console.error('Erro ao exportar:', error);
      toast.error(`Erro ao exportar ${format.toUpperCase()}`);
    } finally {
      setIsExporting(false);
    }
  };

  // Download PDF function
  const downloadPDF = async (routeData: any) => {
    setIsExporting(true);
    try {
      // Get active filter types
      const activeFilters: string[] = [];
      if (poiFilters.includeGasStations) activeFilters.push('gas_station');
      if (poiFilters.includeRestaurants) activeFilters.push('restaurant', 'fast_food', 'cafe');
      if (poiFilters.includeHotels) activeFilters.push('hotel');
      if (poiFilters.includeCamping) activeFilters.push('camping');
      if (poiFilters.includeHospitals) activeFilters.push('hospital');
      if (poiFilters.includeTollBooths) activeFilters.push('toll_booth');
      if (poiFilters.includeCities) activeFilters.push('city');
      if (poiFilters.includeTowns) activeFilters.push('town');
      if (poiFilters.includeVillages) activeFilters.push('village');

      const response = await fetch(`${API_URL}/export/pdf`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          origin: routeData.origin,
          destination: routeData.destination,
          total_distance_km: routeData.total_distance_km,
          segments: routeData.segments || [],
          pois: filteredPOIs
        }),
      });

      if (!response.ok) {
        throw new Error('Erro ao exportar PDF');
      }

      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;

      const contentDisposition = response.headers.get('Content-Disposition');
      const filename = contentDisposition
        ? contentDisposition.split('filename=')[1]?.replace(/"/g, '')
        : `pois_${routeData.origin.replace(/[^a-zA-Z0-9]/g, '_')}_${routeData.destination.replace(/[^a-zA-Z0-9]/g, '_')}.pdf`;

      a.download = filename;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);

      toast.success('PDF baixado com sucesso!');
    } catch (error) {
      console.error('Erro ao exportar PDF:', error);
      toast.error('Erro ao exportar PDF');
    } finally {
      setIsExporting(false);
    }
  };

  // Open web tools function
  const openWebTool = async (tool: 'umap' | 'overpass', routeData: any) => {
    try {
      const response = await fetch(`${API_URL}/export/web-urls`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          origin: routeData.origin,
          destination: routeData.destination,
          total_distance_km: routeData.total_distance_km,
          segments: routeData.segments || [],
          pois: routeData.pois || []
        }),
      });

      if (!response.ok) {
        throw new Error('Erro ao gerar URLs');
      }

      const urlData = await response.json();
      const url = tool === 'umap' ? urlData.umap_url : urlData.overpass_turbo_url;

      window.open(url, '_blank');

      if (tool === 'umap') {
        toast.info('uMap aberto! Clique em "Importar dados" e carregue o arquivo GeoJSON baixado');
      } else {
        toast.info('Overpass Turbo aberto! Veja os POIs existentes na região da rota');
      }
    } catch (error) {
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
                        <p className="text-sm text-gray-600 mt-2">{progressPercent}%</p>
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
                      Mapas Salvos
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
      {/* Mobile-First Header - Sticky */}
      <header className="sticky top-0 z-20 bg-white border-b border-gray-200 shadow-sm">
        <div className="px-4 py-3">
          <div className="flex items-center justify-between mb-2">
            <Link
              href="/search"
              className="inline-flex items-center gap-1 text-blue-600 hover:text-blue-700 text-sm font-medium"
            >
              <ArrowLeft className="h-4 w-4" />
              Novo Mapa
            </Link>
            <button
              onClick={() => setIsAdminMenuOpen(true)}
              className="inline-flex items-center gap-1 text-gray-600 hover:text-gray-800 text-sm font-medium"
            >
              <Menu className="h-5 w-5" />
              Menu
            </button>
          </div>
          <div>
            <p className="text-sm text-gray-500">Rota</p>
            <p className="text-base font-semibold text-gray-900 truncate">
              {data.origin} → {data.destination}
            </p>
          </div>
        </div>
      </header>

      {/* Main Content - POI Feed */}
      <main className="px-4 py-4">
        {/* Route Summary Card */}
        <div className="mb-4 p-4 bg-white rounded-lg shadow-sm border border-gray-200">
          <div className="flex items-center justify-between text-sm">
            <span className="text-gray-600">Distância Total</span>
            <span className="font-bold text-blue-600 text-lg">
              {data.total_distance_km ? data.total_distance_km.toFixed(1) : '0.0'} km
            </span>
          </div>
        </div>

        {/* POI Filters */}
        <POIFilters
          filters={filterOptions}
          activeFilters={activeFilters}
          onFilterToggle={handleFilterToggle}
        />

        {/* POI Feed */}
        <POIFeed
          pois={filteredPOIs}
          emptyMessage="Nenhum POI encontrado com os filtros selecionados"
        />
      </main>

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
                  <Button
                    onClick={() => {
                      downloadPDF(data);
                      setIsAdminMenuOpen(false);
                    }}
                    disabled={isExporting}
                    className="w-full justify-start"
                    variant="outline"
                  >
                    <svg className="h-4 w-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
                    </svg>
                    PDF (lista filtrada)
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

              {/* Quick Actions */}
              <div className="pt-6 border-t border-gray-200">
                <div className="space-y-2">
                  <Button
                    variant="outline"
                    onClick={() => {
                      router.push('/search');
                      setIsAdminMenuOpen(false);
                    }}
                    className="w-full"
                  >
                    Criar Novo Mapa
                  </Button>
                  <Button
                    variant="outline"
                    onClick={() => {
                      router.push('/maps');
                      setIsAdminMenuOpen(false);
                    }}
                    className="w-full"
                  >
                    Ver Mapas Salvos
                  </Button>
                </div>
              </div>

              {/* Info Box */}
              <div className="mt-6 p-4 bg-blue-50 rounded-lg">
                <h4 className="font-medium text-blue-800 mb-2 text-sm">Dicas de Uso:</h4>
                <ul className="text-xs text-blue-700 space-y-1">
                  <li>• <strong>GeoJSON:</strong> Importar no uMap para visualização interativa</li>
                  <li>• <strong>GPX:</strong> Usar em apps de navegação GPS</li>
                  <li>• <strong>PDF:</strong> Imprimir lista de POIs</li>
                </ul>
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
