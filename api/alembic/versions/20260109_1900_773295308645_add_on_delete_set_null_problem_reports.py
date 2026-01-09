"""add on delete set null to problem_reports map_id fk

Revision ID: 773295308645
Revises: application_logs_timestamp_tz
Create Date: 2026-01-09 19:00:00.000000

Modifies the foreign key constraint on problem_reports.map_id to use
ON DELETE SET NULL, so that when a map is deleted, the map_id in
associated problem reports is automatically set to NULL instead of
causing a foreign key violation.
"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "773295308645"
down_revision: Union[str, None] = "application_logs_timestamp_tz"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Drop the existing foreign key constraint
    op.drop_constraint(
        "problem_reports_map_id_fkey",
        "problem_reports",
        type_="foreignkey"
    )

    # Recreate with ON DELETE SET NULL
    op.create_foreign_key(
        "problem_reports_map_id_fkey",
        "problem_reports",
        "maps",
        ["map_id"],
        ["id"],
        ondelete="SET NULL"
    )


def downgrade() -> None:
    # Drop the constraint with ON DELETE SET NULL
    op.drop_constraint(
        "problem_reports_map_id_fkey",
        "problem_reports",
        type_="foreignkey"
    )

    # Recreate without ON DELETE behavior (default is NO ACTION/RESTRICT)
    op.create_foreign_key(
        "problem_reports_map_id_fkey",
        "problem_reports",
        "maps",
        ["map_id"],
        ["id"]
    )
