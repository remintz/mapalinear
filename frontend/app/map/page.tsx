'use client';

import React, { useState, useEffect } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import { Button, Card, CardHeader, CardTitle, CardContent } from '@/components/ui';
import { MapPin, Route, ArrowLeft, Bug, Loader2 } from 'lucide-react';
import Link from 'next/link';
import { toast } from 'sonner';

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

  const [poiFilters, setPoiFilters] = useState({
    includeGasStations: true,
    includeRestaurants: true,
    includeHotels: false,
    includeCamping: true,
    includeHospitals: false,
    includeTollBooths: true,
    includeCities: true,
    includeTowns: true,
    includeVillages: true,
  });

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

  // Filter POIs based on user preferences
  const getFilteredPOIs = () => {
    if (!data?.pois) return [];

    return data.pois.filter((poi) => {
      if (poi.type === 'gas_station' && !poiFilters.includeGasStations) return false;
      if (['restaurant', 'fast_food', 'cafe'].includes(poi.type) && !poiFilters.includeRestaurants) return false;
      if (poi.type === 'hotel' && !poiFilters.includeHotels) return false;
      if (poi.type === 'camping' && !poiFilters.includeCamping) return false;
      if (poi.type === 'hospital' && !poiFilters.includeHospitals) return false;
      if (poi.type === 'toll_booth' && !poiFilters.includeTollBooths) return false;
      if (poi.type === 'city' && !poiFilters.includeCities) return false;
      if (poi.type === 'town' && !poiFilters.includeTowns) return false;
      if (poi.type === 'village' && !poiFilters.includeVillages) return false;
      return true;
    });
  };

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
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100">
      <div className="container mx-auto px-4 py-8">
        {/* Header */}
        <header className="mb-8">
          <div className="flex justify-between items-start mb-4">
            <Link href="/search" className="inline-flex items-center gap-2 text-blue-600 hover:text-blue-700">
              <ArrowLeft className="h-4 w-4" />
              Criar Novo Mapa
            </Link>
            <Link href="/debug-segments" className="inline-flex items-center gap-2 text-gray-600 hover:text-gray-800 text-sm">
              <Bug className="h-4 w-4" />
              Debug: Ver Segmentos
            </Link>
          </div>
          <h1 className="text-3xl md:text-4xl font-bold text-gray-900 mb-2">
            Mapa Linear
          </h1>
          <p className="text-lg text-gray-600">
            {data.origin} → {data.destination}
          </p>
        </header>

        {/* Map Display */}
        <div className="mb-8">
          <Card className="max-w-4xl mx-auto">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Route className="h-5 w-5 text-green-600" />
                Rota Encontrada
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-6">
                {/* Route Summary */}
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-center">
                  <div className="p-4 bg-blue-50 rounded-lg">
                    <p className="text-sm text-gray-600 mb-1">Origem</p>
                    <p className="font-semibold text-gray-900">{data.origin}</p>
                  </div>
                  <div className="p-4 bg-green-50 rounded-lg">
                    <p className="text-sm text-gray-600 mb-1">Destino</p>
                    <p className="font-semibold text-gray-900">{data.destination}</p>
                  </div>
                  <div className="p-4 bg-yellow-50 rounded-lg">
                    <p className="text-sm text-gray-600 mb-1">Distância Total</p>
                    <p className="font-semibold text-gray-900">
                      {data.total_distance_km ? data.total_distance_km.toFixed(1) : '0.0'} km
                    </p>
                  </div>
                </div>

                {/* Interactive POI Filters */}
                <div className="border-t pt-6">
                  <h3 className="text-lg font-semibold text-gray-900 mb-4">Filtrar Pontos de Interesse</h3>
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                    {/* Gas Stations */}
                    <label className="flex items-center gap-3 p-3 border rounded hover:bg-gray-50 cursor-pointer transition-colors">
                      <input
                        type="checkbox"
                        checked={poiFilters.includeGasStations}
                        onChange={(e) => setPoiFilters({...poiFilters, includeGasStations: e.target.checked})}
                        className="w-4 h-4 text-blue-600 rounded focus:ring-2 focus:ring-blue-500"
                      />
                      <span className="flex-1 flex items-center justify-between">
                        <span className="text-sm font-medium text-gray-700">⛽ Postos</span>
                        <span className="text-sm font-bold text-blue-600">
                          ({data.pois?.filter(p => p.type === 'gas_station').length || 0})
                        </span>
                      </span>
                    </label>

                    {/* Restaurants */}
                    <label className="flex items-center gap-3 p-3 border rounded hover:bg-gray-50 cursor-pointer transition-colors">
                      <input
                        type="checkbox"
                        checked={poiFilters.includeRestaurants}
                        onChange={(e) => setPoiFilters({...poiFilters, includeRestaurants: e.target.checked})}
                        className="w-4 h-4 text-blue-600 rounded focus:ring-2 focus:ring-blue-500"
                      />
                      <span className="flex-1 flex items-center justify-between">
                        <span className="text-sm font-medium text-gray-700">🍽️ Restaurantes</span>
                        <span className="text-sm font-bold text-orange-600">
                          ({data.pois?.filter(p => ['restaurant', 'fast_food', 'cafe'].includes(p.type)).length || 0})
                        </span>
                      </span>
                    </label>

                    {/* Hotels */}
                    <label className="flex items-center gap-3 p-3 border rounded hover:bg-gray-50 cursor-pointer transition-colors">
                      <input
                        type="checkbox"
                        checked={poiFilters.includeHotels}
                        onChange={(e) => setPoiFilters({...poiFilters, includeHotels: e.target.checked})}
                        className="w-4 h-4 text-blue-600 rounded focus:ring-2 focus:ring-blue-500"
                      />
                      <span className="flex-1 flex items-center justify-between">
                        <span className="text-sm font-medium text-gray-700">🏨 Hotéis</span>
                        <span className="text-sm font-bold text-purple-600">
                          ({data.pois?.filter(p => p.type === 'hotel').length || 0})
                        </span>
                      </span>
                    </label>

                    {/* Camping */}
                    <label className="flex items-center gap-3 p-3 border rounded hover:bg-gray-50 cursor-pointer transition-colors">
                      <input
                        type="checkbox"
                        checked={poiFilters.includeCamping}
                        onChange={(e) => setPoiFilters({...poiFilters, includeCamping: e.target.checked})}
                        className="w-4 h-4 text-blue-600 rounded focus:ring-2 focus:ring-blue-500"
                      />
                      <span className="flex-1 flex items-center justify-between">
                        <span className="text-sm font-medium text-gray-700">⛺ Camping</span>
                        <span className="text-sm font-bold text-green-600">
                          ({data.pois?.filter(p => p.type === 'camping').length || 0})
                        </span>
                      </span>
                    </label>

                    {/* Hospitals */}
                    <label className="flex items-center gap-3 p-3 border rounded hover:bg-gray-50 cursor-pointer transition-colors">
                      <input
                        type="checkbox"
                        checked={poiFilters.includeHospitals}
                        onChange={(e) => setPoiFilters({...poiFilters, includeHospitals: e.target.checked})}
                        className="w-4 h-4 text-blue-600 rounded focus:ring-2 focus:ring-blue-500"
                      />
                      <span className="flex-1 flex items-center justify-between">
                        <span className="text-sm font-medium text-gray-700">🏥 Hospitais</span>
                        <span className="text-sm font-bold text-red-600">
                          ({data.pois?.filter(p => p.type === 'hospital').length || 0})
                        </span>
                      </span>
                    </label>

                    {/* Toll Booths */}
                    <label className="flex items-center gap-3 p-3 border rounded hover:bg-gray-50 cursor-pointer transition-colors">
                      <input
                        type="checkbox"
                        checked={poiFilters.includeTollBooths}
                        onChange={(e) => setPoiFilters({...poiFilters, includeTollBooths: e.target.checked})}
                        className="w-4 h-4 text-blue-600 rounded focus:ring-2 focus:ring-blue-500"
                      />
                      <span className="flex-1 flex items-center justify-between">
                        <span className="text-sm font-medium text-gray-700">🛣️ Pedágios</span>
                        <span className="text-sm font-bold text-gray-600">
                          ({data.pois?.filter(p => p.type === 'toll_booth').length || 0})
                        </span>
                      </span>
                    </label>

                    {/* Cities */}
                    <label className="flex items-center gap-3 p-3 border rounded hover:bg-gray-50 cursor-pointer transition-colors">
                      <input
                        type="checkbox"
                        checked={poiFilters.includeCities}
                        onChange={(e) => setPoiFilters({...poiFilters, includeCities: e.target.checked})}
                        className="w-4 h-4 text-blue-600 rounded focus:ring-2 focus:ring-blue-500"
                      />
                      <span className="flex-1 flex items-center justify-between">
                        <span className="text-sm font-medium text-gray-700">🏙️ Cidades</span>
                        <span className="text-sm font-bold text-indigo-600">
                          ({data.pois?.filter(p => p.type === 'city').length || 0})
                        </span>
                      </span>
                    </label>

                    {/* Towns */}
                    <label className="flex items-center gap-3 p-3 border rounded hover:bg-gray-50 cursor-pointer transition-colors">
                      <input
                        type="checkbox"
                        checked={poiFilters.includeTowns}
                        onChange={(e) => setPoiFilters({...poiFilters, includeTowns: e.target.checked})}
                        className="w-4 h-4 text-blue-600 rounded focus:ring-2 focus:ring-blue-500"
                      />
                      <span className="flex-1 flex items-center justify-between">
                        <span className="text-sm font-medium text-gray-700">🏘️ Vilas</span>
                        <span className="text-sm font-bold text-indigo-600">
                          ({data.pois?.filter(p => p.type === 'town').length || 0})
                        </span>
                      </span>
                    </label>

                    {/* Villages */}
                    <label className="flex items-center gap-3 p-3 border rounded hover:bg-gray-50 cursor-pointer transition-colors">
                      <input
                        type="checkbox"
                        checked={poiFilters.includeVillages}
                        onChange={(e) => setPoiFilters({...poiFilters, includeVillages: e.target.checked})}
                        className="w-4 h-4 text-blue-600 rounded focus:ring-2 focus:ring-blue-500"
                      />
                      <span className="flex-1 flex items-center justify-between">
                        <span className="text-sm font-medium text-gray-700">🏡 Povoados</span>
                        <span className="text-sm font-bold text-indigo-600">
                          ({data.pois?.filter(p => p.type === 'village').length || 0})
                        </span>
                      </span>
                    </label>
                  </div>

                  {/* Total filtered count */}
                  <div className="mt-4 p-3 bg-blue-50 rounded-lg text-center">
                    <p className="text-sm text-gray-600">
                      Mostrando <span className="font-bold text-blue-600">{filteredPOIs.length}</span> de <span className="font-bold">{data.pois?.length || 0}</span> pontos de interesse
                    </p>
                  </div>
                </div>

                {/* POI List */}
                {filteredPOIs.length > 0 && (
                  <div className="border-t pt-6">
                    <h3 className="text-lg font-semibold text-gray-900 mb-4">
                      Pontos de Interesse Selecionados ({filteredPOIs.length})
                    </h3>
                    <div className="overflow-x-auto max-h-96 overflow-y-auto border rounded">
                      <table className="min-w-full divide-y divide-gray-200">
                        <thead className="bg-gray-50 sticky top-0">
                          <tr>
                            <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                              KM
                            </th>
                            <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                              Tipo
                            </th>
                            <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                              Nome
                            </th>
                            <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                              Cidade
                            </th>
                            <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                              Qualidade
                            </th>
                            <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                              Extra
                            </th>
                          </tr>
                        </thead>
                        <tbody className="bg-white divide-y divide-gray-200">
                          {filteredPOIs.map((poi) => (
                            <tr key={poi.id} className="hover:bg-gray-50">
                              <td className="px-3 py-2 whitespace-nowrap text-sm font-medium text-gray-900">
                                {poi.distance_from_origin_km?.toFixed(1) || '0.0'}
                              </td>
                              <td className="px-3 py-2 whitespace-nowrap text-sm text-gray-600">
                                {poi.type === 'gas_station' && '⛽ Posto'}
                                {poi.type === 'restaurant' && '🍽️ Restaurante'}
                                {poi.type === 'fast_food' && '🍔 Fast Food'}
                                {poi.type === 'cafe' && '☕ Café'}
                                {poi.type === 'toll_booth' && '🛣️ Pedágio'}
                                {poi.type === 'hotel' && '🏨 Hotel'}
                                {poi.type === 'camping' && '⛺ Camping'}
                                {poi.type === 'hospital' && '🏥 Hospital'}
                                {poi.type === 'city' && '🏙️ Cidade'}
                                {poi.type === 'town' && '🏘️ Vila'}
                                {poi.type === 'village' && '🏡 Povoado'}
                                {!['gas_station', 'restaurant', 'fast_food', 'cafe', 'toll_booth', 'hotel', 'camping', 'hospital', 'city', 'town', 'village'].includes(poi.type) && poi.type}
                              </td>
                              <td className="px-3 py-2 text-sm text-gray-900">
                                {poi.name || 'Nome não disponível'}
                              </td>
                              <td className="px-3 py-2 whitespace-nowrap text-sm text-gray-600">
                                {poi.city || '-'}
                              </td>
                              <td className="px-3 py-2 whitespace-nowrap text-sm">
                                {poi.quality_score !== undefined ? (
                                  <span className={`inline-flex items-center px-2 py-1 rounded text-xs font-medium ${
                                    poi.quality_score >= 0.7 ? 'bg-green-100 text-green-800' :
                                    poi.quality_score >= 0.4 ? 'bg-yellow-100 text-yellow-800' :
                                    'bg-red-100 text-red-800'
                                  }`}>
                                    {(poi.quality_score * 100).toFixed(0)}%
                                  </span>
                                ) : (
                                  <span className="text-gray-400">-</span>
                                )}
                              </td>
                              <td className="px-3 py-2 text-sm text-gray-600">
                                {poi.operator || poi.brand || '-'}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                )}

                {/* Export Actions */}
                <div className="border-t pt-6">
                  <h3 className="text-lg font-semibold text-gray-900 mb-4">Exportar e Visualizar</h3>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
                    {/* Downloads */}
                    <div className="space-y-2">
                      <h4 className="font-medium text-gray-700">Baixar Arquivos</h4>
                      <div className="space-y-2">
                        <Button
                          onClick={() => downloadFile('geojson', data)}
                          disabled={isExporting}
                          className="w-full justify-start"
                          variant="outline"
                        >
                          <svg className="h-4 w-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                          </svg>
                          GeoJSON (para uMap, QGIS)
                        </Button>
                        <Button
                          onClick={() => downloadFile('gpx', data)}
                          disabled={isExporting}
                          className="w-full justify-start"
                          variant="outline"
                        >
                          <svg className="h-4 w-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 20l-5.447-2.724A1 1 0 013 16.382V5.618a1 1 0 011.447-.894L9 7m0 13l6-3m-6 3V7m6 10l4.553 2.276A1 1 0 0021 18.382V7.618a1 1 0 00-.553-.894L15 4m0 13V4m0 0L9 7" />
                          </svg>
                          GPX (para GPS, apps móveis)
                        </Button>
                      </div>
                    </div>

                    {/* Web Tools */}
                    <div className="space-y-2">
                      <h4 className="font-medium text-gray-700">Abrir em Ferramentas Web</h4>
                      <div className="space-y-2">
                        <Button
                          onClick={() => openWebTool('umap', data)}
                          className="w-full justify-start"
                          variant="outline"
                        >
                          <svg className="h-4 w-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                          </svg>
                          Visualizar no uMap
                        </Button>
                        <Button
                          onClick={() => openWebTool('overpass', data)}
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
                  </div>

                  <div className="bg-blue-50 p-4 rounded-lg mb-4">
                    <h4 className="font-medium text-blue-800 mb-2">Como Visualizar:</h4>
                    <ul className="text-sm text-blue-700 space-y-1">
                      <li>• <strong>uMap:</strong> Baixe o GeoJSON → Abra uMap → "Importar dados"</li>
                      <li>• <strong>GPX:</strong> Arraste o arquivo para map.project-osrm.org</li>
                      <li>• <strong>Overpass:</strong> Compare os POIs encontrados com os dados reais do OSM</li>
                    </ul>
                  </div>

                  <div className="flex gap-3">
                    <Button
                      variant="outline"
                      onClick={() => router.push('/search')}
                      className="flex-1"
                    >
                      Criar Novo Mapa
                    </Button>
                    <Button
                      variant="outline"
                      onClick={() => router.push('/maps')}
                      className="flex-1"
                    >
                      Ver Mapas Salvos
                    </Button>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
