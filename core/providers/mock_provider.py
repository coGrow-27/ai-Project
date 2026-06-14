# -*- coding: utf-8 -*-
import hashlib
import random
from typing import List

from core.providers.base import InfluencerProvider
from core.providers.context import set_search_meta
from core.schemas import CampaignRequest, Influencer, Platform, RecentPost


class MockInfluencerProvider(InfluencerProvider):
    def __init__(self, seed: int = 42, size: int = 100):
        self.seed = seed
        self.size = size
        self._influencers = self._build_mock_influencers()

    def search(self, campaign: CampaignRequest) -> List[Influencer]:
        set_search_meta({"data_source": "mock", "fallback_message": None})
        selected_platforms = {platform.value for platform in campaign.platforms}
        category_terms = self._normalize_category(campaign.influencer_category)

        candidates = []
        for influencer in self._influencers:
            if influencer.platform.value not in selected_platforms:
                continue
            if influencer.engagement_rate is not None and influencer.engagement_rate < campaign.min_engagement_rate * 0.65:
                continue
            if not self._category_related(category_terms, influencer.category):
                continue
            if influencer.followers < max(0, int(campaign.min_followers * 0.45)):
                continue
            if influencer.followers > max(campaign.max_followers * 2, campaign.max_followers + 50000):
                continue
            candidates.append(influencer)

        return candidates

    def _build_mock_influencers(self) -> List[Influencer]:
        rng = random.Random(self.seed)
        categories = [
            "Pet Care",
            "Fitness",
            "Beauty",
            "Home & Kitchen",
            "Tech",
            "Fashion",
            "Food",
            "Parenting",
            "Travel",
            "Outdoor",
        ]
        countries = ["US", "UK", "CA", "AU", "DE", "FR", "JP", "KR", "SG", "BR"]
        languages = {
            "US": "English",
            "UK": "English",
            "CA": "English",
            "AU": "English",
            "DE": "German",
            "FR": "French",
            "JP": "Japanese",
            "KR": "Korean",
            "SG": "English",
            "BR": "Portuguese",
        }
        platforms = [Platform.tiktok, Platform.instagram, Platform.youtube]

        influencers: List[Influencer] = []
        for index in range(self.size):
            category = categories[index % len(categories)]
            country = countries[(index * 3) % len(countries)]
            platform = platforms[index % len(platforms)]
            followers = rng.randint(6_000, 180_000)
            engagement_rate = round(rng.uniform(0.018, 0.092), 4)
            avg_likes = max(80, int(followers * engagement_rate * rng.uniform(0.55, 0.85)))
            avg_comments = max(8, int(followers * engagement_rate * rng.uniform(0.035, 0.11)))
            username = self._username(category, index)
            display_name = f"{category} Creator {index + 1}"
            primary_share = round(rng.uniform(0.48, 0.86), 2)
            secondary_country = countries[(index * 5 + 1) % len(countries)]
            third_country = countries[(index * 7 + 2) % len(countries)]
            remaining = round(1 - primary_share, 2)
            audience_countries = {
                country: primary_share,
                secondary_country: round(remaining * 0.65, 2),
                third_country: round(remaining * 0.35, 2),
            }
            total_posts = rng.randint(50, 800)
            total_views = rng.randint(followers * 20, followers * 500)

            influencers.append(
                Influencer(
                    id=f"mock_{index + 1:03d}",
                    name=display_name,
                    platform=platform,
                    username=username,
                    followers=followers,
                    engagement_rate=engagement_rate,
                    avg_likes=avg_likes,
                    avg_comments=avg_comments,
                    country=country,
                    language=languages[country],
                    category=category,
                    description=f"专注 {category} 内容创作，分享真实体验与实用技巧。",
                    url=f"https://example.com/{username}",
                    profile_img=f"https://api.dicebear.com/8.x/initials/svg?seed={username}",
                    total_views=total_views,
                    total_posts=total_posts,
                    audience_countries=audience_countries,
                    audience_gender={
                        "female": round(rng.uniform(0.35, 0.72), 2),
                        "male": round(rng.uniform(0.25, 0.58), 2),
                    },
                    audience_age={
                        "18-24": round(rng.uniform(0.18, 0.42), 2),
                        "25-34": round(rng.uniform(0.28, 0.52), 2),
                        "35-44": round(rng.uniform(0.12, 0.3), 2),
                    },
                    recent_posts=self._posts(category, username, rng),
                    comment_quality=round(rng.uniform(0.55, 0.96), 2),
                    authenticity_score=round(rng.uniform(0.58, 0.98), 2),
                    audience_fit_score=round(rng.uniform(0.52, 0.95), 2),
                )
            )

        return influencers

    @staticmethod
    def _username(category: str, index: int) -> str:
        prefix = category.lower().replace("&", "").replace(" ", "_")
        suffix = hashlib.md5(f"{category}-{index}".encode("utf-8")).hexdigest()[:5]
        return f"{prefix}_creator_{suffix}"

    @staticmethod
    def _posts(category: str, username: str, rng: random.Random) -> List[RecentPost]:
        topic_map = {
            "Pet Care": ["gentle grooming routine", "testing a self-cleaning pet brush", "cat shedding tips"],
            "Fitness": ["morning strength routine", "protein snack review", "home workout essentials"],
            "Beauty": ["sensitive skin routine", "new serum test", "honest beauty empties"],
            "Home & Kitchen": ["small kitchen upgrade", "cleaning tool review", "weekend home reset"],
            "Tech": ["desk setup refresh", "smart gadget review", "creator workflow tools"],
            "Fashion": ["capsule wardrobe picks", "outfit transition ideas", "brand styling test"],
            "Food": ["quick lunch prep", "healthy snack tasting", "family dinner idea"],
            "Parenting": ["school morning routine", "mom-approved product test", "family organization tips"],
            "Travel": ["city guide", "carry-on essentials", "hotel room review"],
            "Outdoor": ["trail gear checklist", "weekend camping setup", "rainy hike essentials"],
        }
        topics = topic_map.get(category, ["product review", "daily routine", "audience Q&A"])
        return [
            RecentPost(
                title=topic,
                caption=f"@{username} shares authentic {category} experience: {topic}",
                likes=rng.randint(500, 9000),
                comments=rng.randint(35, 900),
                url=None,
            )
            for topic in topics
        ]

    @staticmethod
    def _normalize_category(category: str) -> set[str]:
        aliases = {
            "pet": "pet care",
            "pets": "pet care",
            "cat": "pet care",
            "dog": "pet care",
            "fitness": "fitness",
            "beauty": "beauty",
            "home": "home kitchen",
            "kitchen": "home kitchen",
            "tech": "tech",
            "fashion": "fashion",
        }
        text = category.lower()
        terms = set(text.replace("&", " ").split())
        for key, value in aliases.items():
            if key in text:
                terms.update(value.split())
        return terms

    @staticmethod
    def _category_related(category_terms: set[str], influencer_category: str) -> bool:
        influencer_terms = influencer_category.lower().replace("&", " ").split()
        return bool(category_terms.intersection(influencer_terms))
