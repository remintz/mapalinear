"""add missing_tags to pois

Revision ID: missing_tags_001
Revises: quality_fields_001
Create Date: 2026-01-01 17:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'missing_tags_001'
down_revision: Union[str, None] = 'quality_fields_001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add missing_tags field to pois table
    # Stores list of required tags that are missing for this POI type
    op.add_column('pois', sa.Column('missing_tags', postgresql.JSONB(astext_type=sa.Text()), nullable=True, server_default='[]'))


def downgrade() -> None:
    op.drop_column('pois', 'missing_tags')
