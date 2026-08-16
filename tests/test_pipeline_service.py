"""Tests for the pipeline (script execution) service.

Command construction is pinned here; it mirrors the inline subprocess calls
the dashboard used before extraction.
"""
import sys
import unittest
from pathlib import Path

from jobsearch.services import pipeline_service as P


class TestCommandConstruction(unittest.TestCase):
    def test_repo_root_contains_scripts(self):
        self.assertTrue((P.REPO_ROOT / "scripts" / "run_fetch.py").exists())
        self.assertTrue((P.REPO_ROOT / "scripts" / "run_auto_apply.py").exists())

    def test_fetch_command(self):
        self.assertEqual(
            P.fetch_command(),
            [sys.executable, str(P.SCRIPTS_DIR / "run_fetch.py")],
        )

    def test_extract_keywords_command(self):
        self.assertEqual(
            P.extract_keywords_command(limit=50, offset=100),
            [
                sys.executable,
                str(P.SCRIPTS_DIR / "extract_keywords.py"),
                "--limit",
                "50",
                "--offset",
                "100",
            ],
        )

    def test_extract_keywords_command_with_urls(self):
        self.assertEqual(
            P.extract_keywords_command(limit=50, offset=0, urls=["https://a.example", "https://b.example"]),
            [
                sys.executable,
                str(P.SCRIPTS_DIR / "extract_keywords.py"),
                "--limit",
                "50",
                "--offset",
                "0",
                "--url",
                "https://a.example",
                "--url",
                "https://b.example",
            ],
        )

    def test_auto_apply_minimal(self):
        self.assertEqual(
            P.auto_apply_command(limit=3),
            [sys.executable, str(P.SCRIPTS_DIR / "run_auto_apply.py"), "--limit", "3"],
        )

    def test_auto_apply_all_flags(self):
        cmd = P.auto_apply_command(limit=5, status="Interested", min_priority="4", job_id=42, dry_run=True)
        self.assertEqual(
            cmd,
            [
                sys.executable, str(P.SCRIPTS_DIR / "run_auto_apply.py"),
                "--limit", "5",
                "--status", "Interested",
                "--min-priority", "4",
                "--job-id", "42",
                "--dry-run",
            ],
        )

    def test_auto_apply_omits_falsy_optionals(self):
        # None status / min_priority and job_id 0 are omitted (matches UI "Any"/0).
        cmd = P.auto_apply_command(limit=1, status=None, min_priority=None, job_id=0)
        self.assertEqual(
            cmd,
            [sys.executable, str(P.SCRIPTS_DIR / "run_auto_apply.py"), "--limit", "1"],
        )


class TestRunCommand(unittest.TestCase):
    def test_run_command_captures_output_and_code(self):
        result = P.run_command([sys.executable, "-c", "import sys; print('hi'); sys.exit(3)"])
        self.assertEqual(result.returncode, 3)
        self.assertEqual(result.stdout.strip(), "hi")


if __name__ == "__main__":
    unittest.main()
