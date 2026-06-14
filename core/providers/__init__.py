# -*- coding: utf-8 -*-
from enum import Enum
from typing import Optional

from config.settings import settings
from core.providers.base import InfluencerProvider
from core.providers.mock_provider import MockInfluencerProvider
from core.providers.rapidapi_provider import RapidApiInfluencerProvider
from core.providers.reserved import (
    CreatorIQProvider,
    HypeAuditorProvider,
    ModashProvider,
    UpfluenceProvider,
)


class ProviderName(str, Enum):
    mock = "mock"
    rapidapi = "rapidapi"
    modash = "modash"
    hypeauditor = "hypeauditor"
    creatoriq = "creatoriq"
    upfluence = "upfluence"


def get_influencer_provider(name: Optional[str] = None) -> InfluencerProvider:
    if settings.USE_MOCK:
        return MockInfluencerProvider()

    provider_name = (name or settings.INFLUENCER_PROVIDER).lower()
    providers = {
        ProviderName.mock.value: MockInfluencerProvider,
        ProviderName.rapidapi.value: RapidApiInfluencerProvider,
        ProviderName.modash.value: ModashProvider,
        ProviderName.hypeauditor.value: HypeAuditorProvider,
        ProviderName.creatoriq.value: CreatorIQProvider,
        ProviderName.upfluence.value: UpfluenceProvider,
    }
    provider_cls = providers.get(provider_name, RapidApiInfluencerProvider)
    if provider_cls is RapidApiInfluencerProvider:
        return RapidApiInfluencerProvider(fallback=MockInfluencerProvider())
    return provider_cls()


__all__ = [
    "CreatorIQProvider",
    "HypeAuditorProvider",
    "InfluencerProvider",
    "MockInfluencerProvider",
    "ModashProvider",
    "ProviderName",
    "RapidApiInfluencerProvider",
    "UpfluenceProvider",
    "get_influencer_provider",
]
