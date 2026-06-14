# -*- coding: utf-8 -*-
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from core.schemas import CampaignRequest
from models.persistence import CampaignRecord, RecommendationResultRecord, InfluencerSnapshotRecord


class CampaignRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, campaign: CampaignRequest, campaign_id: str | None = None) -> CampaignRecord:
        record = CampaignRecord(
            campaign_id=campaign_id or str(uuid4()),
            product_name=campaign.product_name,
            category=campaign.product_category,
            target_market=campaign.target_country,
            detailed_marketing_requirements=campaign.detailed_marketing_requirements,
        )
        self.db.add(record)
        self.db.flush()
        return record

    def list(self, limit: int = 50, offset: int = 0) -> list[CampaignRecord]:
        stmt = (
            select(CampaignRecord)
            .order_by(CampaignRecord.create_time.desc())
            .offset(offset)
            .limit(limit)
        )
        return list(self.db.scalars(stmt).all())

    def get(self, campaign_id: str) -> CampaignRecord | None:
        return self.db.get(CampaignRecord, campaign_id)

    def get_detail(self, campaign_id: str) -> dict | None:
        campaign = self.get(campaign_id)
        if campaign is None:
            return None

        results_stmt = (
            select(RecommendationResultRecord)
            .where(RecommendationResultRecord.campaign_id == campaign_id)
            .order_by(RecommendationResultRecord.rank.asc())
        )
        snapshots_stmt = select(InfluencerSnapshotRecord).where(
            InfluencerSnapshotRecord.campaign_id == campaign_id
        )
        snapshots = {item.influencer_id: item for item in self.db.scalars(snapshots_stmt).all()}

        return {
            "campaign": serialize_campaign(campaign),
            "results": [
                serialize_result(result, snapshots.get(result.influencer_id))
                for result in self.db.scalars(results_stmt).all()
            ],
        }


def serialize_campaign(record: CampaignRecord) -> dict:
    return {
        "campaign_id": record.campaign_id,
        "product_name": record.product_name,
        "category": record.category,
        "target_market": record.target_market,
        "detailed_marketing_requirements": record.detailed_marketing_requirements,
        "create_time": record.create_time.isoformat() if record.create_time else None,
    }


def serialize_result(result: RecommendationResultRecord, snapshot: InfluencerSnapshotRecord | None) -> dict:
    return {
        "influencer": serialize_snapshot(snapshot) if snapshot else {"influencer_id": result.influencer_id},
        "rank": result.rank,
        "total_score": result.total_score,
        "semantic_score": result.semantic_score,
        "category_score": result.category_score,
        "market_score": result.market_score,
        "audience_score": result.audience_score,
        "activity_score": result.activity_score,
        "recommendation_reason": result.recommendation_reason,
        "outreach_cn": result.outreach_cn,
        "outreach_en": result.outreach_en,
    }


def serialize_snapshot(record: InfluencerSnapshotRecord) -> dict:
    return {
        "influencer_id": record.influencer_id,
        "username": record.username,
        "platform": record.platform,
        "followers": record.followers,
        "country": record.country,
        "category": record.category,
        "description": record.description,
    }

