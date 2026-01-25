"""drop_gps_debug_logs_table

Revision ID: 8b29bd5d5196
Revises: 508f6e2b823e
Create Date: 2026-01-25 18:00:35.889204

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '8b29bd5d5196'
down_revision: Union[str, None] = '508f6e2b823e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Drop indexes first
    op.drop_index(op.f('ix_gps_debug_logs_user_id'), table_name='gps_debug_logs')
    op.drop_index(op.f('ix_gps_debug_logs_user_email'), table_name='gps_debug_logs')
    op.drop_index(op.f('ix_gps_debug_logs_session_id'), table_name='gps_debug_logs')
    op.drop_index(op.f('ix_gps_debug_logs_map_id'), table_name='gps_debug_logs')
    op.drop_index(op.f('ix_gps_debug_logs_created_at'), table_name='gps_debug_logs')
    op.drop_index('idx_gps_debug_user_created', table_name='gps_debug_logs')
    op.drop_index('idx_gps_debug_map_created', table_name='gps_debug_logs')
    op.drop_index('idx_gps_debug_coords', table_name='gps_debug_logs')
    # Drop table
    op.drop_table('gps_debug_logs')


def downgrade() -> None:
    # Recreate the table
    op.create_table('gps_debug_logs',
    sa.Column('id', sa.UUID(as_uuid=False), nullable=False),
    sa.Column('created_at', postgresql.TIMESTAMP(timezone=True), nullable=False),
    sa.Column('user_id', sa.UUID(as_uuid=False), nullable=False),
    sa.Column('user_email', sa.String(length=320), nullable=False),
    sa.Column('map_id', sa.UUID(as_uuid=False), nullable=False),
    sa.Column('map_origin', sa.String(length=500), nullable=False),
    sa.Column('map_destination', sa.String(length=500), nullable=False),
    sa.Column('latitude', sa.Float(), nullable=False),
    sa.Column('longitude', sa.Float(), nullable=False),
    sa.Column('gps_accuracy', sa.Float(), nullable=True),
    sa.Column('distance_from_origin_km', sa.Float(), nullable=True),
    sa.Column('is_on_route', sa.Boolean(), nullable=False),
    sa.Column('distance_to_route_m', sa.Float(), nullable=True),
    sa.Column('previous_pois', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('next_pois', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('session_id', sa.String(length=36), nullable=True),
    sa.Column('user_agent', sa.String(length=500), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    # Recreate indexes
    op.create_index('idx_gps_debug_coords', 'gps_debug_logs', ['latitude', 'longitude'], unique=False)
    op.create_index('idx_gps_debug_map_created', 'gps_debug_logs', ['map_id', 'created_at'], unique=False)
    op.create_index('idx_gps_debug_user_created', 'gps_debug_logs', ['user_id', 'created_at'], unique=False)
    op.create_index(op.f('ix_gps_debug_logs_created_at'), 'gps_debug_logs', ['created_at'], unique=False)
    op.create_index(op.f('ix_gps_debug_logs_map_id'), 'gps_debug_logs', ['map_id'], unique=False)
    op.create_index(op.f('ix_gps_debug_logs_session_id'), 'gps_debug_logs', ['session_id'], unique=False)
    op.create_index(op.f('ix_gps_debug_logs_user_email'), 'gps_debug_logs', ['user_email'], unique=False)
    op.create_index(op.f('ix_gps_debug_logs_user_id'), 'gps_debug_logs', ['user_id'], unique=False)
