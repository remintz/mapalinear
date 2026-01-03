"use client";

import { useSession } from "next-auth/react";
import { useRouter } from "next/navigation";
import { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import {
  Activity,
  ArrowLeft,
  Loader2,
  RefreshCw,
  CheckCircle,
  XCircle,
  AlertCircle,
  Filter,
  ChevronLeft,
  ChevronRight,
  Ban,
} from "lucide-react";
import { toast } from "sonner";
import { AdminOperation, AdminOperationStats } from "@/lib/types";
import { apiClient } from "@/lib/api";

const PAGE_SIZE = 20;

export default function AdminOperationsPage() {
  const { data: session, status } = useSession();
  const router = useRouter();
  const [operations, setOperations] = useState<AdminOperation[]>([]);
  const [stats, setStats] = useState<AdminOperationStats | null>(null);
  const [total, setTotal] = useState(0);
  const [currentPage, setCurrentPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState<string>("");
  const [autoRefresh, setAutoRefresh] = useState(true);

  const totalPages = Math.ceil(total / PAGE_SIZE);

  const fetchOperations = useCallback(async (page: number = currentPage) => {
    try {
      setError(null);

      const data = await apiClient.getAdminOperations({
        status: statusFilter || undefined,
        skip: (page - 1) * PAGE_SIZE,
        limit: PAGE_SIZE,
      });
      setOperations(data.operations);
      setStats(data.stats);
      setTotal(data.total);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erro desconhecido");
    } finally {
      setLoading(false);
    }
  }, [statusFilter, currentPage]);

  useEffect(() => {
    if (status === "loading") return;

    if (!session?.user?.isAdmin) {
      router.push("/");
      return;
    }

    fetchOperations(currentPage);
  }, [session, status, router, fetchOperations, currentPage]);

  // Reset to page 1 when filter changes
  useEffect(() => {
    setCurrentPage(1);
  }, [statusFilter]);

  const handlePageChange = (page: number) => {
    if (page < 1 || page > totalPages) return;
    setCurrentPage(page);
    setLoading(true);
  };

  const handleCancelOperation = async (operationId: string) => {
    if (!confirm("Tem certeza que deseja cancelar esta operação?")) return;

    try {
      const result = await apiClient.cancelOperation(operationId);
      if (result.success) {
        toast.success(result.message);
        fetchOperations(currentPage);
      } else {
        toast.error(result.message);
      }
    } catch (err) {
      toast.error("Erro ao cancelar operação");
    }
  };

  // Auto-refresh for in_progress operations
  useEffect(() => {
    if (!autoRefresh) return;

    const hasInProgress = operations.some((op) => op.status === "in_progress");
    if (!hasInProgress) return;

    const interval = setInterval(fetchOperations, 3000);
    return () => clearInterval(interval);
  }, [autoRefresh, operations, fetchOperations]);

  const formatDate = (dateString: string | null | undefined) => {
    if (!dateString) return "N/A";
    return new Date(dateString).toLocaleDateString("pt-BR", {
      day: "2-digit",
      month: "2-digit",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  const formatDuration = (seconds: number | undefined | null) => {
    if (!seconds) return "N/A";
    if (seconds < 60) return `${Math.round(seconds)}s`;
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = Math.round(seconds % 60);
    if (minutes < 60) return `${minutes}m ${remainingSeconds}s`;
    const hours = Math.floor(minutes / 60);
    const remainingMinutes = minutes % 60;
    return `${hours}h ${remainingMinutes}m`;
  };

  const formatDistance = (km: number | undefined | null) => {
    if (!km) return "N/A";
    return `${km.toFixed(1)} km`;
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case "in_progress":
        return <Loader2 className="w-4 h-4 animate-spin text-blue-500" />;
      case "completed":
        return <CheckCircle className="w-4 h-4 text-green-500" />;
      case "failed":
        return <XCircle className="w-4 h-4 text-red-500" />;
      default:
        return <AlertCircle className="w-4 h-4 text-gray-500" />;
    }
  };

  const getStatusBadgeClass = (status: string) => {
    switch (status) {
      case "in_progress":
        return "bg-blue-100 text-blue-800";
      case "completed":
        return "bg-green-100 text-green-800";
      case "failed":
        return "bg-red-100 text-red-800";
      default:
        return "bg-gray-100 text-gray-800";
    }
  };

  const getStatusLabel = (status: string) => {
    switch (status) {
      case "in_progress":
        return "Em andamento";
      case "completed":
        return "Concluído";
      case "failed":
        return "Falhou";
      default:
        return status;
    }
  };

  const getOperationTypeLabel = (type: string) => {
    switch (type) {
      case "linear_map":
        return "Novo mapa";
      case "map_regeneration":
        return "Regeneração";
      default:
        return type;
    }
  };

  const getOperationTypeBadgeClass = (type: string) => {
    switch (type) {
      case "linear_map":
        return "bg-indigo-100 text-indigo-800";
      case "map_regeneration":
        return "bg-amber-100 text-amber-800";
      default:
        return "bg-gray-100 text-gray-800";
    }
  };

  if (status === "loading" || loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="flex items-center gap-3">
          <Loader2 className="w-6 h-6 animate-spin text-blue-600" />
          <span className="text-gray-600">Carregando...</span>
        </div>
      </div>
    );
  }

  if (!session?.user?.isAdmin) {
    return null;
  }

  return (
    <div className="min-h-screen bg-gray-50 py-8">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="mb-8">
          <Link
            href="/admin"
            className="inline-flex items-center gap-2 text-gray-600 hover:text-gray-900 mb-4"
          >
            <ArrowLeft className="w-4 h-4" />
            Voltar para Administração
          </Link>

          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold text-gray-900 flex items-center gap-3">
                <Activity className="w-8 h-8 text-indigo-600" />
                Operações de Geração de Mapas
              </h1>
              <p className="mt-2 text-gray-600">
                {total} operaç{total !== 1 ? "ões" : "ão"} encontrada{total !== 1 ? "s" : ""}
              </p>
            </div>
            <div className="flex items-center gap-4">
              <label className="flex items-center gap-2 text-sm text-gray-600">
                <input
                  type="checkbox"
                  checked={autoRefresh}
                  onChange={(e) => setAutoRefresh(e.target.checked)}
                  className="rounded border-gray-300"
                />
                Auto-atualizar
              </label>
              <button
                onClick={() => fetchOperations()}
                className="inline-flex items-center gap-2 px-3 py-2 bg-white border border-gray-300 rounded-md text-sm font-medium text-gray-700 hover:bg-gray-50"
              >
                <RefreshCw className="w-4 h-4" />
                Atualizar
              </button>
            </div>
          </div>
        </div>

        {/* Stats Cards */}
        {stats && (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
            <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
              <div className="flex items-center gap-2 text-gray-500 text-sm mb-1">
                <Activity className="w-4 h-4" />
                Total
              </div>
              <div className="text-2xl font-bold text-gray-900">{stats.total}</div>
            </div>
            <div className="bg-white rounded-lg shadow-sm border border-blue-200 p-4">
              <div className="flex items-center gap-2 text-blue-600 text-sm mb-1">
                <Loader2 className="w-4 h-4" />
                Em andamento
              </div>
              <div className="text-2xl font-bold text-blue-600">{stats.in_progress}</div>
            </div>
            <div className="bg-white rounded-lg shadow-sm border border-green-200 p-4">
              <div className="flex items-center gap-2 text-green-600 text-sm mb-1">
                <CheckCircle className="w-4 h-4" />
                Concluídos
              </div>
              <div className="text-2xl font-bold text-green-600">{stats.completed}</div>
            </div>
            <div className="bg-white rounded-lg shadow-sm border border-red-200 p-4">
              <div className="flex items-center gap-2 text-red-600 text-sm mb-1">
                <XCircle className="w-4 h-4" />
                Falharam
              </div>
              <div className="text-2xl font-bold text-red-600">{stats.failed}</div>
            </div>
          </div>
        )}

        {/* Filter */}
        <div className="mb-6 flex items-center gap-4">
          <div className="flex items-center gap-2">
            <Filter className="w-4 h-4 text-gray-500" />
            <select
              value={statusFilter}
              onChange={(e) => {
                setStatusFilter(e.target.value);
                setLoading(true);
              }}
              className="border border-gray-300 rounded-md px-3 py-2 text-sm"
            >
              <option value="">Todos os status</option>
              <option value="in_progress">Em andamento</option>
              <option value="completed">Concluídos</option>
              <option value="failed">Falharam</option>
            </select>
          </div>
        </div>

        {error && (
          <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg text-red-700">
            {error}
          </div>
        )}

        <div className="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-3 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider w-20">
                    Status
                  </th>
                  <th className="px-3 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Rota
                  </th>
                  <th className="px-3 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Solicitante
                  </th>
                  <th className="px-3 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Início
                  </th>
                  <th className="px-3 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Duração
                  </th>
                  <th className="px-3 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Progresso
                  </th>
                  <th className="px-3 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider w-16">
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {operations.map((op) => (
                  <tr
                    key={op.id}
                    className={`hover:bg-gray-50 ${op.status === "failed" ? "bg-red-50" : ""}`}
                  >
                    <td className="px-3 py-3 whitespace-nowrap">
                      <div className="flex items-center gap-1">
                        <span
                          className={`inline-flex items-center p-1.5 rounded-full ${getStatusBadgeClass(op.status)}`}
                          title={getStatusLabel(op.status)}
                        >
                          {getStatusIcon(op.status)}
                        </span>
                        <span
                          className={`text-xs font-medium px-1.5 py-0.5 rounded ${getOperationTypeBadgeClass(op.operation_type)}`}
                          title={getOperationTypeLabel(op.operation_type)}
                        >
                          {op.operation_type === "linear_map" ? "Novo" : "Regen"}
                        </span>
                      </div>
                    </td>
                    <td className="px-3 py-3">
                      {op.origin && op.destination ? (
                        <div>
                          <div className="text-sm font-medium text-gray-900">
                            {op.origin}
                          </div>
                          <div className="text-sm text-gray-500">
                            → {op.destination}
                          </div>
                          {op.total_length_km && (
                            <div className="text-xs text-gray-400">
                              {formatDistance(op.total_length_km)}
                            </div>
                          )}
                        </div>
                      ) : (
                        <span className="text-gray-400 text-sm italic">
                          {op.status === "in_progress" ? "Calculando..." : "N/A"}
                        </span>
                      )}
                    </td>
                    <td className="px-3 py-3 whitespace-nowrap">
                      {op.user ? (
                        <div>
                          <div className="text-sm text-gray-900">{op.user.name}</div>
                          <div className="text-xs text-gray-500">{op.user.email}</div>
                        </div>
                      ) : (
                        <span className="text-gray-400 text-sm">—</span>
                      )}
                    </td>
                    <td className="px-3 py-3 whitespace-nowrap text-sm text-gray-600">
                      {formatDate(op.started_at)}
                    </td>
                    <td className="px-3 py-3 whitespace-nowrap text-sm text-gray-600">
                      {op.status === "in_progress" ? (
                        <span className="text-blue-600">—</span>
                      ) : (
                        formatDuration(op.duration_seconds)
                      )}
                    </td>
                    <td className="px-3 py-3 whitespace-nowrap max-w-[200px]">
                      {op.status === "in_progress" ? (
                        <div className="w-24">
                          <div className="flex items-center justify-between text-xs text-gray-600 mb-1">
                            <span>{Math.round(op.progress_percent)}%</span>
                          </div>
                          <div className="w-full bg-gray-200 rounded-full h-1.5">
                            <div
                              className="bg-blue-600 h-1.5 rounded-full transition-all duration-300"
                              style={{ width: `${op.progress_percent}%` }}
                            />
                          </div>
                        </div>
                      ) : op.status === "completed" ? (
                        <span className="text-green-600 text-sm">100%</span>
                      ) : (
                        <span
                          className={`text-red-600 text-xs truncate block ${
                            (op.error?.length || 0) > 30 ? "cursor-help underline decoration-dotted" : ""
                          }`}
                          title={(op.error?.length || 0) > 30 ? op.error : undefined}
                        >
                          {op.error || "Erro desconhecido"}
                        </span>
                      )}
                    </td>
                    <td className="px-3 py-3 whitespace-nowrap">
                      {op.status === "in_progress" && (
                        <button
                          onClick={() => handleCancelOperation(op.id)}
                          className="p-1 text-red-600 hover:text-red-800 hover:bg-red-50 rounded"
                          title="Cancelar operação"
                        >
                          <Ban className="w-4 h-4" />
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {operations.length === 0 && !loading && (
            <div className="text-center py-12">
              <Activity className="mx-auto h-12 w-12 text-gray-400" />
              <h3 className="mt-2 text-sm font-medium text-gray-900">
                Nenhuma operação encontrada
              </h3>
              <p className="mt-1 text-sm text-gray-500">
                {statusFilter
                  ? "Nenhuma operação corresponde ao filtro selecionado."
                  : "Não há operações de geração de mapas registradas."}
              </p>
            </div>
          )}

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="px-6 py-4 border-t border-gray-200 flex items-center justify-between">
              <div className="text-sm text-gray-500">
                Mostrando {((currentPage - 1) * PAGE_SIZE) + 1} a {Math.min(currentPage * PAGE_SIZE, total)} de {total} operações
              </div>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => handlePageChange(currentPage - 1)}
                  disabled={currentPage === 1}
                  className="p-2 rounded-md border border-gray-300 disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-50"
                >
                  <ChevronLeft className="w-4 h-4" />
                </button>

                {/* Page numbers */}
                <div className="flex items-center gap-1">
                  {Array.from({ length: totalPages }, (_, i) => i + 1)
                    .filter(page => {
                      // Show first, last, current, and pages around current
                      if (page === 1 || page === totalPages) return true;
                      if (Math.abs(page - currentPage) <= 1) return true;
                      return false;
                    })
                    .map((page, index, arr) => {
                      // Add ellipsis if there's a gap
                      const showEllipsisBefore = index > 0 && page - arr[index - 1] > 1;
                      return (
                        <span key={page} className="flex items-center">
                          {showEllipsisBefore && (
                            <span className="px-2 text-gray-400">...</span>
                          )}
                          <button
                            onClick={() => handlePageChange(page)}
                            className={`px-3 py-1 rounded-md text-sm ${
                              page === currentPage
                                ? "bg-indigo-600 text-white"
                                : "border border-gray-300 hover:bg-gray-50"
                            }`}
                          >
                            {page}
                          </button>
                        </span>
                      );
                    })}
                </div>

                <button
                  onClick={() => handlePageChange(currentPage + 1)}
                  disabled={currentPage === totalPages}
                  className="p-2 rounded-md border border-gray-300 disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-50"
                >
                  <ChevronRight className="w-4 h-4" />
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
