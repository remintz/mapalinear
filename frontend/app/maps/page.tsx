"use client";

import React, { useState, useEffect } from 'react';
import { Button } from '@/components/ui/Button';
import { MapCardBase } from '@/components/ui/MapCardBase';
import {
  Map,
  Trash2,
  FolderOpen,
  Loader2,
  Plus,
  MapPinned
} from 'lucide-react';
import { toast } from 'sonner';
import { useRouter } from 'next/navigation';
import { apiClient, SavedMap } from '@/lib/api';
import RouteMapModal from '@/components/RouteMapModal';
import { useAnalytics } from '@/hooks/useAnalytics';

export default function SavedMapsPage() {
  const [myMaps, setMyMaps] = useState<SavedMap[]>([]);
  const [loading, setLoading] = useState(true);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [osmMapId, setOsmMapId] = useState<string | null>(null);
  const router = useRouter();
  const { trackPageView, trackMapEvent } = useAnalytics();

  useEffect(() => {
    trackPageView('/maps');
    loadMyMaps();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const loadMyMaps = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await apiClient.listMaps();
      setMyMaps(data);
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Erro desconhecido';
      setError(errorMessage);
      toast.error(`Erro ao carregar mapas: ${errorMessage}`);
      setMyMaps([]);
    } finally {
      setLoading(false);
    }
  };

  const handleOpenMap = (mapId: string) => {
    router.push(`/map?mapId=${mapId}`);
  };

  const handleViewOnMap = (mapId: string) => {
    setOsmMapId(mapId);
  };

  const handleRemoveFromCollection = async (mapId: string) => {
    if (!confirm('Remover este mapa da sua coleção?')) return;

    try {
      setDeletingId(mapId);
      const response = await apiClient.deleteMap(mapId);
      toast.success(response.message || 'Mapa removido da coleção');
      trackMapEvent('map_remove', { map_id: mapId });
      loadMyMaps();
    } catch (error) {
      console.error('Error removing map:', error);
      toast.error('Erro ao remover mapa');
    } finally {
      setDeletingId(null);
    }
  };

  const MapCard = ({ map }: { map: SavedMap }) => {
    return (
      <MapCardBase map={map}>
        <Button
          onClick={() => handleOpenMap(map.id)}
          className="flex-1"
          size="sm"
        >
          <FolderOpen className="h-4 w-4 mr-1" />
          Abrir
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
        <Button
          onClick={() => handleRemoveFromCollection(map.id)}
          size="sm"
          variant="destructive"
          disabled={deletingId === map.id}
          className="px-3"
          title="Remover da coleção"
        >
          {deletingId === map.id ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <Trash2 className="h-4 w-4" />
          )}
        </Button>
      </MapCardBase>
    );
  };

  if (loading) {
    return (
      <div className="container mx-auto p-6">
        <div className="flex items-center justify-center min-h-[400px]">
          <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center p-4">
        <div className="text-center max-w-md w-full">
          <div className="text-6xl mb-4">!</div>
          <h2 className="text-xl font-bold text-gray-900 mb-2">Erro ao carregar mapas</h2>
          <p className="text-sm text-gray-600 mb-4">{error}</p>
          <Button onClick={() => loadMyMaps()}>Tentar Novamente</Button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="sticky top-0 z-20 bg-white border-b border-gray-200 shadow-sm">
        <div className="max-w-6xl mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <Map className="h-6 w-6 text-blue-600" />
              <div>
                <h1 className="text-xl font-bold text-gray-900">Meus Mapas</h1>
                <p className="text-xs text-gray-600">
                  {myMaps.length} {myMaps.length === 1 ? 'mapa' : 'mapas'} na sua coleção
                </p>
              </div>
            </div>
            <Button
              onClick={() => router.push('/search')}
              size="sm"
              className="text-xs"
            >
              <Plus className="h-4 w-4 mr-1" />
              Novo Mapa
            </Button>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-6xl mx-auto px-4 py-4 lg:py-8">
        {myMaps.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-16 px-4 text-center">
            <Map className="h-20 w-20 text-gray-300 mb-4" />
            <h2 className="text-lg font-semibold text-gray-700 mb-2">Nenhum mapa na sua coleção</h2>
            <p className="text-sm text-gray-500 mb-6 max-w-xs">
              Crie um novo mapa ou selecione um mapa existente
            </p>
            <Button onClick={() => router.push('/search')}>
              <Plus className="h-4 w-4 mr-1" />
              Criar ou Selecionar Mapa
            </Button>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 pb-20">
            {myMaps.map((map) => (
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
