"""documents.doc_key and speeches.speaker_id

Revision ID: d4e2a1b9c0f5
Revises: c3d1f0a2b7e4
Create Date: 2026-10-31 12:30:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'd4e2a1b9c0f5'
down_revision: Union[str, Sequence[str], None] = 'c3d1f0a2b7e4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('documents') as b:
        b.add_column(sa.Column('doc_key', sa.String(length=128), nullable=True))
        b.create_index('ix_documents_doc_key', ['doc_key'])
    op.execute("UPDATE documents SET doc_key = url WHERE doc_key IS NULL")
    with op.batch_alter_table('speeches') as b:
        b.add_column(sa.Column('speaker_id', sa.String(length=32), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table('speeches') as b:
        b.drop_column('speaker_id')
    with op.batch_alter_table('documents') as b:
        b.drop_index('ix_documents_doc_key')
        b.drop_column('doc_key')
