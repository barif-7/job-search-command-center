"""Characterization tests for the parsing logic extracted from app.py.

The expected values were captured from the original in-app implementations
before extraction (golden master), so these tests pin behavior exactly.
"""
import unittest

from jobsearch.parsing.markdown import (
    parse_exported_job_bullet,
    parse_job_entry,
    parse_md_jobs,
    parse_md_stats,
)
from jobsearch.parsing.query import parse_comp_value, parse_query_chips

SAMPLE_MD = """\
## San Francisco — iOS Roles

### 1. 🔥 Senior iOS Engineer @ Anthropic
- **Link:** https://boards.greenhouse.io/anthropic/jobs/123
- **Comp:** $200K–$280K
- **Location:** San Francisco
- **Board:** greenhouse
- **Fit:** Strong **SwiftUI** match and AI infra overlap.
- **Concerns:** Onsite heavy.
- **Priority: 9/10**
- Status: **Interested**

### AI-SF-2. Forward Deployed Engineer @ OpenAI _(see also #4)_
- **Link:** https://jobs.lever.co/openai/abc — apply here
- **Comp:** not fetched yet
- **Board:** lever
- **Fit:** _review needed_
- **Priority: ?/10**

## New Findings

### NEW-1. Mobile Engineer @ Faire
- **Link:** https://faire.com/careers/9
- **Location:** Toronto
- **Board:** greenhouse
- **Priority: 6/10**

## Saved

- **[Linear]** iOS Engineer — Remote (greenhouse, 2026-01-10)
  https://linear.app/careers/1
- **[Ramp]** Machine Learning Engineer — New York (lever, 2026-02-01)
  https://ramp.com/careers/2
"""

EXPECTED_JOBS = [
    {
        "company": "Anthropic", "title": "🔥 Senior iOS Engineer",
        "url": "https://boards.greenhouse.io/anthropic/jobs/123",
        "comp": "$200K–$280K", "location": "San Francisco", "board": "greenhouse",
        "fit": "Strong **SwiftUI** match and AI infra overlap.", "concerns": "Onsite heavy.",
        "priority": 9, "status": "Interested", "type": "top",
        "section": "San Francisco — iOS Roles",
    },
    {
        "company": "OpenAI", "title": "Forward Deployed Engineer",
        "url": "https://jobs.lever.co/openai/abc", "comp": "", "location": "San Francisco",
        "board": "lever", "fit": "", "concerns": "", "priority": 0, "status": "Saved",
        "type": "ai", "section": "San Francisco — iOS Roles",
    },
    {
        "company": "Faire", "title": "Mobile Engineer", "url": "https://faire.com/careers/9",
        "comp": "", "location": "Toronto", "board": "greenhouse", "fit": "", "concerns": "",
        "priority": 6, "status": "Saved", "type": "new", "section": "New Findings",
    },
    {
        "company": "Linear", "title": "iOS Engineer", "url": "https://linear.app/careers/1",
        "comp": "", "location": "Remote", "board": "greenhouse", "fit": "", "concerns": "",
        "priority": 0, "status": "Saved", "type": "ios", "section": "Saved",
    },
    {
        "company": "Ramp", "title": "Machine Learning Engineer", "url": "https://ramp.com/careers/2",
        "comp": "", "location": "New York", "board": "lever", "fit": "", "concerns": "",
        "priority": 0, "status": "Saved", "type": "ai", "section": "Saved",
    },
]


class TestParseMdJobs(unittest.TestCase):
    def test_full_document_matches_golden(self):
        self.assertEqual(parse_md_jobs(SAMPLE_MD), EXPECTED_JOBS)

    def test_heading_without_at_is_not_a_job(self):
        self.assertIsNone(parse_job_entry("Just a section header", "", "Saved"))

    def test_bullet_without_match_returns_none(self):
        self.assertIsNone(parse_exported_job_bullet("- plain bullet text", "", "Saved"))


class TestParseCompValue(unittest.TestCase):
    GOLDEN = {
        "$150K–$200K": 150000, "$180K base": 180000, "": None, "not listed": None,
        "competitive": None, "$1,250,000": 1250000, "950": 950000,
        "market rate": None, "120k": 120000, "tbd": None,
    }

    def test_golden(self):
        for comp_str, expected in self.GOLDEN.items():
            self.assertEqual(parse_comp_value(comp_str), expected, comp_str)


class TestParseQueryChips(unittest.TestCase):
    def test_mixed_free_text_and_chips(self):
        free, chips = parse_query_chips("python loc:SF priority:8+ skill:pytorch")
        self.assertEqual(free, "python")
        self.assertEqual(
            chips,
            [
                {"key": "loc", "value": "SF", "label": "loc:sf"},
                {"key": "priority", "value": "8+", "label": "priority:8+"},
                {"key": "skill", "value": "pytorch", "label": "skill:pytorch"},
            ],
        )

    def test_unknown_key_and_empty_value_stay_free_text(self):
        free, chips = parse_query_chips("loc: type:ai unknown:x")
        self.assertEqual(free, "loc: unknown:x")
        self.assertEqual(chips, [{"key": "type", "value": "ai", "label": "type:ai"}])

    def test_pure_free_text(self):
        self.assertEqual(parse_query_chips("just free text"), ("just free text", []))


class TestParseMdStats(unittest.TestCase):
    def test_counts_and_unknown_modified_without_path(self):
        stats = parse_md_stats(SAMPLE_MD)
        self.assertEqual(stats["curated"], 2)       # "1." and "AI-SF-2."
        self.assertEqual(stats["new_fetched"], 1)   # "NEW-1."
        self.assertEqual(stats["total"], 3)
        self.assertEqual(stats["top_priority"], 1)  # one 9/10
        self.assertEqual(stats["last_modified"], "Unknown")


if __name__ == "__main__":
    unittest.main()
