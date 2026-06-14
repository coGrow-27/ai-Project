import unittest

from core.mock_data import MockDataLoader
from core.rag_engine import InfluencerRagEngine


class InfluencerRagEngineTest(unittest.TestCase):
    def test_mock_rag_engine_generates_match_result(self):
        influencers = MockDataLoader().get_all_influencers()
        engine = InfluencerRagEngine(use_mock=True)

        engine.build_index(influencers)
        result = engine.query("猫咪 去毛梳 一键清理 温和 宠物 梳毛")

        self.assertIn("红人匹配结果", result)
        self.assertIn("开发信草稿", result)
        self.assertTrue("cat_mom_jessie" in result or "grooming_pro_dan" in result)
