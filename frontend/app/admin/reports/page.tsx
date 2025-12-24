'use client';

import { useState, useEffect, useCallback } from 'react';
import { useSession } from 'next-auth/react';
import { useRouter } from 'next/navigation';
import { ArrowLeft, Loader2, AlertTriangle, ChevronRight, MapPin, Calendar, User, Image as ImageIcon, Mic } from 'lucide-react';
import Link from 'next/link';
import { apiClient, ProblemReport } from '@/lib/api';

const STATUS_LABELS: Record<string, { label: string; color: string }> = {
  nova: { label: 'Nova', color: 'bg-blue-100 text-blue-700' },
  em_andamento: { label: 'Em Andamento', color: 'bg-yellow-100 text-yellow-700' },
  concluido: { label: 'Concluido', color: 'bg-green-100 text-green-700' },
};

export default function ReportsPage() {
  const { data: session, status } = useSession();
  const router = useRouter();

  const [reports, setReports] = useState<ProblemReport[]>([]);
  const [total, setTotal] = useState(0);
  const [countsByStatus, setCountsByStatus] = useState<Record<string, number>>({});
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [statusFilter, setStatusFilter] = useState<string | null>(null);
  const [page, setPage] = useState(0);
  const limit = 20;

  // Check admin access
  useEffect(() => {
    if (status === 'loading') return;
    if (!session?.user?.isAdmin) {
      router.push('/');
    }
  }, [session, status, router]);

  // Fetch reports
  const fetchReports = useCallback(async () => {
    setIsLoading(true);
    try {
      const data = await apiClient.getProblemReports({
        skip: page * limit,
        limit,
        status_filter: statusFilter || undefined,
      });
      setReports(data.reports);
      setTotal(data.total);
      setCountsByStatus(data.counts_by_status);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Erro ao carregar reports');
    } finally {
      setIsLoading(false);
    }
  }, [page, statusFilter]);

  useEffect(() => {
    if (session?.user?.isAdmin) {
      fetchReports();
    }
  }, [session, fetchReports]);

  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr);
    return date.toLocaleDateString('pt-BR', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  if (status === 'loading') {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Loader2 className="w-8 h-8 animate-spin text-blue-600" />
      </div>
    );
  }

  if (!session?.user?.isAdmin) {
    return null;
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-6xl mx-auto px-4 py-8">
        {/* Header */}
        <div className="mb-8">
          <Link
            href="/admin"
            className="inline-flex items-center gap-2 text-sm text-gray-600 hover:text-gray-900 mb-4"
          >
            <ArrowLeft className="w-4 h-4" />
            Voltar para Administracao
          </Link>
          <div className="flex items-center gap-3">
            <AlertTriangle className="w-8 h-8 text-amber-500" />
            <div>
              <h1 className="text-2xl font-bold text-gray-900">Reports de Problemas</h1>
              <p className="text-sm text-gray-600">
                Gerencie os problemas reportados pelos usuarios
              </p>
            </div>
          </div>
        </div>

        {/* Status filter tabs */}
        <div className="flex flex-wrap gap-2 mb-6">
          <button
            onClick={() => {
              setStatusFilter(null);
              setPage(0);
            }}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
              statusFilter === null
                ? 'bg-gray-900 text-white'
                : 'bg-white text-gray-600 hover:bg-gray-100 border border-gray-200'
            }`}
          >
            Todos ({total})
          </button>
          {Object.entries(STATUS_LABELS).map(([key, { label }]) => (
            <button
              key={key}
              onClick={() => {
                setStatusFilter(key);
                setPage(0);
              }}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                statusFilter === key
                  ? 'bg-gray-900 text-white'
                  : `bg-white text-gray-600 hover:bg-gray-100 border border-gray-200`
              }`}
            >
              {label} ({countsByStatus[key] || 0})
            </button>
          ))}
        </div>

        {/* Error */}
        {error && (
          <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg text-red-700">
            {error}
          </div>
        )}

        {/* Loading */}
        {isLoading ? (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="w-8 h-8 animate-spin text-blue-600" />
          </div>
        ) : reports.length === 0 ? (
          <div className="bg-white border border-gray-200 rounded-lg p-12 text-center">
            <AlertTriangle className="w-12 h-12 text-gray-400 mx-auto mb-4" />
            <p className="text-gray-600">Nenhum report encontrado</p>
          </div>
        ) : (
          <>
            {/* Reports list */}
            <div className="bg-white border border-gray-200 rounded-lg shadow-sm overflow-hidden">
              <div className="divide-y divide-gray-200">
                {reports.map((report) => (
                  <Link
                    key={report.id}
                    href={`/admin/reports/${report.id}`}
                    className="block p-4 hover:bg-gray-50 transition-colors"
                  >
                    <div className="flex items-start justify-between gap-4">
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-2">
                          <span
                            className={`px-2 py-0.5 text-xs font-medium rounded-full ${
                              STATUS_LABELS[report.status]?.color || 'bg-gray-100 text-gray-700'
                            }`}
                          >
                            {STATUS_LABELS[report.status]?.label || report.status}
                          </span>
                          <span className="text-sm font-medium text-gray-900">
                            {report.problem_type.name}
                          </span>
                        </div>

                        <p className="text-sm text-gray-600 line-clamp-2 mb-2">
                          {report.description}
                        </p>

                        <div className="flex flex-wrap items-center gap-4 text-xs text-gray-500">
                          <span className="flex items-center gap-1">
                            <User className="w-3 h-3" />
                            {report.user.name}
                          </span>
                          <span className="flex items-center gap-1">
                            <Calendar className="w-3 h-3" />
                            {formatDate(report.created_at)}
                          </span>
                          {report.map && (
                            <span className="flex items-center gap-1">
                              <MapPin className="w-3 h-3" />
                              {report.map.origin} → {report.map.destination}
                            </span>
                          )}
                          {report.attachment_count > 0 && (
                            <span className="flex items-center gap-1">
                              {report.attachments.some((a) => a.type === 'image') && (
                                <ImageIcon className="w-3 h-3" />
                              )}
                              {report.attachments.some((a) => a.type === 'audio') && (
                                <Mic className="w-3 h-3" />
                              )}
                              {report.attachment_count} anexo(s)
                            </span>
                          )}
                        </div>
                      </div>

                      <ChevronRight className="w-5 h-5 text-gray-400 flex-shrink-0" />
                    </div>
                  </Link>
                ))}
              </div>
            </div>

            {/* Pagination */}
            {total > limit && (
              <div className="flex items-center justify-between mt-4">
                <p className="text-sm text-gray-600">
                  Mostrando {page * limit + 1} - {Math.min((page + 1) * limit, total)} de {total}
                </p>
                <div className="flex gap-2">
                  <button
                    onClick={() => setPage((p) => Math.max(0, p - 1))}
                    disabled={page === 0}
                    className="px-4 py-2 text-sm border border-gray-200 rounded-lg
                              hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    Anterior
                  </button>
                  <button
                    onClick={() => setPage((p) => p + 1)}
                    disabled={(page + 1) * limit >= total}
                    className="px-4 py-2 text-sm border border-gray-200 rounded-lg
                              hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    Proximo
                  </button>
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
