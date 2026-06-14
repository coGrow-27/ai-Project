# -*- coding: utf-8 -*-
from abc import ABC, abstractmethod
from typing import List

from core.schemas import CampaignRequest, Influencer


class InfluencerProvider(ABC):
    @abstractmethod
    def search(self, campaign: CampaignRequest) -> List[Influencer]:
        """根据 Campaign 条件返回统一格式的红人列表。"""
