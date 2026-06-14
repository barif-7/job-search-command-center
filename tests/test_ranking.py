"""Characterization tests for the ranking logic extracted from app.py.

Expected values captured from the original in-app implementations (golden
master) before extraction.
"""
import json
import tempfile
import unittest
from pathlib import Path

from jobsearch.ranking.clustering import cluster_jobs, jaccard, title_tokens
from jobsearch.ranking.filters import apply_filters
from jobsearch.ranking.keywords import load_keyword_data

JOBS = [
    {"company": "Anthropic", "title": "Senior iOS Engineer", "url": "u1", "comp": "$200K", "location": "San Francisco", "board": "greenhouse", "fit": "", "concerns": "", "priority": 9, "status": "New", "type": "top"},
    {"company": "OpenAI", "title": "Forward Deployed Engineer", "url": "u2", "comp": "$300K", "location": "New York", "board": "lever", "fit": "", "concerns": "", "priority": 8, "status": "New", "type": "ai"},
    {"company": "Faire", "title": "Mobile Engineer iOS", "url": "u3", "comp": "", "location": "Toronto", "board": "greenhouse", "fit": "", "concerns": "", "priority": 6, "status": "New", "type": "ios"},
    {"company": "Ramp", "title": "Machine Learning Engineer", "url": "u4", "comp": "$150K-$200K", "location": "Remote", "board": "lever", "fit": "", "concerns": "", "priority": 0, "status": "New", "type": "new"},
]
KW = {"u1": {"swift", "ios", "mobile"}, "u2": {"python", "pytorch", "ml"}, "u3": {"swift", "ios", "mobile"}, "u4": {"python", "ml"}}


def companies(free, chips):
    return [j["company"] for j in apply_filters(JOBS, free, chips, KW)]


class TestApplyFilters(unittest.TestCase):
    def test_free_text_company(self):
        self.assertEqual(companies("anthropic", []), ["Anthropic"])

    def test_free_text_matches_via_keywords(self):
        self.assertEqual(companies("swift", []), ["Anthropic", "Faire"])

    def test_loc_substring_is_literal(self):
        # "sf" is not a substring of "san francisco" — pinned current behavior.
        self.assertEqual(companies("", [{"key": "loc", "value": "SF"}]), [])
        self.assertEqual(companies("", [{"key": "loc", "value": "new york"}]), ["OpenAI"])

    def test_type_chip(self):
        self.assertEqual(companies("", [{"key": "type", "value": "ai"}]), ["OpenAI"])

    def test_priority_threshold_range_and_exact(self):
        self.assertEqual(companies("", [{"key": "priority", "value": "8+"}]), ["Anthropic", "OpenAI"])
        self.assertEqual(companies("", [{"key": "priority", "value": "6-8"}]), ["OpenAI", "Faire"])
        self.assertEqual(companies("", [{"key": "priority", "value": "9"}]), ["Anthropic"])

    def test_skill_company_board(self):
        self.assertEqual(companies("", [{"key": "skill", "value": "pytorch"}]), ["OpenAI"])
        self.assertEqual(companies("", [{"key": "company", "value": "ramp"}]), ["Ramp"])
        self.assertEqual(companies("", [{"key": "board", "value": "lever"}]), ["OpenAI", "Ramp"])

    def test_src_new_and_curated(self):
        self.assertEqual(companies("", [{"key": "src", "value": "new"}]), ["Ramp"])
        self.assertEqual(companies("", [{"key": "src", "value": "curated"}]), ["Anthropic", "OpenAI", "Faire"])

    def test_comp_threshold_and_range(self):
        self.assertEqual(companies("", [{"key": "comp", "value": "250k+"}]), ["OpenAI"])
        self.assertEqual(companies("", [{"key": "comp", "value": "100k-220k"}]), ["Anthropic", "Ramp"])


class TestClustering(unittest.TestCase):
    def test_title_tokens_drop_stopwords_and_short(self):
        self.assertEqual(title_tokens("Senior iOS Engineer @ Anthropic"), {"anthropic", "ios"})

    def test_jaccard(self):
        self.assertEqual(jaccard({"a", "b", "c"}, {"b", "c", "d"}), 0.5)
        self.assertEqual(jaccard(set(), set()), 0.0)

    def test_cluster_grouping_and_order(self):
        clusters = cluster_jobs(JOBS, KW, threshold=0.25)
        summary = [(c["label"], [j["company"] for j in c["jobs"]], c["keywords"]) for c in clusters]
        self.assertEqual(
            summary,
            [
                ("Ios · Mobile · Swift", ["Anthropic", "Faire"], ["ios", "mobile", "swift"]),
                ("Ml · Python", ["OpenAI", "Ramp"], ["ml", "python"]),
            ],
        )

    def test_empty_jobs(self):
        self.assertEqual(cluster_jobs([], {}), [])


class TestLoadKeywordData(unittest.TestCase):
    def test_missing_path_returns_empty(self):
        self.assertEqual(load_keyword_data(None), {})
        self.assertEqual(load_keyword_data(Path("/no/such/file.json")), {})

    def test_aggregates_keywords_across_categories(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "keyword_report.json"
            p.write_text(json.dumps([
                {"url": "u1", "keywords": {"langs": ["swift"], "frameworks": ["swiftui", "uikit"]}},
            ]), encoding="utf-8")
            self.assertEqual(load_keyword_data(p), {"u1": {"swift", "swiftui", "uikit"}})


if __name__ == "__main__":
    unittest.main()
