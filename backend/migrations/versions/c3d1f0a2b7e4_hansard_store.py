"""Hansard store: sources, sitting_days, documents, speeches (+ FTS5)

Revision ID: c3d1f0a2b7e4
Revises: ba7bb0c81405
Create Date: 2026-10-31 04:00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'c3d1f0a2b7e4'
down_revision: Union[str, Sequence[str], None] = 'ba7bb0c81405'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('sources',
    sa.Column('id', sa.String(length=16), nullable=False),
    sa.Column('parliament', sa.String(length=8), nullable=False),
    sa.Column('chamber', sa.String(length=64), nullable=False),
    sa.Column('connector', sa.String(length=32), nullable=False),
    sa.Column('enabled', sa.Boolean(), nullable=False),
    sa.Column('status', sa.String(length=16), nullable=False),
    sa.Column('last_checked_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('last_success_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('watermark_date', sa.Date(), nullable=True),
    sa.Column('notes', sa.Text(), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('sitting_days',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('source_id', sa.String(length=16), nullable=False),
    sa.Column('sitting_date', sa.Date(), nullable=False),
    sa.Column('discovered_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('version', sa.String(length=8), nullable=False),
    sa.Column('status', sa.String(length=16), nullable=False),
    sa.ForeignKeyConstraint(['source_id'], ['sources.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('source_id', 'sitting_date')
    )
    op.create_table('documents',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('sitting_day_id', sa.Integer(), nullable=False),
    sa.Column('url', sa.Text(), nullable=False),
    sa.Column('format', sa.String(length=8), nullable=False),
    sa.Column('version', sa.String(length=8), nullable=False),
    sa.Column('etag', sa.String(length=256), nullable=True),
    sa.Column('last_modified', sa.String(length=64), nullable=True),
    sa.Column('sha256', sa.String(length=64), nullable=False),
    sa.Column('raw_path', sa.Text(), nullable=False),
    sa.Column('fetched_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('superseded_by', sa.Integer(), nullable=True),
    sa.Column('origin', sa.String(length=8), nullable=False),
    sa.ForeignKeyConstraint(['sitting_day_id'], ['sitting_days.id'], ),
    sa.ForeignKeyConstraint(['superseded_by'], ['documents.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('speeches',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('document_id', sa.Integer(), nullable=False),
    sa.Column('seq', sa.Integer(), nullable=False),
    sa.Column('debate_title', sa.Text(), nullable=True),
    sa.Column('proceeding_type', sa.String(length=64), nullable=True),
    sa.Column('speaker_name', sa.String(length=128), nullable=True),
    sa.Column('speaker_role', sa.String(length=128), nullable=True),
    sa.Column('party', sa.String(length=32), nullable=True),
    sa.Column('speaker_side', sa.String(length=16), nullable=True),
    sa.Column('electorate', sa.String(length=64), nullable=True),
    sa.Column('start_time', sa.String(length=16), nullable=True),
    sa.Column('page', sa.String(length=16), nullable=True),
    sa.Column('anchor_url', sa.Text(), nullable=True),
    sa.Column('text', sa.Text(), nullable=False),
    sa.Column('text_sha256', sa.String(length=64), nullable=False),
    sa.ForeignKeyConstraint(['document_id'], ['documents.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_speeches_text_sha256'), 'speeches', ['text_sha256'], unique=False)

    if op.get_bind().dialect.name == "sqlite":
        # Full-text search over all stored Hansard (Explore, §10.3), kept in sync by triggers.
        op.execute("CREATE VIRTUAL TABLE speeches_fts USING fts5("
                   "text, debate_title, speaker_name, content='speeches', content_rowid='id')")
        op.execute("CREATE TRIGGER speeches_ai AFTER INSERT ON speeches BEGIN "
                   "INSERT INTO speeches_fts(rowid, text, debate_title, speaker_name) "
                   "VALUES (new.id, new.text, new.debate_title, new.speaker_name); END")
        op.execute("CREATE TRIGGER speeches_ad AFTER DELETE ON speeches BEGIN "
                   "INSERT INTO speeches_fts(speeches_fts, rowid, text, debate_title, speaker_name) "
                   "VALUES ('delete', old.id, old.text, old.debate_title, old.speaker_name); END")
        op.execute("CREATE TRIGGER speeches_au AFTER UPDATE ON speeches BEGIN "
                   "INSERT INTO speeches_fts(speeches_fts, rowid, text, debate_title, speaker_name) "
                   "VALUES ('delete', old.id, old.text, old.debate_title, old.speaker_name); "
                   "INSERT INTO speeches_fts(rowid, text, debate_title, speaker_name) "
                   "VALUES (new.id, new.text, new.debate_title, new.speaker_name); END")


def downgrade() -> None:
    if op.get_bind().dialect.name == "sqlite":
        for t in ("speeches_ai", "speeches_ad", "speeches_au"):
            op.execute(f"DROP TRIGGER IF EXISTS {t}")
        op.execute("DROP TABLE IF EXISTS speeches_fts")
    op.drop_index(op.f('ix_speeches_text_sha256'), table_name='speeches')
    op.drop_table('speeches')
    op.drop_table('documents')
    op.drop_table('sitting_days')
    op.drop_table('sources')
