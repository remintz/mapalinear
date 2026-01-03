"""add user_id to async_operations

Revision ID: cdcb89268b96
Revises: missing_tags_001
Create Date: 2026-01-03 09:21:48.761403

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'cdcb89268b96'
down_revision: Union[str, None] = 'missing_tags_001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add user_id column to async_operations
    op.add_column('async_operations', sa.Column('user_id', sa.UUID(as_uuid=False), nullable=True))
    op.create_index(op.f('ix_async_operations_user_id'), 'async_operations', ['user_id'], unique=False)
    op.create_foreign_key(
        'fk_async_operations_user_id',
        'async_operations',
        'users',
        ['user_id'],
        ['id'],
        ondelete='SET NULL'
    )


def downgrade() -> None:
    op.drop_constraint('fk_async_operations_user_id', 'async_operations', type_='foreignkey')
    op.drop_index(op.f('ix_async_operations_user_id'), table_name='async_operations')
    op.drop_column('async_operations', 'user_id')
