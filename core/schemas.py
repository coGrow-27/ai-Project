# -*- coding: utf-8 -*-
from enum import Enum
from typing import ClassVar, Dict, List, Optional

from pydantic import BaseModel, Field, computed_field, model_validator


class Platform(str, Enum):
    tiktok = "TikTok"
    instagram = "Instagram"
    youtube = "YouTube"


class CampaignRequest(BaseModel):
    product_name: str = Field(..., min_length=1, max_length=120)
    product_category: str = Field(..., min_length=1, max_length=80)
    product_description: str = Field(..., min_length=10, max_length=2000)
    target_country: str = Field(..., min_length=2, max_length=80)
    target_language: str = Field(..., min_length=2, max_length=80)
    platforms: List[Platform] = Field(..., min_length=1)
    min_followers: int = Field(..., ge=0)
    max_followers: int = Field(..., ge=1)
    min_engagement_rate: float = Field(..., ge=0, le=1)
    influencer_category: str = Field(..., min_length=1, max_length=80)
    campaign_budget: float = Field(..., ge=0)
    detailed_marketing_requirements: Optional[str] = Field(
        default=None,
        max_length=2000,
        description="详细营销要求（中文自然语言），专用于 RAG 语义匹配，不参与传统筛选。",
    )

    @model_validator(mode="after")
    def validate_follower_range(self) -> "CampaignRequest":
        if self.max_followers < self.min_followers:
            raise ValueError("max_followers 必须大于或等于 min_followers。")
        return self

    model_config = {
        "json_schema_extra": {
            "example": {
                "product_name": "Gentle Cat Hair Remover Brush",
                "product_category": "Pet Care",
                "product_description": "一款适合猫咪和小型犬的温和去毛梳，支持一键清理浮毛。",
                "target_country": "US",
                "target_language": "English",
                "platforms": ["TikTok", "Instagram"],
                "min_followers": 10000,
                "max_followers": 80000,
                "min_engagement_rate": 0.03,
                "influencer_category": "Pet Care",
                "campaign_budget": 5000,
            }
        }
    }


class RecentPost(BaseModel):
    title: str
    caption: str
    likes: Optional[int] = None
    comments: Optional[int] = None
    url: Optional[str] = None


class Influencer(BaseModel):
    id: str
    name: str = ""
    username: str
    platform: Platform
    followers: int
    country: Optional[str] = None
    category: str = ""
    description: Optional[str] = None
    url: Optional[str] = None
    profile_img: Optional[str] = None
    total_views: Optional[int] = None
    total_posts: Optional[int] = None
    language: Optional[str] = None
    engagement_rate: Optional[float] = Field(default=None, ge=0, le=1)
    avg_likes: Optional[int] = None
    avg_comments: Optional[int] = None
    audience_countries: Optional[Dict[str, float]] = None
    audience_gender: Optional[Dict[str, float]] = None
    audience_age: Optional[Dict[str, float]] = None
    recent_posts: List[RecentPost] = Field(default_factory=list)
    comment_quality: Optional[float] = Field(default=None, ge=0, le=1)
    authenticity_score: Optional[float] = Field(default=None, ge=0, le=1)
    audience_fit_score: Optional[float] = Field(default=None, ge=0, le=1)

    @computed_field
    @property
    def avatar_url(self) -> str:
        if self.profile_img:
            return self.profile_img
        return f"https://api.dicebear.com/8.x/initials/svg?seed={self.username}"


class ScoreBreakdown(BaseModel):
    semantic_match: int = Field(..., ge=0, le=25)
    category_match: int = Field(..., ge=0, le=30)
    market_match: int = Field(..., ge=0, le=20)
    audience_size_fit: int = Field(..., ge=0, le=15)
    activity_score: int = Field(..., ge=0, le=10)

    SEMANTIC_DISPLAY_MAX: ClassVar[int] = 30

    @property
    def total_score(self) -> int:
        return (
            self.semantic_match
            + self.category_match
            + self.market_match
            + self.audience_size_fit
            + self.activity_score
        )

    @staticmethod
    def semantic_display_score(similarity: float) -> int:
        """向量语义相似度映射为 0~25 展示分（用于推荐理由引用）。"""
        ratio = max(0.0, min(1.0, similarity))
        return int(round(ratio * ScoreBreakdown.SEMANTIC_DISPLAY_MAX))

    def format_lines(self, *, semantic_similarity: Optional[float] = None) -> List[str]:
        display = (
            self.semantic_display_score(semantic_similarity)
            if semantic_similarity is not None
            else self.semantic_match
        )
        display_max = self.SEMANTIC_DISPLAY_MAX if semantic_similarity is not None else 25
        return [
            f"语义匹配：{display}/{display_max}",
            f"内容类别：{self.category_match}/30",
            f"目标市场：{self.market_match}/20",
            f"粉丝规模：{self.audience_size_fit}/15",
            f"内容活跃：{self.activity_score}/10",
        ]

    def format_summary(self) -> str:
        return " · ".join(self.format_lines())


class SemanticMatchEvidence(BaseModel):
    influencer_id: str
    similarity: float = Field(..., ge=0.0, le=1.0)
    evidence: List[str] = Field(default_factory=list)
    matched_topics: List[str] = Field(default_factory=list)


class ScoredInfluencer(BaseModel):
    rank: int
    avatar_url: str
    username: str
    platform: Platform
    score: int
    breakdown: ScoreBreakdown
    recommendation_reason: str
    influencer: Influencer


class OutreachLetter(BaseModel):
    subject: str
    body: str


class OutreachBundle(BaseModel):
    zh: OutreachLetter
    en: OutreachLetter


class CampaignMatchItem(ScoredInfluencer):
    detail_generated: bool = True
    outreach: Optional[OutreachBundle] = None
    rag_evidence: Optional[List[str]] = None
    semantic_similarity: Optional[float] = None


class CampaignMatchResponse(BaseModel):
    campaign: CampaignRequest
    total_candidates: int
    content_top_k: int = 5
    data_source: str = "mock"
    fallback_message: Optional[str] = None
    results: List[CampaignMatchItem]
