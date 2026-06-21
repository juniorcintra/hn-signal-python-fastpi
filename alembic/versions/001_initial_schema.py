"""Initial schema with articles and pipeline_jobs tables

Revision ID: 001
Revises: 
Create Date: 2024-01-01 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'articles',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('hn_id', sa.String(), nullable=False),
        sa.Column('title', sa.String(), nullable=False),
        sa.Column('url', sa.String(), nullable=True),
        sa.Column('points', sa.Integer(), nullable=False),
        sa.Column('comments_count', sa.Integer(), nullable=False),
        sa.Column('author', sa.String(), nullable=False),
        sa.Column('rank', sa.Integer(), nullable=False),
        sa.Column('scraped_at', sa.DateTime(), nullable=False),
        sa.Column('enrichment_status', sa.Enum('pending', 'processing', 'completed', 'failed', name='enrichmentstatus'), nullable=False),
        sa.Column('summary', sa.String(), nullable=True),
        sa.Column('category', sa.String(), nullable=True),
        sa.Column('tags', sa.JSON(), nullable=True),
        sa.Column('technical_level', sa.String(), nullable=True),
        sa.Column('sentiment', sa.String(), nullable=True),
        sa.Column('enriched_at', sa.DateTime(), nullable=True),
        sa.Column('enrichment_error', sa.String(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('hn_id')
    )
    op.create_index('ix_articles_category', 'articles', ['category'])
    op.create_index('ix_articles_enrichment_status', 'articles', ['enrichment_status'])
    op.create_index('ix_articles_hn_id', 'articles', ['hn_id'])

    op.create_table(
        'pipeline_jobs',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('status', sa.Enum('pending', 'running', 'completed', 'failed', name='jobstatus'), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('scraped', sa.Integer(), nullable=False),
        sa.Column('new_items', sa.Integer(), nullable=False),
        sa.Column('enriched', sa.Integer(), nullable=False),
        sa.Column('failed', sa.Integer(), nullable=False),
        sa.Column('error_message', sa.String(), nullable=True),
        sa.Column('job_metadata', sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade() -> None:
    op.drop_table('pipeline_jobs')
    op.drop_index('ix_articles_hn_id', table_name='articles')
    op.drop_index('ix_articles_enrichment_status', table_name='articles')
    op.drop_index('ix_articles_category', table_name='articles')
    op.drop_table('articles')
