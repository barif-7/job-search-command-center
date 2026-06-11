import unittest
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

if __name__ == '__main__':
    unittest.main()
