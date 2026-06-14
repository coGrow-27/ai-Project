# -*- coding: utf-8 -*-
"""add persistence tables

Revision ID: 20260613_0001
Revises:
Create Date: 2026-06-13
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "20260613_0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "campaigns",
        sa.Column("campaign_id", sa.String(length=36), nullable=False),
        sa.Column("product_name", sa.String(length=120), nullable=False),
        sa.Column("category", sa.String(length=80), nullable=False),
        sa.Column("target_market", sa.String(length=80), nullable=False),
        sa.Column("detailed_marketing_requirements", sa.Text(), nullable=True),
        sa.Column("create_time", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("campaign_id"),
    )

    op.create_table(
        "jobs",
        sa.Column("task_id", sa.String(length=64), nullable=False),
        sa.Column("campaign_id", sa.String(length=36), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("progress", sa.Integer(), nullable=False),
        sa.Column("stage", sa.String(length=120), nullable=True),
        sa.Column("start_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finish_time", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["campaign_id"], ["campaigns.campaign_id"]),
        sa.PrimaryKeyConstraint("task_id"),
    )
    op.create_index("ix_jobs_campaign_id", "jobs", ["campaign_id"])

    op.create_table(
        "influencer_snapshots",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("campaign_id", sa.String(length=36), nullable=False),
        sa.Column("influencer_id", sa.String(length=120), nullable=False),
        sa.Column("username", sa.String(length=120), nullable=False),
        sa.Column("platform", sa.String(length=40), nullable=False),
        sa.Column("followers", sa.Integer(), nullable=False),
        sa.Column("country", sa.String(length=80), nullable=True),
        sa.Column("category", sa.String(length=120), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["campaign_id"], ["campaigns.campaign_id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("campaign_id", "influencer_id", name="uq_snapshot_campaign_influencer"),
    )
    op.create_index("ix_influencer_snapshots_campaign_id", "influencer_snapshots", ["campaign_id"])
    op.create_index("ix_influencer_snapshots_influencer_id", "influencer_snapshots", ["influencer_id"])

    op.create_table(
        "recommendation_results",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("campaign_id", sa.String(length=36), nullable=False),
        sa.Column("influencer_id", sa.String(length=120), nullable=False),
        sa.Column("rank", sa.Integer(), nullable=False),
        sa.Column("total_score", sa.Integer(), nullable=False),
        sa.Column("semantic_score", sa.Integer(), nullable=False),
        sa.Column("category_score", sa.Integer(), nullable=False),
        sa.Column("market_score", sa.Integer(), nullable=False),
        sa.Column("audience_score", sa.Integer(), nullable=False),
        sa.Column("activity_score", sa.Integer(), nullable=False),
        sa.Column("recommendation_reason", sa.Text(), nullable=False),
        sa.Column("outreach_cn", sa.Text(), nullable=True),
        sa.Column("outreach_en", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["campaign_id"], ["campaigns.campaign_id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("campaign_id", "influencer_id", name="uq_result_campaign_influencer"),
    )
    op.create_index("ix_recommendation_results_campaign_id", "recommendation_results", ["campaign_id"])
    op.create_index("ix_recommendation_results_influencer_id", "recommendation_results", ["influencer_id"])


def downgrade() -> None:
    op.drop_index("ix_recommendation_results_influencer_id", table_name="recommendation_results")
    op.drop_index("ix_recommendation_results_campaign_id", table_name="recommendation_results")
    op.drop_table("recommendation_results")
    op.drop_index("ix_influencer_snapshots_influencer_id", table_name="influencer_snapshots")
    op.drop_index("ix_influencer_snapshots_campaign_id", table_name="influencer_snapshots")
    op.drop_table("influencer_snapshots")
    op.drop_index("ix_jobs_campaign_id", table_name="jobs")
    op.drop_table("jobs")
    op.drop_table("campaigns")
