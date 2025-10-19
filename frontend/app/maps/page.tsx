"use client";

import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle, Button } from '@/components/ui';
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
    <div className="container mx-auto p-6 max-w-6xl">
      <div className="mb-8">
        <div className="flex items-center gap-3 mb-2">
          <Map className="h-8 w-8 text-blue-600" />
          <h1 className="text-3xl font-bold">Mapas Salvos</h1>
        </div>
        <p className="text-gray-600">Gerencie seus mapas lineares salvos</p>
      </div>

      {maps.length === 0 ? (
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-12">
            <Map className="h-16 w-16 text-gray-300 mb-4" />
            <p className="text-gray-500 text-lg mb-2">Nenhum mapa salvo ainda</p>
            <p className="text-gray-400 text-sm mb-4">
              Crie um novo mapa na página de busca
            </p>
            <Button onClick={() => router.push('/search')}>
              Ir para Busca
            </Button>
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-4">
          {maps.map((map) => (
            <Card key={map.id} className="hover:shadow-lg transition-shadow">
              <CardHeader>
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <CardTitle className="text-xl mb-2">
                      {map.origin} → {map.destination}
                    </CardTitle>
                    <CardDescription className="flex items-center gap-4 text-sm">
                      <span className="flex items-center gap-1">
                        <Calendar className="h-4 w-4" />
                        {formatDate(map.creation_date)}
                      </span>
                      <span className="flex items-center gap-1">
                        <MapPin className="h-4 w-4" />
                        {map.milestone_count} pontos
                      </span>
                    </CardDescription>
                  </div>
                  <Badge variant="secondary" className="bg-blue-100 text-blue-800">
                    {map.total_length_km.toFixed(1)} km
                  </Badge>
                </div>
              </CardHeader>
              <CardContent>
                <div className="flex gap-2">
                  <Button
                    onClick={() => handleOpenMap(map.id)}
                    className="flex-1"
                    variant="default"
                  >
                    <FolderOpen className="h-4 w-4 mr-2" />
                    Abrir
                  </Button>
                  <Button
                    onClick={() => handleRegenerateMap(map.id)}
                    className="flex-1"
                    variant="outline"
                    disabled={regeneratingId === map.id}
                  >
                    {regeneratingId === map.id ? (
                      <>
                        <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                        Regenerando...
                      </>
                    ) : (
                      <>
                        <RefreshCw className="h-4 w-4 mr-2" />
                        Regenerar
                      </>
                    )}
                  </Button>
                  <Button
                    onClick={() => handleDeleteMap(map.id)}
                    variant="destructive"
                    disabled={deletingId === map.id}
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
    </div>
  );
}
