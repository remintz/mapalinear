'use client';

import React, { useState, useEffect } from 'react';
import { Button, Card, CardHeader, CardTitle, CardContent } from '@/components/ui';
import { ArrowLeft } from 'lucide-react';
import Link from 'next/link';
import { toast } from 'sonner';
import dynamic from 'next/dynamic';
import { apiClient, DebugSegmentsData } from '@/lib/api';

// Importar o mapa dinamicamente para evitar SSR issues
const SegmentsMap = dynamic(() => import('./SegmentsMap'), {
  ssr: false,
  loading: () => <div className="h-[600px] bg-gray-100 animate-pulse rounded-lg flex items-center justify-center">Carregando mapa...</div>
});

export default function DebugSegmentsPage() {
  const [isLoading, setIsLoading] = useState(true);
  const [debugData, setDebugData] = useState<DebugSegmentsData | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const loadSegments = async () => {
      setIsLoading(true);
      setError(null);

      try {
        const data = await apiClient.getDebugSegments();
        setDebugData(data);
      } catch (error) {
        // apiClient handles 401 automatically and redirects to login
        console.error('Erro:', error);
        const errorMessage = error instanceof Error ? error.message : 'Erro ao buscar segmentos';
        setError(errorMessage);
        toast.error(errorMessage);
      } finally {
        setIsLoading(false);
      }
    };

    loadSegments();
  }, []);

  return (
    <div className="container mx-auto px-4 py-8">
      {/* Header */}
      <div className="mb-8">
        <Link href="/search" className="inline-flex items-center text-blue-600 hover:text-blue-800 mb-4">
          <ArrowLeft className="w-4 h-4 mr-2" />
          Voltar para Busca
        </Link>
        <h1 className="text-3xl font-bold text-gray-900">
          🔍 Debug: Visualizar Segmentos da Rota
        </h1>
        <p className="text-gray-600 mt-2">
          Mostrando os segmentos do último mapa gerado.
          Use para debugar se os pontos de interesse estão sendo corretamente associados aos segmentos.
        </p>
      </div>

      {/* Loading State */}
      {isLoading && (
        <Card>
          <CardContent className="py-12">
            <div className="flex flex-col items-center justify-center">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mb-4"></div>
              <p className="text-gray-600">Carregando segmentos...</p>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Error State */}
      {error && !isLoading && (
        <Card className="border-red-200 bg-red-50">
          <CardHeader>
            <CardTitle className="text-red-800">Erro ao carregar segmentos</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-red-700 mb-4">{error}</p>
            <p className="text-sm text-gray-600">
              Dica: Vá para a página de busca e gere um mapa primeiro.
            </p>
            <Link href="/search" className="inline-block mt-4">
              <Button>Ir para Busca</Button>
            </Link>
          </CardContent>
        </Card>
      )}

      {/* Results */}
      {debugData && !isLoading && (
        <>
          <Card className="mb-8">
            <CardHeader>
              <CardTitle>Informações da Rota</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid md:grid-cols-4 gap-4">
                <div>
                  <p className="text-sm text-gray-600">Origem</p>
                  <p className="font-semibold">{debugData.origin}</p>
                </div>
                <div>
                  <p className="text-sm text-gray-600">Destino</p>
                  <p className="font-semibold">{debugData.destination}</p>
                </div>
                <div>
                  <p className="text-sm text-gray-600">Distância Total</p>
                  <p className="font-semibold">{debugData.total_distance_km.toFixed(2)} km</p>
                </div>
                <div>
                  <p className="text-sm text-gray-600">Total de Segmentos</p>
                  <p className="font-semibold">{debugData.total_segments}</p>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Mapa de Segmentos</CardTitle>
            </CardHeader>
            <CardContent>
              <SegmentsMap segments={debugData.segments} />
            </CardContent>
          </Card>

          {/* Segments List */}
          <Card className="mt-8">
            <CardHeader>
              <CardTitle>Lista de Segmentos</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-2 max-h-96 overflow-y-auto">
                {debugData.segments.map((segment) => (
                  <div key={segment.id} className="p-3 bg-gray-50 rounded-lg">
                    <div className="flex justify-between items-start">
                      <div>
                        <p className="font-semibold">{segment.id}</p>
                        <p className="text-sm text-gray-600">{segment.name}</p>
                      </div>
                      <div className="text-right text-sm">
                        <p className="text-gray-600">
                          {segment.start_distance_km.toFixed(2)} - {segment.end_distance_km.toFixed(2)} km
                        </p>
                        <p className="text-gray-500">
                          Comprimento: {segment.length_km.toFixed(2)} km
                        </p>
                      </div>
                    </div>
                    <div className="mt-2 text-xs text-gray-500">
                      <p>Início: ({segment.start_coordinates.latitude.toFixed(6)}, {segment.start_coordinates.longitude.toFixed(6)})</p>
                      <p>Fim: ({segment.end_coordinates.latitude.toFixed(6)}, {segment.end_coordinates.longitude.toFixed(6)})</p>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </>
      )}
    </div>
  );
}
