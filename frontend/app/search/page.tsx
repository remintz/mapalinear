'use client';

import React, { useEffect } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui';
import { SearchForm } from '@/components/forms/SearchForm';
import { useAsyncRouteSearch } from '@/hooks/useAsyncRouteSearch';
import { ArrowLeft, Bug } from 'lucide-react';
import Link from 'next/link';

export default function SearchPage() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const operationId = searchParams.get('operationId');

  const { searchRoute, isLoading, error, data, progressMessage, progressPercent, estimatedCompletion } = useAsyncRouteSearch();

  // Redirect to map page when data is available
  useEffect(() => {
    if (data && (data as any).id) {
      // Mapa criado com sucesso, redirecionar para visualização com o mapId
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
            Criar Mapa
          </h1>
          <p className="text-lg text-gray-600">
            Digite sua origem e destino para criar um mapa linear da rota.
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

        {/* Instructions */}
        {!isLoading && (
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
                  <p>Aguarde enquanto criamos seu mapa linear personalizado</p>
                </div>
                <div className="flex items-start gap-3">
                  <span className="flex-shrink-0 w-6 h-6 bg-blue-100 text-blue-600 rounded-full flex items-center justify-center text-xs font-semibold">5</span>
                  <p>Você será redirecionado automaticamente para visualizar e filtrar os pontos de interesse</p>
                </div>
              </div>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
}
