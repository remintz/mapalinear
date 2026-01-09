"use client";

import { useSession } from "next-auth/react";
import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useState, useCallback, Suspense } from "react";
import Link from "next/link";
import {
  ArrowLeft,
  MapPin,
  Filter,
  RefreshCw,
  ChevronLeft,
  ChevronRight,
  AlertTriangle,
  CheckCircle,
  Loader2,
  Search,
  X,
} from "lucide-react";
import { toast } from "sonner";
import { apiClient } from "@/lib/api";
import { AdminPOI, AdminPOIFilters, AdminPOIStats } from "@/lib/types";

const POI_TYPE_LABELS: Record<string, string> = {
  // Main categories
  gas_station: "Posto de Combustível",
  fuel: "Combustível",
  restaurant: "Restaurante",
  food: "Alimentação",
  fast_food: "Fast Food",
  cafe: "Café",
  hotel: "Hotel",
  lodging: "Hospedagem",
  camping: "Camping",
  hospital: "Hospital",
  pharmacy: "Farmácia",
  bank: "Banco",
  atm: "Caixa Eletrônico",
  shopping: "Shopping",
  supermarket: "Supermercado",
  tourist_attraction: "Atração Turística",
  rest_area: "Área de Descanso",
  parking: "Estacionamento",
  toll_booth: "Pedágio",
  police: "Polícia",
  mechanic: "Mecânica",
  other: "Desconhecido",
  // Place types
  city: "Cidade",
  town: "Cidade Pequena",
  village: "Vila",
};

const POI_TYPE_ICONS: Record<string, string> = {
  // Main categories
  gas_station: "⛽",
  fuel: "⛽",
  restaurant: "🍽️",
  food: "🍴",
  fast_food: "🍔",
  cafe: "☕",
  hotel: "🏨",
  lodging: "🛏️",
  camping: "⛺",
  hospital: "🏥",
  pharmacy: "💊",
  bank: "🏦",
  atm: "💳",
  shopping: "🛒",
  supermarket: "🛒",
  tourist_attraction: "🏛️",
  rest_area: "🅿️",
  parking: "🅿️",
  toll_booth: "🚧",
  police: "👮",
  mechanic: "🔧",
  services: "🏢",
  other: "📍",
  // Place types
  city: "🏙️",
  town: "🏘️",
  village: "🏡",
};

function AdminPOIsPageContent() {
  const { data: session, status } = useSession();
  const router = useRouter();
  const searchParams = useSearchParams();

  // Data state
  const [pois, setPois] = useState<AdminPOI[]>([]);
  const [filters, setFilters] = useState<AdminPOIFilters | null>(null);
  const [stats, setStats] = useState<AdminPOIStats | null>(null);
  const [total, setTotal] = useState(0);

  // Read filter state from URL params
  const nameFilter = searchParams.get("name") || "";
  const cityFilter = searchParams.get("city") || "";
  const typeFilter = searchParams.get("type") || "";
  const lowQualityOnly = searchParams.get("low_quality") === "true";
  const page = parseInt(searchParams.get("page") || "1", 10);
  const [limit] = useState(50);

  // Local state for search input (debounced)
  const [nameInput, setNameInput] = useState(nameFilter);

  // Loading state
  const [loading, setLoading] = useState(true);
  const [loadingFilters, setLoadingFilters] = useState(true);
  const [recalculating, setRecalculating] = useState(false);
  const [updating, setUpdating] = useState(false);

  // Selection state
  const [selectedPois, setSelectedPois] = useState<Set<string>>(new Set());

  // Helper to update URL params
  const updateUrlParams = useCallback(
    (updates: Record<string, string | null>) => {
      const params = new URLSearchParams(searchParams.toString());

      Object.entries(updates).forEach(([key, value]) => {
        if (value === null || value === "" || value === "false" || value === "1") {
          // Remove param if it's empty, false, or page 1 (defaults)
          if (key === "page" && value === "1") {
            params.delete(key);
          } else if (value === null || value === "" || value === "false") {
            params.delete(key);
          } else {
            params.set(key, value);
          }
        } else {
          params.set(key, value);
        }
      });

      const queryString = params.toString();
      router.push(queryString ? `?${queryString}` : "/admin/pois", { scroll: false });
    },
    [searchParams, router]
  );

  // Filter setters that update URL
  const setNameFilter = (value: string) => {
    updateUrlParams({ name: value, page: "1" });
  };

  const setCityFilter = (value: string) => {
    updateUrlParams({ city: value, page: "1" });
  };

  const setTypeFilter = (value: string) => {
    updateUrlParams({ type: value, page: "1" });
  };

  const setLowQualityOnly = (value: boolean) => {
    updateUrlParams({ low_quality: value ? "true" : null, page: "1" });
  };

  const setPage = (newPage: number) => {
    updateUrlParams({ page: newPage === 1 ? null : String(newPage) });
  };

  // Sync nameInput with URL when navigating back
  useEffect(() => {
    setNameInput(nameFilter);
  }, [nameFilter]);

  // Debounce name search
  useEffect(() => {
    const timer = setTimeout(() => {
      if (nameInput !== nameFilter) {
        setNameFilter(nameInput);
      }
    }, 300);
    return () => clearTimeout(timer);
  }, [nameInput, nameFilter]);

  // Load filters and stats
  const loadFiltersAndStats = useCallback(async () => {
    try {
      setLoadingFilters(true);
      const [filtersData, statsData] = await Promise.all([
        apiClient.getAdminPOIFilters(),
        apiClient.getAdminPOIStats(),
      ]);
      setFilters(filtersData);
      setStats(statsData);
    } catch (error) {
      console.error("Error loading filters:", error);
      toast.error("Erro ao carregar filtros");
    } finally {
      setLoadingFilters(false);
    }
  }, []);

  // Load POIs
  const loadPOIs = useCallback(async () => {
    try {
      setLoading(true);
      const data = await apiClient.getAdminPOIs({
        name: nameFilter || undefined,
        city: cityFilter || undefined,
        poi_type: typeFilter || undefined,
        low_quality_only: lowQualityOnly,
        page,
        limit,
      });
      setPois(data.pois);
      setTotal(data.total);
    } catch (error) {
      console.error("Error loading POIs:", error);
      toast.error("Erro ao carregar POIs");
    } finally {
      setLoading(false);
    }
  }, [nameFilter, cityFilter, typeFilter, lowQualityOnly, page, limit]);

  // Auth check
  useEffect(() => {
    if (status === "loading") return;
    if (!session?.user?.isAdmin) {
      router.push("/");
    }
  }, [session, status, router]);

  // Load data on mount
  useEffect(() => {
    if (session?.user?.isAdmin) {
      loadFiltersAndStats();
    }
  }, [session, loadFiltersAndStats]);

  // Load POIs when filters change
  useEffect(() => {
    if (session?.user?.isAdmin) {
      loadPOIs();
    }
  }, [session, loadPOIs]);

  const handleRecalculateQuality = async () => {
    if (!confirm("Recalcular qualidade de todos os POIs? Isso pode demorar alguns minutos.")) {
      return;
    }

    try {
      setRecalculating(true);
      const result = await apiClient.recalculatePOIQuality();
      toast.success(result.message);
      // Reload data
      await Promise.all([loadFiltersAndStats(), loadPOIs()]);
    } catch (error) {
      console.error("Error recalculating quality:", error);
      toast.error("Erro ao recalcular qualidade");
    } finally {
      setRecalculating(false);
    }
  };

  const clearFilters = () => {
    router.push("/admin/pois", { scroll: false });
  };

  // Selection handlers
  const handleSelectAll = (checked: boolean) => {
    if (checked) {
      setSelectedPois(new Set(pois.map((poi) => poi.id)));
    } else {
      setSelectedPois(new Set());
    }
  };

  const handleSelectPoi = (poiId: string, checked: boolean) => {
    const newSelection = new Set(selectedPois);
    if (checked) {
      newSelection.add(poiId);
    } else {
      newSelection.delete(poiId);
    }
    setSelectedPois(newSelection);
  };

  const isAllSelected = pois.length > 0 && pois.every((poi) => selectedPois.has(poi.id));
  const isSomeSelected = pois.some((poi) => selectedPois.has(poi.id));

  // Clear selection when POIs change (page change, filter change)
  useEffect(() => {
    setSelectedPois(new Set());
  }, [pois]);

  const handleUpdateSelected = async () => {
    if (selectedPois.size === 0) return;

    if (!confirm(`Atualizar informações de ${selectedPois.size} POI(s) selecionado(s)?`)) {
      return;
    }

    try {
      setUpdating(true);
      const result = await apiClient.refreshPOIs(Array.from(selectedPois));
      toast.success(result.message);
      setSelectedPois(new Set());
      // Reload data
      await loadPOIs();
    } catch (error) {
      console.error("Error updating POIs:", error);
      toast.error("Erro ao atualizar POIs");
    } finally {
      setUpdating(false);
    }
  };

  const totalPages = Math.ceil(total / limit);

  if (status === "loading" || !session?.user?.isAdmin) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="sticky top-0 z-20 bg-white border-b border-gray-200 shadow-sm">
        <div className="max-w-7xl mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <Link href="/admin" className="text-blue-600 hover:text-blue-700">
                <ArrowLeft className="h-5 w-5" />
              </Link>
              <div>
                <h1 className="text-xl font-bold text-gray-900 flex items-center gap-2">
                  <MapPin className="h-5 w-5 text-blue-600" />
                  Pontos de Interesse
                </h1>
                <p className="text-sm text-gray-600">
                  {stats && `${stats.total} POIs total, ${stats.low_quality} com problemas`}
                </p>
              </div>
            </div>
            <button
              onClick={handleRecalculateQuality}
              disabled={recalculating}
              className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
            >
              {recalculating ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <RefreshCw className="h-4 w-4" />
              )}
              Recalcular Qualidade
            </button>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 py-6">
        {/* Filters */}
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4 mb-6">
          <div className="flex items-center gap-2 mb-3">
            <Filter className="h-4 w-4 text-gray-500" />
            <span className="text-sm font-medium text-gray-700">Filtros</span>
            {(nameFilter || cityFilter || typeFilter || lowQualityOnly) && (
              <button
                onClick={clearFilters}
                className="ml-auto text-xs text-blue-600 hover:text-blue-700 flex items-center gap-1"
              >
                <X className="h-3 w-3" />
                Limpar filtros
              </button>
            )}
          </div>

          <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
            {/* Name search */}
            <div className="md:col-span-2">
              <label className="block text-xs text-gray-500 mb-1">Pesquisar por nome</label>
              <div className="relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
                <input
                  type="text"
                  value={nameInput}
                  onChange={(e) => setNameInput(e.target.value)}
                  placeholder="Digite o nome do POI..."
                  className="w-full pl-9 pr-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
                {nameInput && (
                  <button
                    onClick={() => setNameInput("")}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
                  >
                    <X className="h-4 w-4" />
                  </button>
                )}
              </div>
            </div>

            {/* City filter */}
            <div>
              <label className="block text-xs text-gray-500 mb-1">Cidade</label>
              <select
                value={cityFilter}
                onChange={(e) => setCityFilter(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                disabled={loadingFilters}
              >
                <option value="">Todas</option>
                <option value="__no_city__">Sem cidade</option>
                {filters?.cities.map((city) => (
                  <option key={city} value={city}>
                    {city}
                  </option>
                ))}
              </select>
            </div>

            {/* Type filter */}
            <div>
              <label className="block text-xs text-gray-500 mb-1">Tipo</label>
              <select
                value={typeFilter}
                onChange={(e) => setTypeFilter(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                disabled={loadingFilters}
              >
                <option value="">Todos</option>
                {filters?.types.map((type) => (
                  <option key={type} value={type}>
                    {POI_TYPE_ICONS[type] || "📍"} {POI_TYPE_LABELS[type] || type}
                  </option>
                ))}
              </select>
            </div>

            {/* Low quality only + Results count */}
            <div className="flex flex-col justify-end gap-2">
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={lowQualityOnly}
                  onChange={(e) => setLowQualityOnly(e.target.checked)}
                  className="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
                />
                <span className="text-sm text-gray-700">Baixa qualidade</span>
              </label>
              <span className="text-sm text-gray-500">
                {total} resultado{total !== 1 ? "s" : ""}
              </span>
            </div>
          </div>
        </div>

        {/* Selection Actions Bar */}
        {selectedPois.size > 0 && (
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-3 mb-4 flex items-center justify-between">
            <span className="text-sm text-blue-800">
              {selectedPois.size} POI{selectedPois.size !== 1 ? "s" : ""} selecionado{selectedPois.size !== 1 ? "s" : ""}
            </span>
            <div className="flex items-center gap-2">
              <button
                onClick={() => setSelectedPois(new Set())}
                className="text-sm text-blue-600 hover:text-blue-700"
              >
                Limpar seleção
              </button>
              <button
                onClick={handleUpdateSelected}
                disabled={updating}
                className="flex items-center gap-2 px-3 py-1.5 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700 disabled:opacity-50"
              >
                {updating ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <RefreshCw className="h-4 w-4" />
                )}
                Atualizar Selecionados
              </button>
            </div>
          </div>
        )}

        {/* POI Table */}
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
          {loading ? (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
            </div>
          ) : pois.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-12 text-gray-500">
              <Search className="h-12 w-12 mb-3 text-gray-300" />
              <p>Nenhum POI encontrado</p>
              {(nameFilter || cityFilter || typeFilter || lowQualityOnly) && (
                <button
                  onClick={clearFilters}
                  className="mt-2 text-sm text-blue-600 hover:text-blue-700"
                >
                  Limpar filtros
                </button>
              )}
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-gray-50 border-b border-gray-200">
                  <tr>
                    <th className="px-4 py-3 text-left">
                      <input
                        type="checkbox"
                        checked={isAllSelected}
                        ref={(el) => {
                          if (el) el.indeterminate = isSomeSelected && !isAllSelected;
                        }}
                        onChange={(e) => handleSelectAll(e.target.checked)}
                        className="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
                      />
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Nome
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Tipo
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Cidade
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Qualidade
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Ações
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200">
                  {pois.map((poi) => (
                    <tr key={poi.id} className={`hover:bg-gray-50 ${selectedPois.has(poi.id) ? "bg-blue-50" : ""}`}>
                      <td className="px-4 py-3">
                        <input
                          type="checkbox"
                          checked={selectedPois.has(poi.id)}
                          onChange={(e) => handleSelectPoi(poi.id, e.target.checked)}
                          className="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
                        />
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-2">
                          <span className="text-lg">{POI_TYPE_ICONS[poi.type] || "📍"}</span>
                          <div>
                            <div className="font-medium text-gray-900 text-sm">
                              {poi.name || "Sem nome"}
                            </div>
                            {poi.brand && (
                              <div className="text-xs text-gray-500">{poi.brand}</div>
                            )}
                          </div>
                        </div>
                      </td>
                      <td className="px-4 py-3 text-sm text-gray-600">
                        {POI_TYPE_LABELS[poi.type] || poi.type}
                      </td>
                      <td className="px-4 py-3 text-sm text-gray-600">
                        {poi.city || "-"}
                      </td>
                      <td className="px-4 py-3">
                        {poi.is_low_quality ? (
                          <div className="flex items-center gap-1">
                            <AlertTriangle className="h-4 w-4 text-amber-500" />
                            <span className="text-xs text-amber-600">
                              Falta {poi.missing_tags.length} tag{poi.missing_tags.length > 1 ? "s" : ""}
                            </span>
                          </div>
                        ) : (
                          <div className="flex items-center gap-1">
                            <CheckCircle className="h-4 w-4 text-green-500" />
                            <span className="text-xs text-green-600">OK</span>
                          </div>
                        )}
                      </td>
                      <td className="px-4 py-3">
                        <Link
                          href={`/admin/pois/${poi.id}`}
                          className="text-sm text-blue-600 hover:text-blue-700"
                        >
                          Detalhes
                        </Link>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="flex items-center justify-between px-4 py-3 border-t border-gray-200 bg-gray-50">
              <div className="text-sm text-gray-500">
                Mostrando {(page - 1) * limit + 1} - {Math.min(page * limit, total)} de {total}
              </div>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => setPage(Math.max(1, page - 1))}
                  disabled={page === 1}
                  className="p-2 text-gray-600 hover:text-gray-900 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <ChevronLeft className="h-5 w-5" />
                </button>
                <span className="text-sm text-gray-600">
                  Página {page} de {totalPages}
                </span>
                <button
                  onClick={() => setPage(Math.min(totalPages, page + 1))}
                  disabled={page === totalPages}
                  className="p-2 text-gray-600 hover:text-gray-900 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <ChevronRight className="h-5 w-5" />
                </button>
              </div>
            </div>
          )}
        </div>
      </main>
    </div>
  );
}

// Wrap in Suspense for useSearchParams
export default function AdminPOIsPage() {
  return (
    <Suspense
      fallback={
        <div className="min-h-screen flex items-center justify-center">
          <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
        </div>
      }
    >
      <AdminPOIsPageContent />
    </Suspense>
  );
}
