import json
import tempfile
import unittest
from pathlib import Path

from jobsearch.apply.results import ApplyResult
from jobsearch.apply.review import create_review_dir, render_review_md, write_review_bundle


def make_result(**overrides) -> ApplyResult:
    base = dict(
        job_id=7,
        company="Acme Corp",
        title="iOS Engineer",
        job_url="https://example.com/job",
        application_url="https://example.com/job/apply",
        ats_provider="Lever",
        status="READY_FOR_REVIEW",
        attempted_at="2026-06-11T12:00:00+00:00",
        fields_completed=["email"],
        detected_count=2,
        detected_fields=[
            {"kind": "inputs", "label": "Email", "name": "email", "type": "email", "required": True},
            {"kind": "inputs", "label": "Salary expectation", "name": "salary", "type": "text", "required": False},
        ],
        filled_fields=[{"field": "email", "value": "me@example.com", "matched": {"label": "Email"}, "score": 2}],
        skipped_fields=[{"field": "salary", "reason": "no confident visible match (best score 1)"}],
        human_required_reason="final submit approval",
    )
    base.update(overrides)
    return ApplyResult(**base)


class TestReviewBundle(unittest.TestCase):
    def test_create_review_dir_uses_job_id_and_company_slug(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = create_review_dir(Path(tmp), make_result())
            self.assertTrue(path.is_dir())
            self.assertIn("_7_acme-corp", path.name)

    def test_write_review_bundle_emits_summary_and_review(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = make_result(review_dir=str(Path(tmp) / "attempt1"))
            review_dir = write_review_bundle(result)

            summary = json.loads((review_dir / "summary.json").read_text(encoding="utf-8"))
            self.assertEqual(summary["status"], "READY_FOR_REVIEW")
            self.assertEqual(summary["filled_fields"][0]["field"], "email")
            self.assertEqual(summary["skipped_fields"][0]["field"], "salary")

            review = (review_dir / "review.md").read_text(encoding="utf-8")
            self.assertIn("Acme Corp", review)
            self.assertIn("## Detected fields (2)", review)
            self.assertIn("## Filled (1)", review)
            self.assertIn("## Skipped (1)", review)
            self.assertIn("never clicks final submit", review)

    def test_render_review_md_shows_blockers(self):
        result = make_result(status="BLOCKED", blockers=["captcha"], filled_fields=[], skipped_fields=[], detected_fields=[])
        review = render_review_md(result)
        self.assertIn("## Blockers", review)
        self.assertIn("captcha", review)
        self.assertIn("_Nothing was filled._", review)


if __name__ == "__main__":
    unittest.main()
