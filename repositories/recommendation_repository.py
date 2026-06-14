# -*- coding: utf-8 -*-
from sqlalchemy import delete
from sqlalchemy.orm import Session

from core.schemas import CampaignMatchResponse, CampaignMatchItem, OutreachBundle
from models.persistence import InfluencerSnapshotRecord, RecommendationResultRecord


class RecommendationResultRepository:
    def __init__(self, db: Session):
        self.db = db

    def save_match_response(self, campaign_id: str, response: CampaignMatchResponse) -> None:
        self.db.execute(
            delete(RecommendationResultRecord).where(RecommendationResultRecord.campaign_id == campaign_id)
        )
        self.db.execute(
            delete(InfluencerSnapshotRecord).where(InfluencerSnapshotRecord.campaign_id == campaign_id)
        )
        for item in response.results:
            self._save_snapshot(campaign_id, item)
            self._save_result(campaign_id, item)
        self.db.flush()

    def _save_snapshot(self, campaign_id: str, item: CampaignMatchItem) -> None:
        influencer = item.influencer
        self.db.add(
            InfluencerSnapshotRecord(
                campaign_id=campaign_id,
                influencer_id=influencer.id,
                username=influencer.username,
                platform=influencer.platform.value,
                followers=influencer.followers,
                country=influencer.country,
                category=influencer.category,
                description=influencer.description,
            )
        )

    def _save_result(self, campaign_id: str, item: CampaignMatchItem) -> None:
        breakdown = item.breakdown
        self.db.add(
            RecommendationResultRecord(
                campaign_id=campaign_id,
                influencer_id=item.influencer.id,
                rank=item.rank,
                total_score=item.score,
                semantic_score=breakdown.semantic_match,
                category_score=breakdown.category_match,
                market_score=breakdown.market_match,
                audience_score=breakdown.audience_size_fit,
                activity_score=breakdown.activity_score,
                recommendation_reason=item.recommendation_reason,
                outreach_cn=_format_outreach(item.outreach, "zh"),
                outreach_en=_format_outreach(item.outreach, "en"),
            )
        )


def _format_outreach(outreach: OutreachBundle | None, language: str) -> str | None:
    if outreach is None:
        return None
    letter = outreach.zh if language == "zh" else outreach.en
    return f"Subject: {letter.subject}\nBody: {letter.body}"
