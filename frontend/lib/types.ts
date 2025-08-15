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
  tags: Record<string, unknown>;
  operator?: string;
  brand?: string;
  opening_hours?: string;
  quality_score?: number;
}

// Enums
export enum POIType {
  CITY = 'city',
  GAS_STATION = 'gas_station',
  RESTAURANT = 'restaurant',
  TOLL_BOOTH = 'toll_booth'
}

// Export types
export interface ExportPOI {
  id: string;
  name: string;
  type: string;
  coordinates: Coordinates;
  distance_from_origin_km: number;
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
  start_coordinates: Coordinates;
  end_coordinates: Coordinates;
  distance_km: number;
  highway?: string;
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
  tags?: Record<string, unknown>;
  operator?: string;
  brand?: string;
  opening_hours?: string;
  quality_score?: number;
}

export enum MilestoneType {
  CITY = 'city',
  TOWN = 'town', 
  VILLAGE = 'village',
  GAS_STATION = 'gas_station',
  RESTAURANT = 'restaurant',
  HOTEL = 'hotel',
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
  include_gas_stations?: boolean;
  include_restaurants?: boolean;
  include_toll_booths?: boolean;
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