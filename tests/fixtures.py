"""Shared test fixtures."""

from core.schemas import CampaignRequest, Platform


def sample_campaign(**overrides) -> CampaignRequest:
    payload = {
        "product_name": "Gentle Cat Hair Remover Brush",
        "product_category": "Pet Care",
        "product_description": "一款适合猫咪和小型犬的温和去毛梳，支持一键清理浮毛。",
        "target_country": "US",
        "target_language": "English",
        "platforms": [Platform.tiktok, Platform.instagram],
        "min_followers": 10000,
        "max_followers": 80000,
        "min_engagement_rate": 0.03,
        "influencer_category": "Pet Care",
        "campaign_budget": 5000,
    }
    payload.update(overrides)
    return CampaignRequest(**payload)
