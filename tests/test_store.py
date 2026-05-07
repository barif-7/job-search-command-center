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

if __name__ == '__main__':
    unittest.main()
