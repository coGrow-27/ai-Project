# -*- coding: utf-8 -*-
from core.providers.base import InfluencerProvider
from core.schemas import CampaignRequest, Influencer


class ModashProvider(InfluencerProvider):
    def search(self, campaign: CampaignRequest) -> list[Influencer]:
        raise NotImplementedError("ModashProvider 预留接口，请新增 core/providers/modash_provider.py 实现。")


class HypeAuditorProvider(InfluencerProvider):
    def search(self, campaign: CampaignRequest) -> list[Influencer]:
        raise NotImplementedError("HypeAuditorProvider 预留接口，请新增 core/providers/hypeauditor_provider.py 实现。")


class CreatorIQProvider(InfluencerProvider):
    def search(self, campaign: CampaignRequest) -> list[Influencer]:
        raise NotImplementedError("CreatorIQProvider 预留接口，请新增 core/providers/creatoriq_provider.py 实现。")


class UpfluenceProvider(InfluencerProvider):
    def search(self, campaign: CampaignRequest) -> list[Influencer]:
        raise NotImplementedError("UpfluenceProvider 预留接口，请新增 core/providers/upfluence_provider.py 实现。")
