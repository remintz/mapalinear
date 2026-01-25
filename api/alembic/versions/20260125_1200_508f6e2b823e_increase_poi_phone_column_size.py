"""increase poi phone column size to 200 chars

Revision ID: 508f6e2b823e
Revises: a534469ffcff
Create Date: 2026-01-25 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '508f6e2b823e'
down_revision: Union[str, None] = 'a534469ffcff'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Increase phone column size from 50 to 200 chars to accommodate
    # multiple phone numbers separated by semicolons (common in OSM data)
    op.alter_column('pois', 'phone',
               existing_type=sa.VARCHAR(length=50),
               type_=sa.VARCHAR(length=200),
               existing_nullable=True)


def downgrade() -> None:
    # Note: downgrade may truncate data if phone values exceed 50 chars
    op.alter_column('pois', 'phone',
               existing_type=sa.VARCHAR(length=200),
               type_=sa.VARCHAR(length=50),
               existing_nullable=True)
