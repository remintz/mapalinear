import axios, { AxiosInstance } from 'axios';
import { getSession } from 'next-auth/react';
import { RouteSearchRequest, RouteSearchResponse, AsyncOperation, ExportRouteData } from './types';

class APIClient {
  private client: AxiosInstance;

  constructor() {
    this.client = axios.create({
      baseURL: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001/api',
      timeout: 180000, // 3 minutes for complex route searches
      headers: {
        'Content-Type': 'application/json',
      },
    });

    this.setupInterceptors();
  }

  private setupInterceptors() {
    this.client.interceptors.request.use(async (config) => {
      // Add request ID for debugging
      config.headers['X-Request-ID'] = Math.random().toString(36).substr(2, 9);

      // Add auth token if available
      try {
        const session = await getSession();
        if (session?.accessToken) {
          config.headers['Authorization'] = `Bearer ${session.accessToken}`;
        }
      } catch {
        // Ignore session errors - user might not be logged in
      }

      return config;
    });

    this.client.interceptors.response.use(
      (response) => response,
      (error) => {
        // Global error handling
        console.error('API Error:', {
          message: error.message,
          status: error.response?.status,
          data: error.response?.data,
        });
        
        // Transform error for better UX
        if (error.response?.status === 400) {
          throw new Error(error.response.data?.detail || 'Dados inválidos');
        }

        if (error.response?.status === 401) {
          // Redirect to login on auth error
          if (typeof window !== 'undefined') {
            window.location.href = '/login';
          }
          throw new Error('Sessão expirada. Faça login novamente.');
        }

        if (error.response?.status === 500) {
          throw new Error('Erro interno do servidor. Tente novamente.');
        }
        
        if (error.code === 'ECONNABORTED') {
          throw new Error('A busca está demorando mais que o esperado. Tente novamente com uma rota menor ou verifique sua conexão.');
        }
        
        throw error;
      }
    );
  }

  async searchRoute(params: RouteSearchRequest): Promise<RouteSearchResponse> {
    const { data } = await this.client.post<RouteSearchResponse>('/roads/linear-map', params);
    return data;
  }

  async startAsyncRouteSearch(params: RouteSearchRequest): Promise<{ operation_id: string }> {
    const { data } = await this.client.post<{ operation_id: string }>('/operations/linear-map', params);
    return data;
  }

  async getOperationStatus(operationId: string): Promise<AsyncOperation> {
    const { data } = await this.client.get<AsyncOperation>(`/operations/${operationId}`);
    return data;
  }

  async healthCheck(): Promise<{ status: string; timestamp: string }> {
    const { data } = await this.client.get('/health');
    return data;
  }

  // Export functions
  async exportRouteAsGeoJSON(routeData: ExportRouteData): Promise<Blob> {
    const response = await this.client.post('/export/geojson', routeData, {
      responseType: 'blob',
    });
    return response.data;
  }

  async exportRouteAsGPX(routeData: ExportRouteData): Promise<Blob> {
    const response = await this.client.post('/export/gpx', routeData, {
      responseType: 'blob',
    });
    return response.data;
  }

  async getWebVisualizationURLs(routeData: ExportRouteData): Promise<{
    umap_url: string;
    overpass_turbo_url: string;
    openrouteservice_url: string;
    osrm_map_url: string;
    instructions: Record<string, string>;
  }> {
    const { data } = await this.client.post('/export/web-urls', routeData);
    return data;
  }

  // Saved Maps functions
  async listMaps(): Promise<SavedMap[]> {
    const { data } = await this.client.get<SavedMap[]>('/maps');
    return data;
  }

  async getMap(mapId: string): Promise<RouteSearchResponse> {
    const { data } = await this.client.get<RouteSearchResponse>(`/maps/${mapId}`);
    return data;
  }

  async deleteMap(mapId: string): Promise<void> {
    await this.client.delete(`/maps/${mapId}`);
  }

  async regenerateMap(mapId: string): Promise<{ operation_id: string }> {
    const { data } = await this.client.post<{ operation_id: string }>(`/maps/${mapId}/regenerate`);
    return data;
  }

  async exportMapToPDF(mapId: string, types?: string): Promise<Blob> {
    const params = types ? `?types=${types}` : '';
    const response = await this.client.get(`/maps/${mapId}/pdf${params}`, {
      responseType: 'blob',
    });
    return response.data;
  }
}

// Types for saved maps
export interface SavedMap {
  id: string;
  name: string | null;
  origin: string;
  destination: string;
  total_length_km: number;
  creation_date: string;
  road_refs: string[];
  milestone_count: number;
}

export const apiClient = new APIClient();