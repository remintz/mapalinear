'use client';

import React, { useState } from 'react';
import { Button, Card, CardHeader, CardTitle, CardContent } from '@/components/ui';
import { SearchForm } from '@/components/forms/SearchForm';
import { useAsyncRouteSearch } from '@/hooks/useAsyncRouteSearch';
import { MapPin, Route, ArrowLeft } from 'lucide-react';
import Link from 'next/link';
import { toast } from 'sonner';

export default function SearchPage() {
  const { searchRoute, isLoading, error, data, reset, progressMessage, progressPercent, estimatedCompletion } = useAsyncRouteSearch();
  const [isExporting, setIsExporting] = useState(false);

  const handleSearch = (formData: any) => {
    searchRoute(formData);
  };

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
          pois: routeData.pois || []
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
          <Link href="/" className="inline-flex items-center gap-2 text-blue-600 hover:text-blue-700 mb-4">
            <ArrowLeft className="h-4 w-4" />
            Voltar ao início
          </Link>
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
                  
                  {/* POI Summary */}
                  <div className="border-t pt-6">
                    <h3 className="text-lg font-semibold text-gray-900 mb-4">Pontos de Interesse</h3>
                    <div className="grid grid-cols-1 md:grid-cols-4 gap-4 text-center">
                      <div className="p-3 bg-gray-50 rounded">
                        <p className="text-2xl font-bold text-blue-600">{data.pois?.length || 0}</p>
                        <p className="text-sm text-gray-600">Total</p>
                      </div>
                      <div className="p-3 bg-gray-50 rounded">
                        <p className="text-2xl font-bold text-green-600">
                          {data.pois?.filter(poi => poi.type === 'gas_station').length || 0}
                        </p>
                        <p className="text-sm text-gray-600">Postos</p>
                      </div>
                      <div className="p-3 bg-gray-50 rounded">
                        <p className="text-2xl font-bold text-orange-600">
                          {data.pois?.filter(poi => poi.type === 'restaurant').length || 0}
                        </p>
                        <p className="text-sm text-gray-600">Restaurantes</p>
                      </div>
                      <div className="p-3 bg-gray-50 rounded">
                        <p className="text-2xl font-bold text-purple-600">
                          {data.pois?.filter(poi => poi.type === 'toll_booth').length || 0}
                        </p>
                        <p className="text-sm text-gray-600">Pedágios</p>
                      </div>
                    </div>
                  </div>

                  {/* POI List */}
                  {data.pois && data.pois.length > 0 && (
                    <div className="border-t pt-6">
                      <h3 className="text-lg font-semibold text-gray-900 mb-4">Detalhes dos Pontos</h3>
                      <div className="space-y-3 max-h-96 overflow-y-auto">
                        {data.pois.slice(0, 10).map((poi, index) => (
                          <div key={poi.id} className="flex items-center gap-3 p-3 bg-gray-50 rounded">
                            <div className="flex-shrink-0">
                              {poi.type === 'gas_station' && <div className="w-3 h-3 bg-green-500 rounded-full"></div>}
                              {poi.type === 'restaurant' && <div className="w-3 h-3 bg-orange-500 rounded-full"></div>}
                              {poi.type === 'toll_booth' && <div className="w-3 h-3 bg-purple-500 rounded-full"></div>}
                            </div>
                            <div className="flex-grow">
                              <p className="font-medium text-gray-900">{poi.name || 'Nome não disponível'}</p>
                              <p className="text-sm text-gray-600">
                                {poi.distance_from_origin_km ? poi.distance_from_origin_km.toFixed(1) : '0.0'} km da origem
                              </p>
                            </div>
                            <div className="text-right">
                              <MapPin className="h-4 w-4 text-gray-400" />
                            </div>
                          </div>
                        ))}
                        {data.pois && data.pois.length > 10 && (
                          <p className="text-sm text-gray-600 text-center py-2">
                            ... e mais {data.pois.length - 10} pontos de interesse
                          </p>
                        )}
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
                  <p>Escolha quais tipos de pontos de interesse você quer encontrar</p>
                </div>
                <div className="flex items-start gap-3">
                  <span className="flex-shrink-0 w-6 h-6 bg-blue-100 text-blue-600 rounded-full flex items-center justify-center text-xs font-semibold">4</span>
                  <p>Defina a distância máxima da rota para buscar pontos próximos</p>
                </div>
              </div>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
}