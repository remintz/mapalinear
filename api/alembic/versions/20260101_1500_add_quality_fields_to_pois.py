"""add quality fields to pois

Revision ID: quality_fields_001
Revises: 6111984c4d7e
Create Date: 2026-01-01 15:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'quality_fields_001'
down_revision: Union[str, None] = '6111984c4d7e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add quality fields to pois table
    op.add_column('pois', sa.Column('quality_score', sa.Float(), nullable=True))
    op.add_column('pois', sa.Column('quality_issues', postgresql.JSONB(astext_type=sa.Text()), nullable=True, server_default='[]'))
    op.add_column('pois', sa.Column('is_low_quality', sa.Boolean(), nullable=False, server_default=sa.false()))

    # Create index on is_low_quality for efficient filtering
    op.create_index('idx_pois_is_low_quality', 'pois', ['is_low_quality'], unique=False)


def downgrade() -> None:
    op.drop_index('idx_pois_is_low_quality', table_name='pois')
    op.drop_column('pois', 'is_low_quality')
    op.drop_column('pois', 'quality_issues')
    op.drop_column('pois', 'quality_score')
