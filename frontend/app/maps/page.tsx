"use client";

import React, { useState, useEffect } from 'react';
import { Card, CardContent } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/badge';
import {
  Map,
  Trash2,
  RefreshCw,
  FolderOpen,
  Calendar,
  MapPin,
  Loader2
} from 'lucide-react';
import { toast } from 'sonner';
import { useRouter } from 'next/navigation';

interface SavedMap {
  id: string;
  name: string | null;
  origin: string;
  destination: string;
  total_length_km: number;
  creation_date: string;
  road_refs: string[];
  milestone_count: number;
}

export default function SavedMapsPage() {
  const [maps, setMaps] = useState<SavedMap[]>([]);
  const [loading, setLoading] = useState(true);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [regeneratingId, setRegeneratingId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [debugLogs, setDebugLogs] = useState<string[]>([]);
  const [API_URL, setAPI_URL] = useState<string | null>(null);
  const router = useRouter();

  const addDebugLog = (message: string) => {
    setDebugLogs(prev => [...prev, `${new Date().toLocaleTimeString()}: ${message}`]);
    console.log(message);
  };

  // Detect API URL on client side
  useEffect(() => {
    addDebugLog('[INIT] Detecting API URL...');

    // Always use auto-detection based on window.location
    // This ensures the frontend works when accessed via IP address
    const protocol = window.location.protocol;
    const hostname = window.location.hostname;
    const detectedUrl = `${protocol}//${hostname}:8001/api`;

    addDebugLog(`[INIT] protocol: ${protocol}`);
    addDebugLog(`[INIT] hostname: ${hostname}`);
    addDebugLog(`[INIT] Detected URL: ${detectedUrl}`);

    setAPI_URL(detectedUrl);
  }, []);

  // Load saved maps when API_URL is ready
  useEffect(() => {
    // Only load when API_URL has been detected (not null)
    if (API_URL) {
      addDebugLog(`useEffect triggered, API_URL: ${API_URL}`);
      try {
        loadMaps();
      } catch (error) {
        console.error('Error in useEffect:', error);
        setLoading(false);
        setMaps([]);
      }
    } else {
      addDebugLog('Waiting for API_URL to be detected...');
    }
  }, [API_URL]);

  const loadMaps = async () => {
    try {
      setLoading(true);
      setError(null);

      addDebugLog('1. Iniciando carregamento');
      addDebugLog(`2. API_URL: ${API_URL}`);
      addDebugLog(`3. Full URL: ${API_URL}/maps`);

      const response = await fetch(`${API_URL}/maps`);
      addDebugLog(`4. Fetch completo, status: ${response.status}`);

      if (!response.ok) {
        addDebugLog('5. Response não OK');
        throw new Error(`Erro ${response.status}: ${response.statusText}`);
      }

      addDebugLog('6. Response OK, fazendo parse JSON');
      const data = await response.json();
      addDebugLog(`7. JSON parseado, ${data.length} mapas encontrados`);

      setMaps(data);
      addDebugLog('8. Maps setados com sucesso');
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Erro desconhecido';
      addDebugLog(`❌ Erro: ${errorMessage}`);
      addDebugLog(`❌ Error type: ${typeof error}`);
      if (error instanceof Error && error.stack) {
        addDebugLog(`❌ Stack: ${error.stack.substring(0, 200)}`);
      }
      setError(errorMessage);
      toast.error(`Erro ao carregar mapas: ${errorMessage}`);
      setMaps([]);
    } finally {
      setLoading(false);
      addDebugLog('9. Loading finalizado');
    }
  };

  const handleOpenMap = (mapId: string) => {
    // Navigate to map page to view the saved map
    router.push(`/map?mapId=${mapId}`);
  };

  const handleDeleteMap = async (mapId: string) => {
    try {
      setDeletingId(mapId);
      const response = await fetch(`${API_URL}/maps/${mapId}`, {
        method: 'DELETE',
      });

      if (!response.ok) {
        throw new Error('Erro ao deletar mapa');
      }

      toast.success('Mapa deletado com sucesso');
      // Reload maps list
      loadMaps();
    } catch (error) {
      console.error('Error deleting map:', error);
      toast.error('Erro ao deletar mapa');
    } finally {
      setDeletingId(null);
    }
  };

  const handleRegenerateMap = async (mapId: string) => {
    try {
      setRegeneratingId(mapId);
      const response = await fetch(`${API_URL}/maps/${mapId}/regenerate`, {
        method: 'POST',
      });

      if (!response.ok) {
        throw new Error('Erro ao regenerar mapa');
      }

      const data = await response.json();
      toast.success('Regeneração iniciada! Acompanhe o progresso.');

      // Navigate to map page to show progress
      router.push(`/map?operationId=${data.operation_id}`);
    } catch (error) {
      console.error('Error regenerating map:', error);
      toast.error('Erro ao regenerar mapa');
    } finally {
      setRegeneratingId(null);
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
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
      }).format(date);
    } catch (error) {
      console.error('Error formatting date:', error);
      return 'Data inválida';
    }
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
        <div className="text-center max-w-2xl w-full">
          <div className="text-6xl mb-4">⚠️</div>
          <h2 className="text-xl font-bold text-gray-900 mb-2">Erro ao carregar mapas</h2>
          <p className="text-sm text-gray-600 mb-4">{error}</p>
          <Button onClick={() => loadMaps()} className="mb-6">Tentar Novamente</Button>

          {/* Debug Logs */}
          <div className="bg-black text-green-400 p-4 rounded-lg text-left text-xs font-mono max-h-96 overflow-y-auto">
            <div className="font-bold mb-2">Debug Logs:</div>
            {debugLogs.map((log, index) => (
              <div key={index}>{log}</div>
            ))}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header - Responsive */}
      <header className="sticky top-0 z-20 bg-white border-b border-gray-200 shadow-sm">
        <div className="max-w-6xl mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <Map className="h-6 w-6 text-blue-600" />
              <div>
                <h1 className="text-xl font-bold text-gray-900">Mapas Salvos</h1>
                <p className="text-xs text-gray-600">{maps.length} {maps.length === 1 ? 'mapa' : 'mapas'}</p>
              </div>
            </div>
            <Button
              onClick={() => router.push('/search')}
              size="sm"
              className="text-xs"
            >
              + Novo
            </Button>
          </div>
        </div>
      </header>

      {/* Main Content - Centered */}
      <main className="max-w-6xl mx-auto px-4 py-4 lg:py-8">
        {maps.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-16 px-4 text-center">
            <Map className="h-20 w-20 text-gray-300 mb-4" />
            <h2 className="text-lg font-semibold text-gray-700 mb-2">Nenhum mapa salvo</h2>
            <p className="text-sm text-gray-500 mb-6 max-w-xs">
              Crie seu primeiro mapa para começar
            </p>
            <Button onClick={() => router.push('/search')}>
              Criar Novo Mapa
            </Button>
          </div>
        ) : (
          /* Grid layout - 1 column on mobile, 2 on tablet, 3 on desktop */
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 pb-20">
            {maps.map((map) => (
              <Card key={map.id} className="hover:shadow-md transition-shadow">
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
                    <Button
                      onClick={() => handleOpenMap(map.id)}
                      className="flex-1"
                      size="sm"
                    >
                      <FolderOpen className="h-4 w-4 mr-1" />
                      Abrir
                    </Button>
                    <Button
                      onClick={() => handleRegenerateMap(map.id)}
                      size="sm"
                      variant="outline"
                      disabled={regeneratingId === map.id}
                      className="px-3"
                    >
                      {regeneratingId === map.id ? (
                        <Loader2 className="h-4 w-4 animate-spin" />
                      ) : (
                        <RefreshCw className="h-4 w-4" />
                      )}
                    </Button>
                    <Button
                      onClick={() => handleDeleteMap(map.id)}
                      size="sm"
                      variant="destructive"
                      disabled={deletingId === map.id}
                      className="px-3"
                    >
                      {deletingId === map.id ? (
                        <Loader2 className="h-4 w-4 animate-spin" />
                      ) : (
                        <Trash2 className="h-4 w-4" />
                      )}
                    </Button>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </main>
    </div>
  );
}
