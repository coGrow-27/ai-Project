import json
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

import httpx

from core.providers.mock_provider import MockInfluencerProvider
from core.providers.rapidapi_provider import RapidApiInfluencerProvider, map_channel_to_influencer
from core.schemas import Platform
from tests.fixtures import sample_campaign


FIXTURE_PATH = Path(__file__).resolve().parent / "fixtures" / "rapidapi_sample.json"


class RapidApiProviderTest(unittest.TestCase):
    def setUp(self):
        with FIXTURE_PATH.open("r", encoding="utf-8") as handle:
            self.sample_payload = json.load(handle)
        self.campaign = sample_campaign(
            platforms=[Platform.youtube],
            min_followers=10000,
            max_followers=500000,
            influencer_category="Beauty",
            product_category="Beauty",
        )

    def test_map_channel_fields(self):
        raw = self.sample_payload["data"]["channels"][1]
        influencer = map_channel_to_influencer(raw, Platform.youtube)

        self.assertIsNotNone(influencer)
        self.assertEqual(influencer.id, "UC_-ywsA9-7dSTbWmdQdltbQ")
        self.assertEqual(influencer.name, "The Musings of a Crouton")
        self.assertEqual(influencer.username, "themusingsofacrouton1098")
        self.assertEqual(influencer.platform, Platform.youtube)
        self.assertEqual(influencer.followers, 186000)
        self.assertEqual(influencer.country, "US")
        self.assertEqual(influencer.category, "People & Blogs")
        self.assertEqual(influencer.total_views, 9670373)
        self.assertEqual(influencer.total_posts, 592)
        self.assertTrue(influencer.profile_img.startswith("https://"))

    def test_successful_request(self):
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = self.sample_payload
        mock_client.get.return_value = mock_response

        provider = RapidApiInfluencerProvider(
            api_key="test-key",
            api_host="influencer-data1.p.rapidapi.com",
            client=mock_client,
        )
        results = provider.search(self.campaign)

        self.assertGreater(len(results), 0)
        self.assertTrue(all(item.platform == Platform.youtube for item in results))
        mock_client.get.assert_called_once()

    def test_timeout_fallback(self):
        mock_client = MagicMock()
        mock_client.get.side_effect = httpx.TimeoutException("timeout")
        fallback = MagicMock(spec=MockInfluencerProvider)
        fallback.search.return_value = []

        provider = RapidApiInfluencerProvider(
            api_key="test-key",
            api_host="influencer-data1.p.rapidapi.com",
            client=mock_client,
            fallback=fallback,
        )
        provider.search(self.campaign)

        fallback.search.assert_called_once()

    def test_429_fallback(self):
        mock_client = MagicMock()
        response = MagicMock()
        response.status_code = 429
        mock_client.get.side_effect = httpx.HTTPStatusError(
            "rate limited",
            request=MagicMock(),
            response=response,
        )
        fallback = MagicMock(spec=MockInfluencerProvider)
        fallback.search.return_value = []

        provider = RapidApiInfluencerProvider(
            api_key="test-key",
            api_host="influencer-data1.p.rapidapi.com",
            client=mock_client,
            fallback=fallback,
        )
        provider.search(self.campaign)

        fallback.search.assert_called_once()

    def test_http_error_fallback(self):
        mock_client = MagicMock()
        response = MagicMock()
        response.status_code = 500
        mock_client.get.side_effect = httpx.HTTPStatusError(
            "server error",
            request=MagicMock(),
            response=response,
        )
        fallback = MagicMock(spec=MockInfluencerProvider)
        fallback.search.return_value = []

        provider = RapidApiInfluencerProvider(
            api_key="test-key",
            api_host="influencer-data1.p.rapidapi.com",
            client=mock_client,
            fallback=fallback,
        )
        provider.search(self.campaign)

        fallback.search.assert_called_once()

    def test_empty_result_fallback(self):
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {"data": {"channels": []}}
        mock_client.get.return_value = mock_response
        fallback = MagicMock(spec=MockInfluencerProvider)
        fallback.search.return_value = []

        provider = RapidApiInfluencerProvider(
            api_key="test-key",
            api_host="influencer-data1.p.rapidapi.com",
            client=mock_client,
            fallback=fallback,
        )
        provider.search(self.campaign)

        fallback.search.assert_called_once()

    def test_invalid_json_fallback(self):
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = []
        mock_client.get.return_value = mock_response
        fallback = MagicMock(spec=MockInfluencerProvider)
        fallback.search.return_value = []

        provider = RapidApiInfluencerProvider(
            api_key="test-key",
            api_host="influencer-data1.p.rapidapi.com",
            client=mock_client,
            fallback=fallback,
        )
        provider.search(self.campaign)

        fallback.search.assert_called_once()

    def test_unconfigured_uses_fallback(self):
        fallback = MagicMock(spec=MockInfluencerProvider)
        fallback.search.return_value = []

        provider = RapidApiInfluencerProvider(
            api_key="",
            api_host="",
            fallback=fallback,
        )
        provider.search(self.campaign)

        fallback.search.assert_called_once()

    @patch("core.providers.rapidapi_provider.settings")
    def test_fallback_sets_context_meta(self, mock_settings):
        mock_settings.RAPID_API_KEY = "test-key"
        mock_settings.RAPID_API_HOST = "influencer-data1.p.rapidapi.com"
        mock_settings.CANDIDATE_POOL_MAX = 100

        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {"data": {"channels": []}}
        mock_client.get.return_value = mock_response

        from core.providers.context import get_search_meta

        provider = RapidApiInfluencerProvider(
            api_key="test-key",
            api_host="influencer-data1.p.rapidapi.com",
            client=mock_client,
            fallback=MockInfluencerProvider(size=20),
        )
        provider.search(self.campaign)
        meta = get_search_meta()

        self.assertEqual(meta["data_source"], "mock_fallback")
        self.assertIn("Mock", meta["fallback_message"])
