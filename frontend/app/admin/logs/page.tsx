"use client";

import React, { useEffect, useState, useCallback } from "react";
import { useSession } from "next-auth/react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import {
  ArrowLeft,
  Loader2,
  RefreshCw,
  Filter,
  ChevronLeft,
  ChevronRight,
  FileText,
  AlertTriangle,
  AlertCircle,
  Info,
  Bug,
  XCircle,
  Trash2,
  X,
  ChevronDown,
  ChevronUp,
  Search,
} from "lucide-react";
import { toast } from "sonner";
import {
  ApplicationLog,
  ApplicationLogStats,
  LogTimeWindow,
} from "@/lib/types";
import { apiClient } from "@/lib/api";

const PAGE_SIZE = 50;

const TIME_WINDOWS: { value: LogTimeWindow | ""; label: string }[] = [
  { value: "", label: "Todos" },
  { value: "5m", label: "Últimos 5 min" },
  { value: "15m", label: "Últimos 15 min" },
  { value: "1h", label: "Última hora" },
  { value: "24h", label: "Últimas 24h" },
  { value: "custom", label: "Personalizado" },
];

const LOG_LEVELS = ["", "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"];

export default function AdminLogsPage() {
  const { data: session, status } = useSession();
  const router = useRouter();
  const [logs, setLogs] = useState<ApplicationLog[]>([]);
  const [stats, setStats] = useState<ApplicationLogStats | null>(null);
  const [modules, setModules] = useState<string[]>([]);
  const [total, setTotal] = useState(0);
  const [currentPage, setCurrentPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [timeWindow, setTimeWindow] = useState<LogTimeWindow | "">("5m");
  const [levelFilter, setLevelFilter] = useState<string>("");
  const [moduleFilter, setModuleFilter] = useState<string>("");
  const [searchInput, setSearchInput] = useState<string>(""); // Immediate input value
  const [searchFilter, setSearchFilter] = useState<string>(""); // Debounced value for API
  const [userEmailFilter, setUserEmailFilter] = useState<string>("");
  const [sessionIdFilter, setSessionIdFilter] = useState<string>("");
  const [requestIdFilter, setRequestIdFilter] = useState<string>("");
  const [customStartTime, setCustomStartTime] = useState<string>("");
  const [customEndTime, setCustomEndTime] = useState<string>("");

  // UI state
  const [autoRefresh, setAutoRefresh] = useState(false);
  const [expandedLogs, setExpandedLogs] = useState<Set<string>>(new Set());

  const totalPages = Math.ceil(total / PAGE_SIZE);

  const fetchLogs = useCallback(async (page: number = currentPage) => {
    try {
      setError(null);

      const params: Record<string, string | number | undefined> = {
        skip: (page - 1) * PAGE_SIZE,
        limit: PAGE_SIZE,
      };

      if (levelFilter) params.level = levelFilter;
      if (moduleFilter) params.module = moduleFilter;
      if (searchFilter) params.search = searchFilter;
      if (userEmailFilter) params.user_email = userEmailFilter;
      if (sessionIdFilter) params.session_id = sessionIdFilter;
      if (requestIdFilter) params.request_id = requestIdFilter;

      if (timeWindow && timeWindow !== "custom") {
        params.time_window = timeWindow;
      } else if (timeWindow === "custom" && (customStartTime || customEndTime)) {
        params.time_window = "custom";
        if (customStartTime) params.start_time = customStartTime;
        if (customEndTime) params.end_time = customEndTime;
      }

      // Build stats params - only include custom times if they have values
      const statsParams: Record<string, string | undefined> = {};
      if (timeWindow && timeWindow !== "custom") {
        statsParams.time_window = timeWindow;
      } else if (timeWindow === "custom" && (customStartTime || customEndTime)) {
        statsParams.time_window = "custom";
        if (customStartTime) statsParams.start_time = customStartTime;
        if (customEndTime) statsParams.end_time = customEndTime;
      }

      const [logsData, statsData] = await Promise.all([
        apiClient.getApplicationLogs(params),
        apiClient.getApplicationLogStats(statsParams),
      ]);

      setLogs(logsData.logs);
      setTotal(logsData.total);
      setStats(statsData);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erro desconhecido");
    } finally {
      setLoading(false);
    }
  }, [
    currentPage,
    levelFilter,
    moduleFilter,
    searchFilter,
    userEmailFilter,
    sessionIdFilter,
    requestIdFilter,
    timeWindow,
    customStartTime,
    customEndTime,
  ]);

  const fetchModules = useCallback(async () => {
    try {
      const data = await apiClient.getApplicationLogModules();
      setModules(data);
    } catch (err) {
      console.error("Failed to fetch modules:", err);
    }
  }, []);

  useEffect(() => {
    if (status === "loading") return;

    if (!session?.user?.isAdmin) {
      router.push("/");
      return;
    }

    fetchLogs(currentPage);
    fetchModules();
  }, [session, status, router, fetchLogs, fetchModules, currentPage]);

  // Debounce search input
  useEffect(() => {
    const timer = setTimeout(() => {
      setSearchFilter(searchInput);
    }, 300);
    return () => clearTimeout(timer);
  }, [searchInput]);

  // Reset to page 1 when filters change
  useEffect(() => {
    setCurrentPage(1);
    setLoading(true);
  }, [levelFilter, moduleFilter, searchFilter, userEmailFilter, sessionIdFilter, requestIdFilter, timeWindow, customStartTime, customEndTime]);

  // Auto-refresh
  useEffect(() => {
    if (!autoRefresh) return;
    const interval = setInterval(() => fetchLogs(currentPage), 5000);
    return () => clearInterval(interval);
  }, [autoRefresh, fetchLogs, currentPage]);

  const handlePageChange = (page: number) => {
    if (page < 1 || page > totalPages) return;
    setCurrentPage(page);
    setLoading(true);
  };

  const handleCleanup = async () => {
    if (!confirm("Tem certeza que deseja limpar logs com mais de 30 dias?")) return;

    try {
      const result = await apiClient.cleanupApplicationLogs(30);
      toast.success(result.message);
      fetchLogs(currentPage);
    } catch {
      toast.error("Erro ao limpar logs");
    }
  };

  const handleTestError = async () => {
    try {
      const baseUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001/api";
      const apiUrl = baseUrl.replace("/api", "");
      await fetch(`${apiUrl}/api/frontend-errors`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          session_id: crypto.randomUUID(),
          error_type: "test_error",
          message: "Erro de teste simulado pelo administrador",
          url: window.location.href,
        }),
      });
      toast.success("Erro de teste enviado! Aguarde alguns segundos e atualize.");
    } catch {
      toast.error("Falha ao enviar erro de teste");
    }
  };

  const clearFilters = () => {
    setTimeWindow("");
    setLevelFilter("");
    setModuleFilter("");
    setSearchInput("");
    setSearchFilter("");
    setUserEmailFilter("");
    setSessionIdFilter("");
    setRequestIdFilter("");
    setCustomStartTime("");
    setCustomEndTime("");
    setCurrentPage(1);
    setLoading(true);
  };

  const hasActiveFilters = timeWindow || levelFilter || moduleFilter || searchInput || userEmailFilter || sessionIdFilter || requestIdFilter;

  const toggleLogExpanded = (logId: string) => {
    setExpandedLogs(prev => {
      const newSet = new Set(prev);
      if (newSet.has(logId)) {
        newSet.delete(logId);
      } else {
        newSet.add(logId);
      }
      return newSet;
    });
  };

  const formatTimestamp = (timestamp: string) => {
    const date = new Date(timestamp);
    return date.toLocaleString("pt-BR", {
      day: "2-digit",
      month: "2-digit",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
    });
  };

  const formatRelativeTime = (timestamp: string) => {
    const now = new Date();
    const then = new Date(timestamp);
    const diffMs = now.getTime() - then.getTime();
    const diffSecs = Math.floor(diffMs / 1000);
    const diffMins = Math.floor(diffSecs / 60);
    const diffHours = Math.floor(diffMins / 60);
    const diffDays = Math.floor(diffHours / 24);

    if (diffSecs < 60) return `${diffSecs}s atrás`;
    if (diffMins < 60) return `${diffMins}m atrás`;
    if (diffHours < 24) return `${diffHours}h atrás`;
    return `${diffDays}d atrás`;
  };

  const getLevelIcon = (level: string) => {
    switch (level) {
      case "DEBUG":
        return <Bug className="w-4 h-4 text-gray-500" />;
      case "INFO":
        return <Info className="w-4 h-4 text-blue-500" />;
      case "WARNING":
        return <AlertTriangle className="w-4 h-4 text-amber-500" />;
      case "ERROR":
        return <XCircle className="w-4 h-4 text-red-500" />;
      case "CRITICAL":
        return <AlertCircle className="w-4 h-4 text-red-700" />;
      default:
        return <FileText className="w-4 h-4 text-gray-500" />;
    }
  };

  const getLevelBadgeClass = (level: string) => {
    switch (level) {
      case "DEBUG":
        return "bg-gray-100 text-gray-800";
      case "INFO":
        return "bg-blue-100 text-blue-800";
      case "WARNING":
        return "bg-amber-100 text-amber-800";
      case "ERROR":
        return "bg-red-100 text-red-800";
      case "CRITICAL":
        return "bg-red-200 text-red-900 font-bold";
      default:
        return "bg-gray-100 text-gray-800";
    }
  };

  if (status === "loading") {
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
                <FileText className="w-8 h-8 text-indigo-600" />
                Logs da Aplicação
              </h1>
              <p className="mt-2 text-gray-600">
                {total} log{total !== 1 ? "s" : ""} encontrado{total !== 1 ? "s" : ""}
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
                onClick={() => fetchLogs(currentPage)}
                className="inline-flex items-center gap-2 px-3 py-2 bg-white border border-gray-300 rounded-md text-sm font-medium text-gray-700 hover:bg-gray-50"
              >
                <RefreshCw className="w-4 h-4" />
                Atualizar
              </button>
              <button
                onClick={handleTestError}
                className="inline-flex items-center gap-2 px-3 py-2 bg-amber-50 border border-amber-200 rounded-md text-sm font-medium text-amber-700 hover:bg-amber-100"
              >
                <AlertTriangle className="w-4 h-4" />
                Testar Erro
              </button>
              <button
                onClick={handleCleanup}
                className="inline-flex items-center gap-2 px-3 py-2 bg-red-50 border border-red-200 rounded-md text-sm font-medium text-red-700 hover:bg-red-100"
              >
                <Trash2 className="w-4 h-4" />
                Limpar antigos
              </button>
            </div>
          </div>
        </div>

        {/* Stats Cards */}
        {stats && (
          <div className="grid grid-cols-3 md:grid-cols-6 gap-2 mb-4">
            <button
              onClick={() => setLevelFilter("")}
              className={`bg-white rounded-lg shadow-sm border px-3 py-2 text-left hover:bg-gray-50 transition-colors ${
                levelFilter === "" ? "border-gray-400 ring-1 ring-gray-400" : "border-gray-200"
              }`}
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-1 text-gray-500 text-xs">
                  <FileText className="w-3 h-3" />
                  Total
                </div>
                <div className="text-lg font-bold text-gray-900">{stats.total}</div>
              </div>
            </button>
            <button
              onClick={() => setLevelFilter("DEBUG")}
              className={`bg-white rounded-lg shadow-sm border px-3 py-2 text-left hover:bg-gray-50 transition-colors ${
                levelFilter === "DEBUG" ? "border-gray-400 ring-1 ring-gray-400" : "border-gray-200"
              }`}
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-1 text-gray-500 text-xs">
                  <Bug className="w-3 h-3" />
                  Debug
                </div>
                <div className="text-lg font-bold text-gray-500">{stats.debug}</div>
              </div>
            </button>
            <button
              onClick={() => setLevelFilter("INFO")}
              className={`bg-white rounded-lg shadow-sm border px-3 py-2 text-left hover:bg-blue-50 transition-colors ${
                levelFilter === "INFO" ? "border-blue-400 ring-1 ring-blue-400" : "border-blue-200"
              }`}
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-1 text-blue-600 text-xs">
                  <Info className="w-3 h-3" />
                  Info
                </div>
                <div className="text-lg font-bold text-blue-600">{stats.info}</div>
              </div>
            </button>
            <button
              onClick={() => setLevelFilter("WARNING")}
              className={`bg-white rounded-lg shadow-sm border px-3 py-2 text-left hover:bg-amber-50 transition-colors ${
                levelFilter === "WARNING" ? "border-amber-400 ring-1 ring-amber-400" : "border-amber-200"
              }`}
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-1 text-amber-600 text-xs">
                  <AlertTriangle className="w-3 h-3" />
                  Warning
                </div>
                <div className="text-lg font-bold text-amber-600">{stats.warning}</div>
              </div>
            </button>
            <button
              onClick={() => setLevelFilter("ERROR")}
              className={`bg-white rounded-lg shadow-sm border px-3 py-2 text-left hover:bg-red-50 transition-colors ${
                levelFilter === "ERROR" ? "border-red-400 ring-1 ring-red-400" : "border-red-200"
              }`}
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-1 text-red-600 text-xs">
                  <XCircle className="w-3 h-3" />
                  Error
                </div>
                <div className="text-lg font-bold text-red-600">{stats.error}</div>
              </div>
            </button>
            <button
              onClick={() => setLevelFilter("CRITICAL")}
              className={`bg-white rounded-lg shadow-sm border px-3 py-2 text-left hover:bg-red-100 transition-colors ${
                levelFilter === "CRITICAL" ? "border-red-500 ring-1 ring-red-500" : "border-red-300"
              }`}
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-1 text-red-700 text-xs">
                  <AlertCircle className="w-3 h-3" />
                  Critical
                </div>
                <div className="text-lg font-bold text-red-700">{stats.critical}</div>
              </div>
            </button>
          </div>
        )}

        {/* Filters */}
        <div className="mb-6 bg-white rounded-lg shadow-sm border border-gray-200 p-4">
          <div className="flex items-center gap-2 mb-4">
            <Filter className="w-4 h-4 text-gray-500" />
            <span className="font-medium text-gray-700">Filtros</span>
            {hasActiveFilters && (
              <button
                onClick={clearFilters}
                className="ml-auto text-sm text-blue-600 hover:text-blue-800 flex items-center gap-1"
              >
                <X className="w-3 h-3" />
                Limpar filtros
              </button>
            )}
          </div>

          {/* Search field */}
          <div className="mb-4">
            <label className="block text-xs font-medium text-gray-500 mb-1">
              Buscar na mensagem
            </label>
            <div className="relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400" />
              <input
                type="text"
                value={searchInput}
                onChange={(e) => setSearchInput(e.target.value)}
                placeholder="Digite para buscar nos logs..."
                className="w-full border border-gray-300 rounded-md pl-10 pr-8 py-2 text-sm"
              />
              {searchInput && (
                <button
                  onClick={() => {
                    setSearchInput("");
                    setSearchFilter("");
                  }}
                  className="absolute right-2 top-1/2 transform -translate-y-1/2 text-gray-400 hover:text-gray-600"
                  title="Limpar busca"
                >
                  <X className="w-4 h-4" />
                </button>
              )}
            </div>
          </div>

          {/* First row: Period (and custom dates if selected) */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
            {/* Time Window */}
            <div>
              <label className="block text-xs font-medium text-gray-500 mb-1">
                Período
              </label>
              <div className="relative">
                <select
                  value={timeWindow}
                  onChange={(e) => {
                    const value = e.target.value as LogTimeWindow | "";
                    setTimeWindow(value);
                    if (value === "custom") {
                      // Set default: 5 minutes ago to 5 minutes ahead
                      const now = new Date();
                      const fiveMinAgo = new Date(now.getTime() - 5 * 60 * 1000);
                      const fiveMinAhead = new Date(now.getTime() + 5 * 60 * 1000);
                      // Format as YYYY-MM-DDTHH:mm for datetime-local input
                      const formatDateTime = (d: Date) => {
                        const pad = (n: number) => n.toString().padStart(2, "0");
                        return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
                      };
                      setCustomStartTime(formatDateTime(fiveMinAgo));
                      setCustomEndTime(formatDateTime(fiveMinAhead));
                    }
                  }}
                  className="w-full border border-gray-300 rounded-md pl-3 pr-14 py-2 text-sm appearance-none"
                >
                  {TIME_WINDOWS.map((tw) => (
                    <option key={tw.value} value={tw.value}>
                      {tw.label}
                    </option>
                  ))}
                </select>
                <ChevronDown className="absolute right-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400 pointer-events-none" />
                {timeWindow && timeWindow !== "5m" && (
                  <button
                    onClick={() => {
                      setTimeWindow("5m");
                      setCustomStartTime("");
                      setCustomEndTime("");
                    }}
                    className="absolute right-8 top-1/2 transform -translate-y-1/2 text-gray-400 hover:text-gray-600"
                    title="Voltar para últimos 5 min"
                  >
                    <X className="w-4 h-4" />
                  </button>
                )}
              </div>
            </div>

            {/* Custom Date Range */}
            {timeWindow === "custom" && (
              <>
                <div>
                  <label className="block text-xs font-medium text-gray-500 mb-1">
                    Início
                  </label>
                  <input
                    type="datetime-local"
                    value={customStartTime}
                    onChange={(e) => setCustomStartTime(e.target.value)}
                    className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-500 mb-1">
                    Fim
                  </label>
                  <input
                    type="datetime-local"
                    value={customEndTime}
                    onChange={(e) => setCustomEndTime(e.target.value)}
                    className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm"
                  />
                </div>
              </>
            )}
          </div>

          {/* Second row: Other filters */}
          <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-5 gap-4">
            {/* Level */}
            <div>
              <label className="block text-xs font-medium text-gray-500 mb-1">
                Nível
              </label>
              <div className="relative">
                <select
                  value={levelFilter}
                  onChange={(e) => setLevelFilter(e.target.value)}
                  className="w-full border border-gray-300 rounded-md pl-3 pr-14 py-2 text-sm appearance-none"
                >
                  <option value="">Todos</option>
                  {LOG_LEVELS.slice(1).map((level) => (
                    <option key={level} value={level}>
                      {level}+
                    </option>
                  ))}
                </select>
                <ChevronDown className="absolute right-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400 pointer-events-none" />
                {levelFilter && (
                  <button
                    onClick={() => setLevelFilter("")}
                    className="absolute right-8 top-1/2 transform -translate-y-1/2 text-gray-400 hover:text-gray-600"
                    title="Limpar nível"
                  >
                    <X className="w-4 h-4" />
                  </button>
                )}
              </div>
            </div>

            {/* Module */}
            <div>
              <label className="block text-xs font-medium text-gray-500 mb-1">
                Módulo
              </label>
              <div className="relative">
                <select
                  value={moduleFilter}
                  onChange={(e) => setModuleFilter(e.target.value)}
                  className="w-full border border-gray-300 rounded-md pl-3 pr-14 py-2 text-sm appearance-none"
                >
                  <option value="">Todos</option>
                  {modules.map((module) => (
                    <option key={module} value={module}>
                      {module}
                    </option>
                  ))}
                </select>
                <ChevronDown className="absolute right-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400 pointer-events-none" />
                {moduleFilter && (
                  <button
                    onClick={() => setModuleFilter("")}
                    className="absolute right-8 top-1/2 transform -translate-y-1/2 text-gray-400 hover:text-gray-600"
                    title="Limpar módulo"
                  >
                    <X className="w-4 h-4" />
                  </button>
                )}
              </div>
            </div>

            {/* User Email */}
            <div>
              <label className="block text-xs font-medium text-gray-500 mb-1">
                Usuário
              </label>
              <div className="relative">
                <input
                  type="text"
                  value={userEmailFilter}
                  onChange={(e) => setUserEmailFilter(e.target.value)}
                  placeholder="Filtrar por email..."
                  className="w-full border border-gray-300 rounded-md px-3 py-2 pr-8 text-sm"
                />
                {userEmailFilter && (
                  <button
                    onClick={() => setUserEmailFilter("")}
                    className="absolute right-2 top-1/2 transform -translate-y-1/2 text-gray-400 hover:text-gray-600"
                    title="Limpar usuário"
                  >
                    <X className="w-4 h-4" />
                  </button>
                )}
              </div>
            </div>

            {/* Session ID */}
            <div>
              <label className="block text-xs font-medium text-gray-500 mb-1">
                Session ID
              </label>
              <div className="relative">
                <input
                  type="text"
                  value={sessionIdFilter}
                  onChange={(e) => setSessionIdFilter(e.target.value)}
                  placeholder="Filtrar por sessão..."
                  className="w-full border border-gray-300 rounded-md px-3 py-2 pr-8 text-sm"
                />
                {sessionIdFilter && (
                  <button
                    onClick={() => setSessionIdFilter("")}
                    className="absolute right-2 top-1/2 transform -translate-y-1/2 text-gray-400 hover:text-gray-600"
                    title="Limpar sessão"
                  >
                    <X className="w-4 h-4" />
                  </button>
                )}
              </div>
            </div>

            {/* Request ID */}
            <div>
              <label className="block text-xs font-medium text-gray-500 mb-1">
                Request ID
              </label>
              <div className="relative">
                <input
                  type="text"
                  value={requestIdFilter}
                  onChange={(e) => setRequestIdFilter(e.target.value)}
                  placeholder="Filtrar por request..."
                  className="w-full border border-gray-300 rounded-md px-3 py-2 pr-8 text-sm"
                />
                {requestIdFilter && (
                  <button
                    onClick={() => setRequestIdFilter("")}
                    className="absolute right-2 top-1/2 transform -translate-y-1/2 text-gray-400 hover:text-gray-600"
                    title="Limpar request"
                  >
                    <X className="w-4 h-4" />
                  </button>
                )}
              </div>
            </div>
          </div>
        </div>

        {error && (
          <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg text-red-700">
            {error}
          </div>
        )}

        {/* Logs Table */}
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden relative">
          {loading && (
            <div className="absolute inset-0 bg-white/70 z-10 flex items-center justify-center">
              <div className="flex items-center gap-3">
                <Loader2 className="w-6 h-6 animate-spin text-blue-600" />
                <span className="text-gray-600">Carregando...</span>
              </div>
            </div>
          )}
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-3 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider w-40">
                    Timestamp
                  </th>
                  <th className="px-3 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider w-24">
                    Nível
                  </th>
                  <th className="px-3 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider w-48">
                    Módulo
                  </th>
                  <th className="px-3 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Mensagem
                  </th>
                  <th className="px-3 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider w-24">
                    Request
                  </th>
                  <th className="px-3 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider w-24">
                    Session
                  </th>
                  <th className="px-3 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider w-24">
                    User
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {logs.map((log) => (
                  <React.Fragment key={log.id}>
                    <tr
                      className={`hover:bg-gray-50 cursor-pointer ${
                        log.level === "ERROR" || log.level === "CRITICAL"
                          ? "bg-red-50"
                          : log.level === "WARNING"
                          ? "bg-amber-50"
                          : ""
                      }`}
                      onClick={() => toggleLogExpanded(log.id)}
                    >
                      <td className="px-3 py-3 whitespace-nowrap text-sm">
                        <div
                          className="text-gray-900"
                          title={formatTimestamp(log.timestamp)}
                        >
                          {formatRelativeTime(log.timestamp)}
                        </div>
                        <div className="text-xs text-gray-500">
                          {formatTimestamp(log.timestamp)}
                        </div>
                      </td>
                      <td className="px-3 py-3 whitespace-nowrap">
                        <span
                          className={`inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium ${getLevelBadgeClass(
                            log.level
                          )}`}
                        >
                          {getLevelIcon(log.level)}
                          {log.level}
                        </span>
                      </td>
                      <td className="px-3 py-3 whitespace-nowrap">
                        <span className="text-sm text-gray-900 font-mono">
                          {log.module.split(".").pop()}
                        </span>
                        <div className="text-xs text-gray-500 truncate max-w-[180px]" title={log.module}>
                          {log.module}
                        </div>
                      </td>
                      <td className="px-3 py-3">
                        <div className="flex items-center gap-2">
                          <span className="text-sm text-gray-900 truncate max-w-md">
                            {log.message.substring(0, 100)}
                            {log.message.length > 100 ? "..." : ""}
                          </span>
                          {(log.message.length > 100 || log.exc_info) && (
                            expandedLogs.has(log.id) ? (
                              <ChevronUp className="w-4 h-4 text-gray-400 flex-shrink-0" />
                            ) : (
                              <ChevronDown className="w-4 h-4 text-gray-400 flex-shrink-0" />
                            )
                          )}
                        </div>
                      </td>
                      <td className="px-3 py-3 whitespace-nowrap">
                        {log.request_id ? (
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              setRequestIdFilter(log.request_id!);
                            }}
                            className="text-xs font-mono text-blue-600 hover:text-blue-800 hover:underline"
                            title={`Filtrar por request_id: ${log.request_id}`}
                          >
                            {log.request_id}
                          </button>
                        ) : (
                          <span className="text-gray-400 text-xs">-</span>
                        )}
                      </td>
                      <td className="px-3 py-3 whitespace-nowrap">
                        {log.session_id ? (
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              setSessionIdFilter(log.session_id!);
                            }}
                            className="text-xs font-mono text-blue-600 hover:text-blue-800 hover:underline"
                            title={`Filtrar por session_id: ${log.session_id}`}
                          >
                            {log.session_id.substring(0, 8)}
                          </button>
                        ) : (
                          <span className="text-gray-400 text-xs">-</span>
                        )}
                      </td>
                      <td className="px-3 py-3 whitespace-nowrap">
                        {log.user_email ? (
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              setUserEmailFilter(log.user_email!);
                            }}
                            className="text-xs text-blue-600 hover:text-blue-800 hover:underline truncate max-w-[150px]"
                            title={`Filtrar por usuário: ${log.user_email}`}
                          >
                            {log.user_email}
                          </button>
                        ) : (
                          <span className="text-gray-400 text-xs">-</span>
                        )}
                      </td>
                    </tr>
                    {expandedLogs.has(log.id) && (
                      <tr className="bg-gray-50">
                        <td colSpan={7} className="px-6 py-4">
                          <div className="space-y-3">
                            <div>
                              <span className="text-xs font-medium text-gray-500">
                                Mensagem completa:
                              </span>
                              <pre className="mt-1 text-sm text-gray-900 whitespace-pre-wrap font-mono bg-white p-3 rounded border border-gray-200">
                                {log.message}
                              </pre>
                            </div>
                            {log.func_name && (
                              <div className="text-sm">
                                <span className="text-gray-500">Função:</span>{" "}
                                <span className="font-mono">{log.func_name}</span>
                                {log.line_no && (
                                  <span className="text-gray-400">
                                    :{log.line_no}
                                  </span>
                                )}
                              </div>
                            )}
                            {log.exc_info && (
                              <div>
                                <span className="text-xs font-medium text-red-600">
                                  Stack Trace:
                                </span>
                                <pre className="mt-1 text-xs text-red-800 whitespace-pre-wrap font-mono bg-red-50 p-3 rounded border border-red-200 overflow-x-auto">
                                  {log.exc_info}
                                </pre>
                              </div>
                            )}
                          </div>
                        </td>
                      </tr>
                    )}
                  </React.Fragment>
                ))}
              </tbody>
            </table>
          </div>

          {logs.length === 0 && !loading && (
            <div className="text-center py-12">
              <FileText className="mx-auto h-12 w-12 text-gray-400" />
              <h3 className="mt-2 text-sm font-medium text-gray-900">
                Nenhum log encontrado
              </h3>
              <p className="mt-1 text-sm text-gray-500">
                {hasActiveFilters
                  ? "Nenhum log corresponde aos filtros selecionados."
                  : "Não há logs registrados no banco de dados."}
              </p>
            </div>
          )}

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="px-6 py-4 border-t border-gray-200 flex items-center justify-between">
              <div className="text-sm text-gray-500">
                Mostrando {(currentPage - 1) * PAGE_SIZE + 1} a{" "}
                {Math.min(currentPage * PAGE_SIZE, total)} de {total} logs
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
                    .filter((page) => {
                      if (page === 1 || page === totalPages) return true;
                      if (Math.abs(page - currentPage) <= 1) return true;
                      return false;
                    })
                    .map((page, index, arr) => {
                      const showEllipsisBefore =
                        index > 0 && page - arr[index - 1] > 1;
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
