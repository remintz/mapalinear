/**
 * Type definitions for user analytics events.
 */

/**
 * Event categories for user analytics.
 */
export enum EventCategory {
  AUTH = 'auth',
  NAVIGATION = 'navigation',
  MAP_MANAGEMENT = 'map_management',
  PREFERENCES = 'preferences',
  INTERACTION = 'interaction',
  REPORTING = 'reporting',
  TRACKING = 'tracking',
  PERFORMANCE = 'performance',
  CONVERSION = 'conversion',
}

/**
 * Event types for user analytics.
 */
export enum EventType {
  // Auth events
  LOGIN = 'login',
  LOGOUT = 'logout',

  // Navigation events
  PAGE_VIEW = 'page_view',
  LINEAR_MAP_VIEW = 'linear_map_view',
  OSM_MAP_VIEW = 'osm_map_view',

  // Map management events
  MAP_CREATE = 'map_create',
  MAP_ADOPT = 'map_adopt',
  MAP_REMOVE = 'map_remove',
  MAP_SEARCH = 'map_search',
  MAP_EXPORT_PDF = 'map_export_pdf',
  MAP_EXPORT_GEOJSON = 'map_export_geojson',
  MAP_EXPORT_GPX = 'map_export_gpx',

  // Preferences events
  POI_FILTER_TOGGLE = 'poi_filter_toggle',

  // Interaction events
  POI_CLICK = 'poi_click',

  // Reporting events
  PROBLEM_REPORT_START = 'problem_report_start',
  PROBLEM_REPORT_SUBMIT = 'problem_report_submit',

  // Tracking events
  ROUTE_TRACKING_START = 'route_tracking_start',
  ROUTE_TRACKING_STOP = 'route_tracking_stop',

  // Performance events
  MAP_LOAD_TIME = 'map_load_time',
  SEARCH_RESPONSE_TIME = 'search_response_time',

  // Conversion funnel events
  SEARCH_STARTED = 'search_started',
  SEARCH_COMPLETED = 'search_completed',
  SEARCH_ABANDONED = 'search_abandoned',
}

/**
 * Device types for analytics.
 */
export type DeviceType = 'mobile' | 'tablet' | 'desktop';

/**
 * User event data structure sent to the backend.
 */
export interface UserEvent {
  event_type: string;
  event_category?: string;
  session_id: string;
  user_id?: string;
  event_data?: Record<string, unknown>;
  device_type?: DeviceType;
  os?: string;
  browser?: string;
  screen_width?: number;
  screen_height?: number;
  page_path?: string;
  referrer?: string;
  latitude?: number;
  longitude?: number;
  duration_ms?: number;
}

/**
 * Response from the track events endpoint.
 */
export interface TrackEventsResponse {
  success: boolean;
  queued_count: number;
}

/**
 * Device info detected from the user agent.
 */
export interface DeviceInfo {
  deviceType: DeviceType;
  os: string;
  browser: string;
  screenWidth: number;
  screenHeight: number;
}

/**
 * Mapping from event types to their categories.
 */
export const EVENT_TYPE_TO_CATEGORY: Record<string, EventCategory> = {
  // Auth
  [EventType.LOGIN]: EventCategory.AUTH,
  [EventType.LOGOUT]: EventCategory.AUTH,

  // Navigation
  [EventType.PAGE_VIEW]: EventCategory.NAVIGATION,
  [EventType.LINEAR_MAP_VIEW]: EventCategory.NAVIGATION,
  [EventType.OSM_MAP_VIEW]: EventCategory.NAVIGATION,

  // Map management
  [EventType.MAP_CREATE]: EventCategory.MAP_MANAGEMENT,
  [EventType.MAP_ADOPT]: EventCategory.MAP_MANAGEMENT,
  [EventType.MAP_REMOVE]: EventCategory.MAP_MANAGEMENT,
  [EventType.MAP_SEARCH]: EventCategory.MAP_MANAGEMENT,
  [EventType.MAP_EXPORT_PDF]: EventCategory.MAP_MANAGEMENT,
  [EventType.MAP_EXPORT_GEOJSON]: EventCategory.MAP_MANAGEMENT,
  [EventType.MAP_EXPORT_GPX]: EventCategory.MAP_MANAGEMENT,

  // Preferences
  [EventType.POI_FILTER_TOGGLE]: EventCategory.PREFERENCES,

  // Interaction
  [EventType.POI_CLICK]: EventCategory.INTERACTION,

  // Reporting
  [EventType.PROBLEM_REPORT_START]: EventCategory.REPORTING,
  [EventType.PROBLEM_REPORT_SUBMIT]: EventCategory.REPORTING,

  // Tracking
  [EventType.ROUTE_TRACKING_START]: EventCategory.TRACKING,
  [EventType.ROUTE_TRACKING_STOP]: EventCategory.TRACKING,

  // Performance
  [EventType.MAP_LOAD_TIME]: EventCategory.PERFORMANCE,
  [EventType.SEARCH_RESPONSE_TIME]: EventCategory.PERFORMANCE,

  // Conversion
  [EventType.SEARCH_STARTED]: EventCategory.CONVERSION,
  [EventType.SEARCH_COMPLETED]: EventCategory.CONVERSION,
  [EventType.SEARCH_ABANDONED]: EventCategory.CONVERSION,
};

/**
 * Get the category for an event type.
 */
export function getCategoryForEventType(eventType: string): EventCategory | undefined {
  return EVENT_TYPE_TO_CATEGORY[eventType];
}
