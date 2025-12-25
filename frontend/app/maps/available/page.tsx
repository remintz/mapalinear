'use client';

import React, { useState, useEffect, useCallback } from 'react';
import { Card, CardContent } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/badge';
import { CityCombobox } from '@/components/ui/CityCombobox';
import {
  Globe,
  Search,
  MapPin,
  Plus,
  Loader2,
  ArrowLeft,
  Calendar,
  Check,
  MapPinned
} from 'lucide-react';
import { toast } from 'sonner';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { apiClient, SavedMap } from '@/lib/api';
import RouteMapModal from '@/components/RouteMapModal';

export default function AvailableMapsPage() {
  const [availableMaps, setAvailableMaps] = useState<SavedMap[]>([]);
  const [myMapIds, setMyMapIds] = useState<Set<string>>(new Set());
  const [loading, setLoading] = useState(true);
  const [searchLoading, setSearchLoading] = useState(false);
  const [adoptingId, setAdoptingId] = useState<string | null>(null);
  const [searchOrigin, setSearchOrigin] = useState('');
  const [searchDestination, setSearchDestination] = useState('');
  const [osmMapId, setOsmMapId] = useState<string | null>(null);
  const router = useRouter();

  // Load user's maps to know which ones they already have
  const loadMyMaps = useCallback(async () => {
    try {
      const maps = await apiClient.listMaps();
      setMyMapIds(new Set(maps.map(m => m.id)));
    } catch (error) {
      console.error('Error loading my maps:', error);
    }
  }, []);

  // Load available maps
  const loadAvailableMaps = useCallback(async (origin?: string, destination?: string) => {
    try {
      setSearchLoading(true);
      const maps = await apiClient.listAvailableMaps({
        origin: origin || undefined,
        destination: destination || undefined,
        limit: 100
      });
      setAvailableMaps(maps);
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Erro desconhecido';
      toast.error(`Erro ao carregar mapas: ${errorMessage}`);
      setAvailableMaps([]);
    } finally {
      setSearchLoading(false);
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadMyMaps();
    loadAvailableMaps();
  }, [loadMyMaps, loadAvailableMaps]);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    loadAvailableMaps(searchOrigin, searchDestination);
  };

  const handleClearSearch = () => {
    setSearchOrigin('');
    setSearchDestination('');
    loadAvailableMaps();
  };

  const handleOpenMap = (mapId: string) => {
    router.push(`/map?mapId=${mapId}`);
  };

  const handleViewOnMap = (mapId: string) => {
    setOsmMapId(mapId);
  };

  const handleAdoptMap = async (mapId: string) => {
    try {
      setAdoptingId(mapId);
      await apiClient.adoptMap(mapId);
      toast.success('Mapa adicionado à sua coleção!');
      setMyMapIds(prev => new Set(prev).add(mapId));
    } catch (error) {
      console.error('Error adopting map:', error);
      toast.error('Erro ao adicionar mapa');
    } finally {
      setAdoptingId(null);
    }
  };

  const formatDate = (dateString: string) => {
    try {
      const date = new Date(dateString);
      if (isNaN(date.getTime())) {
        return 'Data inválida';
      }
      return new Intl.DateTimeFormat('pt-BR', {
        day: '2-digit',
        month: '2-digit',
        year: 'numeric'
      }).format(date);
    } catch {
      return 'Data inválida';
    }
  };

  const MapCard = ({ map }: { map: SavedMap }) => {
    const alreadyHave = myMapIds.has(map.id);

    return (
      <Card className="hover:shadow-md transition-shadow">
        <CardContent className="p-4">
          {/* Route Info */}
          <div className="mb-3">
            <h3 className="text-base font-semibold text-gray-900 mb-1 truncate">
              {map.origin} → {map.destination}
            </h3>
            <div className="flex flex-wrap items-center gap-2 text-xs text-gray-600">
              <span className="flex items-center gap-1">
                <Calendar className="h-3 w-3" />
                {formatDate(map.creation_date)}
              </span>
              <span className="flex items-center gap-1">
                <MapPin className="h-3 w-3" />
                {map.milestone_count} pontos
              </span>
              <Badge variant="secondary" className="bg-blue-100 text-blue-800 text-xs">
                {map.total_length_km.toFixed(1)} km
              </Badge>
            </div>
          </div>

          {/* Action Buttons */}
          <div className="flex gap-2">
            {alreadyHave ? (
              <>
                <Button
                  onClick={() => handleOpenMap(map.id)}
                  className="flex-1"
                  size="sm"
                >
                  Abrir Mapa
                </Button>
                <Button
                  onClick={() => handleViewOnMap(map.id)}
                  size="sm"
                  variant="outline"
                  className="px-3"
                  title="Ver rota no mapa"
                >
                  <MapPinned className="h-4 w-4" />
                </Button>
                <Badge variant="outline" className="flex items-center gap-1 text-green-700 border-green-300">
                  <Check className="h-3 w-3" />
                  Na coleção
                </Badge>
              </>
            ) : (
              <>
                <Button
                  onClick={() => handleAdoptMap(map.id)}
                  className="flex-1"
                  size="sm"
                  disabled={adoptingId === map.id}
                >
                  {adoptingId === map.id ? (
                    <Loader2 className="h-4 w-4 mr-1 animate-spin" />
                  ) : (
                    <Plus className="h-4 w-4 mr-1" />
                  )}
                  Adicionar à Coleção
                </Button>
                <Button
                  onClick={() => handleViewOnMap(map.id)}
                  size="sm"
                  variant="outline"
                  className="px-3"
                  title="Ver rota no mapa"
                >
                  <MapPinned className="h-4 w-4" />
                </Button>
              </>
            )}
          </div>
        </CardContent>
      </Card>
    );
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="sticky top-0 z-20 bg-white border-b border-gray-200 shadow-sm">
        <div className="max-w-6xl mx-auto px-4 py-4">
          <div className="flex items-center gap-3">
            <Link href="/search" className="text-blue-600 hover:text-blue-700">
              <ArrowLeft className="h-5 w-5" />
            </Link>
            <div className="flex items-center gap-3">
              <Globe className="h-6 w-6 text-blue-600" />
              <div>
                <h1 className="text-xl font-bold text-gray-900">Mapas Disponíveis</h1>
                <p className="text-xs text-gray-600">
                  {availableMaps.length} {availableMaps.length === 1 ? 'mapa encontrado' : 'mapas encontrados'}
                </p>
              </div>
            </div>
          </div>
        </div>
      </header>

      {/* Search Form */}
      <div className="bg-white border-b border-gray-200 py-4">
        <div className="max-w-6xl mx-auto px-4">
          <form onSubmit={handleSearch} className="flex flex-col sm:flex-row gap-3">
            <div className="flex-1">
              <CityCombobox
                placeholder="Filtrar por origem..."
                value={searchOrigin}
                onChange={setSearchOrigin}
              />
            </div>
            <div className="flex-1">
              <CityCombobox
                placeholder="Filtrar por destino..."
                value={searchDestination}
                onChange={setSearchDestination}
              />
            </div>
            <div className="flex gap-2">
              <Button type="submit" disabled={searchLoading}>
                {searchLoading ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Search className="h-4 w-4" />
                )}
                <span className="ml-2 hidden sm:inline">Buscar</span>
              </Button>
              {(searchOrigin || searchDestination) && (
                <Button type="button" variant="outline" onClick={handleClearSearch}>
                  Limpar
                </Button>
              )}
            </div>
          </form>
        </div>
      </div>

      {/* Main Content */}
      <main className="max-w-6xl mx-auto px-4 py-6">
        {searchLoading ? (
          <div className="flex items-center justify-center py-16">
            <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
          </div>
        ) : availableMaps.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-16 px-4 text-center">
            <Globe className="h-20 w-20 text-gray-300 mb-4" />
            <h2 className="text-lg font-semibold text-gray-700 mb-2">Nenhum mapa encontrado</h2>
            <p className="text-sm text-gray-500 mb-6 max-w-xs">
              {searchOrigin || searchDestination
                ? 'Tente outra busca ou crie um novo mapa'
                : 'Seja o primeiro a criar um mapa!'
              }
            </p>
            <Button onClick={() => router.push('/search')}>
              Criar Novo Mapa
            </Button>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 pb-20">
            {availableMaps.map((map) => (
              <MapCard key={map.id} map={map} />
            ))}
          </div>
        )}
      </main>

      {/* OSM Map Modal */}
      {osmMapId && (
        <RouteMapModal
          mapId={osmMapId}
          isOpen={true}
          onClose={() => setOsmMapId(null)}
        />
      )}
    </div>
  );
}
