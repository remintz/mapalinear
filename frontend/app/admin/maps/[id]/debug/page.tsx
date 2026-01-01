'use client';

import { useSession } from 'next-auth/react';
import { useRouter, useParams } from 'next/navigation';
import { useEffect, useState, useCallback } from 'react';
import Link from 'next/link';
import dynamic from 'next/dynamic';
import {
  ArrowLeft,
  Loader2,
  AlertTriangle,
  MapPin,
  ArrowLeftRight,
  Route,
  Info,
  ChevronRight,
  ChevronLeft,
} from 'lucide-react';
import { POIDebugData, POIDebugListResponse } from '@/lib/types';
import { apiClient } from '@/lib/api';

// Dynamically import the map component to avoid SSR issues with Leaflet
const POIDebugMap = dynamic(() => import('@/components/debug/POIDebugMap'), {
  ssr: false,
  loading: () => (
    <div className="h-[400px] flex items-center justify-center bg-gray-100 rounded-lg">
      <Loader2 className="w-6 h-6 animate-spin text-blue-600" />
    </div>
  ),
});

export default function POIDebugPage() {
  const { data: session, status } = useSession();
  const router = useRouter();
  const params = useParams();
  const mapId = params.id as string;

  const [debugData, setDebugData] = useState<POIDebugListResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedPOI, setSelectedPOI] = useState<POIDebugData | null>(null);

  const fetchDebugData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);

      const data = await apiClient.getPOIDebugData(mapId);
      setDebugData(data);

      // Select first POI if available
      if (data.pois.length > 0) {
        setSelectedPOI(data.pois[0]);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Erro desconhecido');
    } finally {
      setLoading(false);
    }
  }, [mapId]);

  useEffect(() => {
    if (status === 'loading') return;

    if (!session?.user?.isAdmin) {
      router.push('/');
      return;
    }

    fetchDebugData();
  }, [session, status, router, fetchDebugData]);

  const getSideBadge = (side: string) => {
    switch (side) {
      case 'left':
        return (
          <span className="px-2 py-0.5 text-xs font-medium rounded-full bg-blue-100 text-blue-700">
            ESQ
          </span>
        );
      case 'right':
        return (
          <span className="px-2 py-0.5 text-xs font-medium rounded-full bg-green-100 text-green-700">
            DIR
          </span>
        );
      default:
        return (
          <span className="px-2 py-0.5 text-xs font-medium rounded-full bg-gray-100 text-gray-700">
            CENTRO
          </span>
        );
    }
  };

  const getDetourBadge = (requiresDetour: boolean) => {
    if (!requiresDetour) return null;
    return (
      <span className="px-2 py-0.5 text-xs font-medium rounded-full bg-amber-100 text-amber-700">
        DESVIO
      </span>
    );
  };

  if (status === 'loading' || loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="flex items-center gap-3">
          <Loader2 className="w-6 h-6 animate-spin text-blue-600" />
          <span className="text-gray-600">Carregando dados de debug...</span>
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
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <Link
            href={`/admin/maps/${mapId}`}
            className="inline-flex items-center gap-2 text-gray-600 hover:text-gray-900 mb-4"
          >
            <ArrowLeft className="w-4 h-4" />
            Voltar para Detalhes
          </Link>
          <div className="p-6 bg-red-50 border border-red-200 rounded-lg text-red-700">
            {error}
          </div>
        </div>
      </div>
    );
  }

  if (!debugData) {
    return null;
  }

  return (
    <div className="min-h-screen bg-gray-50 py-8">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Header */}
        <div className="mb-6">
          <Link
            href={`/admin/maps/${mapId}`}
            className="inline-flex items-center gap-2 text-gray-600 hover:text-gray-900 mb-4"
          >
            <ArrowLeft className="w-4 h-4" />
            Voltar para Detalhes
          </Link>

          <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-3">
            <MapPin className="w-7 h-7 text-blue-600" />
            Debug de POIs
          </h1>

          {!debugData.has_debug_data && (
            <div className="mt-4 p-4 bg-amber-50 border border-amber-200 rounded-lg flex items-start gap-3">
              <AlertTriangle className="w-5 h-5 text-amber-600 flex-shrink-0 mt-0.5" />
              <div>
                <p className="text-amber-800 font-medium">Dados Parciais</p>
                <p className="text-amber-700 text-sm">
                  Este mapa foi criado antes do sistema de debug. Apenas informacoes basicas estao disponiveis.
                  Recalcule o mapa para obter dados completos de debug.
                </p>
              </div>
            </div>
          )}
        </div>

        {/* Summary Cards */}
        <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mb-6">
          <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
            <div className="text-2xl font-bold text-gray-900">{debugData.summary.total}</div>
            <div className="text-sm text-gray-500">Total POIs</div>
          </div>
          <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
            <div className="text-2xl font-bold text-blue-600">{debugData.summary.left_count}</div>
            <div className="text-sm text-gray-500">Esquerda</div>
          </div>
          <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
            <div className="text-2xl font-bold text-green-600">{debugData.summary.right_count}</div>
            <div className="text-sm text-gray-500">Direita</div>
          </div>
          <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
            <div className="text-2xl font-bold text-gray-600">{debugData.summary.center_count}</div>
            <div className="text-sm text-gray-500">Centro</div>
          </div>
          <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
            <div className="text-2xl font-bold text-amber-600">{debugData.summary.detour_count}</div>
            <div className="text-sm text-gray-500">Com Desvio</div>
          </div>
        </div>

        {/* Main Content */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* POI List */}
          <div className="lg:col-span-1 bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
            <div className="px-4 py-3 bg-gray-50 border-b border-gray-200">
              <h2 className="font-semibold text-gray-900">Lista de POIs</h2>
            </div>
            <div className="max-h-[600px] overflow-y-auto">
              {debugData.pois.length === 0 ? (
                <div className="p-4 text-gray-500 text-center">
                  Nenhum POI encontrado
                </div>
              ) : (
                <ul className="divide-y divide-gray-200">
                  {debugData.pois.map((poi) => (
                    <li key={poi.id}>
                      <button
                        onClick={() => setSelectedPOI(poi)}
                        className={`w-full px-4 py-3 text-left hover:bg-gray-50 transition-colors flex items-center gap-3 ${
                          selectedPOI?.id === poi.id ? 'bg-blue-50 border-l-4 border-blue-600' : ''
                        }`}
                      >
                        <div className="flex-1 min-w-0">
                          <div className="font-medium text-gray-900 truncate">
                            {poi.poi_name}
                          </div>
                          <div className="text-sm text-gray-500 flex items-center gap-2 mt-1">
                            <span className="capitalize">{poi.poi_type.replace(/_/g, ' ')}</span>
                            <span className="text-gray-300">|</span>
                            <span>{poi.distance_from_road_m.toFixed(0)}m</span>
                          </div>
                        </div>
                        <div className="flex items-center gap-2 flex-shrink-0">
                          {getSideBadge(poi.final_side)}
                          {getDetourBadge(poi.requires_detour)}
                          <ChevronRight className="w-4 h-4 text-gray-400" />
                        </div>
                      </button>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </div>

          {/* POI Details */}
          <div className="lg:col-span-2 space-y-6">
            {selectedPOI ? (
              <>
                {/* Map */}
                <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
                  <h3 className="font-semibold text-gray-900 mb-4 flex items-center gap-2">
                    <Route className="w-5 h-5 text-blue-600" />
                    Visualizacao no Mapa
                  </h3>
                  <POIDebugMap debugData={selectedPOI} />
                  <div className="mt-3 flex items-center gap-4 text-xs text-gray-500">
                    <span className="flex items-center gap-1">
                      <span className="w-4 h-1 bg-blue-500 rounded"></span>
                      Rota Principal
                    </span>
                    <span className="flex items-center gap-1">
                      <span className="w-4 h-1 bg-amber-500 rounded border-dashed"></span>
                      Rota de Acesso
                    </span>
                    <span className="flex items-center gap-1">
                      <span className="w-4 h-4 rounded-full bg-amber-500 text-white text-[10px] flex items-center justify-center">J</span>
                      Juncao
                    </span>
                    <span className="flex items-center gap-1">
                      <span className="w-4 h-4 rounded-full bg-red-500 text-white text-[10px] flex items-center justify-center">P</span>
                      POI
                    </span>
                  </div>
                </div>

                {/* POI Info */}
                <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
                  <h3 className="font-semibold text-gray-900 mb-4 flex items-center gap-2">
                    <Info className="w-5 h-5 text-blue-600" />
                    Informacoes do POI
                  </h3>
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                    <div>
                      <div className="text-sm text-gray-500">Nome</div>
                      <div className="font-medium text-gray-900">{selectedPOI.poi_name}</div>
                    </div>
                    <div>
                      <div className="text-sm text-gray-500">Tipo</div>
                      <div className="font-medium text-gray-900 capitalize">
                        {selectedPOI.poi_type.replace(/_/g, ' ')}
                      </div>
                    </div>
                    <div>
                      <div className="text-sm text-gray-500">Lado Final</div>
                      <div className="font-medium">
                        <span className={
                          selectedPOI.final_side === 'left' ? 'text-blue-600' :
                          selectedPOI.final_side === 'right' ? 'text-green-600' : 'text-gray-600'
                        }>
                          {selectedPOI.final_side === 'left' ? 'ESQUERDA' :
                           selectedPOI.final_side === 'right' ? 'DIREITA' : 'CENTRO'}
                        </span>
                      </div>
                    </div>
                    <div>
                      <div className="text-sm text-gray-500">Requer Desvio</div>
                      <div className="font-medium">
                        <span className={selectedPOI.requires_detour ? 'text-amber-600' : 'text-gray-600'}>
                          {selectedPOI.requires_detour ? 'Sim' : 'Nao'}
                        </span>
                      </div>
                    </div>
                    <div>
                      <div className="text-sm text-gray-500">Distancia da Rota</div>
                      <div className="font-medium text-gray-900">
                        {selectedPOI.distance_from_road_m.toFixed(1)} m
                      </div>
                    </div>
                    <div>
                      <div className="text-sm text-gray-500">Coordenadas POI</div>
                      <div className="font-medium text-gray-900 text-sm">
                        {selectedPOI.poi_lat.toFixed(6)}, {selectedPOI.poi_lon.toFixed(6)}
                      </div>
                    </div>
                    {selectedPOI.junction_lat && selectedPOI.junction_lon && (
                      <>
                        <div>
                          <div className="text-sm text-gray-500">Dist. Juncao (origem)</div>
                          <div className="font-medium text-gray-900">
                            {selectedPOI.junction_distance_km?.toFixed(2)} km
                          </div>
                        </div>
                        <div>
                          <div className="text-sm text-gray-500">Coordenadas Juncao</div>
                          <div className="font-medium text-gray-900 text-sm">
                            {selectedPOI.junction_lat.toFixed(6)}, {selectedPOI.junction_lon.toFixed(6)}
                          </div>
                        </div>
                      </>
                    )}
                    {selectedPOI.access_route_distance_km && (
                      <div>
                        <div className="text-sm text-gray-500">Distancia Rota Acesso</div>
                        <div className="font-medium text-gray-900">
                          {selectedPOI.access_route_distance_km.toFixed(2)} km
                        </div>
                      </div>
                    )}
                  </div>
                </div>

                {/* Side Calculation Details */}
                {selectedPOI.side_calculation && (
                  <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
                    <h3 className="font-semibold text-gray-900 mb-4 flex items-center gap-2">
                      <ArrowLeftRight className="w-5 h-5 text-blue-600" />
                      Calculo do Lado (Cross Product)
                      {selectedPOI.side_calculation.method === 'access_route_direction' && (
                        <span className="text-xs bg-green-100 text-green-700 px-2 py-1 rounded">
                          via Rota de Acesso
                        </span>
                      )}
                    </h3>
                    <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                      <div>
                        <div className="text-sm text-gray-500">Vetor da Rota</div>
                        <div className="font-mono text-sm text-gray-900">
                          dx: {selectedPOI.side_calculation.road_vector.dx.toFixed(6)}<br />
                          dy: {selectedPOI.side_calculation.road_vector.dy.toFixed(6)}
                        </div>
                      </div>
                      <div>
                        <div className="text-sm text-gray-500">
                          {selectedPOI.side_calculation.access_vector ? 'Vetor de Acesso' : 'Vetor do POI'}
                        </div>
                        <div className="font-mono text-sm text-gray-900">
                          {selectedPOI.side_calculation.access_vector ? (
                            <>
                              dx: {selectedPOI.side_calculation.access_vector.dx.toFixed(6)}<br />
                              dy: {selectedPOI.side_calculation.access_vector.dy.toFixed(6)}
                            </>
                          ) : selectedPOI.side_calculation.poi_vector ? (
                            <>
                              dx: {selectedPOI.side_calculation.poi_vector.dx.toFixed(6)}<br />
                              dy: {selectedPOI.side_calculation.poi_vector.dy.toFixed(6)}
                            </>
                          ) : (
                            <span className="text-gray-400">N/A</span>
                          )}
                        </div>
                      </div>
                      <div>
                        <div className="text-sm text-gray-500">Cross Product</div>
                        <div className="font-mono text-sm font-medium">
                          <span className={selectedPOI.side_calculation.cross_product > 0 ? 'text-blue-600' : 'text-green-600'}>
                            {selectedPOI.side_calculation.cross_product.toFixed(10)}
                          </span>
                        </div>
                        <div className="text-xs text-gray-500 mt-1">
                          {selectedPOI.side_calculation.cross_product > 0 ? '> 0 = Esquerda' : '< 0 = Direita'}
                        </div>
                      </div>
                      <div>
                        <div className="text-sm text-gray-500">Inicio do Segmento</div>
                        <div className="font-mono text-sm text-gray-900">
                          {selectedPOI.side_calculation.segment_start.lat.toFixed(6)}, {selectedPOI.side_calculation.segment_start.lon.toFixed(6)}
                        </div>
                      </div>
                      <div>
                        <div className="text-sm text-gray-500">Fim do Segmento</div>
                        <div className="font-mono text-sm text-gray-900">
                          {selectedPOI.side_calculation.segment_end.lat.toFixed(6)}, {selectedPOI.side_calculation.segment_end.lon.toFixed(6)}
                        </div>
                      </div>
                      <div>
                        <div className="text-sm text-gray-500">Lado Calculado</div>
                        <div className="font-medium">
                          <span className={
                            selectedPOI.side_calculation.resulting_side === 'left' ? 'text-blue-600' : 'text-green-600'
                          }>
                            {selectedPOI.side_calculation.resulting_side === 'left' ? 'ESQUERDA' : 'DIREITA'}
                          </span>
                        </div>
                      </div>
                    </div>
                  </div>
                )}

                {/* Junction Calculation */}
                {selectedPOI.junction_calculation && (
                  <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
                    <h3 className="font-semibold text-gray-900 mb-4 flex items-center gap-2">
                      <Route className="w-5 h-5 text-amber-600" />
                      Calculo da Juncao
                      {selectedPOI.junction_calculation.method && (
                        <span className="text-xs bg-amber-100 text-amber-700 px-2 py-1 rounded">
                          {selectedPOI.junction_calculation.method}
                        </span>
                      )}
                    </h3>
                    <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                      {selectedPOI.junction_calculation.exit_point_index != null && (
                        <div>
                          <div className="text-sm text-gray-500">Ponto de Saida</div>
                          <div className="font-medium text-gray-900">
                            {selectedPOI.junction_calculation.exit_point_index}
                            {selectedPOI.junction_calculation.total_access_points && (
                              <span className="text-gray-500 text-sm">
                                {' / '}{selectedPOI.junction_calculation.total_access_points} pontos
                              </span>
                            )}
                          </div>
                        </div>
                      )}
                      {selectedPOI.junction_calculation.junction_distance_km != null && (
                        <div>
                          <div className="text-sm text-gray-500">Dist. Juncao (origem)</div>
                          <div className="font-medium text-gray-900">
                            {selectedPOI.junction_calculation.junction_distance_km.toFixed(2)} km
                          </div>
                        </div>
                      )}
                      {selectedPOI.junction_calculation.distance_along_access_to_crossing_km != null && (
                        <div>
                          <div className="text-sm text-gray-500">Dist. ao longo do acesso</div>
                          <div className="font-medium text-gray-900">
                            {selectedPOI.junction_calculation.distance_along_access_to_crossing_km.toFixed(3)} km
                          </div>
                        </div>
                      )}
                      {selectedPOI.junction_calculation.access_route_total_km != null && (
                        <div>
                          <div className="text-sm text-gray-500">Rota de Acesso Total</div>
                          <div className="font-medium text-gray-900">
                            {selectedPOI.junction_calculation.access_route_total_km.toFixed(2)} km
                          </div>
                        </div>
                      )}
                      {selectedPOI.junction_calculation.intersection_distance_m != null && (
                        <div>
                          <div className="text-sm text-gray-500">Dist. Intersecao</div>
                          <div className="font-medium text-gray-900">
                            {selectedPOI.junction_calculation.intersection_distance_m.toFixed(1)} m
                          </div>
                        </div>
                      )}
                      {selectedPOI.junction_calculation.crossing_point_on_access && (
                        <div>
                          <div className="text-sm text-gray-500">Ponto Cruzamento (acesso)</div>
                          <div className="font-mono text-sm text-gray-900">
                            {selectedPOI.junction_calculation.crossing_point_on_access.lat.toFixed(6)}, {selectedPOI.junction_calculation.crossing_point_on_access.lon.toFixed(6)}
                          </div>
                        </div>
                      )}
                      {selectedPOI.junction_calculation.corresponding_point_on_main && (
                        <div>
                          <div className="text-sm text-gray-500">Ponto Correspondente (principal)</div>
                          <div className="font-mono text-sm text-gray-900">
                            {selectedPOI.junction_calculation.corresponding_point_on_main.lat.toFixed(6)}, {selectedPOI.junction_calculation.corresponding_point_on_main.lon.toFixed(6)}
                          </div>
                        </div>
                      )}
                    </div>
                  </div>
                )}

                {/* Lookback Data */}
                {selectedPOI.lookback_data && (
                  <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
                    <h3 className="font-semibold text-gray-900 mb-4 flex items-center gap-2">
                      <ChevronLeft className="w-5 h-5 text-blue-600" />
                      Dados de Lookback
                      {selectedPOI.lookback_data.lookback_method && (
                        <span className={`px-2 py-0.5 rounded text-xs font-medium ${
                          selectedPOI.lookback_data.lookback_method === 'search_point'
                            ? 'bg-green-100 text-green-700'
                            : selectedPOI.lookback_data.lookback_method === 'search_point_first'
                            ? 'bg-yellow-100 text-yellow-700'
                            : 'bg-gray-100 text-gray-700'
                        }`}>
                          {selectedPOI.lookback_data.lookback_method === 'search_point'
                            ? 'via Search Point'
                            : selectedPOI.lookback_data.lookback_method === 'search_point_first'
                            ? 'Search Point (primeiro)'
                            : 'Interpolado'}
                        </span>
                      )}
                    </h3>
                    <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                      <div>
                        <div className="text-sm text-gray-500">Distancia POI-Rota</div>
                        <div className="font-medium text-gray-900">
                          {selectedPOI.lookback_data.poi_distance_from_road_m.toFixed(1)} m
                        </div>
                      </div>
                      {selectedPOI.lookback_data.current_search_point_index != null && (
                        <div>
                          <div className="text-sm text-gray-500">Indice Search Point</div>
                          <div className="font-medium text-gray-900">
                            {selectedPOI.lookback_data.current_search_point_index}
                            {selectedPOI.lookback_data.lookback_index != null && (
                              <span className="text-gray-500 text-xs ml-1">
                                (lookback: {selectedPOI.lookback_data.lookback_index})
                              </span>
                            )}
                          </div>
                        </div>
                      )}
                      {selectedPOI.lookback_data.lookback_km != null && (
                        <div>
                          <div className="text-sm text-gray-500">Lookback Dist.</div>
                          <div className="font-medium text-gray-900">
                            {selectedPOI.lookback_data.lookback_km.toFixed(2)} km
                          </div>
                        </div>
                      )}
                      {/* Legacy field for old data */}
                      {selectedPOI.lookback_data.lookback_milestone_name && (
                        <div>
                          <div className="text-sm text-gray-500">Milestone Usado (legado)</div>
                          <div className="font-medium text-gray-900">
                            {selectedPOI.lookback_data.lookback_milestone_name}
                          </div>
                        </div>
                      )}
                      <div>
                        <div className="text-sm text-gray-500">Dist. Ponto Lookback</div>
                        <div className="font-medium text-gray-900">
                          {selectedPOI.lookback_data.lookback_distance_km.toFixed(2)} km
                        </div>
                      </div>
                      <div>
                        <div className="text-sm text-gray-500">Ponto de Lookback</div>
                        <div className="font-mono text-sm text-gray-900">
                          {selectedPOI.lookback_data.lookback_point.lat.toFixed(6)}, {selectedPOI.lookback_data.lookback_point.lon.toFixed(6)}
                        </div>
                      </div>
                      <div>
                        <div className="text-sm text-gray-500">Ponto de Busca</div>
                        <div className="font-mono text-sm text-gray-900">
                          {selectedPOI.lookback_data.search_point.lat.toFixed(6)}, {selectedPOI.lookback_data.search_point.lon.toFixed(6)}
                        </div>
                      </div>
                      <div>
                        <div className="text-sm text-gray-500">Dist. Ponto Busca</div>
                        <div className="font-medium text-gray-900">
                          {selectedPOI.lookback_data.search_point_distance_km.toFixed(2)} km
                        </div>
                      </div>
                      {selectedPOI.lookback_data.lookback_count_setting != null && (
                        <div>
                          <div className="text-sm text-gray-500">Config. Lookback</div>
                          <div className="font-medium text-gray-900">
                            {selectedPOI.lookback_data.lookback_count_setting} pontos
                          </div>
                        </div>
                      )}
                      {/* Legacy field for old data */}
                      {selectedPOI.lookback_data.milestones_available_before != null && (
                        <div>
                          <div className="text-sm text-gray-500">Milestones Disponiveis (legado)</div>
                          <div className="font-medium text-gray-900">
                            {selectedPOI.lookback_data.milestones_available_before}
                            {selectedPOI.lookback_data.lookback_milestones_count_setting && (
                              <span className="text-gray-500 text-xs ml-1">
                                (config: {selectedPOI.lookback_data.lookback_milestones_count_setting})
                              </span>
                            )}
                          </div>
                        </div>
                      )}
                    </div>
                  </div>
                )}

                {/* Recalculation History */}
                {selectedPOI.recalculation_history && selectedPOI.recalculation_history.length > 0 && (
                  <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
                    <h3 className="font-semibold text-gray-900 mb-4">
                      Historico de Recalculos ({selectedPOI.recalculation_history.length} tentativas)
                    </h3>
                    <div className="overflow-x-auto">
                      <table className="min-w-full text-sm">
                        <thead>
                          <tr className="border-b border-gray-200">
                            <th className="px-3 py-2 text-left text-gray-500 font-medium">#</th>
                            <th className="px-3 py-2 text-left text-gray-500 font-medium">Ponto Busca</th>
                            <th className="px-3 py-2 text-left text-gray-500 font-medium">Juncao</th>
                            <th className="px-3 py-2 text-left text-gray-500 font-medium">Dist. Juncao</th>
                            <th className="px-3 py-2 text-left text-gray-500 font-medium">Dist. Acesso</th>
                            <th className="px-3 py-2 text-left text-gray-500 font-medium">Melhorou?</th>
                            <th className="px-3 py-2 text-left text-gray-500 font-medium">Motivo</th>
                          </tr>
                        </thead>
                        <tbody>
                          {selectedPOI.recalculation_history.map((attempt) => (
                            <tr key={attempt.attempt} className="border-b border-gray-100">
                              <td className="px-3 py-2 font-medium">{attempt.attempt}</td>
                              <td className="px-3 py-2 font-mono text-xs">
                                {attempt.search_point.lat.toFixed(4)}, {attempt.search_point.lon.toFixed(4)}
                              </td>
                              <td className="px-3 py-2">
                                <span className={attempt.junction_found ? 'text-green-600' : 'text-red-600'}>
                                  {attempt.junction_found ? 'Sim' : 'Nao'}
                                </span>
                              </td>
                              <td className="px-3 py-2">
                                {attempt.junction_distance_km?.toFixed(2) || '-'} km
                              </td>
                              <td className="px-3 py-2">
                                {attempt.access_route_distance_km?.toFixed(2) || '-'} km
                              </td>
                              <td className="px-3 py-2">
                                <span className={attempt.improvement ? 'text-green-600' : 'text-gray-400'}>
                                  {attempt.improvement ? 'Sim' : 'Nao'}
                                </span>
                              </td>
                              <td className="px-3 py-2 text-gray-500 text-xs">
                                {attempt.reason || '-'}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                )}
              </>
            ) : (
              <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-8 text-center text-gray-500">
                Selecione um POI da lista para ver os detalhes de debug
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
