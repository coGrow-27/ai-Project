import unittest

from core.mock_data import MockDataLoader


class MockDataLoaderTest(unittest.TestCase):
    def test_load_mock_influencers(self):
        influencers = MockDataLoader().get_all_influencers()

        self.assertGreaterEqual(len(influencers), 3)
        self.assertTrue(influencers[0]["username"])

    def test_filter_influencers_by_region_and_category(self):
        influencers = MockDataLoader().get_filtered_influencers(category="cat brush", region="US")

        self.assertTrue(influencers)
        self.assertTrue(all(item["region"] == "US" for item in influencers))
