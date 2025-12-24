"""add impersonation_sessions table

Revision ID: impersonation_sessions_001
Revises: shared_maps_001
Create Date: 2025-12-24 16:30:00.000000

This migration creates the impersonation_sessions table for admin user impersonation.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


# revision identifiers, used by Alembic.
revision: str = 'impersonation_sessions_001'
down_revision: Union[str, None] = 'shared_maps_001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('impersonation_sessions',
        sa.Column('id', UUID(as_uuid=True), nullable=False),
        sa.Column('admin_id', UUID(as_uuid=True), nullable=False),
        sa.Column('target_user_id', UUID(as_uuid=True), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['admin_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['target_user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_impersonation_sessions_admin_id', 'impersonation_sessions', ['admin_id'], unique=False)
    op.create_index('ix_impersonation_sessions_target_user_id', 'impersonation_sessions', ['target_user_id'], unique=False)
    op.create_index('ix_impersonation_sessions_is_active', 'impersonation_sessions', ['is_active'], unique=False)
    op.create_index('ix_impersonation_sessions_expires_at', 'impersonation_sessions', ['expires_at'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_impersonation_sessions_expires_at', table_name='impersonation_sessions')
    op.drop_index('ix_impersonation_sessions_is_active', table_name='impersonation_sessions')
    op.drop_index('ix_impersonation_sessions_target_user_id', table_name='impersonation_sessions')
    op.drop_index('ix_impersonation_sessions_admin_id', table_name='impersonation_sessions')
    op.drop_table('impersonation_sessions')
