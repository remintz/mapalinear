"use client";

import { useSession } from "next-auth/react";
import { useRouter } from "next/navigation";
import { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import {
  Settings,
  ArrowLeft,
  Save,
  Loader2,
  MapPin,
  Copy,
  Database,
  Trash2,
  AlertTriangle,
  CheckCircle,
  RefreshCw,
  Bug,
  Clock,
  BarChart2,
} from "lucide-react";
import { toast } from "sonner";
import {
  apiClient,
  SystemSettings,
  DatabaseStats,
  MaintenanceResult,
  LogCleanupResult,
} from "@/lib/api";

export default function AdminSettingsPage() {
  const { data: session, status } = useSession();
  const router = useRouter();
  const [settings, setSettings] = useState<SystemSettings>({
    poi_search_radius_km: "5",
    duplicate_map_tolerance_km: "10",
    poi_debug_enabled: "true",
    log_retention_days: "7",
    analytics_retention_days: "90",
  });
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Database maintenance state
  const [dbStats, setDbStats] = useState<DatabaseStats | null>(null);
  const [loadingStats, setLoadingStats] = useState(false);
  const [runningMaintenance, setRunningMaintenance] = useState(false);
  const [lastMaintenanceResult, setLastMaintenanceResult] = useState<MaintenanceResult | null>(null);

  // Log cleanup state
  const [runningLogCleanup, setRunningLogCleanup] = useState(false);
  const [lastLogCleanupResult, setLastLogCleanupResult] = useState<LogCleanupResult | null>(null);

  const fetchSettings = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);

      const data = await apiClient.getSettings();
      setSettings(data.settings);
    } catch (err) {
      // apiClient handles 401 automatically and redirects to login
      setError(err instanceof Error ? err.message : "Erro desconhecido");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (status === "loading") return;

    if (!session?.user?.isAdmin) {
      router.push("/");
      return;
    }

    fetchSettings();
  }, [session, status, router, fetchSettings]);

  const handleSave = async () => {
    try {
      setSaving(true);

      await apiClient.updateSettings(settings);
      toast.success("Configurações salvas com sucesso!");
    } catch (err) {
      // apiClient handles 401 automatically and redirects to login
      toast.error(err instanceof Error ? err.message : "Erro ao salvar");
    } finally {
      setSaving(false);
    }
  };

  const handleRadiusChange = (value: string) => {
    // Allow only numbers
    const numericValue = value.replace(/[^0-9]/g, "");
    setSettings((prev) => ({
      ...prev,
      poi_search_radius_km: numericValue,
    }));
  };

  const handleToleranceChange = (value: string) => {
    // Allow only numbers
    const numericValue = value.replace(/[^0-9]/g, "");
    setSettings((prev) => ({
      ...prev,
      duplicate_map_tolerance_km: numericValue,
    }));
  };

  const handleDebugToggle = () => {
    setSettings((prev) => ({
      ...prev,
      poi_debug_enabled: prev.poi_debug_enabled === "true" ? "false" : "true",
    }));
  };

  const handleRetentionChange = (value: string) => {
    // Allow only numbers
    const numericValue = value.replace(/[^0-9]/g, "");
    setSettings((prev) => ({
      ...prev,
      log_retention_days: numericValue,
    }));
  };

  const handleAnalyticsRetentionChange = (value: string) => {
    // Allow only numbers
    const numericValue = value.replace(/[^0-9]/g, "");
    setSettings((prev) => ({
      ...prev,
      analytics_retention_days: numericValue,
    }));
  };

  const fetchDatabaseStats = useCallback(async () => {
    try {
      setLoadingStats(true);
      const data = await apiClient.getMaintenanceStats();
      setDbStats(data);
    } catch (err) {
      // apiClient handles 401 automatically and redirects to login
      toast.error(err instanceof Error ? err.message : "Erro ao carregar estatísticas");
    } finally {
      setLoadingStats(false);
    }
  }, []);

  const runMaintenance = async (dryRun: boolean) => {
    try {
      setRunningMaintenance(true);
      setLastMaintenanceResult(null);

      const result = await apiClient.runMaintenance(dryRun);
      setLastMaintenanceResult(result);

      if (dryRun) {
        toast.info(`Simulação concluída em ${result.execution_time_ms}ms`);
      } else {
        toast.success(
          `Manutenção concluída: ${result.orphan_pois_deleted} POIs removidos, ${result.is_referenced_fixed} flags corrigidas`
        );
        // Refresh stats after real maintenance
        fetchDatabaseStats();
      }
    } catch (err) {
      // apiClient handles 401 automatically and redirects to login
      toast.error(err instanceof Error ? err.message : "Erro na manutenção");
    } finally {
      setRunningMaintenance(false);
    }
  };

  const runLogCleanup = async () => {
    try {
      setRunningLogCleanup(true);
      setLastLogCleanupResult(null);

      const result = await apiClient.runLogCleanup();
      setLastLogCleanupResult(result);

      toast.success(
        `Limpeza concluída: ${result.total_deleted} logs removidos`
      );
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Erro na limpeza de logs");
    } finally {
      setRunningLogCleanup(false);
    }
  };

  // Load database stats when page loads
  useEffect(() => {
    if (session?.accessToken && !loading) {
      fetchDatabaseStats();
    }
  }, [session?.accessToken, loading, fetchDatabaseStats]);

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
      <div className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="mb-8">
          <Link
            href="/admin"
            className="inline-flex items-center gap-2 text-gray-600 hover:text-gray-900 mb-4"
          >
            <ArrowLeft className="w-4 h-4" />
            Voltar para Administração
          </Link>

          <h1 className="text-3xl font-bold text-gray-900 flex items-center gap-3">
            <Settings className="w-8 h-8 text-blue-600" />
            Configurações do Sistema
          </h1>
          <p className="mt-2 text-gray-600">
            Configure parâmetros globais do MapaLinear
          </p>
        </div>

        {error && (
          <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg text-red-700">
            {error}
          </div>
        )}

        <div className="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
          <div className="p-6 space-y-6">
            {/* POI Search Radius */}
            <div className="space-y-3">
              <label className="block">
                <span className="flex items-center gap-2 text-sm font-medium text-gray-900">
                  <MapPin className="w-4 h-4 text-blue-600" />
                  Raio de busca de pontos de interesse
                </span>
                <span className="text-sm text-gray-500 mt-1 block">
                  Define a distância máxima da rodovia para buscar postos, restaurantes, hotéis e outros POIs.
                  Valores menores (1-2km) mostram apenas POIs muito próximos.
                  Valores maiores (10-20km) incluem estabelecimentos em centros urbanos próximos.
                </span>
              </label>
              <div className="flex items-center gap-3">
                <input
                  type="range"
                  min="1"
                  max="20"
                  step="1"
                  value={settings.poi_search_radius_km || "5"}
                  onChange={(e) => handleRadiusChange(e.target.value)}
                  className="flex-1 h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-blue-600"
                />
                <div className="flex items-center gap-1 min-w-[80px]">
                  <input
                    type="number"
                    min="1"
                    max="20"
                    value={settings.poi_search_radius_km || "5"}
                    onChange={(e) => handleRadiusChange(e.target.value)}
                    className="w-16 px-2 py-1 text-center border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  />
                  <span className="text-sm text-gray-600">km</span>
                </div>
              </div>
              <div className="flex justify-between text-xs text-gray-400">
                <span>1 km</span>
                <span>20 km</span>
              </div>
            </div>

            {/* Duplicate Map Tolerance */}
            <div className="space-y-3">
              <label className="block">
                <span className="flex items-center gap-2 text-sm font-medium text-gray-900">
                  <Copy className="w-4 h-4 text-orange-600" />
                  Tolerância para detecção de mapas duplicados
                </span>
                <span className="text-sm text-gray-500 mt-1 block">
                  Define a distância máxima entre coordenadas de origem/destino para considerar dois mapas como duplicados.
                  Valores menores exigem correspondência mais exata.
                  Valores maiores permitem variações na forma como as cidades são escritas.
                </span>
              </label>
              <div className="flex items-center gap-3">
                <input
                  type="range"
                  min="1"
                  max="50"
                  step="1"
                  value={settings.duplicate_map_tolerance_km || "10"}
                  onChange={(e) => handleToleranceChange(e.target.value)}
                  className="flex-1 h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-orange-600"
                />
                <div className="flex items-center gap-1 min-w-[80px]">
                  <input
                    type="number"
                    min="1"
                    max="50"
                    value={settings.duplicate_map_tolerance_km || "10"}
                    onChange={(e) => handleToleranceChange(e.target.value)}
                    className="w-16 px-2 py-1 text-center border border-gray-300 rounded-md focus:ring-2 focus:ring-orange-500 focus:border-orange-500"
                  />
                  <span className="text-sm text-gray-600">km</span>
                </div>
              </div>
              <div className="flex justify-between text-xs text-gray-400">
                <span>1 km</span>
                <span>50 km</span>
              </div>
            </div>

            {/* POI Debug Toggle */}
            <div className="space-y-3 pt-4 border-t border-gray-200">
              <div className="flex items-center justify-between">
                <div className="flex-1">
                  <span className="flex items-center gap-2 text-sm font-medium text-gray-900">
                    <Bug className="w-4 h-4 text-amber-600" />
                    Coleta de dados de debug para POIs
                  </span>
                  <span className="text-sm text-gray-500 mt-1 block">
                    Quando habilitado, o sistema armazena informações detalhadas sobre como cada POI foi calculado
                    (vetores de direção, cross product, rotas de acesso, pontos de junção). Útil para diagnosticar
                    problemas de posicionamento de POIs.
                  </span>
                </div>
                <button
                  type="button"
                  onClick={handleDebugToggle}
                  className={`relative inline-flex h-6 w-11 flex-shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none focus:ring-2 focus:ring-amber-500 focus:ring-offset-2 ${
                    settings.poi_debug_enabled === "true" ? "bg-amber-600" : "bg-gray-200"
                  }`}
                  role="switch"
                  aria-checked={settings.poi_debug_enabled === "true"}
                >
                  <span
                    className={`pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out ${
                      settings.poi_debug_enabled === "true" ? "translate-x-5" : "translate-x-0"
                    }`}
                  />
                </button>
              </div>
              <div className="text-xs text-gray-400">
                {settings.poi_debug_enabled === "true" ? (
                  <span className="text-amber-600">Debug habilitado - dados serão coletados ao gerar novos mapas</span>
                ) : (
                  <span>Debug desabilitado - nenhum dado de debug será coletado</span>
                )}
              </div>
            </div>

            {/* Log Retention Period */}
            <div className="space-y-3 pt-4 border-t border-gray-200">
              <label className="block">
                <span className="flex items-center gap-2 text-sm font-medium text-gray-900">
                  <Clock className="w-4 h-4 text-purple-600" />
                  Período de retenção de logs
                </span>
                <span className="text-sm text-gray-500 mt-1 block">
                  Define por quantos dias os logs são mantidos no banco de dados.
                  Logs mais antigos são automaticamente removidos a cada 24 horas.
                  Afeta logs de aplicação, chamadas de API e erros do frontend.
                </span>
              </label>
              <div className="flex items-center gap-3">
                <input
                  type="range"
                  min="1"
                  max="90"
                  step="1"
                  value={settings.log_retention_days || "7"}
                  onChange={(e) => handleRetentionChange(e.target.value)}
                  className="flex-1 h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-purple-600"
                />
                <div className="flex items-center gap-1 min-w-[100px]">
                  <input
                    type="number"
                    min="1"
                    max="365"
                    value={settings.log_retention_days || "7"}
                    onChange={(e) => handleRetentionChange(e.target.value)}
                    className="w-16 px-2 py-1 text-center border border-gray-300 rounded-md focus:ring-2 focus:ring-purple-500 focus:border-purple-500"
                  />
                  <span className="text-sm text-gray-600">dias</span>
                </div>
              </div>
              <div className="flex justify-between text-xs text-gray-400">
                <span>1 dia</span>
                <span>90 dias</span>
              </div>
              <div className="text-xs text-gray-500">
                Valores acima de 90 podem ser digitados manualmente (máximo: 365 dias)
              </div>

              {/* Manual Log Cleanup */}
              <div className="mt-4 pt-4 border-t border-gray-100">
                <div className="flex items-center justify-between">
                  <div>
                    <span className="text-sm font-medium text-gray-700">
                      Limpeza manual de logs
                    </span>
                    <p className="text-xs text-gray-500 mt-1">
                      A limpeza automática executa a cada 24h. Use este botão para executar imediatamente.
                    </p>
                  </div>
                  <button
                    onClick={runLogCleanup}
                    disabled={runningLogCleanup || saving}
                    className="inline-flex items-center gap-2 px-3 py-1.5 bg-purple-100 text-purple-700 rounded-lg hover:bg-purple-200 disabled:opacity-50 disabled:cursor-not-allowed transition-colors text-sm"
                  >
                    {runningLogCleanup ? (
                      <>
                        <Loader2 className="w-4 h-4 animate-spin" />
                        Limpando...
                      </>
                    ) : (
                      <>
                        <Trash2 className="w-4 h-4" />
                        Limpar Agora
                      </>
                    )}
                  </button>
                </div>

                {/* Log Cleanup Result */}
                {lastLogCleanupResult && (
                  <div className="mt-3 p-3 bg-purple-50 border border-purple-200 rounded-lg">
                    <div className="flex items-center gap-2 mb-2">
                      <CheckCircle className="w-4 h-4 text-purple-600" />
                      <span className="font-medium text-purple-700">
                        Limpeza Concluída
                      </span>
                    </div>
                    <div className="text-sm text-purple-600 space-y-1">
                      <p>Período de retenção: {lastLogCleanupResult.retention_days} dias</p>
                      <p>Logs de aplicação: {lastLogCleanupResult.application_logs_deleted} removidos</p>
                      <p>Logs de API: {lastLogCleanupResult.api_logs_deleted} removidos</p>
                      <p>Erros do frontend: {lastLogCleanupResult.frontend_logs_deleted} removidos</p>
                      <p className="font-medium pt-1 border-t border-purple-200">
                        Total: {lastLogCleanupResult.total_deleted} logs removidos
                      </p>
                    </div>
                  </div>
                )}
              </div>
            </div>

            {/* Analytics Retention Period */}
            <div className="space-y-3 pt-4 border-t border-gray-200">
              <label className="block">
                <span className="flex items-center gap-2 text-sm font-medium text-gray-900">
                  <BarChart2 className="w-4 h-4 text-green-600" />
                  Período de retenção de analytics
                </span>
                <span className="text-sm text-gray-500 mt-1 block">
                  Define por quantos dias os registros de analytics (eventos de usuário) são mantidos.
                  Registros mais antigos são automaticamente removidos a cada 24 horas.
                </span>
              </label>
              <div className="flex items-center gap-3">
                <input
                  type="range"
                  min="1"
                  max="365"
                  step="1"
                  value={settings.analytics_retention_days || "90"}
                  onChange={(e) => handleAnalyticsRetentionChange(e.target.value)}
                  className="flex-1 h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-green-600"
                />
                <div className="flex items-center gap-1 min-w-[100px]">
                  <input
                    type="number"
                    min="1"
                    max="365"
                    value={settings.analytics_retention_days || "90"}
                    onChange={(e) => handleAnalyticsRetentionChange(e.target.value)}
                    className="w-16 px-2 py-1 text-center border border-gray-300 rounded-md focus:ring-2 focus:ring-green-500 focus:border-green-500"
                  />
                  <span className="text-sm text-gray-600">dias</span>
                </div>
              </div>
              <div className="flex justify-between text-xs text-gray-400">
                <span>1 dia</span>
                <span>365 dias</span>
              </div>
            </div>
          </div>

          {/* Save Button */}
          <div className="px-6 py-4 bg-gray-50 border-t border-gray-200 flex justify-end">
            <button
              onClick={handleSave}
              disabled={saving}
              className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {saving ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  Salvando...
                </>
              ) : (
                <>
                  <Save className="w-4 h-4" />
                  Salvar Configurações
                </>
              )}
            </button>
          </div>
        </div>

        {/* Database Maintenance Section */}
        <div className="mt-8 bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
          <div className="p-6 border-b border-gray-200">
            <h2 className="text-xl font-semibold text-gray-900 flex items-center gap-2">
              <Database className="w-5 h-5 text-purple-600" />
              Manutenção do Banco de Dados
            </h2>
            <p className="mt-1 text-sm text-gray-600">
              Limpe dados órfãos e corrija inconsistências no banco de dados
            </p>
          </div>

          <div className="p-6 space-y-6">
            {/* Database Stats */}
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium text-gray-900">
                  Estatísticas do Banco
                </span>
                <button
                  onClick={fetchDatabaseStats}
                  disabled={loadingStats}
                  className="inline-flex items-center gap-1 text-sm text-blue-600 hover:text-blue-700 disabled:opacity-50"
                >
                  <RefreshCw className={`w-4 h-4 ${loadingStats ? "animate-spin" : ""}`} />
                  Atualizar
                </button>
              </div>

              {loadingStats ? (
                <div className="flex items-center justify-center py-4">
                  <Loader2 className="w-5 h-5 animate-spin text-gray-400" />
                </div>
              ) : dbStats ? (
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  <div className="bg-gray-50 rounded-lg p-3">
                    <div className="text-2xl font-bold text-gray-900">
                      {dbStats.total_maps}
                    </div>
                    <div className="text-xs text-gray-500">Mapas</div>
                  </div>
                  <div className="bg-gray-50 rounded-lg p-3">
                    <div className="text-2xl font-bold text-gray-900">
                      {dbStats.total_pois}
                    </div>
                    <div className="text-xs text-gray-500">POIs Total</div>
                  </div>
                  <div className="bg-green-50 rounded-lg p-3">
                    <div className="text-2xl font-bold text-green-700">
                      {dbStats.referenced_pois}
                    </div>
                    <div className="text-xs text-green-600">POIs em Mapas</div>
                  </div>
                  <div className={`rounded-lg p-3 ${dbStats.unreferenced_pois > 0 ? "bg-amber-50" : "bg-gray-50"}`}>
                    <div className={`text-2xl font-bold ${dbStats.unreferenced_pois > 0 ? "text-amber-700" : "text-gray-900"}`}>
                      {dbStats.unreferenced_pois}
                    </div>
                    <div className={`text-xs ${dbStats.unreferenced_pois > 0 ? "text-amber-600" : "text-gray-500"}`}>
                      POIs Órfãos
                    </div>
                  </div>
                </div>
              ) : (
                <div className="text-sm text-gray-500 py-4 text-center">
                  Clique em &quot;Atualizar&quot; para carregar estatísticas
                </div>
              )}

              {dbStats && (dbStats.pending_operations > 0 || dbStats.stale_operations > 0) && (
                <div className="mt-3 flex gap-4 text-sm">
                  {dbStats.pending_operations > 0 && (
                    <span className="text-blue-600">
                      {dbStats.pending_operations} operações em andamento
                    </span>
                  )}
                  {dbStats.stale_operations > 0 && (
                    <span className="text-amber-600">
                      {dbStats.stale_operations} operações travadas
                    </span>
                  )}
                </div>
              )}
            </div>

            {/* Maintenance Actions */}
            <div className="space-y-3 pt-4 border-t border-gray-200">
              <span className="text-sm font-medium text-gray-900">
                Ações de Manutenção
              </span>
              <p className="text-sm text-gray-500">
                A manutenção irá:
              </p>
              <ul className="text-sm text-gray-600 list-disc list-inside space-y-1">
                <li>Remover POIs que não estão em nenhum mapa</li>
                <li>Corrigir flags de referência incorretas</li>
                <li>Limpar operações travadas há mais de 2 horas</li>
              </ul>

              {/* Last Maintenance Result */}
              {lastMaintenanceResult && (
                <div className={`mt-4 p-4 rounded-lg ${lastMaintenanceResult.dry_run ? "bg-blue-50 border border-blue-200" : "bg-green-50 border border-green-200"}`}>
                  <div className="flex items-center gap-2 mb-2">
                    {lastMaintenanceResult.dry_run ? (
                      <AlertTriangle className="w-4 h-4 text-blue-600" />
                    ) : (
                      <CheckCircle className="w-4 h-4 text-green-600" />
                    )}
                    <span className={`font-medium ${lastMaintenanceResult.dry_run ? "text-blue-700" : "text-green-700"}`}>
                      {lastMaintenanceResult.dry_run ? "Resultado da Simulação" : "Manutenção Concluída"}
                    </span>
                  </div>
                  <div className="text-sm space-y-1">
                    <p className={lastMaintenanceResult.dry_run ? "text-blue-600" : "text-green-600"}>
                      {lastMaintenanceResult.orphan_pois_found > 0
                        ? `${lastMaintenanceResult.dry_run ? "Seriam removidos" : "Removidos"} ${lastMaintenanceResult.orphan_pois_deleted} POIs órfãos`
                        : "Nenhum POI órfão encontrado"}
                    </p>
                    <p className={lastMaintenanceResult.dry_run ? "text-blue-600" : "text-green-600"}>
                      {lastMaintenanceResult.is_referenced_fixed > 0
                        ? `${lastMaintenanceResult.dry_run ? "Seriam corrigidas" : "Corrigidas"} ${lastMaintenanceResult.is_referenced_fixed} flags`
                        : "Todas as flags estão corretas"}
                    </p>
                    <p className={lastMaintenanceResult.dry_run ? "text-blue-600" : "text-green-600"}>
                      {lastMaintenanceResult.stale_operations_cleaned > 0
                        ? `Limpas ${lastMaintenanceResult.stale_operations_cleaned} operações travadas`
                        : "Nenhuma operação travada"}
                    </p>
                    <p className="text-gray-500 text-xs mt-2">
                      Tempo de execução: {lastMaintenanceResult.execution_time_ms}ms
                    </p>
                  </div>
                </div>
              )}

              <div className="flex gap-3 mt-4">
                <button
                  onClick={() => runMaintenance(true)}
                  disabled={runningMaintenance}
                  className="inline-flex items-center gap-2 px-4 py-2 bg-blue-100 text-blue-700 rounded-lg hover:bg-blue-200 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                >
                  {runningMaintenance ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  ) : (
                    <AlertTriangle className="w-4 h-4" />
                  )}
                  Simular
                </button>
                <button
                  onClick={() => runMaintenance(false)}
                  disabled={runningMaintenance}
                  className="inline-flex items-center gap-2 px-4 py-2 bg-red-100 text-red-700 rounded-lg hover:bg-red-200 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                >
                  {runningMaintenance ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  ) : (
                    <Trash2 className="w-4 h-4" />
                  )}
                  Executar Limpeza
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
