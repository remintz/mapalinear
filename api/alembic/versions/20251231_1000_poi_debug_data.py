"""add poi_debug_data table

Revision ID: poi_debug_data_001
Revises: optional_location_001
Create Date: 2025-12-31 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB


# revision identifiers, used by Alembic.
revision: str = 'poi_debug_data_001'
down_revision: Union[str, None] = 'optional_location_001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create poi_debug_data table
    op.create_table(
        'poi_debug_data',
        # Primary key
        sa.Column('id', UUID(as_uuid=True), primary_key=True),

        # Foreign keys
        sa.Column('map_id', UUID(as_uuid=True), sa.ForeignKey('maps.id', ondelete='CASCADE'), nullable=False),
        sa.Column('map_poi_id', UUID(as_uuid=True), sa.ForeignKey('map_pois.id', ondelete='CASCADE'), nullable=False),

        # POI identification
        sa.Column('poi_name', sa.String(500), nullable=False),
        sa.Column('poi_type', sa.String(50), nullable=False),

        # POI location
        sa.Column('poi_lat', sa.Float(), nullable=False),
        sa.Column('poi_lon', sa.Float(), nullable=False),

        # Main route segment (JSONB)
        sa.Column('main_route_segment', JSONB, nullable=True),
        sa.Column('segment_start_idx', sa.Integer(), nullable=True),
        sa.Column('segment_end_idx', sa.Integer(), nullable=True),

        # Junction point
        sa.Column('junction_lat', sa.Float(), nullable=True),
        sa.Column('junction_lon', sa.Float(), nullable=True),
        sa.Column('junction_distance_km', sa.Float(), nullable=True),

        # Access route
        sa.Column('access_route_geometry', JSONB, nullable=True),
        sa.Column('access_route_distance_km', sa.Float(), nullable=True),

        # Calculation details (JSONB)
        sa.Column('side_calculation', JSONB, nullable=True),
        sa.Column('lookback_data', JSONB, nullable=True),
        sa.Column('recalculation_history', JSONB, nullable=True),

        # Final result
        sa.Column('final_side', sa.String(20), nullable=False),
        sa.Column('requires_detour', sa.Boolean(), default=False, nullable=False),
        sa.Column('distance_from_road_m', sa.Float(), nullable=False),

        # Timestamp
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )

    # Create indexes
    op.create_index('idx_poi_debug_map', 'poi_debug_data', ['map_id'])
    op.create_index('idx_poi_debug_map_poi', 'poi_debug_data', ['map_poi_id'])


def downgrade() -> None:
    # Drop indexes
    op.drop_index('idx_poi_debug_map_poi', 'poi_debug_data')
    op.drop_index('idx_poi_debug_map', 'poi_debug_data')

    # Drop table
    op.drop_table('poi_debug_data')
