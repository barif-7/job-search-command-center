"""Tests for the AI summary service extracted from app.py.

Covers the graceful-degradation branches without making a network call.
"""
import unittest

from jobsearch.services.summary_service import SUMMARY_PROMPT, stream_ai_summary


class TestStreamAiSummary(unittest.TestCase):
    def test_missing_api_key_yields_single_message(self):
        chunks = list(stream_ai_summary("some doc", api_key=""))
        self.assertEqual(len(chunks), 1)
        self.assertIn("ANTHROPIC_API_KEY", chunks[0])

    def test_prompt_structure_is_stable(self):
        # The exact section headers the UI depends on.
        for header in (
            "## 🔥 Apply This Week",
            "## 🎯 Strongest Fit Signals",
            "## 📍 Location Strategy",
            "## ✨ Hidden Gems in New Findings",
            "## ⚠️ Roles to Deprioritize",
            "## 📋 This Week's Action Plan",
        ):
            self.assertIn(header, SUMMARY_PROMPT)


if __name__ == "__main__":
    unittest.main()
