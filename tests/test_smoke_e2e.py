"""End-to-end smoke test: does the workflow loop still hang together?

Exercises fetch (mocked boards) → store (real temp DB file with migrations)
→ markdown export → apply queue build + preview. No live network, no browser.
"""
import asyncio
import tempfile
import unittest
from pathlib import Path

from jobsearch.apply.runner import build_apply_queue, preview_queue
from jobsearch.boards import BoardFetchResult
from jobsearch.fetcher import JobFetcher
from jobsearch.markdown_export import MarkdownExporter
from jobsearch.store import JobStore

FIXTURE_JOBS = [
    {
        "company": "Acme",
        "title": "iOS Engineer",
        "location": "Remote",
        "url": "https://jobs.lever.co/acme/1",
        "board": "lever",
        "description": "",
    },
    {
        "company": "Globex",
        "title": "Senior iOS Engineer",
        "location": "NYC",
        "url": "https://boards.greenhouse.io/globex/jobs/2",
        "board": "greenhouse",
        "description": "",
    },
]


class FakeBoard:
    def __init__(self, jobs=None, exc=None):
        self._jobs = jobs or []
        self._exc = exc

    async def fetch(self, client, config):
        if self._exc:
            raise self._exc
        return BoardFetchResult(jobs=list(self._jobs), companies_total=1)


class TestWorkflowSmoke(unittest.TestCase):
    def test_full_loop_on_temp_db(self):
        with tempfile.TemporaryDirectory() as tmp:
            db_path = str(Path(tmp) / "jobs.db")
            export_path = Path(tmp) / "out.md"

            # Fetch (mocked boards, one of them down) → store
            store = JobStore(db_path=db_path)
            fetcher = JobFetcher(store)
            fetcher.fetchers = {
                "lever": FakeBoard(jobs=[FIXTURE_JOBS[0]]),
                "greenhouse": FakeBoard(jobs=[FIXTURE_JOBS[1]]),
                "ashby": FakeBoard(exc=RuntimeError("board down")),
            }
            report = asyncio.run(fetcher.run_fetch_and_store())
            self.assertEqual(report.total_fetched, 2)
            self.assertEqual(report.failed_boards, ["ashby"])
            self.assertFalse(report.ok)  # partial failure is surfaced, not hidden
            self.assertEqual(len(store.get_all_jobs()), 2)

            # Re-run is idempotent: same postings, no duplicate rows
            asyncio.run(fetcher.run_fetch_and_store())
            self.assertEqual(len(store.get_all_jobs()), 2)

            # Export
            count, written = MarkdownExporter(store).export(path=str(export_path))
            self.assertEqual(count, 2)
            content = written.read_text(encoding="utf-8")
            self.assertIn("Acme", content)
            self.assertIn("https://boards.greenhouse.io/globex/jobs/2", content)
            self.assertNotIn("\\n", content)  # real newlines, not escaped

            # Apply queue build + preview (no browser)
            store.update_job_status(FIXTURE_JOBS[0]["url"], "Interested")
            queue = build_apply_queue(store, status="Interested", limit=5)
            self.assertEqual(len(queue), 1)
            preview = preview_queue(queue)
            self.assertEqual(preview[0]["company"], "Acme")
            self.assertEqual(preview[0]["ats_provider"], "Lever")
            self.assertTrue(preview[0]["application_url"])

            # Attempt audit trail is wired into the same DB
            attempt_id = store.record_application_attempt(
                job_url=FIXTURE_JOBS[0]["url"],
                attempted_at="2026-06-11T00:00:00+00:00",
                status="READY_FOR_REVIEW",
            )
            self.assertIsNotNone(attempt_id)
            self.assertEqual(len(store.get_application_attempts(FIXTURE_JOBS[0]["url"])), 1)
            store.close()


if __name__ == "__main__":
    unittest.main()
