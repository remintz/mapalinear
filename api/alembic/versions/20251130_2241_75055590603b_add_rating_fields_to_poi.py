"""add_rating_fields_to_poi

Revision ID: 75055590603b
Revises: 57b038ef1196
Create Date: 2025-11-30 22:41:31.746072

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '75055590603b'
down_revision: Union[str, None] = '57b038ef1196'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add Google rating fields to POIs table
    op.add_column('pois', sa.Column('rating', sa.Float(), nullable=True))
    op.add_column('pois', sa.Column('rating_count', sa.Integer(), nullable=True))
    op.add_column('pois', sa.Column('google_maps_uri', sa.String(length=500), nullable=True))

    # Remove unused cache_stats table
    op.drop_table('cache_stats')


def downgrade() -> None:
    # Remove Google rating fields from POIs table
    op.drop_column('pois', 'google_maps_uri')
    op.drop_column('pois', 'rating_count')
    op.drop_column('pois', 'rating')

    # Recreate cache_stats table
    op.create_table('cache_stats',
        sa.Column('id', sa.INTEGER(), autoincrement=True, nullable=False),
        sa.Column('recorded_at', sa.TIMESTAMP(), server_default=sa.text('now()'), nullable=False),
        sa.Column('total_entries', sa.INTEGER(), nullable=False),
        sa.Column('hits', sa.INTEGER(), nullable=False),
        sa.Column('misses', sa.INTEGER(), nullable=False),
        sa.Column('sets', sa.INTEGER(), nullable=False),
        sa.Column('evictions', sa.INTEGER(), nullable=False),
        sa.Column('hit_rate_percent', sa.NUMERIC(precision=5, scale=2), nullable=False),
        sa.PrimaryKeyConstraint('id', name='cache_stats_pkey')
    )
