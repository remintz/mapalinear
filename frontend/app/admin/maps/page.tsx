"use client";

import { useSession } from "next-auth/react";
import { useRouter } from "next/navigation";
import { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import {
  Map as MapIcon,
  ArrowLeft,
  Calendar,
  Users,
  Loader2,
  RefreshCw,
  Trash2,
  AlertTriangle,
  Route,
  X,
  Eye,
} from "lucide-react";
import React from "react";
import { AdminMap } from "@/lib/types";
import { apiClient } from "@/lib/api";
import { toast } from "sonner";

export default function AdminMapsPage() {
  const { data: session, status } = useSession();
  const router = useRouter();
  const [maps, setMaps] = useState<AdminMap[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [regeneratingMap, setRegeneratingMap] = useState<string | null>(null);
  const [deletingMap, setDeletingMap] = useState<string | null>(null);
  const [deleteConfirmation, setDeleteConfirmation] = useState<{
    mapId: string;
    userCount: number;
    step: 1 | 2;
  } | null>(null);

  const fetchMaps = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);

      const data = await apiClient.getAdminMaps();
      setMaps(data.maps);
    } catch (err) {
      // apiClient handles 401 automatically and redirects to login
      setError(err instanceof Error ? err.message : "Erro desconhecido");
    } finally {
      setLoading(false);
    }
  }, []);

  const handleRegenerate = async (e: React.MouseEvent, mapId: string) => {
    e.stopPropagation();
    if (!confirm("Deseja recalcular este mapa? Isso pode levar alguns minutos.")) {
      return;
    }

    try {
      setRegeneratingMap(mapId);

      const data = await apiClient.regenerateMap(mapId);
      toast.success(`Recálculo iniciado. Operation ID: ${data.operation_id}`);

      // Refresh the list after a delay
      setTimeout(() => {
        fetchMaps();
      }, 2000);
    } catch (err) {
      // apiClient handles 401 automatically and redirects to login
      toast.error(err instanceof Error ? err.message : "Erro ao recalcular mapa");
    } finally {
      setRegeneratingMap(null);
    }
  };

  const initiateDelete = (e: React.MouseEvent, mapId: string, userCount: number) => {
    e.stopPropagation();
    setDeleteConfirmation({ mapId, userCount, step: 1 });
  };

  const handleDelete = async () => {
    if (!deleteConfirmation) return;

    const { mapId, userCount, step } = deleteConfirmation;

    // If map has users and we're on step 1, move to step 2
    if (userCount > 0 && step === 1) {
      setDeleteConfirmation({ ...deleteConfirmation, step: 2 });
      return;
    }

    try {
      setDeletingMap(mapId);

      await apiClient.permanentlyDeleteMap(mapId);

      toast.success("Mapa deletado permanentemente");
      setMaps((prev) => prev.filter((m) => m.id !== mapId));
      setDeleteConfirmation(null);
    } catch (err) {
      // apiClient handles 401 automatically and redirects to login
      toast.error(err instanceof Error ? err.message : "Erro ao deletar mapa");
    } finally {
      setDeletingMap(null);
    }
  };

  const cancelDelete = () => {
    setDeleteConfirmation(null);
  };

  useEffect(() => {
    if (status === "loading") return;

    if (!session?.user?.isAdmin) {
      router.push("/");
      return;
    }

    fetchMaps();
  }, [session, status, router, fetchMaps]);

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

  const formatDistance = (km: number) => {
    return `${km.toFixed(1)} km`;
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

          <h1 className="text-3xl font-bold text-gray-900 flex items-center gap-3">
            <MapIcon className="w-8 h-8 text-blue-600" />
            Mapas
          </h1>
          <p className="mt-2 text-gray-600">
            {maps.length} mapa{maps.length !== 1 ? "s" : ""} cadastrado
            {maps.length !== 1 ? "s" : ""}
          </p>
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
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Rota
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Distância
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Criado em
                  </th>
                  <th className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Usuários
                  </th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Ações
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {maps.map((map) => (
                  <tr
                    key={map.id}
                    className="hover:bg-gray-50 cursor-pointer"
                    onClick={() => router.push(`/admin/maps/${map.id}`)}
                  >
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-3">
                        <div className="p-2 bg-blue-100 rounded-lg">
                          <Route className="w-5 h-5 text-blue-600" />
                        </div>
                        <div>
                          <div className="text-sm font-medium text-gray-900">
                            {map.origin}
                          </div>
                          <div className="text-sm text-gray-500">
                            → {map.destination}
                          </div>
                        </div>
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className="text-sm text-gray-600">
                        {formatDistance(map.total_length_km)}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="flex items-center gap-1 text-sm text-gray-600">
                        <Calendar className="w-4 h-4" />
                        {formatDate(map.created_at)}
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-center">
                      <span
                        className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium ${
                          map.user_count > 0
                            ? "bg-green-100 text-green-800"
                            : "bg-gray-100 text-gray-600"
                        }`}
                      >
                        <Users className="w-3 h-3" />
                        {map.user_count}
                      </span>
                    </td>
                    <td
                      className="px-6 py-4 whitespace-nowrap text-right"
                      onClick={(e) => e.stopPropagation()}
                    >
                      <div className="flex items-center justify-end gap-2">
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            router.push(`/admin/maps/${map.id}`);
                          }}
                          className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md text-sm font-medium bg-gray-100 text-gray-700 hover:bg-gray-200 transition-colors"
                          title="Ver detalhes"
                        >
                          <Eye className="w-4 h-4" />
                          Detalhes
                        </button>
                        <button
                          onClick={(e) => handleRegenerate(e, map.id)}
                          disabled={regeneratingMap === map.id}
                          className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md text-sm font-medium bg-blue-100 text-blue-700 hover:bg-blue-200 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                          title="Recalcular mapa"
                        >
                          {regeneratingMap === map.id ? (
                            <Loader2 className="w-4 h-4 animate-spin" />
                          ) : (
                            <RefreshCw className="w-4 h-4" />
                          )}
                          Recalcular
                        </button>
                        <button
                          onClick={(e) => initiateDelete(e, map.id, map.user_count)}
                          disabled={deletingMap === map.id}
                          className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md text-sm font-medium bg-red-100 text-red-700 hover:bg-red-200 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                          title="Deletar permanentemente"
                        >
                          {deletingMap === map.id ? (
                            <Loader2 className="w-4 h-4 animate-spin" />
                          ) : (
                            <Trash2 className="w-4 h-4" />
                          )}
                          Deletar
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {maps.length === 0 && !loading && (
            <div className="text-center py-12">
              <MapIcon className="mx-auto h-12 w-12 text-gray-400" />
              <h3 className="mt-2 text-sm font-medium text-gray-900">
                Nenhum mapa encontrado
              </h3>
              <p className="mt-1 text-sm text-gray-500">
                Não há mapas cadastrados no sistema.
              </p>
            </div>
          )}
        </div>
      </div>

      {/* Delete Confirmation Modal */}
      {deleteConfirmation && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl max-w-md w-full mx-4 overflow-hidden">
            <div className="p-6">
              <div className="flex items-center gap-3 mb-4">
                <div
                  className={`p-3 rounded-full ${
                    deleteConfirmation.step === 2
                      ? "bg-red-100"
                      : "bg-amber-100"
                  }`}
                >
                  <AlertTriangle
                    className={`w-6 h-6 ${
                      deleteConfirmation.step === 2
                        ? "text-red-600"
                        : "text-amber-600"
                    }`}
                  />
                </div>
                <div>
                  <h3 className="text-lg font-semibold text-gray-900">
                    {deleteConfirmation.step === 2
                      ? "Confirmação Final"
                      : "Confirmar Exclusão"}
                  </h3>
                </div>
                <button
                  onClick={cancelDelete}
                  className="ml-auto p-1 hover:bg-gray-100 rounded"
                >
                  <X className="w-5 h-5 text-gray-500" />
                </button>
              </div>

              {deleteConfirmation.step === 1 ? (
                <div className="space-y-4">
                  <p className="text-gray-600">
                    Você está prestes a deletar permanentemente este mapa. Esta
                    ação não pode ser desfeita.
                  </p>
                  {deleteConfirmation.userCount > 0 && (
                    <div className="p-3 bg-amber-50 border border-amber-200 rounded-lg">
                      <p className="text-amber-800 font-medium flex items-center gap-2">
                        <Users className="w-4 h-4" />
                        {deleteConfirmation.userCount} usuário
                        {deleteConfirmation.userCount !== 1 ? "s" : ""}{" "}
                        {deleteConfirmation.userCount !== 1 ? "têm" : "tem"}{" "}
                        este mapa em sua coleção
                      </p>
                      <p className="text-amber-700 text-sm mt-1">
                        A exclusão removerá o mapa da coleção de todos os
                        usuários.
                      </p>
                    </div>
                  )}
                </div>
              ) : (
                <div className="space-y-4">
                  <div className="p-4 bg-red-50 border border-red-200 rounded-lg">
                    <p className="text-red-800 font-bold text-center">
                      ATENÇÃO: Esta ação é IRREVERSÍVEL!
                    </p>
                    <p className="text-red-700 text-sm mt-2 text-center">
                      {deleteConfirmation.userCount} usuário
                      {deleteConfirmation.userCount !== 1 ? "s" : ""} perderá
                      {deleteConfirmation.userCount !== 1 ? "ão" : ""} acesso a
                      este mapa permanentemente.
                    </p>
                  </div>
                  <p className="text-gray-600 text-center">
                    Tem certeza absoluta que deseja continuar?
                  </p>
                </div>
              )}
            </div>

            <div className="px-6 py-4 bg-gray-50 flex gap-3 justify-end">
              <button
                onClick={cancelDelete}
                className="px-4 py-2 text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 transition-colors"
              >
                Cancelar
              </button>
              <button
                onClick={handleDelete}
                disabled={deletingMap !== null}
                className={`px-4 py-2 text-white rounded-md transition-colors disabled:opacity-50 ${
                  deleteConfirmation.step === 2
                    ? "bg-red-600 hover:bg-red-700"
                    : "bg-amber-600 hover:bg-amber-700"
                }`}
              >
                {deletingMap ? (
                  <span className="flex items-center gap-2">
                    <Loader2 className="w-4 h-4 animate-spin" />
                    Deletando...
                  </span>
                ) : deleteConfirmation.step === 2 ? (
                  "Sim, deletar permanentemente"
                ) : deleteConfirmation.userCount > 0 ? (
                  "Continuar"
                ) : (
                  "Deletar"
                )}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
