"""
SQLAlchemy models for MapaLinear.
"""
from api.database.models.api_call_log import ApiCallLog
from api.database.models.application_log import ApplicationLog
from api.database.models.async_operation import AsyncOperation
from api.database.models.cache import CacheEntry
from api.database.models.google_places_cache import GooglePlacesCache
from api.database.models.impersonation_session import ImpersonationSession
from api.database.models.map import Map
from api.database.models.map_poi import MapPOI
from api.database.models.map_segment import MapSegment
from api.database.models.poi import POI
from api.database.models.route_segment import RouteSegment
from api.database.models.segment_poi import SegmentPOI
from api.database.models.user import User
from api.database.models.user_map import UserMap
from api.database.models.system_settings import SystemSettings
from api.database.models.problem_type import ProblemType
from api.database.models.report_attachment import ReportAttachment
from api.database.models.problem_report import ProblemReport
from api.database.models.poi_debug_data import POIDebugData
from api.database.models.frontend_error_log import FrontendErrorLog
from api.database.models.gps_debug_log import GPSDebugLog
from api.database.models.user_event import UserEvent
from api.database.models.event_types import EventCategory, EventType, EVENT_TYPE_TO_CATEGORY, get_category_for_event_type

__all__ = [
    "ApiCallLog",
    "ApplicationLog",
    "AsyncOperation",
    "ImpersonationSession",
    "Map",
    "MapPOI",
    "MapSegment",
    "POI",
    "RouteSegment",
    "SegmentPOI",
    "CacheEntry",
    "GooglePlacesCache",
    "User",
    "UserMap",
    "SystemSettings",
    "ProblemType",
    "ReportAttachment",
    "ProblemReport",
    "POIDebugData",
    "FrontendErrorLog",
    "GPSDebugLog",
    "UserEvent",
    "EventCategory",
    "EventType",
    "EVENT_TYPE_TO_CATEGORY",
    "get_category_for_event_type",
]
