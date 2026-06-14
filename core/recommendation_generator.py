# -*- coding: utf-8 -*-
from typing import Optional

from core.llm_client import complete
from core.schemas import CampaignRequest, Influencer, ScoreBreakdown, SemanticMatchEvidence


class RecommendationGenerator:
    """基于 Campaign、红人、RAG 证据与评分拆解生成可解释推荐理由。"""

    def generate(
        self,
        campaign: CampaignRequest,
        influencer: Influencer,
        breakdown: ScoreBreakdown,
        semantic: Optional[SemanticMatchEvidence] = None,
    ) -> str:
        prompt = self._build_prompt(campaign, influencer, breakdown, semantic)
        llm_text = complete(prompt, temperature=0.35, max_tokens=700)
        if llm_text:
            return llm_text.strip()
        return self._generate_data_driven_reason(campaign, influencer, breakdown, semantic)

    @staticmethod
    def _build_prompt(
        campaign: CampaignRequest,
        influencer: Influencer,
        breakdown: ScoreBreakdown,
        semantic: Optional[SemanticMatchEvidence],
    ) -> str:
        breakdown_text = "；".join(
            breakdown.format_lines(
                semantic_similarity=semantic.similarity if semantic else None
            )
        )
        rag_block = RecommendationGenerator._rag_block(influencer, semantic, breakdown)
        marketing_req = campaign.detailed_marketing_requirements or "（未填写，使用产品描述作为语义参考）"
        return (
            "你是一名海外红人营销顾问。请根据以下信息，用中文输出 4-5 条简洁的推荐理由。\n"
            "要求：每条以数字序号开头；必须引用 RAG 召回证据（description/category/匹配主题）；"
            "必须引用语义匹配分数；不得编造互动率或粉丝真实性；不要夹杂英文句子。\n\n"
            f"产品：{campaign.product_name}（{campaign.product_category}）\n"
            f"详细营销要求：{marketing_req}\n"
            f"目标市场：{campaign.target_country}\n"
            f"红人：{influencer.name or influencer.username}（@{influencer.username}）\n"
            f"国家：{influencer.country or '未知'}，分类：{influencer.category}\n"
            f"频道简介：{(influencer.description or '无')[:220]}\n"
            f"{rag_block}\n"
            f"评分拆解：{breakdown_text}"
        )

    @staticmethod
    def _rag_block(
        influencer: Influencer,
        semantic: Optional[SemanticMatchEvidence],
        breakdown: ScoreBreakdown,
    ) -> str:
        if not semantic:
            return "RAG 证据：暂无语义召回结果。"
        evidence_text = "；".join(semantic.evidence) if semantic.evidence else "暂无"
        topics = "、".join(semantic.matched_topics) if semantic.matched_topics else influencer.category
        display = ScoreBreakdown.semantic_display_score(semantic.similarity)
        return (
            f"RAG 召回主题：{topics}\n"
            f"RAG 证据片段：{evidence_text}\n"
            f"语义匹配度：{display}/30"
        )

    @staticmethod
    def _generate_data_driven_reason(
        campaign: CampaignRequest,
        influencer: Influencer,
        breakdown: ScoreBreakdown,
        semantic: Optional[SemanticMatchEvidence],
    ) -> str:
        lines = ["推荐原因：", ""]
        marketing_hint = (campaign.detailed_marketing_requirements or campaign.product_description)[:80]
        display_semantic = (
            ScoreBreakdown.semantic_display_score(semantic.similarity) if semantic else breakdown.semantic_match
        )
        category_label = influencer.category or "未知类别"
        desc_snippet = (influencer.description or "").strip()[:100]

        if semantic and semantic.matched_topics:
            topics = "、".join(semantic.matched_topics[:4])
            lines.append(
                f"1. 该达人内容长期聚焦「{category_label}」与「{topics}」，"
                f"与商家要求的「{marketing_hint}…」高度相关。"
            )
        elif influencer.category:
            lines.append(
                f"1. 该达人内容长期聚焦「{category_label}」，"
                f"与商家要求的「{campaign.product_category}」及「{marketing_hint}…」存在明确关联。"
            )

        if semantic and semantic.evidence:
            evidence = semantic.evidence[0][:120]
            lines.append(f"2. RAG 召回证据：{evidence}")
        elif desc_snippet:
            lines.append(f"2. 频道简介显示：{desc_snippet}…")

        lines.append(
            f"3. 语义匹配度 {display_semantic}/30，"
            f"内容类别 {breakdown.category_match}/30，目标市场 {breakdown.market_match}/20。"
        )

        if breakdown.audience_size_fit >= 10:
            lines.append(
                f"4. 粉丝量 {influencer.followers:,} 符合目标区间 "
                f"{campaign.min_followers:,}–{campaign.max_followers:,}（{breakdown.audience_size_fit}/15）。"
            )
        else:
            lines.append(
                f"4. 粉丝量 {influencer.followers:,}，接近 Campaign 设定区间（{breakdown.audience_size_fit}/15）。"
            )

        country_text = influencer.country or "未标注"
        activity_parts = []
        if influencer.total_posts is not None:
            activity_parts.append(f"{influencer.total_posts:,} 个作品")
        if influencer.total_views is not None:
            activity_parts.append(f"{influencer.total_views:,} 次浏览")
        activity_text = "、".join(activity_parts) if activity_parts else "持续更新内容"
        lines.append(
            f"5. 达人位于 {country_text}，频道活跃度 {breakdown.activity_score}/10（{activity_text}），适合品牌合作沟通。"
        )
        return "\n".join(lines)

