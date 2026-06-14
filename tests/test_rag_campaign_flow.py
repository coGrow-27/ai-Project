import unittest

from core.campaign_matcher import CampaignMatcher
from core.campaign_semantic import CampaignSemanticIndex
from core.providers import MockInfluencerProvider
from tests.fixtures import sample_campaign


class RagCampaignFlowTest(unittest.TestCase):
    def test_campaign_matcher_builds_and_releases_semantic_index(self):
        campaign = sample_campaign(
            detailed_marketing_requirements="适合推荐温和护肤产品，说话风格温柔，面向18-30岁女性",
            product_category="美妆",
            influencer_category="Beauty",
        )
        provider = MockInfluencerProvider(size=40)
        matcher = CampaignMatcher(provider=provider)
        response = matcher.match(campaign)

        self.assertGreater(response.total_candidates, 0)
        self.assertLessEqual(len(response.results), 10)
        top = response.results[0]
        self.assertGreaterEqual(top.breakdown.semantic_match, 0)
        self.assertIn("推荐原因", top.recommendation_reason)

    def test_semantic_index_lifecycle(self):
        provider = MockInfluencerProvider(size=15)
        campaign = sample_campaign(detailed_marketing_requirements="pet grooming gentle brush")
        candidates = provider.search(campaign)
        index = CampaignSemanticIndex(use_mock=True)
        index.build_from_influencers(candidates)
        scores = index.score_all("pet grooming cat brush")
        index.close()
        self.assertEqual(len(scores), len(candidates))
