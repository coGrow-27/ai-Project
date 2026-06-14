# -*- coding: utf-8 -*-
from typing import Dict, Optional

from config.settings import settings
from core.campaign_semantic import CampaignSemanticIndex, build_semantic_query
from core.outreach_generator import OutreachGenerator
from core.progress import (
    STAGE_COMPLETED,
    STAGE_FETCHING,
    STAGE_INDEXING,
    STAGE_OUTREACH,
    STAGE_SCORING,
    ProgressCallback,
    emit_progress,
)
from core.providers import InfluencerProvider, get_influencer_provider
from core.recommendation_generator import RecommendationGenerator
from core.schemas import (
    CampaignMatchItem,
    CampaignMatchResponse,
    CampaignRequest,
    Influencer,
    ScoreBreakdown,
    SemanticMatchEvidence,
)
from core.scoring_engine import InfluencerScoringEngine


class CampaignMatcher:
    """Campaign 商业匹配编排：RapidAPI 召回 → RAG 语义索引 → 评分 → Top10 → Top5 文案。"""

    def __init__(
        self,
        provider: Optional[InfluencerProvider] = None,
        scorer: Optional[InfluencerScoringEngine] = None,
        reason_generator: Optional[RecommendationGenerator] = None,
        outreach_generator: Optional[OutreachGenerator] = None,
    ):
        self.provider = provider or get_influencer_provider()
        self.scorer = scorer or InfluencerScoringEngine()
        self.reason_generator = reason_generator or RecommendationGenerator()
        self.outreach_generator = outreach_generator or OutreachGenerator()
        self.top_k = settings.CAMPAIGN_TOP_K
        self.content_top_k = settings.CONTENT_TOP_K

    def match(
        self,
        campaign: CampaignRequest,
        progress_callback: Optional[ProgressCallback] = None,
    ) -> CampaignMatchResponse:
        emit_progress(progress_callback, 10, STAGE_FETCHING, "正在检索海外红人...")
        candidates = self.provider.search(campaign)

        semantic_map: Dict[str, SemanticMatchEvidence] = {}
        semantic_index: Optional[CampaignSemanticIndex] = None
        semantic_query = build_semantic_query(campaign)
        if candidates:
            emit_progress(progress_callback, 30, STAGE_INDEXING, "正在构建语义向量索引...")
            semantic_index = CampaignSemanticIndex()
            try:
                semantic_index.build_from_influencers(candidates)
                semantic_map = semantic_index.score_all(semantic_query)
            finally:
                semantic_index.close()

        emit_progress(progress_callback, 60, STAGE_SCORING, "正在计算匹配评分...")
        ranked: list[tuple[int, ScoreBreakdown, Influencer, Optional[SemanticMatchEvidence]]] = []
        for influencer in candidates:
            semantic = semantic_map.get(influencer.id)
            breakdown = self.scorer.score(campaign, influencer, semantic)
            total = self.scorer.total_score(breakdown)
            ranked.append((total, breakdown, influencer, semantic))

        ranked.sort(key=lambda item: item[0], reverse=True)
        top_slice = ranked[: self.top_k]

        results: list[CampaignMatchItem] = []
        for index, (total, breakdown, influencer, semantic) in enumerate(top_slice, start=1):
            detail_generated = index <= self.content_top_k
            rag_evidence = semantic.evidence if semantic else None
            semantic_similarity = semantic.similarity if semantic else None

            if detail_generated:
                emit_progress(
                    progress_callback,
                    90,
                    STAGE_OUTREACH,
                    f"正在生成 Top {index} 推荐理由与邀约信...",
                )
                recommendation = self.reason_generator.generate(
                    campaign, influencer, breakdown, semantic=semantic
                )
                outreach = self.outreach_generator.generate(
                    campaign, influencer, breakdown, semantic=semantic
                )
            else:
                recommendation = self._summary_reason(total, breakdown)
                outreach = None

            results.append(
                CampaignMatchItem(
                    rank=index,
                    avatar_url=influencer.avatar_url,
                    username=influencer.username,
                    platform=influencer.platform,
                    score=total,
                    breakdown=breakdown,
                    recommendation_reason=recommendation,
                    influencer=influencer,
                    detail_generated=detail_generated,
                    outreach=outreach,
                    rag_evidence=rag_evidence,
                    semantic_similarity=semantic_similarity,
                )
            )

        emit_progress(progress_callback, 100, STAGE_COMPLETED, "任务完成")
        return CampaignMatchResponse(
            campaign=campaign,
            total_candidates=len(candidates),
            content_top_k=self.content_top_k,
            results=results,
        )

    @staticmethod
    def _summary_reason(total: int, breakdown: ScoreBreakdown) -> str:
        return (
            f"综合评分 {total} 分（{breakdown.format_summary()}）。"
            "该红人已进入 Top 10 推荐名单；完整推荐理由与邀约信仅对 Top 5 生成。"
        )
