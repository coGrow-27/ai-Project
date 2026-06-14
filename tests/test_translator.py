import unittest
from unittest.mock import patch

from core.translator import (
    contains_chinese,
    translate_campaign_for_api,
    translate_to_english,
)
from tests.fixtures import sample_campaign


class TranslatorTest(unittest.TestCase):
    def test_contains_chinese(self):
        self.assertTrue(contains_chinese("温和猫咪去毛梳"))
        self.assertFalse(contains_chinese("pet care"))

    def test_category_dictionary_translation(self):
        translate_to_english.cache_clear()
        self.assertEqual(translate_to_english("宠物护理"), "pet care")
        self.assertEqual(translate_to_english("美妆"), "beauty makeup")

    @patch("core.translator._translate_via_mymemory")
    def test_translate_product_name_via_remote(self, mock_remote):
        translate_to_english.cache_clear()
        mock_remote.return_value = "Gentle cat hair remover brush"
        result = translate_to_english("温和猫咪去毛梳")
        self.assertEqual(result, "Gentle cat hair remover brush")

    @patch("core.translator.translate_to_english")
    def test_translate_campaign_for_api(self, mock_translate):
        mock_translate.side_effect = lambda text: {
            "温和猫咪去毛梳": "Gentle cat brush",
            "宠物护理": "pet care",
            "一款适合猫咪的温和去毛梳。": "A gentle brush for cats.",
        }.get(text, text)

        campaign = sample_campaign(
            product_name="温和猫咪去毛梳",
            product_category="宠物护理",
            product_description="一款适合猫咪的温和去毛梳。",
            influencer_category="宠物护理",
        )
        english = translate_campaign_for_api(campaign)
        self.assertEqual(english["product_name"], "Gentle cat brush")
        self.assertEqual(english["product_category"], "pet care")


class RapidApiKeywordTest(unittest.TestCase):
    @patch("core.providers.rapidapi_provider.translate_campaign_for_api")
    def test_build_keywords_calls_translation(self, mock_translate):
        from core.providers.rapidapi_provider import RapidApiInfluencerProvider

        mock_translate.return_value = {
            "product_name": "Gentle cat brush",
            "product_category": "pet care",
            "product_description": "A gentle brush for cats and small dogs.",
            "influencer_category": "pet care",
        }
        campaign = sample_campaign(
            product_name="温和猫咪去毛梳",
            product_category="宠物护理",
        )
        keywords = RapidApiInfluencerProvider._build_keywords(campaign)
        self.assertIn("pet care", keywords)
        self.assertIn("Gentle cat brush", keywords)
        mock_translate.assert_called_once_with(campaign)
