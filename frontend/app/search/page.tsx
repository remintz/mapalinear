'use client';

import React, { Suspense, useEffect, useState, useCallback } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import { SearchForm } from '@/components/forms/SearchForm';
import { useAsyncRouteSearch } from '@/hooks/useAsyncRouteSearch';
import { Card, CardContent } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/badge';
import {
  ArrowLeft,
  Map,
  MapPin,
  Plus,
  Loader2,
  Clock,
  ChevronRight,
  Navigation
} from 'lucide-react';
import Link from 'next/link';
import { apiClient, SavedMap } from '@/lib/api';
import { toast } from 'sonner';

function SearchPageContent() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const operationId = searchParams.get('operationId');

  const { searchRoute, isLoading, error, data, progressMessage, progressPercent, estimatedCompletion } = useAsyncRouteSearch();

  // State for suggested maps
  const [suggestedMaps, setSuggestedMaps] = useState<SavedMap[]>([]);
  const [loadingMaps, setLoadingMaps] = useState(true);
  const [userLocation, setUserLocation] = useState<{ lat: number; lon: number } | null>(null);
  const [adoptingId, setAdoptingId] = useState<string | null>(null);
  const [showCreateForm, setShowCreateForm] = useState(false);

  // Get user location
  useEffect(() => {
    if (navigator.geolocation) {
      navigator.geolocation.getCurrentPosition(
        (position) => {
          setUserLocation({
            lat: position.coords.latitude,
            lon: position.coords.longitude
          });
        },
        (error) => {
          console.log('Geolocation not available:', error.message);
        },
        { timeout: 5000, maximumAge: 300000 } // 5s timeout, 5min cache
      );
    }
  }, []);

  // Load suggested maps
  const loadSuggestedMaps = useCallback(async () => {
    try {
      setLoadingMaps(true);
      const maps = await apiClient.getSuggestedMaps({
        limit: 10,
        lat: userLocation?.lat,
        lon: userLocation?.lon
      });
      setSuggestedMaps(maps);
    } catch (error) {
      console.error('Error loading suggested maps:', error);
    } finally {
      setLoadingMaps(false);
    }
  }, [userLocation]);

  useEffect(() => {
    loadSuggestedMaps();
  }, [loadSuggestedMaps]);

  // Redirect to map page when data is available
  useEffect(() => {
    if (data && (data as any).id) {
      const mapId = (data as any).id;
      router.push(`/map?mapId=${mapId}`);
    }
  }, [data, router]);

  // If operationId is provided in URL, redirect to map page to monitor it there
  useEffect(() => {
    if (operationId) {
      router.push(`/map?operationId=${operationId}`);
    }
  }, [operationId, router]);

  const handleSearch = (formData: any) => {
    searchRoute(formData);
  };

  const handleAdoptMap = async (mapId: string) => {
    try {
      setAdoptingId(mapId);
      await apiClient.adoptMap(mapId);
      toast.success('Mapa adicionado à sua coleção!');
      router.push(`/map?mapId=${mapId}`);
    } catch (error) {
      console.error('Error adopting map:', error);
      toast.error('Erro ao adicionar mapa');
    } finally {
      setAdoptingId(null);
    }
  };

  const MapCard = ({ map }: { map: SavedMap }) => (
    <button
      type="button"
      onClick={() => handleAdoptMap(map.id)}
      className="w-full text-left"
    >
      <Card className="hover:shadow-md transition-shadow cursor-pointer group">
        <CardContent className="p-3">
          <div className="flex items-start justify-between gap-2">
            <div className="flex-1 min-w-0">
              <h3 className="text-sm font-medium text-gray-900 truncate group-hover:text-blue-600">
                {map.origin}
              </h3>
              <div className="flex items-center gap-1 text-xs text-gray-500">
                <span>→</span>
                <span className="truncate">{map.destination}</span>
              </div>
              <div className="flex items-center gap-2 mt-1">
                <Badge variant="secondary" className="bg-blue-50 text-blue-700 text-xs px-1.5 py-0">
                  {map.total_length_km.toFixed(0)} km
                </Badge>
                <span className="text-xs text-gray-400">
                  {map.milestone_count} pontos
                </span>
              </div>
            </div>
            {adoptingId === map.id ? (
              <Loader2 className="h-5 w-5 text-blue-600 animate-spin flex-shrink-0" />
            ) : (
              <Plus className="h-5 w-5 text-gray-400 group-hover:text-blue-600 flex-shrink-0" />
            )}
          </div>
        </CardContent>
      </Card>
    </button>
  );

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="sticky top-0 z-20 bg-white border-b border-gray-200 shadow-sm">
        <div className="max-w-4xl mx-auto px-4 py-4">
          <div className="flex items-center gap-3">
            <Link href="/" className="text-blue-600 hover:text-blue-700">
              <ArrowLeft className="h-5 w-5" />
            </Link>
            <div>
              <h1 className="text-xl font-bold text-gray-900">Novo Mapa</h1>
              <p className="text-sm text-gray-600">Selecione um mapa existente ou crie um novo</p>
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-4xl mx-auto px-4 py-6">
        {/* Suggested Maps Section */}
        <section className="mb-8">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <Map className="h-5 w-5 text-blue-600" />
              <h2 className="text-lg font-semibold text-gray-900">Mapas Disponíveis</h2>
              {userLocation && (
                <Badge variant="outline" className="text-xs flex items-center gap-1">
                  <Navigation className="h-3 w-3" />
                  Próximos a você
                </Badge>
              )}
            </div>
            <Link
              href="/maps/available"
              className="text-sm text-blue-600 hover:text-blue-700 flex items-center gap-1"
            >
              Ver todos
              <ChevronRight className="h-4 w-4" />
            </Link>
          </div>

          {loadingMaps ? (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="h-6 w-6 animate-spin text-blue-600" />
            </div>
          ) : suggestedMaps.length === 0 ? (
            <Card className="bg-gray-50 border-dashed">
              <CardContent className="p-6 text-center">
                <Map className="h-10 w-10 text-gray-300 mx-auto mb-2" />
                <p className="text-sm text-gray-500">Nenhum mapa disponível ainda.</p>
                <p className="text-xs text-gray-400 mt-1">Seja o primeiro a criar um mapa!</p>
              </CardContent>
            </Card>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
              {suggestedMaps.slice(0, 9).map((map) => (
                <MapCard key={map.id} map={map} />
              ))}
            </div>
          )}

          {suggestedMaps.length > 0 && (
            <p className="text-xs text-gray-500 mt-3 text-center">
              Clique em um mapa para adicioná-lo à sua coleção e visualizar
            </p>
          )}
        </section>

        {/* Divider */}
        <div className="relative my-8">
          <div className="absolute inset-0 flex items-center">
            <div className="w-full border-t border-gray-200"></div>
          </div>
          <div className="relative flex justify-center">
            <span className="bg-gray-50 px-4 text-sm text-gray-500">ou</span>
          </div>
        </div>

        {/* Create New Map Section */}
        <section>
          {!showCreateForm ? (
            <Card className="border-2 border-dashed border-gray-300 hover:border-blue-400 transition-colors">
              <CardContent className="p-6">
                <button
                  onClick={() => setShowCreateForm(true)}
                  className="w-full text-center"
                >
                  <div className="flex flex-col items-center gap-3">
                    <div className="p-3 bg-blue-50 rounded-full">
                      <Plus className="h-6 w-6 text-blue-600" />
                    </div>
                    <div>
                      <h3 className="text-lg font-semibold text-gray-900">Criar Novo Mapa</h3>
                      <p className="text-sm text-gray-500 mt-1">
                        Gere um mapa personalizado entre duas cidades
                      </p>
                    </div>
                  </div>
                </button>

                {/* Warning about time */}
                <div className="mt-4 p-3 bg-amber-50 rounded-lg border border-amber-100">
                  <div className="flex items-start gap-2">
                    <Clock className="h-4 w-4 text-amber-600 mt-0.5 flex-shrink-0" />
                    <div className="text-xs text-amber-700">
                      <p className="font-medium">Atenção:</p>
                      <p>A criação de um novo mapa pode demorar alguns minutos dependendo das distâncias envolvidas.</p>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          ) : (
            <div>
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-lg font-semibold text-gray-900 flex items-center gap-2">
                  <MapPin className="h-5 w-5 text-blue-600" />
                  Criar Novo Mapa
                </h2>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setShowCreateForm(false)}
                  disabled={isLoading}
                >
                  Cancelar
                </Button>
              </div>

              {/* Warning about time */}
              <div className="mb-4 p-3 bg-amber-50 rounded-lg border border-amber-100">
                <div className="flex items-start gap-2">
                  <Clock className="h-4 w-4 text-amber-600 mt-0.5 flex-shrink-0" />
                  <p className="text-xs text-amber-700">
                    A criação pode demorar alguns minutos dependendo das distâncias envolvidas.
                  </p>
                </div>
              </div>

              <SearchForm
                onSubmit={handleSearch}
                isLoading={isLoading}
                error={error}
                progressMessage={progressMessage}
                progressPercent={progressPercent}
                estimatedCompletion={estimatedCompletion}
              />
            </div>
          )}
        </section>

        {/* Quick Help - Only show when not loading and not in form mode */}
        {!isLoading && !showCreateForm && (
          <div className="mt-8">
            <div className="p-4 bg-blue-50 rounded-lg border border-blue-100">
              <h3 className="text-sm font-semibold text-blue-900 mb-2">Dica rápida</h3>
              <p className="text-xs text-blue-700">
                Selecione um mapa existente para economizar tempo. Novos mapas são criados automaticamente
                quando você escolhe uma rota que ainda não existe.
              </p>
            </div>

            {/* Link to saved maps */}
            <div className="mt-4 text-center">
              <Link
                href="/maps"
                className="text-sm text-gray-600 hover:text-gray-800 underline"
              >
                Ver meus mapas salvos
              </Link>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}

export default function SearchPage() {
  return (
    <Suspense fallback={<div className="min-h-screen bg-gray-50 flex items-center justify-center">Carregando...</div>}>
      <SearchPageContent />
    </Suspense>
  );
}
