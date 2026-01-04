"use client";

import React, { useEffect, useState, useCallback } from "react";
import { useSession } from "next-auth/react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import dynamic from "next/dynamic";
import {
  ArrowLeft,
  Loader2,
  RefreshCw,
  BarChart3,
  Users,
  Smartphone,
  Activity,
  TrendingUp,
  Filter as FilterIcon,
  AlertCircle,
  Download,
  Monitor,
  Tablet,
  Clock,
  Info,
  X,
  MapPin,
} from "lucide-react";
import { toast } from "sonner";
import { apiClient } from "@/lib/api";
import {
  UserEventStatsOverview,
  EventTypeStats,
  DeviceStats,
  DailyActiveUsers,
  FeatureUsageStats,
  POIFilterUsageStats,
  ConversionFunnelStats,
  PerformanceStats,
  LoginLocation,
} from "@/lib/types";

// Dynamic import for Leaflet map (no SSR)
const LoginLocationsMap = dynamic(
  () => import("@/components/admin/LoginLocationsMap"),
  {
    ssr: false,
    loading: () => (
      <div className="h-[500px] flex items-center justify-center bg-gray-100 rounded-lg">
        <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
      </div>
    ),
  }
);

const DAYS_OPTIONS = [
  { value: 7, label: "7 dias" },
  { value: 14, label: "14 dias" },
  { value: 30, label: "30 dias" },
  { value: 60, label: "60 dias" },
  { value: 90, label: "90 dias" },
];

// Descrições dos indicadores
const INDICATOR_DESCRIPTIONS: Record<string, string> = {
  total_events: "Número total de eventos registrados no período selecionado. Inclui todas as interações dos usuários como cliques, visualizações e ações.",
  unique_sessions: "Número de sessões únicas de navegação. Uma sessão representa uma visita ao site, mesmo que o usuário não esteja logado.",
  unique_users: "Número de usuários únicos que fizeram login durante o período. Não inclui visitantes anônimos.",
  feature_usage: "Mostra quais funcionalidades são mais utilizadas, incluindo criação de mapas, exportações e filtros de POI.",
  event_types: "Lista todos os tipos de eventos registrados, agrupados por categoria (auth, navigation, map_management, etc).",
  poi_filters: "Estatísticas de uso dos filtros de pontos de interesse. Mostra quantas vezes cada filtro foi ativado ou desativado.",
  performance: "Métricas de performance das operações. Mostra tempo médio, mínimo e máximo de carregamento.",
  daily_activity: "Histórico diário de atividade mostrando sessões, usuários logados e total de eventos por dia.",
  devices: "Distribuição de dispositivos, sistemas operacionais e navegadores utilizados pelos usuários.",
  funnel: "Funil de conversão mostrando a jornada do usuário: pesquisa → conclusão → criação/adoção de mapa.",
  completion_rate: "Percentual de pesquisas que foram concluídas com sucesso em relação ao total iniciado.",
  abandonment_rate: "Percentual de pesquisas abandonadas (usuário saiu antes de concluir).",
  map_creation_rate: "Percentual de sessões que resultaram na criação ou adoção de um mapa.",
};

// Componente InfoButton com tooltip
function InfoButton({ indicatorKey }: { indicatorKey: string }) {
  const [isOpen, setIsOpen] = useState(false);
  const description = INDICATOR_DESCRIPTIONS[indicatorKey];

  if (!description) return null;

  return (
    <div className="relative inline-block">
      <button
        onClick={(e) => {
          e.stopPropagation();
          setIsOpen(!isOpen);
        }}
        className="p-1 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-full transition-colors"
        title="Ver descrição"
      >
        <Info className="h-4 w-4" />
      </button>

      {isOpen && (
        <>
          {/* Backdrop para fechar ao clicar fora */}
          <div
            className="fixed inset-0 z-40"
            onClick={() => setIsOpen(false)}
          />
          {/* Tooltip */}
          <div className="absolute z-50 w-64 p-3 mt-1 bg-gray-900 text-white text-xs rounded-lg shadow-lg right-0 top-full">
            <button
              onClick={() => setIsOpen(false)}
              className="absolute top-1 right-1 p-1 hover:bg-gray-700 rounded"
            >
              <X className="h-3 w-3" />
            </button>
            <p className="pr-4">{description}</p>
          </div>
        </>
      )}
    </div>
  );
}

export default function AdminAnalyticsPage() {
  const { data: session, status } = useSession();
  const router = useRouter();

  // Data state
  const [overview, setOverview] = useState<UserEventStatsOverview | null>(null);
  const [eventStats, setEventStats] = useState<EventTypeStats[]>([]);
  const [deviceStats, setDeviceStats] = useState<DeviceStats[]>([]);
  const [dailyStats, setDailyStats] = useState<DailyActiveUsers[]>([]);
  const [featureStats, setFeatureStats] = useState<FeatureUsageStats[]>([]);
  const [poiFilterStats, setPOIFilterStats] = useState<POIFilterUsageStats[]>([]);
  const [funnelStats, setFunnelStats] = useState<ConversionFunnelStats | null>(null);
  const [performanceStats, setPerformanceStats] = useState<PerformanceStats[]>([]);
  const [loginLocations, setLoginLocations] = useState<LoginLocation[]>([]);

  // UI state
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [days, setDays] = useState(30);
  const [autoRefresh, setAutoRefresh] = useState(false);
  const [activeTab, setActiveTab] = useState<"overview" | "devices" | "funnel" | "locations">("overview");

  const fetchData = useCallback(async () => {
    try {
      setError(null);

      const [
        overviewData,
        eventData,
        deviceData,
        dailyData,
        featureData,
        poiFilterData,
        funnelData,
        performanceData,
        loginLocationsData,
      ] = await Promise.all([
        apiClient.getEventStatsOverview(days),
        apiClient.getEventTypeStats(days),
        apiClient.getDeviceStats(days),
        apiClient.getDailyActiveUsers(days),
        apiClient.getFeatureUsageStats(days),
        apiClient.getPOIFilterStats(days),
        apiClient.getConversionFunnelStats(days),
        apiClient.getPerformanceStats(days),
        apiClient.getLoginLocations(days),
      ]);

      setOverview(overviewData);
      setEventStats(eventData);
      setDeviceStats(deviceData);
      setDailyStats(dailyData);
      setFeatureStats(featureData);
      setPOIFilterStats(poiFilterData);
      setFunnelStats(funnelData);
      setPerformanceStats(performanceData);
      setLoginLocations(loginLocationsData);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erro desconhecido");
    } finally {
      setLoading(false);
    }
  }, [days]);

  useEffect(() => {
    if (status === "loading") return;

    if (!session?.user?.isAdmin) {
      router.push("/");
      return;
    }

    fetchData();
  }, [session, status, router, fetchData]);

  useEffect(() => {
    if (!autoRefresh) return;
    const interval = setInterval(fetchData, 30000);
    return () => clearInterval(interval);
  }, [autoRefresh, fetchData]);

  const handleExportCSV = async () => {
    try {
      const blob = await apiClient.exportEventsCsv(days);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `user_events_${days}days.csv`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
      toast.success("Exportado com sucesso!");
    } catch {
      toast.error("Erro ao exportar dados");
    }
  };

  const getDeviceIcon = (deviceType: string | null) => {
    switch (deviceType) {
      case "mobile":
        return <Smartphone className="h-4 w-4" />;
      case "tablet":
        return <Tablet className="h-4 w-4" />;
      default:
        return <Monitor className="h-4 w-4" />;
    }
  };

  const formatNumber = (num: number) => {
    return new Intl.NumberFormat("pt-BR").format(num);
  };

  const formatPercent = (num: number) => {
    return `${num.toFixed(1)}%`;
  };

  if (status === "loading" || loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
      </div>
    );
  }

  if (!session?.user?.isAdmin) {
    return null;
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-7xl mx-auto px-4 py-8">
        {/* Header */}
        <div className="mb-8">
          <Link
            href="/admin"
            className="inline-flex items-center text-gray-600 hover:text-gray-900 mb-4"
          >
            <ArrowLeft className="h-4 w-4 mr-1" />
            Voltar ao Admin
          </Link>

          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <BarChart3 className="h-8 w-8 text-purple-600" />
              <div>
                <h1 className="text-2xl font-bold text-gray-900">Analytics</h1>
                <p className="text-gray-600">
                  Estatísticas de uso e comportamento dos usuários
                </p>
              </div>
            </div>

            <div className="flex items-center gap-4">
              <select
                value={days}
                onChange={(e) => setDays(Number(e.target.value))}
                className="px-3 py-2 border border-gray-300 rounded-md bg-white text-sm"
              >
                {DAYS_OPTIONS.map((opt) => (
                  <option key={opt.value} value={opt.value}>
                    {opt.label}
                  </option>
                ))}
              </select>

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
                onClick={() => fetchData()}
                className="inline-flex items-center gap-2 px-3 py-2 bg-white border border-gray-300 rounded-md text-sm font-medium text-gray-700 hover:bg-gray-50"
              >
                <RefreshCw className="h-4 w-4" />
                Atualizar
              </button>

              <button
                onClick={handleExportCSV}
                className="inline-flex items-center gap-2 px-3 py-2 bg-blue-600 text-white rounded-md text-sm font-medium hover:bg-blue-700"
              >
                <Download className="h-4 w-4" />
                Exportar CSV
              </button>
            </div>
          </div>
        </div>

        {error && (
          <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg text-red-600">
            {error}
          </div>
        )}

        {/* Overview Cards */}
        {overview && (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
            <div className="bg-white rounded-lg shadow p-6">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="p-3 bg-purple-100 rounded-lg">
                    <Activity className="h-6 w-6 text-purple-600" />
                  </div>
                  <div>
                    <p className="text-sm text-gray-600">Total de Eventos</p>
                    <p className="text-2xl font-bold">{formatNumber(overview.total_events)}</p>
                  </div>
                </div>
                <InfoButton indicatorKey="total_events" />
              </div>
            </div>

            <div className="bg-white rounded-lg shadow p-6">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="p-3 bg-blue-100 rounded-lg">
                    <Users className="h-6 w-6 text-blue-600" />
                  </div>
                  <div>
                    <p className="text-sm text-gray-600">Sessões Únicas</p>
                    <p className="text-2xl font-bold">{formatNumber(overview.unique_sessions)}</p>
                  </div>
                </div>
                <InfoButton indicatorKey="unique_sessions" />
              </div>
            </div>

            <div className="bg-white rounded-lg shadow p-6">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="p-3 bg-green-100 rounded-lg">
                    <TrendingUp className="h-6 w-6 text-green-600" />
                  </div>
                  <div>
                    <p className="text-sm text-gray-600">Usuários Logados</p>
                    <p className="text-2xl font-bold">{formatNumber(overview.unique_users)}</p>
                  </div>
                </div>
                <InfoButton indicatorKey="unique_users" />
              </div>
            </div>
          </div>
        )}

        {/* Tabs */}
        <div className="mb-6 border-b">
          <nav className="flex gap-4">
            {[
              { id: "overview", label: "Visão Geral" },
              { id: "devices", label: "Dispositivos" },
              { id: "funnel", label: "Funil" },
              { id: "locations", label: "Localização" },
            ].map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id as typeof activeTab)}
                className={`px-4 py-2 border-b-2 font-medium text-sm ${
                  activeTab === tab.id
                    ? "border-purple-600 text-purple-600"
                    : "border-transparent text-gray-500 hover:text-gray-700"
                }`}
              >
                {tab.label}
              </button>
            ))}
          </nav>
        </div>

        {/* Tab Content */}
        {activeTab === "overview" && (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Feature Usage */}
            <div className="bg-white rounded-lg shadow p-6">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-semibold">Uso de Funcionalidades</h3>
                <InfoButton indicatorKey="feature_usage" />
              </div>
              {featureStats.length > 0 ? (
                <div className="space-y-3">
                  {featureStats.map((stat) => (
                    <div key={stat.feature} className="flex items-center justify-between">
                      <span className="text-sm text-gray-700">{stat.feature}</span>
                      <div className="flex items-center gap-4">
                        <span className="text-sm font-medium">{formatNumber(stat.count)}</span>
                        <span className="text-xs text-gray-500">
                          {stat.unique_sessions} sessões
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-gray-500 text-sm">Nenhum dado disponível</p>
              )}
            </div>

            {/* Event Types */}
            <div className="bg-white rounded-lg shadow p-6">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-semibold">Eventos por Tipo</h3>
                <InfoButton indicatorKey="event_types" />
              </div>
              {eventStats.length > 0 ? (
                <div className="space-y-3 max-h-80 overflow-y-auto">
                  {eventStats.slice(0, 15).map((stat) => (
                    <div key={`${stat.event_category}-${stat.event_type}`} className="flex items-center justify-between">
                      <div>
                        <span className="text-sm text-gray-700">{stat.event_type}</span>
                        <span className="ml-2 text-xs text-gray-400">{stat.event_category}</span>
                      </div>
                      <span className="text-sm font-medium">{formatNumber(stat.count)}</span>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-gray-500 text-sm">Nenhum dado disponível</p>
              )}
            </div>

            {/* POI Filters */}
            <div className="bg-white rounded-lg shadow p-6">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-semibold flex items-center gap-2">
                  <FilterIcon className="h-5 w-5" />
                  Filtros de POI
                </h3>
                <InfoButton indicatorKey="poi_filters" />
              </div>
              {poiFilterStats.length > 0 ? (
                <div className="space-y-3">
                  {poiFilterStats.map((stat, idx) => (
                    <div key={idx} className="flex items-center justify-between">
                      <span className="text-sm text-gray-700">{stat.filter_name || "Desconhecido"}</span>
                      <div className="flex items-center gap-2">
                        <span className={`text-xs px-2 py-1 rounded ${stat.enabled ? "bg-green-100 text-green-600" : "bg-red-100 text-red-600"}`}>
                          {stat.enabled ? "Ativado" : "Desativado"}
                        </span>
                        <span className="text-sm font-medium">{formatNumber(stat.count)}</span>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-gray-500 text-sm">Nenhum dado disponível</p>
              )}
            </div>

            {/* Performance */}
            <div className="bg-white rounded-lg shadow p-6">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-semibold flex items-center gap-2">
                  <Clock className="h-5 w-5" />
                  Performance
                </h3>
                <InfoButton indicatorKey="performance" />
              </div>
              {performanceStats.length > 0 ? (
                <div className="space-y-3">
                  {performanceStats.map((stat) => (
                    <div key={stat.event_type} className="flex items-center justify-between">
                      <span className="text-sm text-gray-700">{stat.event_type}</span>
                      <div className="text-right">
                        <span className="text-sm font-medium">{stat.avg_duration_ms.toFixed(0)}ms</span>
                        <span className="text-xs text-gray-400 ml-2">
                          ({stat.min_duration_ms}-{stat.max_duration_ms}ms)
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-gray-500 text-sm">Nenhum dado disponível</p>
              )}
            </div>

            {/* Daily Active Users */}
            <div className="bg-white rounded-lg shadow p-6 lg:col-span-2">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-semibold">Atividade Diária</h3>
                <InfoButton indicatorKey="daily_activity" />
              </div>
              {dailyStats.length > 0 ? (
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b">
                        <th className="text-left py-2 px-3">Data</th>
                        <th className="text-right py-2 px-3">Sessões</th>
                        <th className="text-right py-2 px-3">Usuários</th>
                        <th className="text-right py-2 px-3">Eventos</th>
                      </tr>
                    </thead>
                    <tbody>
                      {dailyStats.slice(0, 14).map((stat) => (
                        <tr key={stat.date} className="border-b hover:bg-gray-50">
                          <td className="py-2 px-3">{stat.date}</td>
                          <td className="text-right py-2 px-3">{formatNumber(stat.unique_sessions)}</td>
                          <td className="text-right py-2 px-3">{formatNumber(stat.unique_users)}</td>
                          <td className="text-right py-2 px-3">{formatNumber(stat.total_events)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <p className="text-gray-500 text-sm">Nenhum dado disponível</p>
              )}
            </div>
          </div>
        )}

        {activeTab === "devices" && (
          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold">Distribuição de Dispositivos</h3>
              <InfoButton indicatorKey="devices" />
            </div>
            {deviceStats.length > 0 ? (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b">
                      <th className="text-left py-2 px-3">Dispositivo</th>
                      <th className="text-left py-2 px-3">Sistema</th>
                      <th className="text-left py-2 px-3">Navegador</th>
                      <th className="text-right py-2 px-3">Eventos</th>
                      <th className="text-right py-2 px-3">Sessões</th>
                    </tr>
                  </thead>
                  <tbody>
                    {deviceStats.map((stat, idx) => (
                      <tr key={idx} className="border-b hover:bg-gray-50">
                        <td className="py-2 px-3">
                          <div className="flex items-center gap-2">
                            {getDeviceIcon(stat.device_type)}
                            <span className="capitalize">{stat.device_type || "Desconhecido"}</span>
                          </div>
                        </td>
                        <td className="py-2 px-3">{stat.os || "-"}</td>
                        <td className="py-2 px-3">{stat.browser || "-"}</td>
                        <td className="text-right py-2 px-3">{formatNumber(stat.count)}</td>
                        <td className="text-right py-2 px-3">{formatNumber(stat.unique_sessions)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <p className="text-gray-500 text-sm">Nenhum dado disponível</p>
            )}
          </div>
        )}

        {activeTab === "funnel" && funnelStats && (
          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center justify-between mb-6">
              <h3 className="text-lg font-semibold">Funil de Conversão</h3>
              <InfoButton indicatorKey="funnel" />
            </div>

            <div className="space-y-6">
              {/* Funnel Visualization */}
              <div className="space-y-4">
                <div className="relative">
                  <div className="bg-blue-100 rounded-lg p-4">
                    <div className="flex justify-between items-center">
                      <span className="font-medium">Pesquisas Iniciadas</span>
                      <span className="text-lg font-bold">{funnelStats.search_started.sessions} sessões</span>
                    </div>
                  </div>
                </div>

                <div className="relative ml-8">
                  <div className="bg-blue-200 rounded-lg p-4">
                    <div className="flex justify-between items-center">
                      <span className="font-medium">Pesquisas Concluídas</span>
                      <div className="text-right">
                        <span className="text-lg font-bold">{funnelStats.search_completed.sessions} sessões</span>
                        <span className="ml-2 text-sm text-green-600">
                          ({formatPercent(funnelStats.completion_rate)})
                        </span>
                      </div>
                    </div>
                  </div>
                </div>

                <div className="relative ml-16">
                  <div className="bg-green-100 rounded-lg p-4">
                    <div className="flex justify-between items-center">
                      <span className="font-medium">Mapas Criados</span>
                      <div className="text-right">
                        <span className="text-lg font-bold">{funnelStats.map_create.sessions} sessões</span>
                      </div>
                    </div>
                  </div>
                </div>

                <div className="relative ml-16">
                  <div className="bg-green-200 rounded-lg p-4">
                    <div className="flex justify-between items-center">
                      <span className="font-medium">Mapas Adotados</span>
                      <div className="text-right">
                        <span className="text-lg font-bold">{funnelStats.map_adopt.sessions} sessões</span>
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              {/* Stats */}
              <div className="grid grid-cols-3 gap-4 mt-8 pt-6 border-t">
                <div className="text-center">
                  <div className="flex items-center justify-center gap-1">
                    <p className="text-sm text-gray-600">Taxa de Conclusão</p>
                    <InfoButton indicatorKey="completion_rate" />
                  </div>
                  <p className="text-2xl font-bold text-green-600">{formatPercent(funnelStats.completion_rate)}</p>
                </div>
                <div className="text-center">
                  <div className="flex items-center justify-center gap-1">
                    <p className="text-sm text-gray-600">Taxa de Abandono</p>
                    <InfoButton indicatorKey="abandonment_rate" />
                  </div>
                  <p className="text-2xl font-bold text-red-600">{formatPercent(funnelStats.abandonment_rate)}</p>
                </div>
                <div className="text-center">
                  <div className="flex items-center justify-center gap-1">
                    <p className="text-sm text-gray-600">Taxa de Criação de Mapas</p>
                    <InfoButton indicatorKey="map_creation_rate" />
                  </div>
                  <p className="text-2xl font-bold text-blue-600">{formatPercent(funnelStats.map_creation_rate)}</p>
                </div>
              </div>

              {/* Abandoned searches */}
              <div className="mt-6 p-4 bg-amber-50 rounded-lg">
                <div className="flex items-center gap-2 text-amber-700">
                  <AlertCircle className="h-5 w-5" />
                  <span>
                    <strong>{funnelStats.search_abandoned.sessions}</strong> pesquisas foram abandonadas
                  </span>
                </div>
              </div>
            </div>
          </div>
        )}

        {activeTab === "locations" && (
          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center justify-between mb-6">
              <div className="flex items-center gap-2">
                <MapPin className="h-5 w-5 text-blue-600" />
                <h3 className="text-lg font-semibold">Localização dos Logins</h3>
              </div>
              <div className="text-sm text-gray-500">
                {loginLocations.length} logins com localização
              </div>
            </div>

            {loginLocations.length > 0 ? (
              <>
                <LoginLocationsMap locations={loginLocations} />

                {/* Legend */}
                <div className="mt-4 flex items-center gap-6 text-sm text-gray-600">
                  <div className="flex items-center gap-2">
                    <div className="w-4 h-4 rounded-full bg-green-500"></div>
                    <span>Mobile</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <div className="w-4 h-4 rounded-full bg-purple-500"></div>
                    <span>Tablet</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <div className="w-4 h-4 rounded-full bg-blue-500"></div>
                    <span>Desktop</span>
                  </div>
                </div>

                {/* Stats summary */}
                <div className="mt-4 grid grid-cols-3 gap-4 pt-4 border-t">
                  <div className="text-center">
                    <p className="text-sm text-gray-600">Total de Logins</p>
                    <p className="text-xl font-bold">{loginLocations.length}</p>
                  </div>
                  <div className="text-center">
                    <p className="text-sm text-gray-600">Mobile</p>
                    <p className="text-xl font-bold text-green-600">
                      {loginLocations.filter(l => l.device_type === 'mobile').length}
                    </p>
                  </div>
                  <div className="text-center">
                    <p className="text-sm text-gray-600">Desktop</p>
                    <p className="text-xl font-bold text-blue-600">
                      {loginLocations.filter(l => l.device_type === 'desktop').length}
                    </p>
                  </div>
                </div>
              </>
            ) : (
              <div className="h-[300px] flex flex-col items-center justify-center text-gray-500">
                <MapPin className="h-12 w-12 text-gray-300 mb-4" />
                <p>Nenhum login com localização registrado</p>
                <p className="text-sm mt-1">
                  Os logins aparecerão aqui quando os usuários permitirem a localização
                </p>
              </div>
            )}
          </div>
        )}

      </div>
    </div>
  );
}
