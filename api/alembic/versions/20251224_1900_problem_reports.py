"""add problem reports system

Revision ID: problem_reports_001
Revises: 833e594c7a29
Create Date: 2025-12-24 19:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'problem_reports_001'
down_revision: Union[str, None] = '833e594c7a29'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Problem Types table
    op.create_table(
        'problem_types',
        sa.Column('id', sa.UUID(), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('sort_order', sa.Integer(), nullable=False, server_default=sa.text('0')),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name')
    )

    # Problem Reports table
    op.create_table(
        'problem_reports',
        sa.Column('id', sa.UUID(), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('status', sa.String(length=20), nullable=False, server_default=sa.text("'nova'")),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('latitude', sa.Float(), nullable=False),
        sa.Column('longitude', sa.Float(), nullable=False),
        sa.Column('problem_type_id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('map_id', sa.UUID(), nullable=True),
        sa.Column('poi_id', sa.UUID(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['problem_type_id'], ['problem_types.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['map_id'], ['maps.id'], ),
        sa.ForeignKeyConstraint(['poi_id'], ['pois.id'], ),
    )
    op.create_index('idx_problem_reports_status', 'problem_reports', ['status'])
    op.create_index('idx_problem_reports_created_at', 'problem_reports', [sa.text('created_at DESC')])

    # Report Attachments table (files stored as BYTEA)
    op.create_table(
        'report_attachments',
        sa.Column('id', sa.UUID(), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('report_id', sa.UUID(), nullable=False),
        sa.Column('type', sa.String(length=20), nullable=False),
        sa.Column('filename', sa.String(length=255), nullable=False),
        sa.Column('mime_type', sa.String(length=100), nullable=False),
        sa.Column('size_bytes', sa.Integer(), nullable=False),
        sa.Column('data', sa.LargeBinary(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['report_id'], ['problem_reports.id'], ondelete='CASCADE'),
    )
    op.create_index('idx_report_attachments_report_id', 'report_attachments', ['report_id'])

    # Insert default problem types
    op.execute("""
        INSERT INTO problem_types (name, description, sort_order) VALUES
            ('Informação incorreta', 'POI com nome, endereço ou dados incorretos', 1),
            ('POI não existe mais', 'Estabelecimento fechado ou não encontrado', 2),
            ('POI faltando', 'Estabelecimento existe mas não aparece no mapa', 3),
            ('Problema na rota', 'Trecho de rota incorreto ou bloqueado', 4),
            ('Outro', 'Outro tipo de problema', 99)
    """)


def downgrade() -> None:
    op.drop_table('report_attachments')
    op.drop_table('problem_reports')
    op.drop_table('problem_types')
