"""add application_logs table for database logging

Revision ID: 4bbb723f56c8
Revises: 8873067d696c
Create Date: 2026-01-03 17:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "4bbb723f56c8"
down_revision: Union[str, None] = "8873067d696c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create application_logs table
    op.create_table(
        "application_logs",
        sa.Column("id", sa.UUID(as_uuid=False), nullable=False),
        sa.Column("timestamp", sa.DateTime(), nullable=False),
        sa.Column("level", sa.String(length=20), nullable=False),
        sa.Column("level_no", sa.Integer(), nullable=False),
        sa.Column("module", sa.String(length=255), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("request_id", sa.String(length=16), nullable=True),
        sa.Column("session_id", sa.String(length=36), nullable=True),
        sa.Column("user_id", sa.UUID(as_uuid=False), nullable=True),
        sa.Column("func_name", sa.String(length=255), nullable=True),
        sa.Column("line_no", sa.Integer(), nullable=True),
        sa.Column("exc_info", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    # Single column indexes
    op.create_index(
        op.f("ix_application_logs_timestamp"), "application_logs", ["timestamp"]
    )
    op.create_index(op.f("ix_application_logs_level"), "application_logs", ["level"])
    op.create_index(
        op.f("ix_application_logs_level_no"), "application_logs", ["level_no"]
    )
    op.create_index(op.f("ix_application_logs_module"), "application_logs", ["module"])
    op.create_index(
        op.f("ix_application_logs_request_id"), "application_logs", ["request_id"]
    )
    op.create_index(
        op.f("ix_application_logs_session_id"), "application_logs", ["session_id"]
    )
    op.create_index(
        op.f("ix_application_logs_user_id"), "application_logs", ["user_id"]
    )

    # Composite indexes for common query patterns
    op.create_index(
        "idx_app_log_timestamp_level",
        "application_logs",
        ["timestamp", "level_no"],
    )
    op.create_index(
        "idx_app_log_module_timestamp",
        "application_logs",
        ["module", "timestamp"],
    )
    op.create_index(
        "idx_app_log_user_timestamp",
        "application_logs",
        ["user_id", "timestamp"],
    )
    op.create_index(
        "idx_app_log_session_timestamp",
        "application_logs",
        ["session_id", "timestamp"],
    )
    op.create_index(
        "idx_app_log_request_timestamp",
        "application_logs",
        ["request_id", "timestamp"],
    )


def downgrade() -> None:
    # Drop composite indexes
    op.drop_index("idx_app_log_request_timestamp", table_name="application_logs")
    op.drop_index("idx_app_log_session_timestamp", table_name="application_logs")
    op.drop_index("idx_app_log_user_timestamp", table_name="application_logs")
    op.drop_index("idx_app_log_module_timestamp", table_name="application_logs")
    op.drop_index("idx_app_log_timestamp_level", table_name="application_logs")

    # Drop single column indexes
    op.drop_index(op.f("ix_application_logs_user_id"), table_name="application_logs")
    op.drop_index(op.f("ix_application_logs_session_id"), table_name="application_logs")
    op.drop_index(op.f("ix_application_logs_request_id"), table_name="application_logs")
    op.drop_index(op.f("ix_application_logs_module"), table_name="application_logs")
    op.drop_index(op.f("ix_application_logs_level_no"), table_name="application_logs")
    op.drop_index(op.f("ix_application_logs_level"), table_name="application_logs")
    op.drop_index(op.f("ix_application_logs_timestamp"), table_name="application_logs")

    # Drop table
    op.drop_table("application_logs")
