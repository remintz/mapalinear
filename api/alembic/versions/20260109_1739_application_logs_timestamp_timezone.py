"""change application_logs timestamp to timezone-aware

Revision ID: application_logs_timestamp_tz
Revises: 6438e08a65df
Create Date: 2026-01-09 17:39:00.000000

Changes the timestamp column in application_logs from TIMESTAMP WITHOUT TIME ZONE
to TIMESTAMP WITH TIME ZONE to properly handle timezone information.
Existing timestamps (assumed to be UTC) are converted to UTC timezone.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "application_logs_timestamp_tz"
down_revision: Union[str, None] = "6438e08a65df"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Convert existing timestamp column from TIMESTAMP WITHOUT TIME ZONE
    # to TIMESTAMP WITH TIME ZONE
    # We assume existing timestamps are in UTC
    op.execute("""
        ALTER TABLE application_logs
        ALTER COLUMN timestamp TYPE TIMESTAMP WITH TIME ZONE
        USING timestamp AT TIME ZONE 'UTC'
    """)


def downgrade() -> None:
    # Convert back to TIMESTAMP WITHOUT TIME ZONE
    # Remove timezone information (convert to UTC first, then strip timezone)
    op.execute("""
        ALTER TABLE application_logs
        ALTER COLUMN timestamp TYPE TIMESTAMP WITHOUT TIME ZONE
        USING timestamp AT TIME ZONE 'UTC'
    """)
