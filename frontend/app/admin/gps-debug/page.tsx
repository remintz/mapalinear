"use client";

import React, { useEffect, useState, useCallback } from "react";
import { useSession } from "next-auth/react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import {
  ArrowLeft,
  Loader2,
  RefreshCw,
  MapPin,
  Navigation,
  ChevronDown,
  ChevronUp,
  Map,
  Clock,
  User,
  Trash2,
  ExternalLink,
} from "lucide-react";
import { toast } from "sonner";
import { GPSDebugLogEntry, GPSDebugPOIInfo } from "@/lib/types";
import { apiClient } from "@/lib/api";

export default function AdminGPSDebugPage() {
  const { data: session, status } = useSession();
  const router = useRouter();
  const [logs, setLogs] = useState<GPSDebugLogEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expandedLogs, setExpandedLogs] = useState<Set<string>>(new Set());
  const [autoRefresh, setAutoRefresh] = useState(false);

  const fetchLogs = useCallback(async () => {
    try {
      setError(null);
      const data = await apiClient.getGPSDebugLogs(100);
      setLogs(data);
    } catch (err) {
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

    fetchLogs();
  }, [session, status, router, fetchLogs]);

  // Auto-refresh
  useEffect(() => {
    if (!autoRefresh) return;
    const interval = setInterval(() => fetchLogs(), 10000);
    return () => clearInterval(interval);
  }, [autoRefresh, fetchLogs]);

  const toggleLogExpanded = (logId: string) => {
    setExpandedLogs((prev) => {
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

  const handleCleanup = async () => {
    if (!confirm("Tem certeza que deseja limpar logs com mais de 30 dias?"))
      return;

    try {
      const baseUrl =
        process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001/api";
      const response = await fetch(`${baseUrl}/gps-debug/cleanup?days_to_keep=30`, {
        method: "DELETE",
        headers: {
          Authorization: `Bearer ${session?.accessToken}`,
        },
      });
      const result = await response.json();
      toast.success(result.message);
      fetchLogs();
    } catch {
      toast.error("Erro ao limpar logs");
    }
  };

  const openInGoogleMaps = (lat: number, lon: number) => {
    window.open(
      `https://www.google.com/maps?q=${lat},${lon}`,
      "_blank"
    );
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
                <Navigation className="w-8 h-8 text-orange-600" />
                GPS Debug Logs
              </h1>
              <p className="mt-2 text-gray-600">
                {logs.length} log{logs.length !== 1 ? "s" : ""} de debug GPS
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
                onClick={() => {
                  setLoading(true);
                  fetchLogs();
                }}
                className="inline-flex items-center gap-2 px-3 py-2 bg-white border border-gray-300 rounded-md text-sm font-medium text-gray-700 hover:bg-gray-50"
              >
                <RefreshCw className="w-4 h-4" />
                Atualizar
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

        {error && (
          <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg text-red-700">
            {error}
          </div>
        )}

        {/* Logs List */}
        <div className="space-y-4">
          {loading ? (
            <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-12 flex items-center justify-center">
              <div className="flex items-center gap-3">
                <Loader2 className="w-6 h-6 animate-spin text-blue-600" />
                <span className="text-gray-600">Carregando logs...</span>
              </div>
            </div>
          ) : logs.length === 0 ? (
            <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-12 text-center">
              <Navigation className="mx-auto h-12 w-12 text-gray-400" />
              <h3 className="mt-2 text-sm font-medium text-gray-900">
                Nenhum log de GPS debug
              </h3>
              <p className="mt-1 text-sm text-gray-500">
                Os logs são gerados automaticamente quando um admin abre o mapa
                com GPS ativo.
              </p>
            </div>
          ) : (
            logs.map((log) => (
              <div
                key={log.id}
                className="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden"
              >
                {/* Header */}
                <div
                  className="p-4 cursor-pointer hover:bg-gray-50"
                  onClick={() => toggleLogExpanded(log.id)}
                >
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center gap-3 mb-2">
                        <span
                          className={`inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium ${
                            log.is_on_route
                              ? "bg-green-100 text-green-800"
                              : "bg-red-100 text-red-800"
                          }`}
                        >
                          <MapPin className="w-3 h-3" />
                          {log.is_on_route ? "Na rota" : "Fora da rota"}
                        </span>
                        <span className="text-sm text-gray-500 flex items-center gap-1">
                          <Clock className="w-3 h-3" />
                          {formatRelativeTime(log.created_at)}
                        </span>
                        <span className="text-sm text-gray-500 flex items-center gap-1">
                          <User className="w-3 h-3" />
                          {log.user_email}
                        </span>
                      </div>

                      <div className="flex items-center gap-2 mb-2">
                        <Map className="w-4 h-4 text-blue-600" />
                        <span className="font-medium text-gray-900">
                          {log.map_origin} → {log.map_destination}
                        </span>
                      </div>

                      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                        <div>
                          <span className="text-gray-500">Coordenadas:</span>
                          <div className="font-mono text-gray-900">
                            {log.latitude.toFixed(5)}, {log.longitude.toFixed(5)}
                          </div>
                        </div>
                        <div>
                          <span className="text-gray-500">Distância da origem:</span>
                          <div className="font-semibold text-blue-600">
                            {log.distance_from_origin_km?.toFixed(2) ?? "N/A"} km
                          </div>
                        </div>
                        {log.distance_to_route_m !== undefined && (
                          <div>
                            <span className="text-gray-500">Distância da rota:</span>
                            <div className="text-gray-900">
                              {log.distance_to_route_m.toFixed(0)} m
                            </div>
                          </div>
                        )}
                        {log.gps_accuracy !== undefined && (
                          <div>
                            <span className="text-gray-500">Precisão GPS:</span>
                            <div className="text-gray-900">
                              ±{log.gps_accuracy.toFixed(0)} m
                            </div>
                          </div>
                        )}
                      </div>
                    </div>

                    <div className="flex items-center gap-2 ml-4">
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          openInGoogleMaps(log.latitude, log.longitude);
                        }}
                        className="p-2 text-gray-400 hover:text-blue-600 hover:bg-blue-50 rounded-md"
                        title="Abrir no Google Maps"
                      >
                        <ExternalLink className="w-4 h-4" />
                      </button>
                      {expandedLogs.has(log.id) ? (
                        <ChevronUp className="w-5 h-5 text-gray-400" />
                      ) : (
                        <ChevronDown className="w-5 h-5 text-gray-400" />
                      )}
                    </div>
                  </div>
                </div>

                {/* Expanded content */}
                {expandedLogs.has(log.id) && (
                  <div className="border-t border-gray-200 p-4 bg-gray-50">
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                      {/* Previous POIs */}
                      <div>
                        <h4 className="font-medium text-gray-900 mb-3 flex items-center gap-2">
                          <span className="text-red-500">←</span>
                          POIs Anteriores (já passou)
                        </h4>
                        {log.previous_pois && log.previous_pois.length > 0 ? (
                          <div className="space-y-2">
                            {log.previous_pois.map((poi: GPSDebugPOIInfo, idx: number) => (
                              <div
                                key={idx}
                                className="bg-white rounded border border-gray-200 p-3 text-sm"
                              >
                                <div className="flex items-center justify-between">
                                  <div>
                                    <span className="font-medium text-gray-900">
                                      {poi.name}
                                    </span>
                                    <span className="ml-2 text-xs text-gray-500">
                                      ({poi.type})
                                    </span>
                                  </div>
                                  <span className="text-red-600 font-mono text-xs">
                                    {poi.relative_distance_km.toFixed(2)} km
                                  </span>
                                </div>
                                <div className="text-xs text-gray-500 mt-1">
                                  {poi.distance_from_origin_km.toFixed(2)} km da origem
                                </div>
                              </div>
                            ))}
                          </div>
                        ) : (
                          <p className="text-sm text-gray-500 italic">
                            Nenhum POI anterior registrado
                          </p>
                        )}
                      </div>

                      {/* Next POIs */}
                      <div>
                        <h4 className="font-medium text-gray-900 mb-3 flex items-center gap-2">
                          <span className="text-green-500">→</span>
                          Próximos POIs (à frente)
                        </h4>
                        {log.next_pois && log.next_pois.length > 0 ? (
                          <div className="space-y-2">
                            {log.next_pois.map((poi: GPSDebugPOIInfo, idx: number) => (
                              <div
                                key={idx}
                                className="bg-white rounded border border-gray-200 p-3 text-sm"
                              >
                                <div className="flex items-center justify-between">
                                  <div>
                                    <span className="font-medium text-gray-900">
                                      {poi.name}
                                    </span>
                                    <span className="ml-2 text-xs text-gray-500">
                                      ({poi.type})
                                    </span>
                                  </div>
                                  <span className="text-green-600 font-mono text-xs">
                                    +{poi.relative_distance_km.toFixed(2)} km
                                  </span>
                                </div>
                                <div className="text-xs text-gray-500 mt-1">
                                  {poi.distance_from_origin_km.toFixed(2)} km da origem
                                </div>
                              </div>
                            ))}
                          </div>
                        ) : (
                          <p className="text-sm text-gray-500 italic">
                            Nenhum POI à frente registrado
                          </p>
                        )}
                      </div>
                    </div>

                    {/* Additional info */}
                    <div className="mt-4 pt-4 border-t border-gray-200">
                      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-xs text-gray-500">
                        <div>
                          <span className="font-medium">ID do log:</span>
                          <div className="font-mono">{log.id.substring(0, 8)}...</div>
                        </div>
                        <div>
                          <span className="font-medium">Map ID:</span>
                          <div className="font-mono">{log.map_id.substring(0, 8)}...</div>
                        </div>
                        {log.session_id && (
                          <div>
                            <span className="font-medium">Session ID:</span>
                            <div className="font-mono">
                              {log.session_id.substring(0, 8)}...
                            </div>
                          </div>
                        )}
                        <div>
                          <span className="font-medium">Data/hora:</span>
                          <div>{formatTimestamp(log.created_at)}</div>
                        </div>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}
