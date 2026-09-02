"""Tests for the AI summary service extracted from app.py.

Covers provider resolution and the graceful-degradation branches without
making a network call.
"""
import json
import unittest
from unittest import mock

from jobsearch.services import summary_service
from jobsearch.services.summary_service import (
    SUMMARY_PROMPT,
    briefing_char_budget,
    build_briefing_document,
    provider_label,
    resolve_provider,
    stream_ai_summary,
    summary_available,
)
from jobsearch.settings import load_settings


def _settings(**env):
    """Build a Settings from a clean environment plus overrides."""
    with mock.patch.dict("os.environ", env, clear=True):
        return load_settings()


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


class TestResolveProvider(unittest.TestCase):
    def _resolve(self, settings, ollama_up):
        with mock.patch.object(summary_service, "get_settings", return_value=settings), \
             mock.patch.object(summary_service, "ollama_available", return_value=ollama_up):
            return resolve_provider()

    def test_auto_prefers_anthropic_when_key_present(self):
        s = _settings(ANTHROPIC_API_KEY="sk-ant-x")
        self.assertEqual(self._resolve(s, ollama_up=True), "anthropic")

    def test_auto_falls_back_to_ollama_without_key(self):
        s = _settings()
        self.assertEqual(self._resolve(s, ollama_up=True), "ollama")

    def test_auto_returns_none_when_nothing_available(self):
        s = _settings()
        self.assertIsNone(self._resolve(s, ollama_up=False))

    def test_explicit_ollama_ignores_anthropic_key(self):
        s = _settings(SUMMARY_PROVIDER="ollama", ANTHROPIC_API_KEY="sk-ant-x")
        self.assertEqual(self._resolve(s, ollama_up=True), "ollama")

    def test_explicit_ollama_returns_none_when_server_down(self):
        s = _settings(SUMMARY_PROVIDER="ollama")
        self.assertIsNone(self._resolve(s, ollama_up=False))

    def test_explicit_anthropic_ignores_running_ollama(self):
        s = _settings(SUMMARY_PROVIDER="anthropic")
        self.assertIsNone(self._resolve(s, ollama_up=True))

    def test_summary_available_and_label_track_provider(self):
        s = _settings(SUMMARY_PROVIDER="ollama", OLLAMA_MODEL="qwen3.5:latest")
        with mock.patch.object(summary_service, "get_settings", return_value=s), \
             mock.patch.object(summary_service, "ollama_available", return_value=True):
            self.assertTrue(summary_available())
            self.assertIn("qwen3.5:latest", provider_label())
        with mock.patch.object(summary_service, "get_settings", return_value=s), \
             mock.patch.object(summary_service, "ollama_available", return_value=False):
            self.assertFalse(summary_available())
            self.assertIn("No summary backend", provider_label())


class _FakeStream:
    """Stand-in for httpx.stream's context manager over an NDJSON body."""

    def __init__(self, lines, status_code=200):
        self._lines = lines
        self.status_code = status_code
        self.text = ""

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def iter_lines(self):
        return iter(self._lines)

    def read(self):
        return b""


class TestStreamOllama(unittest.TestCase):
    def _run(self, fake, settings=None):
        settings = settings or _settings()
        with mock.patch.object(summary_service, "get_settings", return_value=settings), \
             mock.patch("httpx.stream", return_value=fake) as m:
            chunks = list(summary_service._stream_ollama("doc"))
        return chunks, m

    def test_yields_message_content_until_done(self):
        lines = [
            json.dumps({"message": {"content": "## 🔥 "}, "done": False}),
            "",
            json.dumps({"message": {"content": "Apply This Week"}, "done": False}),
            json.dumps({"message": {"content": ""}, "done": True}),
            json.dumps({"message": {"content": "never reached"}, "done": False}),
        ]
        chunks, _ = self._run(_FakeStream(lines))
        self.assertEqual("".join(chunks), "## 🔥 Apply This Week")

    def test_malformed_lines_are_skipped(self):
        lines = ["not json", json.dumps({"message": {"content": "ok"}, "done": True})]
        chunks, _ = self._run(_FakeStream(lines))
        self.assertEqual("".join(chunks), "ok")

    def test_error_event_surfaces_as_text(self):
        lines = [json.dumps({"error": "model not found"})]
        chunks, _ = self._run(_FakeStream(lines))
        self.assertIn("model not found", "".join(chunks))

    def test_non_200_surfaces_as_text(self):
        chunks, _ = self._run(_FakeStream([], status_code=404))
        self.assertIn("404", "".join(chunks))

    def test_request_carries_prompt_model_and_context(self):
        settings = _settings(OLLAMA_MODEL="m:tag", OLLAMA_NUM_CTX="4096")
        lines = [json.dumps({"message": {"content": "x"}, "done": True})]
        _, m = self._run(_FakeStream(lines), settings)
        payload = m.call_args.kwargs["json"]
        self.assertEqual(payload["model"], "m:tag")
        self.assertEqual(payload["options"]["num_ctx"], 4096)
        self.assertIs(payload["think"], False)
        self.assertEqual(payload["messages"][0]["content"], SUMMARY_PROMPT)
        # The document is followed by the format reinforcement block.
        user = payload["messages"][1]["content"]
        self.assertTrue(user.startswith("doc"))
        self.assertIn("## 🔥 Apply This Week", user)
        self.assertIn("## 📋 This Week's Action Plan", user)


class TestDispatch(unittest.TestCase):
    def test_explicit_provider_routes_to_ollama(self):
        with mock.patch.object(summary_service, "_stream_ollama", return_value=iter(["hi"])) as m:
            self.assertEqual(list(stream_ai_summary("doc", provider="ollama")), ["hi"])
        m.assert_called_once()

    def test_no_backend_yields_actionable_message(self):
        s = _settings()
        with mock.patch.object(summary_service, "get_settings", return_value=s), \
             mock.patch.object(summary_service, "ollama_available", return_value=False):
            chunks = list(stream_ai_summary("doc"))
        self.assertEqual(len(chunks), 1)
        self.assertIn("ANTHROPIC_API_KEY", chunks[0])
        self.assertIn("Ollama", chunks[0])


class TestBuildBriefingDocument(unittest.TestCase):
    """The full export (486k chars) overran a 32k-token window and silently
    truncated; the briefing runs on un-triaged roles as a compact digest."""

    def _jobs(self, n, status="New", prefix="Co"):
        return [{"company": f"{prefix}{i}", "title": f"Engineer {i}",
                 "location": "Toronto", "status": status,
                 "date_found": f"2026-09-{(i % 28) + 1:02d}"} for i in range(n)]

    def test_only_untriaged_roles_are_included(self):
        jobs = self._jobs(3) + [
            {"company": "Applied Co", "title": "Engineer", "location": "NYC",
             "status": "Applied", "date_found": "2026-09-30"},
            {"company": "Rejected Co", "title": "Engineer", "location": "NYC",
             "status": "Rejected", "date_found": "2026-09-30"},
        ]
        doc, included, total = build_briefing_document(jobs)
        self.assertEqual((included, total), (3, 3))
        self.assertNotIn("Applied Co", doc)
        self.assertNotIn("Rejected Co", doc)

    def test_blank_status_counts_as_untriaged(self):
        _, included, _ = build_briefing_document(
            [{"company": "C", "title": "T", "location": "L", "status": ""}])
        self.assertEqual(included, 1)

    def test_caps_at_max_roles_and_reports_the_full_pool(self):
        doc, included, total = build_briefing_document(self._jobs(50), max_roles=10)
        self.assertEqual((included, total), (10, 50))
        # The header must state the real backlog, not just what was sent.
        self.assertIn("50", doc)
        self.assertIn("10", doc)

    def test_newest_roles_are_kept_when_capped(self):
        jobs = [
            {"company": "Old", "title": "E", "location": "L", "status": "New",
             "date_found": "2026-01-01"},
            {"company": "New", "title": "E", "location": "L", "status": "New",
             "date_found": "2026-09-01"},
        ]
        doc, _, _ = build_briefing_document(jobs, max_roles=1)
        self.assertIn("New", doc)
        self.assertNotIn("Old —", doc)

    def test_char_budget_stops_before_overrunning_context(self):
        doc, included, total = build_briefing_document(
            self._jobs(500), max_roles=500, char_budget=400)
        self.assertLessEqual(len(doc), 400 + 120)  # + header
        self.assertLess(included, 500)
        self.assertEqual(total, 500)

    def test_rows_missing_company_or_title_are_skipped(self):
        jobs = [{"company": "", "title": "Engineer", "location": "L", "status": "New"},
                {"company": "Acme", "title": "", "location": "L", "status": "New"},
                {"company": "Acme", "title": "Engineer", "location": "L", "status": "New"}]
        _, included, _ = build_briefing_document(jobs)
        self.assertEqual(included, 1)

    def test_budget_scales_with_configured_context_window(self):
        self.assertGreater(briefing_char_budget(131072), briefing_char_budget(32768))
        # A tiny window still leaves a usable floor rather than going negative.
        self.assertGreater(briefing_char_budget(1000), 0)


if __name__ == "__main__":
    unittest.main()
