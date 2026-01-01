"""add_junction_calculation_to_poi_debug_data

Revision ID: 6111984c4d7e
Revises: poi_debug_data_001
Create Date: 2026-01-01 13:55:25.598580

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '6111984c4d7e'
down_revision: Union[str, None] = 'poi_debug_data_001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add junction_calculation JSONB column to poi_debug_data
    op.add_column('poi_debug_data', sa.Column('junction_calculation', postgresql.JSONB(astext_type=sa.Text()), nullable=True))


def downgrade() -> None:
    op.drop_column('poi_debug_data', 'junction_calculation')
