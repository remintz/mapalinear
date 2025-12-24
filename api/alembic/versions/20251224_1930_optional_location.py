"""make problem report location optional

Revision ID: optional_location_001
Revises: problem_reports_001
Create Date: 2025-12-24 19:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'optional_location_001'
down_revision: Union[str, None] = 'problem_reports_001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Make latitude and longitude nullable
    op.alter_column('problem_reports', 'latitude',
                    existing_type=sa.Float(),
                    nullable=True)
    op.alter_column('problem_reports', 'longitude',
                    existing_type=sa.Float(),
                    nullable=True)


def downgrade() -> None:
    # Make latitude and longitude required again
    op.alter_column('problem_reports', 'longitude',
                    existing_type=sa.Float(),
                    nullable=False)
    op.alter_column('problem_reports', 'latitude',
                    existing_type=sa.Float(),
                    nullable=False)
