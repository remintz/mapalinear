'use client';

import React, { useState } from 'react';
import { Button, Card, CardHeader, CardTitle, CardContent } from '@/components/ui';
import { SearchForm } from '@/components/forms/SearchForm';
import { useAsyncRouteSearch } from '@/hooks/useAsyncRouteSearch';
import { MapPin, Route, ArrowLeft, Bug } from 'lucide-react';
import Link from 'next/link';
import { toast } from 'sonner';

export default function SearchPage() {
  const { searchRoute, isLoading, error, data, reset, progressMessage, progressPercent, estimatedCompletion } = useAsyncRouteSearch();
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

  const handleSearch = (formData: any) => {
    searchRoute(formData);
  };

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

  // Função para download de arquivos
  const downloadFile = async (format: 'geojson' | 'gpx', routeData: any) => {
    setIsExporting(true);
    try {
      const response = await fetch(`/api/export/${format}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          origin: routeData.origin,
          destination: routeData.destination,
          total_distance_km: routeData.total_distance_km,
          segments: routeData.segments || [],
          pois: filteredPOIs  // Use filtered POIs instead of all POIs
        }),
      });

      if (!response.ok) {
        throw new Error(`Erro ao exportar ${format.toUpperCase()}`);
      }

      // Criar blob e download
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      
      // Extrair filename do header ou usar padrão
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
      toast.error(`Erro ao exportar ${format.toUpperCase()}: ${error instanceof Error ? error.message : 'Erro desconhecido'}`);
    } finally {
      setIsExporting(false);
    }
  };

  // Função para abrir URLs de ferramentas web
  const openWebTool = async (tool: 'umap' | 'overpass', routeData: any) => {
    try {
      const response = await fetch('/api/export/web-urls', {
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

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100">
      <div className="container mx-auto px-4 py-8">
        {/* Header */}
        <header className="mb-8">
          <div className="flex justify-between items-start mb-4">
            <Link href="/" className="inline-flex items-center gap-2 text-blue-600 hover:text-blue-700">
              <ArrowLeft className="h-4 w-4" />
              Voltar ao início
            </Link>
            <Link href="/debug-segments" className="inline-flex items-center gap-2 text-gray-600 hover:text-gray-800 text-sm">
              <Bug className="h-4 w-4" />
              Debug: Ver Segmentos
            </Link>
          </div>
          <h1 className="text-3xl md:text-4xl font-bold text-gray-900 mb-2">
            Buscar Rota
          </h1>
          <p className="text-lg text-gray-600">
            Digite sua origem e destino para encontrar pontos de interesse ao longo da rota.
          </p>
        </header>

        {/* Search Form */}
        <div className="mb-8">
          <SearchForm 
            onSubmit={handleSearch}
            isLoading={isLoading}
            error={error}
            progressMessage={progressMessage}
            progressPercent={progressPercent}
            estimatedCompletion={estimatedCompletion}
          />
        </div>

        {/* Results Display */}
        {data && (
          <div className="mb-8">
            <Card className="max-w-4xl mx-auto">
              <CardHeader>
                <div className="flex justify-between items-center">
                  <CardTitle className="flex items-center gap-2">
                    <Route className="h-5 w-5 text-green-600" />
                    Rota Encontrada
                  </CardTitle>
                  <Link href="/debug-segments" target="_blank">
                    <Button variant="outline" size="sm" className="flex items-center gap-2">
                      <Bug className="h-4 w-4" />
                      Ver Segmentos (Debug)
                    </Button>
                  </Link>
                </div>
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

                      {/* Restaurants (includes fast_food and cafe) */}
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
                        onClick={reset}
                        className="flex-1"
                      >
                        Nova Busca
                      </Button>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
        )}

        {/* Instructions */}
        {!data && !isLoading && (
          <Card className="max-w-2xl mx-auto">
            <CardHeader>
              <CardTitle>Como usar</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4 text-sm text-gray-600">
                <div className="flex items-start gap-3">
                  <span className="flex-shrink-0 w-6 h-6 bg-blue-100 text-blue-600 rounded-full flex items-center justify-center text-xs font-semibold">1</span>
                  <p>Digite a cidade de origem no formato "Cidade, UF" (ex: São Paulo, SP)</p>
                </div>
                <div className="flex items-start gap-3">
                  <span className="flex-shrink-0 w-6 h-6 bg-blue-100 text-blue-600 rounded-full flex items-center justify-center text-xs font-semibold">2</span>
                  <p>Digite a cidade de destino no mesmo formato (ex: Rio de Janeiro, RJ)</p>
                </div>
                <div className="flex items-start gap-3">
                  <span className="flex-shrink-0 w-6 h-6 bg-blue-100 text-blue-600 rounded-full flex items-center justify-center text-xs font-semibold">3</span>
                  <p>Defina a distância máxima da rota para buscar pontos próximos</p>
                </div>
                <div className="flex items-start gap-3">
                  <span className="flex-shrink-0 w-6 h-6 bg-blue-100 text-blue-600 rounded-full flex items-center justify-center text-xs font-semibold">4</span>
                  <p>Após a busca, filtre os tipos de pontos de interesse que deseja visualizar</p>
                </div>
              </div>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
}