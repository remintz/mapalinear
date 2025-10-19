"use client";

import React, { useState, useEffect } from 'react';
import { Card, CardContent, Button } from '@/components/ui';
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
  const router = useRouter();

  const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001/api';

  // Load saved maps on mount
  useEffect(() => {
    loadMaps();
  }, []);

  const loadMaps = async () => {
    try {
      setLoading(true);
      const response = await fetch(`${API_URL}/maps`);

      if (!response.ok) {
        throw new Error('Erro ao carregar mapas salvos');
      }

      const data = await response.json();
      setMaps(data);
    } catch (error) {
      console.error('Error loading maps:', error);
      toast.error('Erro ao carregar mapas salvos');
    } finally {
      setLoading(false);
    }
  };

  const handleOpenMap = (mapId: string) => {
    // Navigate to map page to view the saved map
    router.push(`/map?mapId=${mapId}`);
  };

  const handleDeleteMap = async (mapId: string) => {
    if (!confirm('Tem certeza que deseja deletar este mapa?')) {
      return;
    }

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
    if (!confirm('Tem certeza que deseja regenerar este mapa? O mapa atual será substituído.')) {
      return;
    }

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
    const date = new Date(dateString);
    return new Intl.DateTimeFormat('pt-BR', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    }).format(date);
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

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Mobile-First Header - Sticky */}
      <header className="sticky top-0 z-20 bg-white border-b border-gray-200 shadow-sm">
        <div className="px-4 py-4">
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

      {/* Main Content */}
      <main className="px-4 py-4">
        {maps.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-16 px-4 text-center">
            <Map className="h-20 w-20 text-gray-300 mb-4" />
            <h2 className="text-lg font-semibold text-gray-700 mb-2">Nenhum mapa salvo</h2>
            <p className="text-sm text-gray-500 mb-6 max-w-xs">
              Crie seu primeiro mapa linear para começar
            </p>
            <Button onClick={() => router.push('/search')}>
              Criar Novo Mapa
            </Button>
          </div>
        ) : (
          <div className="space-y-3 pb-20">
            {maps.map((map) => (
              <Card key={map.id} className="hover:shadow-md transition-shadow">
                <CardContent className="p-4">
                  {/* Route Info */}
                  <div className="mb-3">
                    <h3 className="text-base font-semibold text-gray-900 mb-1">
                      {map.origin} → {map.destination}
                    </h3>
                    <div className="flex items-center gap-3 text-xs text-gray-600">
                      <span className="flex items-center gap-1">
                        <Calendar className="h-3 w-3" />
                        {formatDate(map.creation_date)}
                      </span>
                      <span className="flex items-center gap-1">
                        <MapPin className="h-3 w-3" />
                        {map.milestone_count} POIs
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
