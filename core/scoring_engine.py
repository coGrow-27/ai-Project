# -*- coding: utf-8 -*-
import math
import re
from typing import Optional, Set

from core.schemas import CampaignRequest, Influencer, ScoreBreakdown, SemanticMatchEvidence
from core.translator import translate_campaign_for_api


class InfluencerScoringEngine:
    """可解释红人评分引擎，总分 100 分。"""
    
    CATEGORY_MAX = 30
    SEMANTIC_MAX = 25
    MARKET_MAX = 20
    AUDIENCE_SIZE_MAX = 15
    ACTIVITY_MAX = 10

    def score(
        self,
        campaign: CampaignRequest,
        influencer: Influencer,
        semantic: Optional[SemanticMatchEvidence] = None,
    ) -> ScoreBreakdown:
        return ScoreBreakdown(
            semantic_match=self._semantic_match(semantic),
            category_match=self._category_match(campaign, influencer),
            market_match=self._market_match(campaign, influencer),
            audience_size_fit=self._audience_size_fit(campaign, influencer),
            activity_score=self._activity_score(influencer),
        )

    @staticmethod
    def total_score(breakdown: ScoreBreakdown) -> int:
        return breakdown.total_score

    @staticmethod
    def _semantic_match(semantic: Optional[SemanticMatchEvidence]) -> int:
        if semantic is None:
            return 0
        ratio = max(0.0, min(1.0, semantic.similarity))
        return int(round(ratio * InfluencerScoringEngine.SEMANTIC_MAX))

    def _category_match(self, campaign: CampaignRequest, influencer: Influencer) -> int:
        english = translate_campaign_for_api(campaign)
        product_terms = self._normalize_terms(english["product_category"])
        product_terms.update(self._normalize_terms(campaign.product_category))
        campaign_terms = self._normalize_terms(english["influencer_category"])
        campaign_terms.update(self._normalize_terms(campaign.influencer_category))
        influencer_terms = self._normalize_terms(influencer.category)

        product_overlap = self._overlap_ratio(product_terms, influencer_terms)
        campaign_overlap = self._overlap_ratio(campaign_terms, influencer_terms)
        raw = 0.55 * product_overlap + 0.45 * campaign_overlap

        if product_terms and product_terms == influencer_terms:
            raw = max(raw, 0.95)
        elif product_overlap >= 0.8 or campaign_overlap >= 0.8:
            raw = max(raw, 0.88)

        return self._to_points(raw, self.CATEGORY_MAX)

    def _market_match(self, campaign: CampaignRequest, influencer: Influencer) -> int:
        target = self._normalize_country(campaign.target_country)
        creator_country = self._normalize_country(influencer.country) if influencer.country else None

        audience_share = 0.0
        if influencer.audience_countries:
            audience_share = self._resolve_audience_share(influencer.audience_countries, target)

        language_bonus = 0.0
        if influencer.language and self._language_matches(campaign.target_language, influencer.language):
            language_bonus = 0.1

        creator_bonus = 0.0
        if creator_country and creator_country == target:
            creator_bonus = 0.35

        if audience_share > 0:
            raw = min(1.0, audience_share + language_bonus + creator_bonus * 0.5)
        elif creator_country:
            raw = min(1.0, creator_bonus + language_bonus)
        else:
            raw = language_bonus * 0.5

        return self._to_points(raw, self.MARKET_MAX)

    def _audience_size_fit(self, campaign: CampaignRequest, influencer: Influencer) -> int:
        followers = influencer.followers
        min_f = campaign.min_followers
        max_f = max(campaign.max_followers, min_f + 1)

        if min_f <= followers <= max_f:
            center = (min_f + max_f) / 2
            half_range = max((max_f - min_f) / 2, 1)
            distance_ratio = abs(followers - center) / half_range
            raw = 1.0 - 0.15 * distance_ratio
            return self._to_points(max(0.82, raw), self.AUDIENCE_SIZE_MAX)

        if followers < min_f:
            ratio = followers / max(min_f, 1)
            raw = math.sqrt(max(ratio, 0.0))
            return self._to_points(raw * 0.85, self.AUDIENCE_SIZE_MAX)

        overshoot = (followers - max_f) / max(max_f, 1)
        raw = max(0.0, 1.0 - min(1.0, overshoot * 1.2))
        return self._to_points(raw * 0.75, self.AUDIENCE_SIZE_MAX)

    def _activity_score(self, influencer: Influencer) -> int:
        posts = influencer.total_posts
        views = influencer.total_views

        if posts is None and views is None:
            if influencer.recent_posts:
                return self._to_points(0.45, self.ACTIVITY_MAX)
            return 0

        post_score = 0.0
        view_score = 0.0

        if posts is not None:
            post_score = min(1.0, posts / 300)
        if views is not None and influencer.followers > 0:
            views_per_follower = views / max(influencer.followers, 1)
            view_score = min(1.0, views_per_follower / 80)

        if posts is None:
            raw = view_score
        elif views is None:
            raw = post_score
        else:
            raw = 0.45 * post_score + 0.55 * view_score

        return self._to_points(raw, self.ACTIVITY_MAX)

    @staticmethod
    def _to_points(ratio: float, maximum: int) -> int:
        clamped = max(0.0, min(1.0, ratio))
        return int(round(clamped * maximum))

    @staticmethod
    def _normalize_country(value: str) -> str:
        aliases = {
            "united states": "US",
            "usa": "US",
            "u.s.": "US",
            "美国": "US",
            "united kingdom": "UK",
            "britain": "UK",
            "英国": "UK",
            "canada": "CA",
            "australia": "AU",
            "germany": "DE",
            "france": "FR",
            "japan": "JP",
            "korea": "KR",
            "singapore": "SG",
            "brazil": "BR",
            "india": "IN",
            "algeria": "DZ",
            "austria": "AT",
        }
        text = value.strip().upper()
        lower = value.strip().lower()
        if len(text) == 2 and text.isalpha():
            return text
        return aliases.get(lower, text)

    @staticmethod
    def _resolve_audience_share(audience_countries: dict, target: str) -> float:
        if target in audience_countries:
            return float(audience_countries[target])
        upper_map = {key.upper(): value for key, value in audience_countries.items()}
        return float(upper_map.get(target, 0.0))

    @staticmethod
    def _language_matches(target_language: str, influencer_language: str) -> bool:
        target = target_language.strip().lower()
        actual = influencer_language.strip().lower()
        if target == actual:
            return True
        aliases = {
            "english": {"english", "en"},
            "chinese": {"chinese", "mandarin", "zh"},
            "german": {"german", "de"},
            "french": {"french", "fr"},
            "japanese": {"japanese", "ja"},
            "korean": {"korean", "ko"},
            "portuguese": {"portuguese", "pt"},
        }
        for canonical, variants in aliases.items():
            if target in variants or target == canonical:
                return actual in variants or actual == canonical
        return False

    @staticmethod
    def _normalize_terms(text: str) -> Set[str]:
        aliases = {
            "pet": "pet care",
            "pets": "pet care",
            "cat": "pet care",
            "dog": "pet care",
            "home": "home kitchen",
            "kitchen": "home kitchen",
            "fitness": "fitness",
            "beauty": "beauty",
            "makeup": "beauty",
            "skincare": "beauty",
            "tech": "tech",
            "fashion": "fashion",
            "food": "food",
            "travel": "travel",
            "outdoor": "outdoor",
            "parenting": "parenting",
            "lifestyle": "lifestyle",
            "blog": "blog",
            "blogs": "blog",
        }
        cleaned = re.sub(r"[^a-zA-Z0-9& ]+", " ", text.lower()).replace("&", " ")
        terms = {part for part in cleaned.split() if len(part) > 1}
        expanded: Set[str] = set()
        for term in terms:
            expanded.add(term)
            if term in aliases:
                expanded.update(aliases[term].split())
        phrase = " ".join(sorted(terms))
        if phrase in aliases:
            expanded.update(aliases[phrase].split())
        return expanded

    @staticmethod
    def _overlap_ratio(left: Set[str], right: Set[str]) -> float:
        if not left or not right:
            return 0.0
        intersection = left.intersection(right)
        if not intersection:
            return 0.0
        return len(intersection) / max(len(left), len(right))
