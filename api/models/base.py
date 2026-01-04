"""
Base Pydantic models with common configurations.

Provides a base model that ensures all datetime fields are serialized
with UTC timezone for consistent frontend handling.
"""

from datetime import datetime, timezone
from typing import Annotated, Any

from pydantic import BaseModel, PlainSerializer


def serialize_datetime_utc(dt: datetime) -> str:
    """
    Serialize datetime to ISO format with UTC timezone.

    If the datetime is naive (no timezone), assumes it's UTC and adds the timezone.
    This ensures the frontend receives timestamps with 'Z' suffix for proper
    local time conversion.
    """
    if dt is None:
        return None

    # If datetime is naive, assume it's UTC
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)

    return dt.isoformat()


# Type alias for datetime fields that should be serialized with UTC timezone
UTCDatetime = Annotated[datetime, PlainSerializer(serialize_datetime_utc, return_type=str)]


class APIBaseModel(BaseModel):
    """
    Base model for API responses.

    Configures Pydantic to serialize datetime fields with UTC timezone,
    ensuring consistent timestamp handling across the frontend.
    """

    model_config = {
        "from_attributes": True,  # Allow ORM model conversion
        "json_encoders": {
            datetime: serialize_datetime_utc,
        },
    }
