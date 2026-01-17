// Base types
export interface Coordinates {
  lat: number;
  lon: number;
}

export interface POI {
  id: string;
  name: string;
  type: POIType;
  coordinates: Coordinates;
  distance_from_origin_km: number;
  distance_from_road_meters?: number;
  side?: 'left' | 'right' | 'center';
  city?: string;
  tags: Record<string, unknown>;
  operator?: string;
  brand?: string;
  opening_hours?: string;
  phone?: string;
  website?: string;
  cuisine?: string;
  amenities?: string[];
  quality_score?: number;
  // Junction information for distant POIs
  junction_distance_km?: number;
  junction_coordinates?: { latitude: number; longitude: number };
  requires_detour?: boolean;
  // Google Places ratings
  rating?: number;
  rating_count?: number;
  google_maps_uri?: string;
}

// Enums
export enum POIType {
  CITY = 'city',
  GAS_STATION = 'gas_station',
  RESTAURANT = 'restaurant',
  FAST_FOOD = 'fast_food',
  CAFE = 'cafe',
  TOLL_BOOTH = 'toll_booth',
  HOTEL = 'hotel',
  CAMPING = 'camping',
  HOSPITAL = 'hospital',
  REST_AREA = 'rest_area'
}

// Export types
export interface ExportPOI {
  id: string;
  name: string;
  type: string;
  coordinates: Coordinates;
  distance_from_origin_km: number;
  city?: string;
  brand?: string;
  operator?: string;
  opening_hours?: string;
}

export interface ExportSegment {
  id: string;
  name?: string;
  geometry: Coordinates[];
  length_km: number;
}

export interface ExportRouteData {
  origin: string;
  destination: string;
  total_distance_km: number;
  segments: ExportSegment[];
  pois: ExportPOI[];
}

// Route related types
export interface RouteSegment {
  id: string;
  start_coordinates: Coordinates;
  end_coordinates: Coordinates;
  distance_km: number;
  // Distance from origin for this segment
  start_distance_km?: number;
  end_distance_km?: number;
  length_km?: number;
  // Road information
  name?: string;
  ref?: string;
  highway?: string;
  highway_type?: string;
  // Full geometry of the segment (list of coordinates)
  geometry?: Coordinates[];
  milestones?: Milestone[];
}

// Milestone type (from API)
export interface Milestone {
  id: string;
  name: string;
  type: MilestoneType;
  coordinates: Coordinates;
  distance_from_origin_km: number;
  distance_from_road_meters?: number;
  side?: 'left' | 'right' | 'center';
  city?: string;
  tags?: Record<string, unknown>;
  operator?: string;
  brand?: string;
  opening_hours?: string;
  phone?: string;
  website?: string;
  cuisine?: string;
  amenities?: string[];
  quality_score?: number;
  // Junction information for distant POIs
  junction_distance_km?: number;
  junction_coordinates?: { latitude: number; longitude: number };
  requires_detour?: boolean;
  // Google Places ratings
  rating?: number;
  rating_count?: number;
  google_maps_uri?: string;
}

export enum MilestoneType {
  CITY = 'city',
  TOWN = 'town',
  VILLAGE = 'village',
  GAS_STATION = 'gas_station',
  RESTAURANT = 'restaurant',
  HOTEL = 'hotel',
  CAMPING = 'camping',
  REST_AREA = 'rest_area',
  TOLL_BOOTH = 'toll_booth',
  HOSPITAL = 'hospital',
  POLICE = 'police',
  INTERSECTION = 'intersection',
  EXIT = 'exit',
  OTHER = 'other'
}

// API Request/Response types
export interface RouteSearchRequest {
  origin: string;
  destination: string;
  max_distance?: number;
}

export interface RouteSearchResponse {
  id: string;
  origin: string;
  destination: string;
  total_distance_km: number;
  total_length_km?: number; // API returns this
  pois: POI[];
  milestones?: Milestone[]; // API returns this
  segments: RouteSegment[];
  created_at?: string;
  creation_date?: string; // API returns this
  osm_road_id?: string;
}

// Component props interfaces
export interface RouteMapProps {
  route: RouteSearchResponse;
  selectedPOI?: string;
  onPOISelect?: (poiId: string) => void;
}

// Map generation phases (must match backend MapGenerationPhase enum)
export type MapGenerationPhase =
  | 'geocoding'
  | 'route_calculation'
  | 'segment_processing'
  | 'poi_search'
  | 'map_creation'
  | 'saving'
  | 'enrichment'
  | 'finalizing';

// Phase descriptions in Portuguese (must match backend PHASE_CONFIGS)
export const PHASE_DESCRIPTIONS: Record<MapGenerationPhase, string> = {
  geocoding: 'Localizando enderecos...',
  route_calculation: 'Calculando rota...',
  segment_processing: 'Processando segmentos...',
  poi_search: 'Buscando pontos de interesse...',
  map_creation: 'Criando mapa...',
  saving: 'Salvando mapa...',
  enrichment: 'Enriquecendo dados...',
  finalizing: 'Finalizando...',
};

// Async operation types
export interface AsyncOperation {
  operation_id: string;
  status: 'in_progress' | 'completed' | 'failed';
  type: 'linear_map' | 'osm_search';
  started_at: string;
  progress_percent: number;
  current_phase?: MapGenerationPhase;
  estimated_completion?: string;
  result?: RouteSearchResponse;
  error?: string;
}

// Form data types are defined in validations.ts

// Admin types
export interface AdminUser {
  id: string;
  email: string;
  name: string;
  avatar_url?: string;
  is_active: boolean;
  is_admin: boolean;
  created_at: string;
  updated_at: string;
  last_login_at?: string;
  map_count: number;
}

export interface AdminUserListResponse {
  users: AdminUser[];
  total: number;
}

// Impersonation types
export interface ImpersonationResponse {
  user: AdminUser;
  message: string;
  session_id: string;
}

export interface StopImpersonationResponse {
  user: AdminUser;
  message: string;
}

export interface ImpersonationStatusResponse {
  is_impersonating: boolean;
  current_user: AdminUser;
  real_admin: AdminUser | null;
}

// Admin Map types
export interface AdminMap {
  id: string;
  origin: string;
  destination: string;
  total_length_km: number;
  created_at: string;
  updated_at: string;
  user_count: number;
  created_by_user_id?: string;
}

export interface AdminMapListResponse {
  maps: AdminMap[];
  total: number;
}

export interface AdminMapDetail extends AdminMap {
  poi_counts: Record<string, number>;
}

// POI Debug types
export interface SideCalculationDetail {
  road_vector: { dx: number; dy: number };
  poi_vector?: { dx: number; dy: number };  // Used by old method (POI position)
  access_vector?: { dx: number; dy: number };  // Used by new method (access route direction)
  cross_product: number;
  resulting_side: 'left' | 'right';
  segment_start: { lat: number; lon: number };
  segment_end: { lat: number; lon: number };
  segment_idx?: number;
  // New fields for access route method
  method?: 'access_route_direction' | 'poi_position';
  junction_idx_on_access?: number;
  access_direction_point_idx?: number;
  access_start?: { lat: number; lon: number };
  access_direction_point?: { lat: number; lon: number };
}

export interface LookbackDetail {
  poi_distance_from_road_m: number;
  lookback_km?: number;  // Only for interpolated method
  lookback_distance_km: number;
  lookback_point: { lat: number; lon: number };
  search_point: { lat: number; lon: number };
  search_point_distance_km: number;
  lookback_method?: 'search_point' | 'search_point_first' | 'interpolated';
  lookback_index?: number;
  current_search_point_index?: number;
  lookback_count_setting?: number;
  // Legacy fields (kept for compatibility with old data)
  lookback_milestone_name?: string;
  milestones_available_before?: number;
  lookback_milestones_count_setting?: number;
}

export interface RecalculationAttempt {
  attempt: number;
  search_point: { lat: number; lon: number };
  search_point_distance_km: number;
  junction_found: boolean;
  junction_distance_km?: number;
  access_route_distance_km?: number;
  improvement: boolean;
  reason?: string;
}

export interface JunctionCalculationDetail {
  method?: string;  // 'first_segment_end', etc.
  junction_distance_km?: number;
  distance_along_access_to_crossing_km?: number;
  exit_point_index?: number;
  total_access_points?: number;
  crossing_point_on_access?: { lat: number; lon: number };
  corresponding_point_on_main?: { lat: number; lon: number };
  intersection_distance_m?: number;
  access_route_total_km?: number;
}

export interface POIDebugData {
  id: string;
  map_poi_id: string;
  poi_name: string;
  poi_type: string;
  poi_lat: number;
  poi_lon: number;
  distance_from_origin_km: number;
  main_route_segment?: number[][];
  junction_lat?: number;
  junction_lon?: number;
  junction_distance_km?: number;
  access_route_geometry?: number[][];
  access_route_distance_km?: number;
  side_calculation?: SideCalculationDetail;
  lookback_data?: LookbackDetail;
  junction_calculation?: JunctionCalculationDetail;
  recalculation_history?: RecalculationAttempt[];
  final_side: 'left' | 'right' | 'center';
  requires_detour: boolean;
  distance_from_road_m: number;
  created_at: string;
}

export interface POIDebugSummary {
  total: number;
  detour_count: number;
  left_count: number;
  right_count: number;
  center_count: number;
}

export interface POIDebugListResponse {
  pois: POIDebugData[];
  summary: POIDebugSummary;
  has_debug_data: boolean;
}

// Admin POI types
export interface AdminPOI {
  id: string;
  osm_id?: string;
  here_id?: string;
  name: string;
  type: string;
  latitude: number;
  longitude: number;
  city?: string;
  quality_score?: number;
  is_low_quality: boolean;
  is_disabled: boolean;
  missing_tags: string[];
  quality_issues: string[];
  brand?: string;
  operator?: string;
  phone?: string;
  website?: string;
  opening_hours?: string;
  cuisine?: string;
  rating?: number;
  rating_count?: number;
  has_name: boolean;
  has_phone: boolean;
  has_website: boolean;
  has_opening_hours: boolean;
  has_brand: boolean;
  has_operator: boolean;
  created_at: string;
}

export interface AdminPOIDetail extends AdminPOI {
  osm_tags: Record<string, unknown>;
  here_data?: Record<string, unknown>;
  enriched_by: string[];
  google_maps_uri?: string;
  is_referenced: boolean;
  amenities: string[];
}

export interface AdminPOIListResponse {
  pois: AdminPOI[];
  total: number;
  page: number;
  limit: number;
}

export interface AdminPOIFilters {
  cities: string[];
  types: string[];
}

export interface AdminPOIStats {
  total: number;
  low_quality: number;
  by_type: Record<string, number>;
  by_city: Record<string, number>;
}

export interface RecalculateQualityResponse {
  updated: number;
  total: number;
  message: string;
}

export interface RequiredTagsConfig {
  required_tags: Record<string, string[]>;
  available_tags: string[];
}

// Admin Operations types
export interface OperationUser {
  id: string;
  email: string;
  name: string;
}

export interface AdminOperation {
  id: string;
  operation_type: string;
  status: 'in_progress' | 'completed' | 'failed';
  progress_percent: number;
  current_phase?: MapGenerationPhase;
  started_at: string;
  completed_at?: string;
  duration_seconds?: number;
  error?: string;
  user?: OperationUser;
  origin?: string;
  destination?: string;
  total_length_km?: number;
}

export interface AdminOperationStats {
  in_progress: number;
  completed: number;
  failed: number;
  total: number;
}

export interface AdminOperationListResponse {
  operations: AdminOperation[];
  total: number;
  stats: AdminOperationStats;
}

// Application Log types
export interface ApplicationLog {
  id: string;
  timestamp: string;
  level: "DEBUG" | "INFO" | "WARNING" | "ERROR" | "CRITICAL";
  module: string;
  message: string;
  request_id?: string;
  session_id?: string;
  user_email?: string;
  func_name?: string;
  line_no?: number;
  exc_info?: string;
}

export interface ApplicationLogsResponse {
  logs: ApplicationLog[];
  total: number;
  skip: number;
  limit: number;
}

export interface ApplicationLogStats {
  debug: number;
  info: number;
  warning: number;
  error: number;
  critical: number;
  total: number;
}

export type LogTimeWindow = "5m" | "15m" | "1h" | "24h" | "custom";

// User Event Analytics Types
export interface UserEventStatsOverview {
  period_start: string;
  period_end: string;
  total_events: number;
  unique_sessions: number;
  unique_users: number;
}

export interface EventTypeStats {
  event_category: string;
  event_type: string;
  count: number;
  unique_sessions: number;
  unique_users: number;
}

export interface DeviceStats {
  device_type: string | null;
  os: string | null;
  browser: string | null;
  count: number;
  unique_sessions: number;
}

export interface DailyActiveUsers {
  date: string;
  unique_sessions: number;
  unique_users: number;
  total_events: number;
}

export interface FeatureUsageStats {
  feature: string;
  count: number;
  unique_sessions: number;
  unique_users: number;
}

export interface POIFilterUsageStats {
  filter_name: string | null;
  enabled: boolean;
  count: number;
}

export interface ConversionFunnelStats {
  search_started: { sessions: number; events: number };
  search_completed: { sessions: number; events: number };
  search_abandoned: { sessions: number; events: number };
  map_create: { sessions: number; events: number };
  map_adopt: { sessions: number; events: number };
  completion_rate: number;
  abandonment_rate: number;
  map_creation_rate: number;
}

export interface PerformanceStats {
  event_type: string;
  count: number;
  avg_duration_ms: number;
  min_duration_ms: number;
  max_duration_ms: number;
}

export interface LoginLocation {
  latitude: number;
  longitude: number;
  user_id: string | null;
  device_type: string | null;
  created_at: string;
  user_email: string | null;
  user_name: string | null;
}

// GPS Debug Log types (admin)
export interface GPSDebugPOIInfo {
  id: string;
  name: string;
  type: string;
  distance_from_origin_km: number;
  relative_distance_km: number;
}

export interface GPSDebugLogRequest {
  map_id: string;
  map_origin: string;
  map_destination: string;
  latitude: number;
  longitude: number;
  gps_accuracy?: number;
  distance_from_origin_km?: number;
  is_on_route: boolean;
  distance_to_route_m?: number;
  previous_pois?: GPSDebugPOIInfo[];
  next_pois?: GPSDebugPOIInfo[];
  session_id?: string;
}

export interface GPSDebugLogResponse {
  status: string;
  message: string;
  log_id?: string;
  last_log_at?: string;
}

export interface GPSDebugLogEntry {
  id: string;
  created_at: string;
  user_email: string;
  map_id: string;
  map_origin: string;
  map_destination: string;
  latitude: number;
  longitude: number;
  gps_accuracy?: number;
  distance_from_origin_km?: number;
  is_on_route: boolean;
  distance_to_route_m?: number;
  previous_pois?: GPSDebugPOIInfo[];
  next_pois?: GPSDebugPOIInfo[];
  session_id?: string;
}

