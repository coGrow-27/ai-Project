import os
import unittest

from config.settings import settings
from core.providers import RapidApiInfluencerProvider
from core.providers.context import get_search_meta
from core.schemas import Platform
from tests.fixtures import sample_campaign


@unittest.skipUnless(
    os.getenv("RUN_LIVE_RAPIDAPI") == "1" and settings.RAPID_API_KEY,
    "设置 RUN_LIVE_RAPIDAPI=1 且配置 RAPID_API_KEY 后运行真实 API 联调测试",
)
class LiveRapidApiIntegrationTest(unittest.TestCase):
    def test_live_campaign_match_via_provider(self):
        campaign = sample_campaign(
            platforms=[Platform.youtube],
            product_category="Beauty",
            influencer_category="Beauty",
            min_followers=10000,
            max_followers=500000,
        )
        provider = RapidApiInfluencerProvider()
        results = provider.search(campaign)
        meta = get_search_meta()

        self.assertEqual(meta["data_source"], "rapidapi")
        self.assertIsNone(meta["fallback_message"])
        self.assertGreater(len(results), 0)
        self.assertEqual(results[0].platform, Platform.youtube)
        self.assertIsNotNone(results[0].followers)
