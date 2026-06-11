import unittest

from jobsearch.apply.runner import build_apply_queue, preview_queue
from jobsearch.models import Job
from jobsearch.store import JobStore


class TestApplyRunner(unittest.TestCase):
    def test_build_apply_queue_filters_submitted_jobs(self):
        store = JobStore(db_path=":memory:")
        first = Job(company="A", title="iOS Engineer", location="Remote", url="https://jobs.lever.co/a/1", board="lever", status="Interested", priority=5)
        second = Job(company="B", title="iOS Engineer", location="Remote", url="https://jobs.lever.co/b/1", board="lever", status="Interested", priority=5)
        store.insert_or_update_job(first)
        store.insert_or_update_job(second)
        store.update_application_state(second.url, application_status="SUBMITTED", touch_attempt=False)

        queue = build_apply_queue(store, status="Interested", min_priority=4, limit=10)

        self.assertEqual(len(queue), 1)
        self.assertEqual(queue[0].company, "A")
        store.close()

    def test_preview_queue_includes_application_url(self):
        store = JobStore(db_path=":memory:")
        job = Job(company="A", title="iOS Engineer", location="Remote", url="https://jobs.lever.co/a/1", board="lever", status="Interested", priority=5)
        store.insert_or_update_job(job)
        queue = build_apply_queue(store, status="Interested", limit=1)

        preview = preview_queue(queue)

        self.assertEqual(preview[0]["ats_provider"], "Lever")
        self.assertTrue(preview[0]["application_url"].endswith("/apply"))
        store.close()


if __name__ == "__main__":
    unittest.main()
