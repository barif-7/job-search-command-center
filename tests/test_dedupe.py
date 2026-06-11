import unittest
from jobsearch.store import JobStore

class TestDedup(unittest.TestCase):
    def test_dedupe_by_url(self):
        store = JobStore(db_path=':memory:')
        from jobsearch.models import Job
        j1 = Job(company='A', title='T', location='L', url='https://u/1')
        j2 = Job(company='A', title='T2', location='L', url='https://u/1')
        store.insert_or_update_job(j1)
        store.insert_or_update_job(j2)
        jobs = store.get_all_jobs()
        self.assertEqual(len(jobs), 1)
        store.close()
