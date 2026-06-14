# -*- coding: utf-8 -*-
"""Campaign 主链路语义索引：针对当前召回达人构建临时内存向量库。"""
from __future__ import annotations

import logging
import re
from typing import Dict, List, Optional

from core.rag_engine import InfluencerRagEngine
from core.schemas import Influencer, SemanticMatchEvidence
from core.translator import translate_to_english

logger = logging.getLogger("campaign_semantic")


def format_influencer_document(influencer: Influencer) -> str:
    """构造 InfluencerDocument 文本，供 RAG 索引与证据引用。"""
    description = (influencer.description or "").strip()
    lines = [
        f"Creator: {influencer.name or influencer.username}",
        f"Username: @{influencer.username}",
        "",
        "Category:",
        influencer.category or "Unknown",
        "",
        "Country:",
        influencer.country or "Unknown",
        "",
        "Description:",
    ]
    if description:
        for part in description.splitlines():
            text = part.strip()
            if text:
                lines.append(text)
    else:
        lines.append("No channel description available.")
    return "\n".join(lines)


def influencer_to_raw_dict(influencer: Influencer) -> dict:
    return {
        "influencer_id": influencer.id,
        "username": influencer.username,
        "name": influencer.name,
        "region": influencer.country or "",
        "follower_count": influencer.followers,
        "bio": influencer.description or "",
        "style_tags": [influencer.category] if influencer.category else [],
        "document_text": format_influencer_document(influencer),
        "recent_videos": [],
    }


def build_semantic_query(campaign) -> str:
    parts: List[str] = []
    if campaign.detailed_marketing_requirements and campaign.detailed_marketing_requirements.strip():
        parts.append(campaign.detailed_marketing_requirements.strip())
    parts.append(campaign.product_description.strip())
    parts.append(campaign.product_category.strip())
    parts.append(campaign.influencer_category.strip())
    return "\n".join(part for part in parts if part)


def extract_matched_topics(document_text: str, query: str, limit: int = 5) -> List[str]:
    topics: List[str] = []
    doc_lower = document_text.lower()
    for token in InfluencerRagEngine._tokenize(query):
        if len(token) < 3:
            continue
        if token in doc_lower and token not in topics:
            topics.append(token)
    category_match = re.findall(r"Category:\s*(.+)", document_text, flags=re.IGNORECASE)
    for item in category_match:
        value = item.strip()
        if value and value not in topics:
            topics.append(value)
    return topics[:limit]


class CampaignSemanticIndex:
    """针对单次 Campaign 召回达人建立的临时语义索引，任务结束自动释放。"""

    def __init__(self, *, use_mock: Optional[bool] = None):
        self._engine = InfluencerRagEngine(use_mock=use_mock)
        self._influencers: List[Influencer] = []
        self._documents: Dict[str, str] = {}

    def build_from_influencers(self, influencers: List[Influencer]) -> None:
        if not influencers:
            return
        self._influencers = influencers
        raw_items = [influencer_to_raw_dict(item) for item in influencers]
        for item, influencer in zip(raw_items, influencers):
            item["document_text"] = format_influencer_document(influencer)
            self._documents[influencer.id] = item["document_text"]
        self._engine.build_campaign_index(raw_items)
        logger.info("Campaign 语义索引已构建，候选 %s 位。", len(influencers))

    def score_all(self, query: str) -> Dict[str, SemanticMatchEvidence]:
        if not self._influencers or not query.strip():
            return {}
        translated_query = translate_to_english(query)
        combined_query = f"{query}\n{translated_query}".strip()
        raw_scores = self._engine.retrieve_campaign(combined_query, top_k=len(self._influencers))

        results: Dict[str, SemanticMatchEvidence] = {}
        max_score = max((item["score"] for item in raw_scores.values()), default=0.0)
        for influencer in self._influencers:
            payload = raw_scores.get(influencer.id, {"score": 0.0, "evidence": []})
            raw_score = float(payload.get("score", 0.0))
            similarity = raw_score / max_score if max_score > 0 else 0.0
            similarity = max(0.0, min(1.0, similarity))
            doc_text = self._documents.get(influencer.id, "")
            evidence = list(payload.get("evidence") or [])
            if not evidence and influencer.description:
                evidence.append(influencer.description.strip()[:160])
            if not evidence and influencer.category:
                evidence.append(f"Category: {influencer.category}")
            topics = extract_matched_topics(doc_text, combined_query)
            results[influencer.id] = SemanticMatchEvidence(
                influencer_id=influencer.id,
                similarity=round(similarity, 4),
                evidence=evidence[:3],
                matched_topics=topics,
            )
        return results

    def close(self) -> None:
        self._engine.close_campaign_index()
        self._influencers = []
        self._documents = {}
