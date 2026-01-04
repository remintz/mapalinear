"""
Event types and categories for user analytics.
"""

from enum import Enum


class EventCategory(str, Enum):
    """Categories of user events."""

    AUTH = "auth"
    NAVIGATION = "navigation"
    MAP_MANAGEMENT = "map_management"
    PREFERENCES = "preferences"
    INTERACTION = "interaction"
    REPORTING = "reporting"
    TRACKING = "tracking"
    ERROR = "error"
    PERFORMANCE = "performance"
    CONVERSION = "conversion"


class EventType(str, Enum):
    """Specific event types within categories."""

    # Auth events
    LOGIN = "login"
    LOGOUT = "logout"

    # Navigation events
    PAGE_VIEW = "page_view"
    LINEAR_MAP_VIEW = "linear_map_view"
    OSM_MAP_VIEW = "osm_map_view"

    # Map management events
    MAP_CREATE = "map_create"
    MAP_ADOPT = "map_adopt"
    MAP_REMOVE = "map_remove"
    MAP_SEARCH = "map_search"
    MAP_EXPORT_PDF = "map_export_pdf"
    MAP_EXPORT_GEOJSON = "map_export_geojson"
    MAP_EXPORT_GPX = "map_export_gpx"

    # Preferences events
    POI_FILTER_TOGGLE = "poi_filter_toggle"

    # Interaction events
    POI_CLICK = "poi_click"

    # Reporting events
    PROBLEM_REPORT_START = "problem_report_start"
    PROBLEM_REPORT_SUBMIT = "problem_report_submit"

    # Tracking events
    ROUTE_TRACKING_START = "route_tracking_start"
    ROUTE_TRACKING_STOP = "route_tracking_stop"

    # Error events
    API_ERROR = "api_error"
    GEOLOCATION_ERROR = "geolocation_error"
    OFFLINE_CACHE_MISS = "offline_cache_miss"

    # Performance events
    MAP_LOAD_TIME = "map_load_time"
    SEARCH_RESPONSE_TIME = "search_response_time"

    # Conversion funnel events
    SEARCH_STARTED = "search_started"
    SEARCH_COMPLETED = "search_completed"
    SEARCH_ABANDONED = "search_abandoned"


# Mapping from event type to category for validation
EVENT_TYPE_TO_CATEGORY: dict[EventType, EventCategory] = {
    # Auth
    EventType.LOGIN: EventCategory.AUTH,
    EventType.LOGOUT: EventCategory.AUTH,
    # Navigation
    EventType.PAGE_VIEW: EventCategory.NAVIGATION,
    EventType.LINEAR_MAP_VIEW: EventCategory.NAVIGATION,
    EventType.OSM_MAP_VIEW: EventCategory.NAVIGATION,
    # Map management
    EventType.MAP_CREATE: EventCategory.MAP_MANAGEMENT,
    EventType.MAP_ADOPT: EventCategory.MAP_MANAGEMENT,
    EventType.MAP_REMOVE: EventCategory.MAP_MANAGEMENT,
    EventType.MAP_SEARCH: EventCategory.MAP_MANAGEMENT,
    EventType.MAP_EXPORT_PDF: EventCategory.MAP_MANAGEMENT,
    EventType.MAP_EXPORT_GEOJSON: EventCategory.MAP_MANAGEMENT,
    EventType.MAP_EXPORT_GPX: EventCategory.MAP_MANAGEMENT,
    # Preferences
    EventType.POI_FILTER_TOGGLE: EventCategory.PREFERENCES,
    # Interaction
    EventType.POI_CLICK: EventCategory.INTERACTION,
    # Reporting
    EventType.PROBLEM_REPORT_START: EventCategory.REPORTING,
    EventType.PROBLEM_REPORT_SUBMIT: EventCategory.REPORTING,
    # Tracking
    EventType.ROUTE_TRACKING_START: EventCategory.TRACKING,
    EventType.ROUTE_TRACKING_STOP: EventCategory.TRACKING,
    # Error
    EventType.API_ERROR: EventCategory.ERROR,
    EventType.GEOLOCATION_ERROR: EventCategory.ERROR,
    EventType.OFFLINE_CACHE_MISS: EventCategory.ERROR,
    # Performance
    EventType.MAP_LOAD_TIME: EventCategory.PERFORMANCE,
    EventType.SEARCH_RESPONSE_TIME: EventCategory.PERFORMANCE,
    # Conversion
    EventType.SEARCH_STARTED: EventCategory.CONVERSION,
    EventType.SEARCH_COMPLETED: EventCategory.CONVERSION,
    EventType.SEARCH_ABANDONED: EventCategory.CONVERSION,
}


def get_category_for_event_type(event_type: str) -> str | None:
    """
    Get the category for a given event type.

    Args:
        event_type: The event type string

    Returns:
        The category string, or None if event type is not found
    """
    try:
        et = EventType(event_type)
        return EVENT_TYPE_TO_CATEGORY.get(et, EventCategory.INTERACTION).value
    except ValueError:
        # Unknown event type, return None to allow custom events
        return None
