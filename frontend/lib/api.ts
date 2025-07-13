import axios, { AxiosInstance } from 'axios';
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
    this.client.interceptors.request.use((config) => {
      // Add request ID for debugging
      config.headers['X-Request-ID'] = Math.random().toString(36).substr(2, 9);
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
}

export const apiClient = new APIClient();