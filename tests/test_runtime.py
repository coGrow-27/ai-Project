import unittest
from unittest.mock import patch

from config.settings import settings
from core.runtime import is_llm_enabled, is_llm_mock, is_rag_mock, runtime_summary


class RuntimeTest(unittest.TestCase):
    def test_runtime_summary_contains_modes(self):
        summary = runtime_summary()
        self.assertIn(summary["rag"], {"mock", "vector"})
        self.assertIsInstance(summary["llm_active"], bool)
        self.assertEqual(summary["content_top_k"], 5)

    @patch.object(settings, "USE_MOCK", new=True)
    def test_mock_flags_default_safe(self):
        self.assertTrue(is_rag_mock())
        self.assertTrue(is_llm_mock())
        self.assertFalse(is_llm_enabled())
