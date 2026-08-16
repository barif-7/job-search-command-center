"""Tests for the keyword extraction logic in scripts/extract_keywords.py."""

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import extract_keywords as ek  # noqa: E402
from jobsearch.models import Job  # noqa: E402


class TestExtractKeywords(unittest.TestCase):
    def test_matches_across_fields_case_insensitively(self):
        job = Job(
            title="Senior iOS Engineer",
            description="Build with SwiftUI and Python.",
            board="LinkedIn",
        )
        kw = ek.extract_keywords(job)
        self.assertEqual(kw["languages"], ["python"])
        self.assertEqual(kw["frameworks"], ["swiftui"])
        self.assertIn("ios", kw["platforms"])

    def test_respects_word_boundaries(self):
        # "JavaScript" must not trip the standalone "java" keyword, and "SwiftUI"
        # must not trip the standalone "swift" language.
        job = Job(title="Frontend Engineer", description="Deep JavaScript and React work.")
        kw = ek.extract_keywords(job)
        self.assertIn("javascript", kw["languages"])
        self.assertNotIn("java", kw["languages"])
        self.assertEqual(kw["frameworks"], ["react"])

    def test_empty_when_no_signal(self):
        job = Job(title="Office Manager", description="Coordinate schedules and vendors.")
        self.assertEqual(ek.extract_keywords(job), {})

    def test_select_jobs_by_offset_and_limit(self):
        jobs = [Job(title=f"J{i}", url=f"https://x/{i}") for i in range(5)]
        picked = ek._select_jobs(jobs, urls=[], limit=2, offset=1)
        self.assertEqual([j.title for j in picked], ["J1", "J2"])

    def test_select_jobs_by_urls_preserves_request_order_and_drops_unknown(self):
        jobs = [Job(title=f"J{i}", url=f"https://x/{i}") for i in range(5)]
        picked = ek._select_jobs(
            jobs, urls=["https://x/3", "https://x/0", "https://x/nope"], limit=50, offset=0
        )
        self.assertEqual([j.url for j in picked], ["https://x/3", "https://x/0"])

    def test_build_report_shape(self):
        jobs = [Job(company="Acme", title="iOS Dev", url="https://x/1", description="SwiftUI")]
        self.assertEqual(
            ek.build_report(jobs),
            [
                {
                    "company": "Acme",
                    "title": "iOS Dev",
                    "url": "https://x/1",
                    "keywords": {"frameworks": ["swiftui"], "platforms": ["ios"]},
                }
            ],
        )


if __name__ == "__main__":
    unittest.main()
