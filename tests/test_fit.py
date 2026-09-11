"""Tests for jobsearch.ranking.fit."""
from __future__ import annotations

import unittest

from jobsearch.ranking.fit import rank_jobs_by_fit, score_job_fit


class FitScoringTests(unittest.TestCase):
    def test_platform_role_scores_higher_than_unrelated(self):
        platform = {
            "title": "Senior AI Platform Engineer",
            "company": "Example",
            "location": "Remote",
            "description": "Own LLM inference, RAG pipelines, and agent tooling on GPU clusters.",
            "url": "https://example.com/a",
        }
        unrelated = {
            "title": "Junior Marketing Coordinator",
            "company": "Example",
            "location": "Remote",
            "description": "Social media calendar and brand guidelines.",
            "url": "https://example.com/b",
        }
        s1 = score_job_fit(platform, preset_keys=["ai_platform", "rag_retrieval"])
        s2 = score_job_fit(unrelated, preset_keys=["ai_platform", "rag_retrieval"])
        self.assertGreater(s1["fit_score"], s2["fit_score"])
        self.assertGreaterEqual(s1["fit_score"], 20)
        self.assertTrue(s1["matched_signals"] or s1["preset_hits"])

    def test_rank_jobs_by_fit_orders_descending(self):
        jobs = [
            {"title": "Marketing Intern", "company": "X", "location": "", "url": "u1"},
            {
                "title": "MLOps Engineer",
                "company": "Y",
                "location": "Toronto",
                "description": "Kubernetes, model serving, inference",
                "url": "u2",
            },
        ]
        ranked = rank_jobs_by_fit(jobs, preset_keys=["ai_platform"])
        self.assertEqual(ranked[0]["url"], "u2")
        self.assertIn("fit_score", ranked[0])


if __name__ == "__main__":
    unittest.main()

