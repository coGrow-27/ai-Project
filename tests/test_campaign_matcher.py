import unittest
from unittest.mock import patch

from config.settings import settings
from core.campaign_matcher import CampaignMatcher
from core.providers import (
    CreatorIQProvider,
    HypeAuditorProvider,
    MockInfluencerProvider,
    ModashProvider,
    get_influencer_provider,
)
from core.schemas import Platform
from tests.fixtures import sample_campaign


class ProviderTest(unittest.TestCase):
    def test_mock_provider_returns_filtered_candidates(self):
        campaign = sample_campaign()
        candidates = MockInfluencerProvider(size=100).search(campaign)

        self.assertGreater(len(candidates), 0)
        self.assertTrue(all(item.platform in campaign.platforms for item in candidates))

    @patch.object(settings, "USE_MOCK", new=True)
    def test_get_influencer_provider_defaults_to_mock(self):
        provider = get_influencer_provider()
        self.assertIsInstance(provider, MockInfluencerProvider)

    def test_external_providers_are_reserved(self):
        campaign = sample_campaign()
        for provider_cls in (ModashProvider, HypeAuditorProvider, CreatorIQProvider):
            with self.assertRaises(NotImplementedError):
                provider_cls().search(campaign)


class CampaignMatcherTest(unittest.TestCase):
    def test_campaign_match_returns_top10_with_top5_content(self):
        matcher = CampaignMatcher(provider=MockInfluencerProvider(size=100))
        response = matcher.match(sample_campaign())

        self.assertGreater(response.total_candidates, 0)
        self.assertLessEqual(len(response.results), 10)
        self.assertGreaterEqual(len(response.results), 1)

        first = response.results[0]
        self.assertEqual(first.rank, 1)
        self.assertTrue(first.detail_generated)
        self.assertIn("推荐原因", first.recommendation_reason)
        self.assertIsNotNone(first.outreach)
        self.assertTrue(first.outreach.zh.subject)

        if len(response.results) > 5:
            sixth = response.results[5]
            self.assertFalse(sixth.detail_generated)
            self.assertIsNone(sixth.outreach)
            self.assertIn("Top 5", sixth.recommendation_reason)

        scores = [item.score for item in response.results]
        self.assertEqual(scores, sorted(scores, reverse=True))

    def test_score_breakdown_sums_to_total(self):
        matcher = CampaignMatcher(provider=MockInfluencerProvider(size=100))
        response = matcher.match(sample_campaign())
        item = response.results[0]
        breakdown_total = (
            item.breakdown.semantic_match
            + item.breakdown.category_match
            + item.breakdown.market_match
            + item.breakdown.audience_size_fit
            + item.breakdown.activity_score
        )
        self.assertEqual(item.score, breakdown_total)

    def test_rag_integrated_when_marketing_requirements_provided(self):
        campaign = sample_campaign(
            detailed_marketing_requirements="希望寻找说话风格温柔、适合护肤产品测评的博主",
            platforms=[Platform.youtube],
        )
        matcher = CampaignMatcher(provider=MockInfluencerProvider(size=100))
        response = matcher.match(campaign)
        top = response.results[0]
        self.assertIsNotNone(top.breakdown.semantic_match)
