"use client";

import { useSession } from "next-auth/react";
import { useRouter, useParams } from "next/navigation";
import { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import dynamic from "next/dynamic";
import {
  ArrowLeft,
  MapPin,
  Phone,
  Globe,
  Clock,
  Star,
  Tag,
  AlertTriangle,
  CheckCircle,
  Loader2,
  ExternalLink,
  Building,
  Map,
  Edit3,
} from "lucide-react";
import { toast } from "sonner";
import { apiClient } from "@/lib/api";
import { AdminPOIDetail } from "@/lib/types";

// Dynamically import the map component to avoid SSR issues with Leaflet
const POIDetailMap = dynamic(() => import("@/components/admin/POIDetailMap"), {
  ssr: false,
  loading: () => (
    <div className="h-64 bg-gray-100 rounded-lg flex items-center justify-center">
      <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
    </div>
  ),
});

const POI_TYPE_LABELS: Record<string, string> = {
  gas_station: "Posto de Combustível",
  restaurant: "Restaurante",
  hotel: "Hotel",
  hospital: "Hospital",
  toll_booth: "Pedágio",
  rest_area: "Área de Descanso",
  city: "Cidade",
  town: "Cidade",
  village: "Vila",
};

const POI_TYPE_ICONS: Record<string, string> = {
  gas_station: "⛽",
  restaurant: "🍽️",
  hotel: "🏨",
  hospital: "🏥",
  toll_booth: "🚧",
  rest_area: "🅿️",
  city: "🏙️",
  town: "🏘️",
  village: "🏡",
};

/**
 * Generate OSM edit URL from osm_id.
 * Supports formats: "node/123456", "way/123456", or just "123456" (assumes node)
 */
function getOsmEditUrl(osmId: string): string | null {
  if (!osmId) return null;

  // Check if it has type prefix (node/way/relation)
  if (osmId.includes("/")) {
    const [osmType, osmNumericId] = osmId.split("/", 2);
    if (!["node", "way", "relation"].includes(osmType)) return null;
    return `https://www.openstreetmap.org/edit?${osmType}=${osmNumericId}`;
  }

  // If it's just a number, assume it's a node (most POIs are nodes)
  if (/^\d+$/.test(osmId)) {
    return `https://www.openstreetmap.org/edit?node=${osmId}`;
  }

  return null;
}

export default function POIDetailPage() {
  const { data: session, status } = useSession();
  const router = useRouter();
  const params = useParams();
  const poiId = params.id as string;

  const [poi, setPoi] = useState<AdminPOIDetail | null>(null);
  const [loading, setLoading] = useState(true);

  const loadPOI = useCallback(async () => {
    try {
      setLoading(true);
      const data = await apiClient.getAdminPOI(poiId);
      setPoi(data);
    } catch (error) {
      console.error("Error loading POI:", error);
      toast.error("Erro ao carregar POI");
      router.push("/admin/pois");
    } finally {
      setLoading(false);
    }
  }, [poiId, router]);

  // Auth check
  useEffect(() => {
    if (status === "loading") return;
    if (!session?.user?.isAdmin) {
      router.push("/");
    }
  }, [session, status, router]);

  // Load POI
  useEffect(() => {
    if (session?.user?.isAdmin && poiId) {
      loadPOI();
    }
  }, [session, poiId, loadPOI]);

  if (status === "loading" || loading || !session?.user?.isAdmin) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
      </div>
    );
  }

  if (!poi) {
    return null;
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="sticky top-0 z-20 bg-white border-b border-gray-200 shadow-sm">
        <div className="max-w-7xl mx-auto px-4 py-4">
          <div className="flex items-center gap-3">
            <Link href="/admin/pois" className="text-blue-600 hover:text-blue-700">
              <ArrowLeft className="h-5 w-5" />
            </Link>
            <div className="flex items-center gap-2">
              <span className="text-2xl">{POI_TYPE_ICONS[poi.type] || "📍"}</span>
              <div>
                <h1 className="text-xl font-bold text-gray-900">{poi.name || "Sem nome"}</h1>
                <p className="text-sm text-gray-600">
                  {POI_TYPE_LABELS[poi.type] || poi.type}
                  {poi.city && ` • ${poi.city}`}
                </p>
              </div>
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 py-6">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Left Column - Map and Location */}
          <div className="space-y-6">
            {/* Map */}
            <div className="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
              <div className="p-4 border-b border-gray-200">
                <h2 className="font-semibold text-gray-900 flex items-center gap-2">
                  <Map className="h-4 w-4 text-blue-600" />
                  Localização
                </h2>
              </div>
              <div className="h-64">
                <POIDetailMap
                  latitude={poi.latitude}
                  longitude={poi.longitude}
                  name={poi.name}
                  type={poi.type}
                />
              </div>
              <div className="p-4 bg-gray-50 text-sm text-gray-600">
                <div className="flex items-center gap-2">
                  <MapPin className="h-4 w-4" />
                  <span>
                    {poi.latitude.toFixed(6)}, {poi.longitude.toFixed(6)}
                  </span>
                </div>
              </div>
            </div>

            {/* Quality Status */}
            <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
              <h2 className="font-semibold text-gray-900 mb-3 flex items-center gap-2">
                {poi.is_low_quality ? (
                  <AlertTriangle className="h-4 w-4 text-amber-500" />
                ) : (
                  <CheckCircle className="h-4 w-4 text-green-500" />
                )}
                Status de Qualidade
              </h2>

              {poi.is_low_quality ? (
                <div className="space-y-3">
                  <div className="p-3 bg-amber-50 border border-amber-200 rounded-lg">
                    <p className="text-sm text-amber-700 font-medium">
                      Este POI está com baixa qualidade
                    </p>
                    <p className="text-xs text-amber-600 mt-1">
                      Tags obrigatórias faltando: {poi.missing_tags.join(", ")}
                    </p>
                  </div>
                </div>
              ) : (
                <div className="p-3 bg-green-50 border border-green-200 rounded-lg">
                  <p className="text-sm text-green-700 font-medium">
                    Este POI está com qualidade OK
                  </p>
                  <p className="text-xs text-green-600 mt-1">
                    Todas as tags obrigatórias estão presentes
                  </p>
                </div>
              )}

              {poi.quality_score !== null && poi.quality_score !== undefined && (
                <div className="mt-3 text-sm text-gray-600">
                  Score de qualidade: {(poi.quality_score * 100).toFixed(0)}%
                </div>
              )}
            </div>
          </div>

          {/* Right Column - Details */}
          <div className="space-y-6">
            {/* Basic Info */}
            <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
              <h2 className="font-semibold text-gray-900 mb-3 flex items-center gap-2">
                <Building className="h-4 w-4 text-blue-600" />
                Informações Básicas
              </h2>

              <dl className="space-y-2">
                {poi.brand && (
                  <div className="flex justify-between">
                    <dt className="text-sm text-gray-500">Marca</dt>
                    <dd className="text-sm text-gray-900 font-medium">{poi.brand}</dd>
                  </div>
                )}
                {poi.operator && (
                  <div className="flex justify-between">
                    <dt className="text-sm text-gray-500">Operadora</dt>
                    <dd className="text-sm text-gray-900">{poi.operator}</dd>
                  </div>
                )}
                {poi.cuisine && (
                  <div className="flex justify-between">
                    <dt className="text-sm text-gray-500">Culinária</dt>
                    <dd className="text-sm text-gray-900">{poi.cuisine}</dd>
                  </div>
                )}
                {poi.rating && (
                  <div className="flex justify-between items-center">
                    <dt className="text-sm text-gray-500 flex items-center gap-1">
                      <Star className="h-3 w-3 text-yellow-500" />
                      Avaliação
                    </dt>
                    <dd className="text-sm text-gray-900">
                      {poi.rating.toFixed(1)}
                      {poi.rating_count && (
                        <span className="text-gray-500 ml-1">({poi.rating_count} avaliações)</span>
                      )}
                    </dd>
                  </div>
                )}
              </dl>
            </div>

            {/* Contact Info */}
            {(poi.phone || poi.website || poi.opening_hours) && (
              <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
                <h2 className="font-semibold text-gray-900 mb-3">Contato</h2>

                <dl className="space-y-2">
                  {poi.phone && (
                    <div className="flex items-center gap-2">
                      <Phone className="h-4 w-4 text-gray-400" />
                      <a
                        href={`tel:${poi.phone}`}
                        className="text-sm text-blue-600 hover:text-blue-700"
                      >
                        {poi.phone}
                      </a>
                    </div>
                  )}
                  {poi.website && (
                    <div className="flex items-center gap-2">
                      <Globe className="h-4 w-4 text-gray-400" />
                      <a
                        href={poi.website}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-sm text-blue-600 hover:text-blue-700 flex items-center gap-1"
                      >
                        {new URL(poi.website).hostname}
                        <ExternalLink className="h-3 w-3" />
                      </a>
                    </div>
                  )}
                  {poi.opening_hours && (
                    <div className="flex items-center gap-2">
                      <Clock className="h-4 w-4 text-gray-400" />
                      <span className="text-sm text-gray-900">{poi.opening_hours}</span>
                    </div>
                  )}
                </dl>

                {poi.google_maps_uri && (
                  <div className="mt-3 pt-3 border-t border-gray-200">
                    <a
                      href={poi.google_maps_uri}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-sm text-blue-600 hover:text-blue-700 flex items-center gap-1"
                    >
                      Ver no Google Maps
                      <ExternalLink className="h-3 w-3" />
                    </a>
                  </div>
                )}
              </div>
            )}

            {/* OSM Tags */}
            {poi.osm_tags && Object.keys(poi.osm_tags).length > 0 && (
              <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
                <h2 className="font-semibold text-gray-900 mb-3 flex items-center gap-2">
                  <Tag className="h-4 w-4 text-blue-600" />
                  Tags OSM
                </h2>

                <div className="max-h-64 overflow-y-auto">
                  <table className="w-full text-sm">
                    <tbody className="divide-y divide-gray-100">
                      {Object.entries(poi.osm_tags)
                        .sort(([a], [b]) => a.localeCompare(b))
                        .map(([key, value]) => (
                          <tr key={key}>
                            <td className="py-1 pr-2 text-gray-500 font-mono text-xs">
                              {key}
                            </td>
                            <td className="py-1 text-gray-900 font-mono text-xs break-all">
                              {String(value)}
                            </td>
                          </tr>
                        ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {/* Technical Info */}
            <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
              <h2 className="font-semibold text-gray-900 mb-3">Informações Técnicas</h2>

              <dl className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <dt className="text-gray-500">ID</dt>
                  <dd className="text-gray-900 font-mono text-xs">{poi.id}</dd>
                </div>
                {poi.osm_id && (
                  <div className="flex justify-between items-center">
                    <dt className="text-gray-500">OSM ID</dt>
                    <dd className="text-gray-900 font-mono text-xs flex items-center gap-2">
                      {poi.osm_id}
                      {getOsmEditUrl(poi.osm_id) && (
                        <a
                          href={getOsmEditUrl(poi.osm_id)!}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="inline-flex items-center gap-1 px-2 py-1 text-xs bg-blue-100 text-blue-700 rounded hover:bg-blue-200 transition-colors"
                          title="Editar este POI no OpenStreetMap"
                        >
                          <Edit3 className="h-3 w-3" />
                          Editar no OSM
                        </a>
                      )}
                    </dd>
                  </div>
                )}
                {poi.here_id && (
                  <div className="flex justify-between">
                    <dt className="text-gray-500">HERE ID</dt>
                    <dd className="text-gray-900 font-mono text-xs">{poi.here_id}</dd>
                  </div>
                )}
                <div className="flex justify-between">
                  <dt className="text-gray-500">Referenciado</dt>
                  <dd className="text-gray-900">{poi.is_referenced ? "Sim" : "Não"}</dd>
                </div>
                {poi.enriched_by.length > 0 && (
                  <div className="flex justify-between">
                    <dt className="text-gray-500">Enriquecido por</dt>
                    <dd className="text-gray-900">{poi.enriched_by.join(", ")}</dd>
                  </div>
                )}
                <div className="flex justify-between">
                  <dt className="text-gray-500">Criado em</dt>
                  <dd className="text-gray-900">
                    {new Date(poi.created_at).toLocaleString("pt-BR")}
                  </dd>
                </div>
              </dl>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
