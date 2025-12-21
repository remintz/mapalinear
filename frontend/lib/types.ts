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