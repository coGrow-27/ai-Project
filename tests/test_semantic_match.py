import unittest

from core.campaign_semantic import CampaignSemanticIndex, build_semantic_query, format_influencer_document
from core.providers import MockInfluencerProvider
from core.schemas import SemanticMatchEvidence
from core.scoring_engine import InfluencerScoringEngine
from tests.fixtures import sample_campaign


class SemanticMatchTest(unittest.TestCase):
    def test_format_influencer_document_contains_core_fields(self):
        provider = MockInfluencerProvider(size=100)
        campaign = sample_campaign()
        candidates = provider.search(campaign)
        self.assertGreater(len(candidates), 0)
        influencer = candidates[0]
        document = format_influencer_document(influencer)
        self.assertIn("Creator:", document)
        self.assertIn("Category:", document)
        self.assertIn("Country:", document)
        self.assertIn("Description:", document)

    def test_semantic_index_scores_candidates(self):
        campaign = sample_campaign(
            detailed_marketing_requirements="寻找温柔护肤测评、适合深夜陪伴风格的美妆博主",
        )
        provider = MockInfluencerProvider(size=30)
        candidates = provider.search(campaign)
        index = CampaignSemanticIndex(use_mock=True)
        try:
            index.build_from_influencers(candidates)
            query = build_semantic_query(campaign)
            scores = index.score_all(query)
            self.assertEqual(len(scores), len(candidates))
            top_id = max(scores.items(), key=lambda item: item[1].similarity)[0]
            self.assertIn(top_id, {item.id for item in candidates})
        finally:
            index.close()

    def test_scoring_engine_semantic_points(self):
        engine = InfluencerScoringEngine()
        campaign = sample_campaign()
        provider = MockInfluencerProvider(size=100)
        candidates = provider.search(campaign)
        self.assertGreater(len(candidates), 0)
        influencer = candidates[0]
        semantic = SemanticMatchEvidence(
            influencer_id=influencer.id,
            similarity=0.9,
            evidence=["Beauty content"],
            matched_topics=["beauty", "skincare"],
        )
        breakdown = engine.score(campaign, influencer, semantic)
        self.assertEqual(breakdown.semantic_match, 22)
