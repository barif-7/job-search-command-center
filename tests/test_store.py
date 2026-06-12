import unittest
from datetime import datetime, timezone

from jobsearch.store import JobStore
from jobsearch.models import Job

class TestStore(unittest.TestCase):
    def test_insert_and_update(self):
        store = JobStore(db_path=':memory:')
        # Insert a job
        job = Job(company='Acme', title='Test Dev', location='Remote', url='https://example.com/job1')
        inserted = store.insert_or_update_job(job)
        self.assertTrue(inserted)
        # Update the same job's notes (user-managed field)
        updated = store.update_job_details(url='https://example.com/job1', notes='Interesting role')
        self.assertTrue(updated)
        store.close()

    def test_update_application_state(self):
        store = JobStore(db_path=':memory:')
        job = Job(company='Acme', title='Test Dev', location='Remote', url='https://example.com/job2')
        store.insert_or_update_job(job)
        updated = store.update_application_state(
            url='https://example.com/job2',
            application_status='READY_FOR_REVIEW',
            application_url='https://example.com/job2/apply',
            ats_provider='Unknown',
            fields_completed='email, phone',
            resume_uploaded=True,
            human_required_reason='final submit approval',
        )
        self.assertTrue(updated)
        saved = store.get_job_by_url('https://example.com/job2')
        self.assertEqual(saved.application_status, 'READY_FOR_REVIEW')
        self.assertEqual(saved.application_url, 'https://example.com/job2/apply')
        self.assertTrue(saved.resume_uploaded)
        store.close()

    def test_refetch_preserves_user_fields_and_date_found(self):
        """A re-run of fetch must never clobber user-managed fields or date_found."""
        store = JobStore(db_path=':memory:')
        url = 'https://example.com/job3'
        first_seen = datetime(2026, 1, 5, tzinfo=timezone.utc)
        original = Job(company='Acme', title='iOS Engineer', location='Remote',
                       url=url, board='lever', date_found=first_seen)
        self.assertTrue(store.insert_or_update_job(original))

        # User curates the job between fetch runs
        store.update_job_status(url, 'Interested')
        store.update_job_details(url, priority=5, notes='dream team')

        # Same posting comes back from a later fetch with a fresh date_found
        refetched = Job(company='Acme', title='iOS Engineer (Senior)', location='Remote',
                        url=url, board='lever',
                        date_found=datetime(2026, 2, 1, tzinfo=timezone.utc))
        result = store.insert_or_update_job(refetched)
        self.assertFalse(result)  # updated, not inserted

        saved = store.get_job_by_url(url)
        self.assertEqual(saved.status, 'Interested')
        self.assertEqual(saved.priority, 5)
        self.assertEqual(saved.notes, 'dream team')
        self.assertEqual(saved.date_found, first_seen)
        # Non-user fields do refresh
        self.assertEqual(saved.title, 'iOS Engineer (Senior)')
        self.assertEqual(len(store.get_all_jobs()), 1)
        store.close()
    def test_application_attempts_keep_full_history(self):
        """The jobs row keeps latest state only; attempts accumulate one row each."""
        store = JobStore(db_path=':memory:')
        url = 'https://example.com/job4'
        store.insert_or_update_job(Job(company='Acme', title='Test Dev', location='Remote', url=url))

        first = store.record_application_attempt(
            job_url=url, attempted_at='2026-06-01T10:00:00+00:00',
            status='BLOCKED', blockers='captcha', review_dir='/tmp/r1',
        )
        second = store.record_application_attempt(
            job_url=url, attempted_at='2026-06-02T10:00:00+00:00',
            status='READY_FOR_REVIEW', detected_count=12,
            fields_completed='email, phone', resume_uploaded=True, review_dir='/tmp/r2',
        )
        self.assertIsNotNone(first)
        self.assertIsNotNone(second)
        self.assertNotEqual(first, second)

        attempts = store.get_application_attempts(url)
        self.assertEqual(len(attempts), 2)
        # Most recent first
        self.assertEqual(attempts[0]['status'], 'READY_FOR_REVIEW')
        self.assertEqual(attempts[0]['detected_count'], 12)
        self.assertEqual(attempts[0]['resume_uploaded'], 1)
        self.assertEqual(attempts[1]['status'], 'BLOCKED')
        self.assertEqual(attempts[1]['blockers'], 'captcha')
        store.close()


if __name__ == '__main__':
    unittest.main()
