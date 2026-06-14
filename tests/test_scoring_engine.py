import unittest

from core.providers import MockInfluencerProvider
from core.schemas import SemanticMatchEvidence
from core.scoring_engine import InfluencerScoringEngine
from tests.fixtures import sample_campaign


class ScoringEngineTest(unittest.TestCase):
    def setUp(self):
        self.engine = InfluencerScoringEngine()
        self.campaign = sample_campaign()

    def test_breakdown_dimensions_within_limits(self):
        provider = MockInfluencerProvider(size=100)
        influencer = provider.search(self.campaign)[0]
        semantic = SemanticMatchEvidence(influencer_id=influencer.id, similarity=0.8, evidence=["beauty"])
        breakdown = self.engine.score(self.campaign, influencer, semantic)

        self.assertLessEqual(breakdown.semantic_match, 25)
        self.assertLessEqual(breakdown.category_match, 30)
        self.assertLessEqual(breakdown.market_match, 20)
        self.assertLessEqual(breakdown.audience_size_fit, 15)
        self.assertLessEqual(breakdown.activity_score, 10)

    def test_total_score_is_sum_of_breakdown(self):
        provider = MockInfluencerProvider(size=100)
        influencer = provider.search(self.campaign)[0]
        breakdown = self.engine.score(self.campaign, influencer)

        self.assertEqual(self.engine.total_score(breakdown), breakdown.total_score)

    def test_semantic_match_scales_with_similarity(self):
        provider = MockInfluencerProvider(size=100)
        influencer = provider.search(self.campaign)[0]
        high = self.engine.score(
            self.campaign,
            influencer,
            SemanticMatchEvidence(influencer_id=influencer.id, similarity=0.9),
        ).semantic_match
        low = self.engine.score(
            self.campaign,
            influencer,
            SemanticMatchEvidence(influencer_id=influencer.id, similarity=0.2),
        ).semantic_match
        self.assertGreater(high, low)

    def test_high_audience_share_scores_higher(self):
        provider = MockInfluencerProvider(size=100)
        candidates = provider.search(self.campaign)
        best = max(
            candidates,
            key=lambda item: (item.audience_countries or {}).get(self.campaign.target_country, 0),
        )
        worst = min(
            candidates,
            key=lambda item: (item.audience_countries or {}).get(self.campaign.target_country, 0),
        )

        best_score = self.engine.score(self.campaign, best).market_match
        worst_score = self.engine.score(self.campaign, worst).market_match
        self.assertGreaterEqual(best_score, worst_score)

    def test_followers_in_range_score_higher_than_far_outside(self):
        provider = MockInfluencerProvider(size=100)
        candidates = provider.search(self.campaign)
        in_range = min(
            candidates,
            key=lambda item: abs(item.followers - (self.campaign.min_followers + self.campaign.max_followers) / 2),
        )
        out_range = max(candidates, key=lambda item: item.followers)

        in_range_score = self.engine.score(self.campaign, in_range).audience_size_fit
        out_range_score = self.engine.score(self.campaign, out_range).audience_size_fit
        self.assertGreaterEqual(in_range_score, out_range_score)

    def test_activity_score_uses_total_posts_and_views(self):
        provider = MockInfluencerProvider(size=100)
        influencer = provider.search(self.campaign)[0]
        breakdown = self.engine.score(self.campaign, influencer)
        self.assertGreater(breakdown.activity_score, 0)
