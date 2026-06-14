# -*- coding: utf-8 -*-
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class CampaignRecord(Base):
    __tablename__ = "campaigns"

    campaign_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    product_name: Mapped[str] = mapped_column(String(120), nullable=False)
    category: Mapped[str] = mapped_column(String(80), nullable=False)
    target_market: Mapped[str] = mapped_column(String(80), nullable=False)
    detailed_marketing_requirements: Mapped[str | None] = mapped_column(Text, nullable=True)
    create_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    jobs: Mapped[list["JobRecord"]] = relationship(back_populates="campaign")
    snapshots: Mapped[list["InfluencerSnapshotRecord"]] = relationship(back_populates="campaign")
    results: Mapped[list["RecommendationResultRecord"]] = relationship(back_populates="campaign")


class JobRecord(Base):
    __tablename__ = "jobs"

    task_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    campaign_id: Mapped[str] = mapped_column(ForeignKey("campaigns.campaign_id"), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="PENDING")
    progress: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    stage: Mapped[str | None] = mapped_column(String(120), nullable=True)
    start_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finish_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    campaign: Mapped[CampaignRecord] = relationship(back_populates="jobs")


class InfluencerSnapshotRecord(Base):
    __tablename__ = "influencer_snapshots"
    __table_args__ = (UniqueConstraint("campaign_id", "influencer_id", name="uq_snapshot_campaign_influencer"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    campaign_id: Mapped[str] = mapped_column(ForeignKey("campaigns.campaign_id"), nullable=False, index=True)
    influencer_id: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    username: Mapped[str] = mapped_column(String(120), nullable=False)
    platform: Mapped[str] = mapped_column(String(40), nullable=False)
    followers: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    country: Mapped[str | None] = mapped_column(String(80), nullable=True)
    category: Mapped[str | None] = mapped_column(String(120), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    campaign: Mapped[CampaignRecord] = relationship(back_populates="snapshots")


class RecommendationResultRecord(Base):
    __tablename__ = "recommendation_results"
    __table_args__ = (UniqueConstraint("campaign_id", "influencer_id", name="uq_result_campaign_influencer"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    campaign_id: Mapped[str] = mapped_column(ForeignKey("campaigns.campaign_id"), nullable=False, index=True)
    influencer_id: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    rank: Mapped[int] = mapped_column(Integer, nullable=False)
    total_score: Mapped[int] = mapped_column(Integer, nullable=False)
    semantic_score: Mapped[int] = mapped_column(Integer, nullable=False)
    category_score: Mapped[int] = mapped_column(Integer, nullable=False)
    market_score: Mapped[int] = mapped_column(Integer, nullable=False)
    audience_score: Mapped[int] = mapped_column(Integer, nullable=False)
    activity_score: Mapped[int] = mapped_column(Integer, nullable=False)
    recommendation_reason: Mapped[str] = mapped_column(Text, nullable=False)
    outreach_cn: Mapped[str | None] = mapped_column(Text, nullable=True)
    outreach_en: Mapped[str | None] = mapped_column(Text, nullable=True)

    campaign: Mapped[CampaignRecord] = relationship(back_populates="results")
