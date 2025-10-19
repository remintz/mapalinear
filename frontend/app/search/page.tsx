'use client';

import React, { useEffect } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import { SearchForm } from '@/components/forms/SearchForm';
import { useAsyncRouteSearch } from '@/hooks/useAsyncRouteSearch';
import { ArrowLeft } from 'lucide-react';
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
    <div className="min-h-screen bg-gray-50">
      {/* Mobile-First Header - Sticky */}
      <header className="sticky top-0 z-20 bg-white border-b border-gray-200 shadow-sm">
        <div className="px-4 py-4">
          <div className="flex items-center gap-3 mb-2">
            <Link
              href="/"
              className="text-blue-600 hover:text-blue-700"
            >
              <ArrowLeft className="h-5 w-5" />
            </Link>
            <div>
              <h1 className="text-xl font-bold text-gray-900">Criar Mapa</h1>
              <p className="text-sm text-gray-600">Configure sua rota</p>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="px-4 py-6">
        {/* Search Form */}
        <div className="mb-6">
          <SearchForm
            onSubmit={handleSearch}
            isLoading={isLoading}
            error={error}
            progressMessage={progressMessage}
            progressPercent={progressPercent}
            estimatedCompletion={estimatedCompletion}
          />
        </div>

        {/* Quick Help - Only show when not loading */}
        {!isLoading && (
          <div className="max-w-2xl mx-auto">
            <div className="p-4 bg-blue-50 rounded-lg border border-blue-100">
              <h3 className="text-sm font-semibold text-blue-900 mb-2">💡 Dica rápida</h3>
              <p className="text-xs text-blue-700">
                Digite cidades no formato <strong>Cidade, UF</strong> (ex: São Paulo, SP).
                Ajuste a distância máxima para encontrar POIs próximos à rota.
              </p>
            </div>

            {/* Link to saved maps */}
            <div className="mt-6 text-center">
              <Link
                href="/maps"
                className="text-sm text-gray-600 hover:text-gray-800 underline"
              >
                Ver mapas salvos
              </Link>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
