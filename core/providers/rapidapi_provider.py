# -*- coding: utf-8 -*-
import hashlib
import logging
import random
from typing import List, Optional

import httpx

from config.settings import settings
from core.providers.base import InfluencerProvider
from core.providers.context import set_search_meta
from core.providers.mock_provider import MockInfluencerProvider
from core.schemas import CampaignRequest, Influencer, Platform
from core.translator import translate_campaign_for_api

logger = logging.getLogger("rapidapi_provider")

FIND_PATH = "/api/v0/analytics/creators/find"

PLATFORM_TYPE_MAP = {
    Platform.youtube: "youtube",
}

API_TYPE_PLATFORM = {
    "youtube": Platform.youtube,
    "tiktok": Platform.tiktok,
    "instagram": Platform.instagram,
}


class RapidApiInfluencerProvider(InfluencerProvider):
    """RapidAPI YouTube 红人检索；失败时自动降级 Mock。"""

    def __init__(
        self,
        *,
        api_key: Optional[str] = None,
        api_host: Optional[str] = None,
        timeout: float = 30.0,
        fallback: Optional[InfluencerProvider] = None,
        client: Optional[httpx.Client] = None,
    ):
        self.api_key = api_key if api_key is not None else settings.RAPID_API_KEY
        self.api_host = api_host if api_host is not None else settings.RAPID_API_HOST
        self.timeout = timeout
        self.fallback = fallback or MockInfluencerProvider()
        self._client = client

    def search(self, campaign: CampaignRequest) -> List[Influencer]:
        if not self._is_configured():
            logger.warning("RapidAPI 未配置 Key/Host，直接使用 Mock 数据。")
            return self._fallback_search(campaign, reason="RapidAPI 未配置，已切换至 Mock 数据模式")

        channel_type = self._resolve_channel_type(campaign)
        if not channel_type:
            logger.warning("当前 Campaign 平台不受 RapidAPI 支持，降级 Mock。")
            return self._fallback_search(
                campaign,
                reason="当前平台组合暂不支持 RapidAPI 检索，已切换至 Mock 数据模式",
            )

        keywords = self._build_keywords(campaign)
        try:
            payload = self._fetch_creators(channel_type, keywords)
            channels = payload.get("data", {}).get("channels", [])
            influencers = self._map_channels(channels, campaign, channel_type)
            influencers = self._filter_by_campaign(influencers, campaign)

            if not influencers:
                logger.warning("RapidAPI 返回空结果，降级 Mock。")
                return self._fallback_search(campaign, reason="RapidAPI 未返回匹配红人，已切换至 Mock 数据模式")

            set_search_meta({"data_source": "rapidapi", "fallback_message": None})
            return influencers
        except httpx.TimeoutException:
            logger.error("RapidAPI 请求超时，降级 Mock。")
            return self._fallback_search(campaign, reason="RapidAPI 请求超时，已切换至 Mock 数据模式")
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 429:
                logger.error("RapidAPI 触发 429 限流，降级 Mock。")
                return self._fallback_search(campaign, reason="RapidAPI 限流（429），已切换至 Mock 数据模式")
            logger.error("RapidAPI HTTP 异常 %s，降级 Mock。", exc.response.status_code)
            return self._fallback_search(
                campaign,
                reason=f"RapidAPI 请求异常（{exc.response.status_code}），已切换至 Mock 数据模式",
            )
        except (httpx.HTTPError, ValueError, KeyError) as exc:
            logger.error("RapidAPI 调用失败：%s，降级 Mock。", exc)
            return self._fallback_search(campaign, reason="RapidAPI 响应异常，已切换至 Mock 数据模式")

    def _fallback_search(self, campaign: CampaignRequest, *, reason: str) -> List[Influencer]:
        results = self.fallback.search(campaign)
        set_search_meta({"data_source": "mock_fallback", "fallback_message": reason})
        return results

    def _is_configured(self) -> bool:
        key = (self.api_key or "").strip()
        host = (self.api_host or "").strip()
        if not key or not host:
            return False
        lowered = key.lower()
        if lowered.startswith("your_") or lowered == "placeholder":
            return False
        return True

    @staticmethod
    def _resolve_channel_type(campaign: CampaignRequest) -> Optional[str]:
        for platform in campaign.platforms:
            mapped = PLATFORM_TYPE_MAP.get(platform)
            if mapped:
                return mapped
        return None

    @staticmethod
    def _build_keywords(campaign: CampaignRequest) -> str:
        english = translate_campaign_for_api(campaign)
        parts = [
            english["product_category"],
            english["influencer_category"],
            english["product_name"],
        ]
        description_bits = (
            english["product_description"]
            .replace("，", " ")
            .replace("。", " ")
            .replace(",", " ")
            .split()
        )
        parts.extend(description_bits[:8])
        cleaned = []
        seen = set()
        for part in parts:
            text = part.strip()
            if not text:
                continue
            key = text.lower()
            if key in seen:
                continue
            seen.add(key)
            cleaned.append(text)
        return ",".join(cleaned[:10])

    def _fetch_creators(self, channel_type: str, keywords: str) -> dict:
        url = f"https://{self.api_host.rstrip('/')}{FIND_PATH}"
        headers = {
            "X-Rapidapi-Key": self.api_key,
            "X-Rapidapi-Host": self.api_host,
        }
        params = {"channelType": channel_type, "keywords": keywords}

        if self._client is not None:
            response = self._client.get(url, headers=headers, params=params, timeout=self.timeout)
        else:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.get(url, headers=headers, params=params)
        response.raise_for_status()
        data = response.json()
        if not isinstance(data, dict):
            raise ValueError("RapidAPI 响应不是 JSON 对象。")
        return data

    def _map_channels(
        self,
        channels: list,
        campaign: CampaignRequest,
        channel_type: str,
    ) -> List[Influencer]:
        influencers: List[Influencer] = []
        platform = API_TYPE_PLATFORM.get(channel_type, Platform.youtube)

        for raw in channels:
            if not isinstance(raw, dict):
                continue
            mapped = map_channel_to_influencer(raw, platform)
            if mapped is None:
                continue
            influencers.append(mapped)
        return influencers

    @staticmethod
    def _filter_by_campaign(influencers: List[Influencer], campaign: CampaignRequest) -> List[Influencer]:
        selected = {platform.value for platform in campaign.platforms}
        target_country = (campaign.target_country or "").upper()
        filtered: List[Influencer] = []
        for influencer in influencers:
            if influencer.platform.value not in selected:
                continue
            if influencer.followers < max(0, int(campaign.min_followers * 0.25)):
                continue
            if influencer.followers > max(campaign.max_followers * 5, campaign.max_followers + 500000):
                continue
            filtered.append(influencer)

        if target_country and len(filtered) >= 20:
            country_matched = [
                item for item in filtered if (item.country or "").upper() == target_country
            ]
            if len(country_matched) >= 10:
                filtered = country_matched

        pool_max = settings.CANDIDATE_POOL_MAX
        if len(filtered) > pool_max:
            filtered.sort(key=lambda item: item.followers)
            return filtered[:pool_max]
        return filtered


def map_channel_to_influencer(raw: dict, platform: Platform) -> Optional[Influencer]:
    """将 RapidAPI channel 对象映射为统一 Influencer。"""
    channel_id = raw.get("id")
    if not channel_id:
        return None

    username = str(raw.get("username") or raw.get("name") or channel_id).strip()
    if username.startswith("@"):
        username = username[1:]

    followers = raw.get("followers")
    if followers is None:
        return None

    try:
        followers_int = int(followers)
    except (TypeError, ValueError):
        return None

    total_views = raw.get("totalViews")
    total_posts = raw.get("totalPosts")
    try:
        total_views_int = int(total_views) if total_views is not None else None
    except (TypeError, ValueError):
        total_views_int = None
    try:
        total_posts_int = int(total_posts) if total_posts is not None else None
    except (TypeError, ValueError):
        total_posts_int = None

    country = raw.get("country")
    if country is not None:
        country = str(country).strip() or None

    return Influencer(
        id=str(channel_id),
        name=str(raw.get("name") or "").strip(),
        username=username,
        platform=platform,
        followers=followers_int,
        country=country,
        category=str(raw.get("categoryName") or "").strip(),
        description=str(raw.get("description") or "").strip() or None,
        url=str(raw.get("url") or "").strip() or None,
        profile_img=str(raw.get("profileImg") or "").strip() or None,
        total_views=total_views_int,
        total_posts=total_posts_int,
    )
