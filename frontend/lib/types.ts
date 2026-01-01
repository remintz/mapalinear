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

// Async operation types
export interface AsyncOperation {
  operation_id: string;
  status: 'in_progress' | 'completed' | 'failed';
  type: 'linear_map' | 'osm_search';
  started_at: string;
  progress_percent: number;
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
  lookback_km: number;
  lookback_distance_km: number;
  lookback_point: { lat: number; lon: number };
  search_point: { lat: number; lon: number };
  search_point_distance_km: number;
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

export interface POIDebugData {
  id: string;
  map_poi_id: string;
  poi_name: string;
  poi_type: string;
  poi_lat: number;
  poi_lon: number;
  main_route_segment?: number[][];
  junction_lat?: number;
  junction_lon?: number;
  junction_distance_km?: number;
  access_route_geometry?: number[][];
  access_route_distance_km?: number;
  side_calculation?: SideCalculationDetail;
  lookback_data?: LookbackDetail;
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