"""add_is_referenced_to_pois

Revision ID: a1b2c3d4e5f6
Revises: 2283f3539ae2
Create Date: 2025-12-14 16:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = '2283f3539ae2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add is_referenced column to pois table
    # This flag indicates if the POI is used in any map
    # POIs with is_referenced=False don't need enrichment
    op.add_column('pois', sa.Column('is_referenced', sa.Boolean(), nullable=True))

    # Set existing POIs that have map_pois relationships as referenced
    # All existing POIs in the database were created through map generation,
    # so they should be marked as referenced
    op.execute("UPDATE pois SET is_referenced = TRUE WHERE is_referenced IS NULL")

    # Make column NOT NULL with default FALSE for new POIs
    op.alter_column('pois', 'is_referenced', nullable=False, server_default='false')

    # Create index for efficient queries on referenced POIs
    op.create_index('idx_pois_is_referenced', 'pois', ['is_referenced'], unique=False)


def downgrade() -> None:
    # Drop index
    op.drop_index('idx_pois_is_referenced', table_name='pois')

    # Drop column
    op.drop_column('pois', 'is_referenced')
