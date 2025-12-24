"""add user_maps table and created_by_user_id to maps

Revision ID: shared_maps_001
Revises: 6d5287c4f909
Create Date: 2025-12-24 12:00:00.000000

This migration:
1. Creates user_maps junction table for user-map associations
2. Migrates existing maps.user_id to user_maps entries
3. Adds created_by_user_id column to maps table
4. Removes user_id FK and column from maps table (maps become global)
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


# revision identifiers, used by Alembic.
revision: str = 'shared_maps_001'
down_revision: Union[str, None] = '6d5287c4f909'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create user_maps junction table
    op.create_table('user_maps',
        sa.Column('id', UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', UUID(as_uuid=True), nullable=False),
        sa.Column('map_id', UUID(as_uuid=True), nullable=False),
        sa.Column('added_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('is_creator', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['map_id'], ['maps.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'map_id', name='uq_user_map')
    )
    op.create_index('idx_user_maps_user_id', 'user_maps', ['user_id'], unique=False)
    op.create_index('idx_user_maps_map_id', 'user_maps', ['map_id'], unique=False)

    # 2. Migrate existing maps.user_id to user_maps entries
    op.execute("""
        INSERT INTO user_maps (id, user_id, map_id, is_creator, added_at)
        SELECT gen_random_uuid(), user_id, id, true, created_at
        FROM maps
        WHERE user_id IS NOT NULL
    """)

    # 3. Add created_by_user_id column to maps table
    op.add_column('maps', sa.Column('created_by_user_id', UUID(as_uuid=True), nullable=True))
    op.create_foreign_key(
        'fk_maps_created_by_user_id',
        'maps', 'users',
        ['created_by_user_id'], ['id'],
        ondelete='SET NULL'
    )

    # 4. Copy user_id to created_by_user_id for audit trail
    op.execute("UPDATE maps SET created_by_user_id = user_id WHERE user_id IS NOT NULL")

    # 5. Remove user_id FK and column from maps table
    op.drop_constraint('maps_user_id_fkey', 'maps', type_='foreignkey')
    op.drop_index('ix_maps_user_id', table_name='maps')
    op.drop_column('maps', 'user_id')


def downgrade() -> None:
    # 1. Re-add user_id column to maps table
    op.add_column('maps', sa.Column('user_id', UUID(as_uuid=True), nullable=True))
    op.create_index('ix_maps_user_id', 'maps', ['user_id'], unique=False)
    op.create_foreign_key(
        'maps_user_id_fkey',
        'maps', 'users',
        ['user_id'], ['id'],
        ondelete='CASCADE'
    )

    # 2. Restore user_id from user_maps (take the creator or first user)
    op.execute("""
        UPDATE maps
        SET user_id = (
            SELECT user_id FROM user_maps
            WHERE user_maps.map_id = maps.id
            ORDER BY is_creator DESC, added_at ASC
            LIMIT 1
        )
    """)

    # 3. Remove created_by_user_id column
    op.drop_constraint('fk_maps_created_by_user_id', 'maps', type_='foreignkey')
    op.drop_column('maps', 'created_by_user_id')

    # 4. Drop user_maps table
    op.drop_index('idx_user_maps_map_id', table_name='user_maps')
    op.drop_index('idx_user_maps_user_id', table_name='user_maps')
    op.drop_table('user_maps')
