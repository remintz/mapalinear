import axios, { AxiosInstance, InternalAxiosRequestConfig } from 'axios';
import { getSession } from 'next-auth/react';
import { RouteSearchRequest, RouteSearchResponse, AsyncOperation, ExportRouteData } from './types';

// Helper to wait for session with retry
async function getSessionWithRetry(maxRetries = 3, delayMs = 500): Promise<string | null> {
  for (let i = 0; i < maxRetries; i++) {
    try {
      const session = await getSession();
      if (session?.accessToken) {
        return session.accessToken;
      }
      // If no token yet, wait and retry
      if (i < maxRetries - 1) {
        await new Promise(resolve => setTimeout(resolve, delayMs));
      }
    } catch (error) {
      console.warn(`Session fetch attempt ${i + 1} failed:`, error);
      if (i < maxRetries - 1) {
        await new Promise(resolve => setTimeout(resolve, delayMs));
      }
    }
  }
  return null;
}

class APIClient {
  private client: AxiosInstance;
  private cachedToken: string | null = null;
  private tokenExpiry: number = 0;

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

  // Allow external setting of token (useful when session is already available)
  setAccessToken(token: string | null) {
    this.cachedToken = token;
    this.tokenExpiry = token ? Date.now() + 3600000 : 0; // 1 hour cache
  }

  private async getValidToken(): Promise<string | null> {
    // Check if we have a valid cached token
    if (this.cachedToken && Date.now() < this.tokenExpiry) {
      return this.cachedToken;
    }

    // Get fresh token with retry
    const token = await getSessionWithRetry();
    if (token) {
      this.cachedToken = token;
      this.tokenExpiry = Date.now() + 3600000; // 1 hour cache
    }
    return token;
  }

  private setupInterceptors() {
    this.client.interceptors.request.use(async (config: InternalAxiosRequestConfig) => {
      // Add request ID for debugging
      config.headers['X-Request-ID'] = Math.random().toString(36).substr(2, 9);

      // Add auth token if available
      const token = await this.getValidToken();
      if (token) {
        config.headers['Authorization'] = `Bearer ${token}`;
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
          // Clear cached token on auth error
          this.cachedToken = null;
          this.tokenExpiry = 0;

          // Redirect to login on auth error
          if (typeof window !== 'undefined') {
            window.location.href = '/login';
          }
          throw new Error('Sessão expirada. Faça login novamente.');
        }

        if (error.response?.status === 409) {
          // Handle duplicate/conflict errors
          // Backend returns: { status_code, message, error_type, details }
          const responseData = error.response.data;
          const details = responseData?.details;

          // Build user-friendly message
          let message = responseData?.message || 'Já existe um mapa com esta origem e destino.';
          if (details?.origin && details?.destination) {
            message += ` (${details.origin} → ${details.destination})`;
          }
          if (details?.hint) {
            message += `. ${details.hint}.`;
          }

          const err = new Error(message) as Error & { details: typeof details };
          err.details = details;
          throw err;
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

  /**
   * List maps in the current user's collection.
   */
  async listMaps(): Promise<SavedMap[]> {
    const { data } = await this.client.get<SavedMap[]>('/maps');
    return data;
  }

  /**
   * Get suggested maps for the create page.
   * Optionally sorted by proximity to user's location.
   */
  async getSuggestedMaps(options?: {
    limit?: number;
    lat?: number;
    lon?: number;
  }): Promise<SavedMap[]> {
    const params = new URLSearchParams();
    if (options?.limit !== undefined) params.append('limit', options.limit.toString());
    if (options?.lat !== undefined) params.append('lat', options.lat.toString());
    if (options?.lon !== undefined) params.append('lon', options.lon.toString());

    const queryString = params.toString();
    const url = queryString ? `/maps/suggested?${queryString}` : '/maps/suggested';
    const { data } = await this.client.get<SavedMap[]>(url);
    return data;
  }

  /**
   * List all available maps (for browsing/adopting).
   */
  async listAvailableMaps(options?: {
    skip?: number;
    limit?: number;
    origin?: string;
    destination?: string;
  }): Promise<SavedMap[]> {
    const params = new URLSearchParams();
    if (options?.skip !== undefined) params.append('skip', options.skip.toString());
    if (options?.limit !== undefined) params.append('limit', options.limit.toString());
    if (options?.origin) params.append('origin', options.origin);
    if (options?.destination) params.append('destination', options.destination);

    const queryString = params.toString();
    const url = queryString ? `/maps/available?${queryString}` : '/maps/available';
    const { data } = await this.client.get<SavedMap[]>(url);
    return data;
  }

  async getMap(mapId: string): Promise<RouteSearchResponse> {
    const { data } = await this.client.get<RouteSearchResponse>(`/maps/${mapId}`);
    return data;
  }

  /**
   * Add an existing map to the user's collection.
   */
  async adoptMap(mapId: string): Promise<{ message: string }> {
    const { data } = await this.client.post<{ message: string }>(`/maps/${mapId}/adopt`);
    return data;
  }

  /**
   * Remove map from collection (regular user) or permanently delete (admin).
   */
  async deleteMap(mapId: string): Promise<{ message: string }> {
    const { data } = await this.client.delete<{ message: string }>(`/maps/${mapId}`);
    return data;
  }

  /**
   * Permanently delete a map (admin only).
   */
  async permanentlyDeleteMap(mapId: string): Promise<{ message: string }> {
    const { data } = await this.client.delete<{ message: string }>(`/maps/${mapId}/permanent`);
    return data;
  }

  /**
   * Regenerate a map with fresh data (admin only).
   */
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

  // Municipalities functions
  async getMunicipalities(uf?: string): Promise<Municipality[]> {
    const params = uf ? `?uf=${uf}` : '';
    const { data } = await this.client.get<Municipality[]>(`/municipalities${params}`);
    return data;
  }

  // Problem Reports functions

  /**
   * Get active problem types for the report form.
   */
  async getProblemTypes(): Promise<ProblemType[]> {
    const { data } = await this.client.get<{ types: ProblemType[] }>('/reports/types');
    return data.types;
  }

  /**
   * Submit a new problem report with attachments.
   */
  async submitProblemReport(formData: FormData): Promise<{ id: string; message: string }> {
    const { data } = await this.client.post<{ id: string; message: string }>(
      '/reports',
      formData,
      {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      }
    );
    return data;
  }

  // Admin Problem Reports functions

  /**
   * List all problem types (admin).
   */
  async getAdminProblemTypes(): Promise<{ types: ProblemTypeAdmin[]; total: number }> {
    const { data } = await this.client.get('/admin/problem-types');
    return data;
  }

  /**
   * Create a new problem type (admin).
   */
  async createProblemType(params: {
    name: string;
    description?: string;
    sort_order?: number;
  }): Promise<ProblemTypeAdmin> {
    const { data } = await this.client.post<ProblemTypeAdmin>('/admin/problem-types', params);
    return data;
  }

  /**
   * Update a problem type (admin).
   */
  async updateProblemType(
    id: string,
    params: {
      name?: string;
      description?: string;
      is_active?: boolean;
      sort_order?: number;
    }
  ): Promise<ProblemTypeAdmin> {
    const { data } = await this.client.put<ProblemTypeAdmin>(`/admin/problem-types/${id}`, params);
    return data;
  }

  /**
   * Delete (deactivate) a problem type (admin).
   */
  async deleteProblemType(id: string): Promise<void> {
    await this.client.delete(`/admin/problem-types/${id}`);
  }

  /**
   * List problem reports (admin).
   */
  async getProblemReports(options?: {
    skip?: number;
    limit?: number;
    status_filter?: string;
    map_id?: string;
  }): Promise<ProblemReportListResponse> {
    const params = new URLSearchParams();
    if (options?.skip !== undefined) params.append('skip', options.skip.toString());
    if (options?.limit !== undefined) params.append('limit', options.limit.toString());
    if (options?.status_filter) params.append('status_filter', options.status_filter);
    if (options?.map_id) params.append('map_id', options.map_id);

    const queryString = params.toString();
    const url = queryString ? `/reports?${queryString}` : '/reports';
    const { data } = await this.client.get<ProblemReportListResponse>(url);
    return data;
  }

  /**
   * Get a single problem report (admin).
   */
  async getProblemReport(id: string): Promise<ProblemReport> {
    const { data } = await this.client.get<ProblemReport>(`/reports/${id}`);
    return data;
  }

  /**
   * Update report status (admin).
   */
  async updateProblemReportStatus(id: string, status: string): Promise<ProblemReport> {
    const { data } = await this.client.put<ProblemReport>(`/reports/${id}/status`, { status });
    return data;
  }

  /**
   * Delete a problem report (admin).
   */
  async deleteProblemReport(id: string): Promise<{ message: string }> {
    const { data } = await this.client.delete<{ message: string }>(`/reports/${id}`);
    return data;
  }

  /**
   * Get attachment download URL with optional token for img src authentication.
   */
  getAttachmentUrl(reportId: string, attachmentId: string, token?: string): string {
    const baseUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001/api';
    const url = `${baseUrl}/reports/${reportId}/attachments/${attachmentId}`;
    return token ? `${url}?token=${encodeURIComponent(token)}` : url;
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

// Types for municipalities
export interface Municipality {
  id: number;
  nome: string;
  uf: string;
}

// Types for problem reports
export interface ProblemType {
  id: string;
  name: string;
  description: string | null;
}

export interface ProblemTypeAdmin extends ProblemType {
  is_active: boolean;
  sort_order: number;
  created_at: string;
  updated_at: string;
}

export interface ProblemReportAttachment {
  id: string;
  type: 'image' | 'audio';
  filename: string;
  mime_type: string;
  size_bytes: number;
}

export interface ProblemReport {
  id: string;
  status: 'nova' | 'em_andamento' | 'concluido';
  description: string;
  latitude: number | null;
  longitude: number | null;
  created_at: string;
  updated_at: string;
  problem_type: ProblemType;
  user: {
    id: string;
    name: string;
    email: string;
    avatar_url: string | null;
  };
  map: {
    id: string;
    origin: string;
    destination: string;
  } | null;
  poi: {
    id: string;
    name: string;
    type: string;
    latitude: number;
    longitude: number;
  } | null;
  attachments: ProblemReportAttachment[];
  attachment_count: number;
}

export interface ProblemReportListResponse {
  reports: ProblemReport[];
  total: number;
  counts_by_status: Record<string, number>;
}

export const apiClient = new APIClient();