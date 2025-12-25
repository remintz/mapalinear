"use client";

import { useSession } from "next-auth/react";
import { useRouter, useParams } from "next/navigation";
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
  ExternalLink,
  Fuel,
  Utensils,
  Bed,
  Tent,
  Hospital,
  Ticket,
  Building2,
  Coffee,
  MapPin,
} from "lucide-react";
import { AdminMapDetail } from "@/lib/types";
import { toast } from "sonner";
import RouteMapModal from "@/components/RouteMapModal";

// POI type labels and icons
const POI_TYPE_CONFIG: Record<string, { label: string; icon: React.ComponentType<{ className?: string }>; color: string }> = {
  gas_station: { label: "Postos de Combustível", icon: Fuel, color: "text-orange-600 bg-orange-100" },
  restaurant: { label: "Restaurantes", icon: Utensils, color: "text-red-600 bg-red-100" },
  fast_food: { label: "Fast Food", icon: Utensils, color: "text-yellow-600 bg-yellow-100" },
  cafe: { label: "Cafeterias", icon: Coffee, color: "text-amber-600 bg-amber-100" },
  hotel: { label: "Hotéis", icon: Bed, color: "text-blue-600 bg-blue-100" },
  camping: { label: "Campings", icon: Tent, color: "text-green-600 bg-green-100" },
  hospital: { label: "Hospitais", icon: Hospital, color: "text-red-600 bg-red-100" },
  toll_booth: { label: "Pedágios", icon: Ticket, color: "text-purple-600 bg-purple-100" },
  rest_area: { label: "Áreas de Descanso", icon: Building2, color: "text-teal-600 bg-teal-100" },
  city: { label: "Cidades", icon: Building2, color: "text-gray-600 bg-gray-100" },
  town: { label: "Vilas", icon: MapPin, color: "text-gray-500 bg-gray-100" },
  village: { label: "Vilarejos", icon: MapPin, color: "text-gray-400 bg-gray-50" },
};

export default function AdminMapDetailsPage() {
  const { data: session, status } = useSession();
  const router = useRouter();
  const params = useParams();
  const mapId = params.id as string;

  const [mapDetails, setMapDetails] = useState<AdminMapDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [regeneratingMap, setRegeneratingMap] = useState(false);
  const [deletingMap, setDeletingMap] = useState(false);
  const [deleteConfirmation, setDeleteConfirmation] = useState<{
    step: 1 | 2;
  } | null>(null);
  const [osmMapOpen, setOsmMapOpen] = useState(false);

  const fetchMapDetails = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);

      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001/api"}/admin/maps/${mapId}`,
        {
          headers: {
            Authorization: `Bearer ${session?.accessToken}`,
          },
        }
      );

      if (!response.ok) {
        throw new Error("Falha ao carregar detalhes do mapa");
      }

      const data: AdminMapDetail = await response.json();
      setMapDetails(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erro desconhecido");
    } finally {
      setLoading(false);
    }
  }, [session?.accessToken, mapId]);

  const handleRegenerate = async () => {
    if (!confirm("Deseja recalcular este mapa? Isso pode levar alguns minutos.")) {
      return;
    }

    try {
      setRegeneratingMap(true);

      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001/api"}/maps/${mapId}/regenerate`,
        {
          method: "POST",
          headers: {
            Authorization: `Bearer ${session?.accessToken}`,
          },
        }
      );

      if (!response.ok) {
        throw new Error("Falha ao iniciar recálculo do mapa");
      }

      const data = await response.json();
      toast.success(`Recálculo iniciado. Operation ID: ${data.operation_id}`);

      // Refresh details after a delay
      setTimeout(() => {
        fetchMapDetails();
      }, 2000);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Erro ao recalcular mapa");
    } finally {
      setRegeneratingMap(false);
    }
  };

  const initiateDelete = () => {
    setDeleteConfirmation({ step: 1 });
  };

  const handleDelete = async () => {
    if (!deleteConfirmation || !mapDetails) return;

    const { step } = deleteConfirmation;

    // If map has users and we're on step 1, move to step 2
    if (mapDetails.user_count > 0 && step === 1) {
      setDeleteConfirmation({ step: 2 });
      return;
    }

    try {
      setDeletingMap(true);

      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001/api"}/maps/${mapId}/permanent`,
        {
          method: "DELETE",
          headers: {
            Authorization: `Bearer ${session?.accessToken}`,
          },
        }
      );

      if (!response.ok) {
        throw new Error("Falha ao deletar mapa");
      }

      toast.success("Mapa deletado permanentemente");
      router.push("/admin/maps");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Erro ao deletar mapa");
    } finally {
      setDeletingMap(false);
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

    fetchMapDetails();
  }, [session, status, router, fetchMapDetails]);

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

  const getTotalPOIs = () => {
    if (!mapDetails?.poi_counts) return 0;
    return Object.values(mapDetails.poi_counts).reduce((a, b) => a + b, 0);
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

  if (error) {
    return (
      <div className="min-h-screen bg-gray-50 py-8">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
          <Link
            href="/admin/maps"
            className="inline-flex items-center gap-2 text-gray-600 hover:text-gray-900 mb-4"
          >
            <ArrowLeft className="w-4 h-4" />
            Voltar para Mapas
          </Link>
          <div className="p-6 bg-red-50 border border-red-200 rounded-lg text-red-700">
            {error}
          </div>
        </div>
      </div>
    );
  }

  if (!mapDetails) {
    return null;
  }

  return (
    <div className="min-h-screen bg-gray-50 py-8">
      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="mb-8">
          <Link
            href="/admin/maps"
            className="inline-flex items-center gap-2 text-gray-600 hover:text-gray-900 mb-4"
          >
            <ArrowLeft className="w-4 h-4" />
            Voltar para Mapas
          </Link>

          <div className="flex items-start justify-between">
            <div>
              <h1 className="text-3xl font-bold text-gray-900 flex items-center gap-3">
                <MapIcon className="w-8 h-8 text-blue-600" />
                Detalhes do Mapa
              </h1>
              <div className="mt-2 flex items-center gap-2">
                <Route className="w-5 h-5 text-gray-400" />
                <span className="text-lg text-gray-600">
                  {mapDetails.origin} → {mapDetails.destination}
                </span>
              </div>
            </div>

            <div className="flex items-center gap-2">
              <button
                onClick={handleRegenerate}
                disabled={regeneratingMap}
                className="inline-flex items-center gap-1.5 px-4 py-2 rounded-md text-sm font-medium bg-blue-100 text-blue-700 hover:bg-blue-200 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {regeneratingMap ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <RefreshCw className="w-4 h-4" />
                )}
                Recalcular
              </button>
              <button
                onClick={initiateDelete}
                disabled={deletingMap}
                className="inline-flex items-center gap-1.5 px-4 py-2 rounded-md text-sm font-medium bg-red-100 text-red-700 hover:bg-red-200 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {deletingMap ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <Trash2 className="w-4 h-4" />
                )}
                Deletar
              </button>
            </div>
          </div>
        </div>

        {/* Info Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
          <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-blue-100 rounded-lg">
                <Route className="w-5 h-5 text-blue-600" />
              </div>
              <div>
                <p className="text-sm text-gray-500">Distância Total</p>
                <p className="text-lg font-semibold text-gray-900">
                  {formatDistance(mapDetails.total_length_km)}
                </p>
              </div>
            </div>
          </div>

          <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-green-100 rounded-lg">
                <Users className="w-5 h-5 text-green-600" />
              </div>
              <div>
                <p className="text-sm text-gray-500">Usuários</p>
                <p className="text-lg font-semibold text-gray-900">
                  {mapDetails.user_count}
                </p>
              </div>
            </div>
          </div>

          <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-purple-100 rounded-lg">
                <Calendar className="w-5 h-5 text-purple-600" />
              </div>
              <div>
                <p className="text-sm text-gray-500">Criado em</p>
                <p className="text-lg font-semibold text-gray-900">
                  {formatDate(mapDetails.created_at)}
                </p>
              </div>
            </div>
          </div>
        </div>

        {/* Action Buttons */}
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 mb-8">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Visualizar Mapa</h2>
          <div className="flex flex-wrap gap-4">
            <Link
              href={`/map?mapId=${mapId}`}
              className="inline-flex items-center gap-2 px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors font-medium"
            >
              <MapIcon className="w-5 h-5" />
              Abrir Mapa Linear
              <ExternalLink className="w-4 h-4" />
            </Link>
            <button
              onClick={() => setOsmMapOpen(true)}
              className="inline-flex items-center gap-2 px-6 py-3 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors font-medium"
            >
              <Route className="w-5 h-5" />
              Abrir Mapa OSM
            </button>
          </div>
        </div>

        {/* POI Counts */}
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">
            Pontos de Interesse ({getTotalPOIs()} total)
          </h2>

          {Object.keys(mapDetails.poi_counts || {}).length === 0 ? (
            <p className="text-gray-500">Nenhum POI encontrado neste mapa.</p>
          ) : (
            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
              {Object.entries(mapDetails.poi_counts)
                .sort((a, b) => b[1] - a[1])
                .map(([type, count]) => {
                  const config = POI_TYPE_CONFIG[type] || {
                    label: type.replace(/_/g, " ").replace(/\b\w/g, (l) => l.toUpperCase()),
                    icon: MapPin,
                    color: "text-gray-600 bg-gray-100",
                  };
                  const IconComponent = config.icon;

                  return (
                    <div
                      key={type}
                      className="flex items-center gap-3 p-3 rounded-lg border border-gray-200"
                    >
                      <div className={`p-2 rounded-lg ${config.color.split(" ")[1]}`}>
                        <IconComponent className={`w-5 h-5 ${config.color.split(" ")[0]}`} />
                      </div>
                      <div>
                        <p className="text-2xl font-bold text-gray-900">{count}</p>
                        <p className="text-xs text-gray-500">{config.label}</p>
                      </div>
                    </div>
                  );
                })}
            </div>
          )}
        </div>
      </div>

      {/* OSM Map Modal */}
      <RouteMapModal
        mapId={mapId}
        isOpen={osmMapOpen}
        onClose={() => setOsmMapOpen(false)}
      />

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
                  {mapDetails.user_count > 0 && (
                    <div className="p-3 bg-amber-50 border border-amber-200 rounded-lg">
                      <p className="text-amber-800 font-medium flex items-center gap-2">
                        <Users className="w-4 h-4" />
                        {mapDetails.user_count} usuário
                        {mapDetails.user_count !== 1 ? "s" : ""}{" "}
                        {mapDetails.user_count !== 1 ? "têm" : "tem"}{" "}
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
                      {mapDetails.user_count} usuário
                      {mapDetails.user_count !== 1 ? "s" : ""} perderá
                      {mapDetails.user_count !== 1 ? "ão" : ""} acesso a
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
                disabled={deletingMap}
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
                ) : mapDetails.user_count > 0 ? (
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
