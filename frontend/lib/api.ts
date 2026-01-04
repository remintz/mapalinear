import axios, { AxiosInstance, InternalAxiosRequestConfig } from 'axios';
import { getSession, signOut } from 'next-auth/react';
import { getSessionId } from './session-id';
import { reportApiError } from './error-reporter';
import {
  RouteSearchRequest,
  RouteSearchResponse,
  AsyncOperation,
  ExportRouteData,
  AdminUser,
  AdminUserListResponse,
  ImpersonationStatusResponse,
  ImpersonationResponse,
  StopImpersonationResponse,
  AdminMapListResponse,
  AdminMapDetail,
  POIDebugListResponse,
  POIDebugData,
  POIDebugSummary,
  AdminPOIDetail,
  AdminPOIListResponse,
  AdminPOIFilters,
  AdminPOIStats,
  RecalculateQualityResponse,
  RequiredTagsConfig,
  AdminOperationListResponse,
  ApplicationLogsResponse,
  ApplicationLogStats,
  LogTimeWindow,
  UserEventStatsOverview,
  EventTypeStats,
  FeatureUsageStats,
  DeviceStats,
  POIFilterUsageStats,
  ConversionFunnelStats,
  DailyActiveUsers,
  PerformanceStats,
} from './types';

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
  private isSigningOut: boolean = false;

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

      // Add session ID for error correlation
      const sessionId = getSessionId();
      if (sessionId) {
        config.headers['X-Session-ID'] = sessionId;
      }

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

        // Report API errors to backend (except 401 which is expected for expired sessions)
        if (error.response?.status !== 401) {
          const errorToReport = new Error(
            error.response?.data?.detail || error.message || 'Unknown API error'
          );
          errorToReport.stack = error.stack;
          reportApiError(errorToReport, {
            url: error.config?.url,
            method: error.config?.method?.toUpperCase(),
            status: error.response?.status,
          });
        }

        // Transform error for better UX
        if (error.response?.status === 400) {
          throw new Error(error.response.data?.detail || 'Dados inválidos');
        }

        if (error.response?.status === 401) {
          // Clear cached token on auth error
          this.cachedToken = null;
          this.tokenExpiry = 0;

          // Force signOut to clear NextAuth session and redirect to login
          // This ensures the expired token is cleared and user must re-authenticate
          // Use flag to prevent multiple signOut calls from parallel requests
          if (typeof window !== 'undefined' && !this.isSigningOut) {
            this.isSigningOut = true;
            signOut({ callbackUrl: '/login' });
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

  // Admin Users functions

  /**
   * List all users (admin).
   */
  async getAdminUsers(): Promise<AdminUserListResponse> {
    const { data } = await this.client.get<AdminUserListResponse>('/admin/users');
    return data;
  }

  /**
   * Toggle admin status for a user (admin).
   */
  async toggleUserAdmin(userId: string, isAdmin: boolean): Promise<AdminUser> {
    const { data } = await this.client.patch<AdminUser>(`/admin/users/${userId}/admin`, {
      is_admin: isAdmin,
    });
    return data;
  }

  // Impersonation functions

  /**
   * Get current impersonation status (admin).
   */
  async getImpersonationStatus(): Promise<ImpersonationStatusResponse> {
    const { data } = await this.client.get<ImpersonationStatusResponse>('/admin/impersonation-status');
    return data;
  }

  /**
   * Start impersonating a user (admin).
   */
  async startImpersonation(userId: string): Promise<ImpersonationResponse> {
    const { data } = await this.client.post<ImpersonationResponse>(`/admin/impersonate/${userId}`);
    return data;
  }

  /**
   * Stop impersonating (admin).
   */
  async stopImpersonation(): Promise<StopImpersonationResponse> {
    const { data } = await this.client.post<StopImpersonationResponse>('/admin/stop-impersonation');
    return data;
  }

  // System Settings functions

  /**
   * Get system settings.
   */
  async getSettings(): Promise<{ settings: SystemSettings }> {
    const { data } = await this.client.get<{ settings: SystemSettings }>('/settings');
    return data;
  }

  /**
   * Update system settings (admin).
   */
  async updateSettings(settings: SystemSettings): Promise<{ settings: SystemSettings }> {
    const { data } = await this.client.put<{ settings: SystemSettings }>('/settings', { settings });
    return data;
  }

  // Database Maintenance functions (admin)

  /**
   * Get database maintenance stats (admin).
   */
  async getMaintenanceStats(): Promise<DatabaseStats> {
    const { data } = await this.client.get<DatabaseStats>('/admin/maintenance/stats');
    return data;
  }

  /**
   * Run database maintenance (admin).
   */
  async runMaintenance(dryRun: boolean): Promise<MaintenanceResult> {
    const { data } = await this.client.post<MaintenanceResult>(`/admin/maintenance/run?dry_run=${dryRun}`);
    return data;
  }

  /**
   * Run manual log cleanup.
   */
  async runLogCleanup(): Promise<LogCleanupResult> {
    const { data } = await this.client.post<LogCleanupResult>('/admin/maintenance/cleanup-logs');
    return data;
  }

  // Admin Maps functions

  /**
   * Get all maps (admin).
   */
  async getAdminMaps(): Promise<AdminMapListResponse> {
    const { data } = await this.client.get<AdminMapListResponse>('/admin/maps');
    return data;
  }

  /**
   * Get map details (admin).
   */
  async getAdminMapDetails(mapId: string): Promise<AdminMapDetail> {
    const { data } = await this.client.get<AdminMapDetail>(`/admin/maps/${mapId}`);
    return data;
  }

  /**
   * Get POI debug data for a map (admin).
   */
  async getPOIDebugData(mapId: string): Promise<POIDebugListResponse> {
    const { data } = await this.client.get<POIDebugListResponse>(`/admin/maps/${mapId}/debug`);
    return data;
  }

  /**
   * Get detailed debug data for a specific POI (admin).
   */
  async getPOIDebugDetail(mapId: string, debugId: string): Promise<POIDebugData> {
    const { data } = await this.client.get<POIDebugData>(`/admin/maps/${mapId}/debug/${debugId}`);
    return data;
  }

  /**
   * Get POI debug summary for a map (admin).
   */
  async getPOIDebugSummary(mapId: string): Promise<POIDebugSummary> {
    const { data } = await this.client.get<POIDebugSummary>(`/admin/maps/${mapId}/debug/summary`);
    return data;
  }

  // Admin POIs

  /**
   * Get list of all POIs with filters (admin).
   */
  async getAdminPOIs(params?: {
    name?: string;
    city?: string;
    poi_type?: string;
    low_quality_only?: boolean;
    page?: number;
    limit?: number;
  }): Promise<AdminPOIListResponse> {
    const { data } = await this.client.get<AdminPOIListResponse>('/admin/pois', { params });
    return data;
  }

  /**
   * Get POI filter options (admin).
   */
  async getAdminPOIFilters(): Promise<AdminPOIFilters> {
    const { data } = await this.client.get<AdminPOIFilters>('/admin/pois/filters');
    return data;
  }

  /**
   * Get POI statistics (admin).
   */
  async getAdminPOIStats(): Promise<AdminPOIStats> {
    const { data } = await this.client.get<AdminPOIStats>('/admin/pois/stats');
    return data;
  }

  /**
   * Recalculate quality for all POIs (admin).
   */
  async recalculatePOIQuality(): Promise<RecalculateQualityResponse> {
    const { data } = await this.client.post<RecalculateQualityResponse>('/admin/pois/recalculate-quality');
    return data;
  }

  /**
   * Get detailed POI information (admin).
   */
  async getAdminPOI(poiId: string): Promise<AdminPOIDetail> {
    const { data } = await this.client.get<AdminPOIDetail>(`/admin/pois/${poiId}`);
    return data;
  }

  // Required Tags Config (admin)

  /**
   * Get required tags configuration.
   */
  async getRequiredTags(): Promise<RequiredTagsConfig> {
    const { data } = await this.client.get<RequiredTagsConfig>('/settings/required-tags');
    return data;
  }

  /**
   * Update required tags configuration (admin).
   */
  async updateRequiredTags(requiredTags: Record<string, string[]>): Promise<RequiredTagsConfig> {
    const { data } = await this.client.put<RequiredTagsConfig>('/settings/required-tags', { required_tags: requiredTags });
    return data;
  }

  /**
   * Reset required tags to defaults (admin).
   */
  async resetRequiredTags(): Promise<RequiredTagsConfig> {
    const { data } = await this.client.post<RequiredTagsConfig>('/settings/required-tags/reset');
    return data;
  }

  // Admin Operations

  /**
   * Get list of async operations (admin).
   */
  async getAdminOperations(params?: {
    status?: string;
    skip?: number;
    limit?: number;
  }): Promise<AdminOperationListResponse> {
    const { data } = await this.client.get<AdminOperationListResponse>('/admin/operations', { params });
    return data;
  }

  /**
   * Cancel an in-progress operation (admin).
   */
  async cancelOperation(operationId: string): Promise<{ success: boolean; message: string }> {
    const { data } = await this.client.post<{ success: boolean; message: string }>(`/admin/operations/${operationId}/cancel`);
    return data;
  }

  // Application Logs (admin)

  /**
   * Get application logs with filters (admin).
   */
  async getApplicationLogs(params?: {
    level?: string;
    module?: string;
    user_id?: string;
    session_id?: string;
    request_id?: string;
    time_window?: LogTimeWindow;
    start_time?: string;
    end_time?: string;
    skip?: number;
    limit?: number;
  }): Promise<ApplicationLogsResponse> {
    const { data } = await this.client.get<ApplicationLogsResponse>('/admin/logs', { params });
    return data;
  }

  /**
   * Get application log statistics by level (admin).
   */
  async getApplicationLogStats(params?: {
    time_window?: LogTimeWindow;
    start_time?: string;
    end_time?: string;
  }): Promise<ApplicationLogStats> {
    const { data } = await this.client.get<ApplicationLogStats>('/admin/logs/stats', { params });
    return data;
  }

  /**
   * Get list of log modules for filter dropdown (admin).
   */
  async getApplicationLogModules(): Promise<string[]> {
    const { data } = await this.client.get<string[]>('/admin/logs/modules');
    return data;
  }

  /**
   * Cleanup old application logs (admin).
   */
  async cleanupApplicationLogs(daysToKeep: number = 30): Promise<{ message: string; deleted_count: number }> {
    const { data } = await this.client.delete<{ message: string; deleted_count: number }>(
      '/admin/logs/cleanup',
      { params: { days_to_keep: daysToKeep } }
    );
    return data;
  }

  // Debug functions

  /**
   * Get debug segments data.
   */
  async getDebugSegments(): Promise<DebugSegmentsData> {
    const { data } = await this.client.get<DebugSegmentsData>('/operations/debug/segments');
    return data;
  }

  // User Event Analytics

  /**
   * Get user event analytics overview stats (admin).
   */
  async getEventStatsOverview(days: number = 30): Promise<UserEventStatsOverview> {
    const { data } = await this.client.get<UserEventStatsOverview>('/events/stats', { params: { days } });
    return data;
  }

  /**
   * Get event type statistics (admin).
   */
  async getEventTypeStats(days: number = 30): Promise<EventTypeStats[]> {
    const { data } = await this.client.get<EventTypeStats[]>('/events/stats/events', { params: { days } });
    return data;
  }

  /**
   * Get feature usage statistics (admin).
   */
  async getFeatureUsageStats(days: number = 30): Promise<FeatureUsageStats[]> {
    const { data } = await this.client.get<FeatureUsageStats[]>('/events/stats/features', { params: { days } });
    return data;
  }

  /**
   * Get device statistics (admin).
   */
  async getDeviceStats(days: number = 30): Promise<DeviceStats[]> {
    const { data } = await this.client.get<DeviceStats[]>('/events/stats/devices', { params: { days } });
    return data;
  }

  /**
   * Get POI filter usage statistics (admin).
   */
  async getPOIFilterStats(days: number = 30): Promise<POIFilterUsageStats[]> {
    const { data } = await this.client.get<POIFilterUsageStats[]>('/events/stats/poi-filters', { params: { days } });
    return data;
  }

  /**
   * Get conversion funnel statistics (admin).
   */
  async getConversionFunnelStats(days: number = 30): Promise<ConversionFunnelStats> {
    const { data } = await this.client.get<ConversionFunnelStats>('/events/stats/funnel', { params: { days } });
    return data;
  }

  /**
   * Get daily active users statistics (admin).
   */
  async getDailyActiveUsers(days: number = 30): Promise<DailyActiveUsers[]> {
    const { data } = await this.client.get<DailyActiveUsers[]>('/events/stats/daily', { params: { days } });
    return data;
  }

  /**
   * Get performance statistics (admin).
   */
  async getPerformanceStats(days: number = 30): Promise<PerformanceStats[]> {
    const { data } = await this.client.get<PerformanceStats[]>('/events/stats/performance', { params: { days } });
    return data;
  }

  /**
   * Export user events to CSV (admin).
   */
  async exportEventsCsv(days: number = 30): Promise<Blob> {
    const response = await this.client.get('/events/export/csv', {
      params: { days },
      responseType: 'blob',
    });
    return response.data;
  }

  /**
   * Cleanup old user events (admin).
   */
  async cleanupUserEvents(daysToKeep: number = 365): Promise<{ message: string; deleted_count: number }> {
    const { data } = await this.client.delete<{ message: string; deleted_count: number }>(
      '/events/cleanup',
      { params: { days_to_keep: daysToKeep } }
    );
    return data;
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

// Types for system settings
export interface SystemSettings {
  poi_search_radius_km: string;
  duplicate_map_tolerance_km: string;
  poi_debug_enabled?: string;
  log_retention_days?: string;
  analytics_retention_days?: string;
}

// Types for database maintenance
export interface DatabaseStats {
  total_pois: number;
  referenced_pois: number;
  unreferenced_pois: number;
  total_maps: number;
  total_map_pois: number;
  pending_operations: number;
  stale_operations: number;
}

export interface MaintenanceResult {
  orphan_pois_found: number;
  orphan_pois_deleted: number;
  is_referenced_fixed: number;
  stale_operations_cleaned: number;
  execution_time_ms: number;
  dry_run: boolean;
}

export interface LogCleanupResult {
  retention_days: number;
  cutoff_date: string;
  application_logs_deleted: number;
  api_logs_deleted: number;
  frontend_logs_deleted: number;
  total_deleted: number;
}

// Types for debug segments
export interface DebugSegment {
  id: string;
  start_distance_km: number;
  end_distance_km: number;
  length_km: number;
  name: string;
  start_coordinates: {
    latitude: number;
    longitude: number;
  };
  end_coordinates: {
    latitude: number;
    longitude: number;
  };
}

export interface DebugSegmentsData {
  origin: string;
  destination: string;
  total_distance_km: number;
  total_segments: number;
  segments: DebugSegment[];
}

export const apiClient = new APIClient();