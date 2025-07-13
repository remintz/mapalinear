'use client';

import React from 'react';
import { Button, Card, CardHeader, CardTitle, CardContent } from '@/components/ui';
import { SearchForm } from '@/components/forms/SearchForm';
import { useAsyncRouteSearch } from '@/hooks/useAsyncRouteSearch';
import { MapPin, Route, ArrowLeft } from 'lucide-react';
import Link from 'next/link';

export default function SearchPage() {
  const { searchRoute, isLoading, error, data, reset, progressMessage, progressPercent, estimatedCompletion } = useAsyncRouteSearch();

  const handleSearch = (formData: any) => {
    searchRoute(formData);
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

                  {/* Actions */}
                  <div className="border-t pt-6 flex gap-3">
                    <Button 
                      variant="outline" 
                      onClick={reset}
                      className="flex-1"
                    >
                      Nova Busca
                    </Button>
                    <Button 
                      className="flex-1"
                      disabled
                    >
                      Ver Mapa Linear (Em breve)
                    </Button>
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