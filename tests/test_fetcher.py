import asyncio
import unittest

from jobsearch.boards import BoardFetchResult
from jobsearch.fetcher import JobFetcher
from jobsearch.store import JobStore


def make_job(url: str, company: str = "Acme") -> dict:
    return {
        "company": company,
        "title": "iOS Engineer",
        "location": "Remote",
        "url": url,
        "board": "fake",
        "description": "",
    }


class FakeFetcher:
    def __init__(self, result=None, exc=None):
        self._result = result
        self._exc = exc

    async def fetch(self, client, config):
        if self._exc:
            raise self._exc
        return self._result


class TestFetchReport(unittest.TestCase):
    def run_fetch(self, fetchers, dry_run=False):
        store = JobStore(db_path=":memory:")
        fetcher = JobFetcher(store)
        fetcher.fetchers = fetchers
        report = asyncio.run(fetcher.run_fetch_and_store(dry_run=dry_run))
        return store, report

    def test_board_failure_is_distinguishable_from_empty(self):
        store, report = self.run_fetch({
            "greenhouse": FakeFetcher(result=BoardFetchResult(jobs=[], companies_total=5)),
            "lever": FakeFetcher(exc=RuntimeError("boom")),
            "ashby": FakeFetcher(result=BoardFetchResult(jobs=[], companies_total=4, companies_failed=4)),
        })
        self.assertEqual(sorted(report.failed_boards), ["ashby", "lever"])
        self.assertFalse(report.ok)
        # greenhouse genuinely returned nothing and is not marked failed
        gh = next(b for b in report.boards if b.board == "greenhouse")
        self.assertFalse(gh.failed)
        store.close()

    def test_healthy_run_stores_jobs_and_reports_ok(self):
        result = BoardFetchResult(jobs=[make_job("https://x/1"), make_job("https://x/2")], companies_total=2)
        store, report = self.run_fetch({
            "greenhouse": FakeFetcher(result=result),
            "lever": FakeFetcher(result=BoardFetchResult(companies_total=1)),
            "ashby": FakeFetcher(result=BoardFetchResult(companies_total=1)),
        })
        self.assertTrue(report.ok)
        self.assertEqual(report.inserted, 2)
        self.assertEqual(len(store.get_all_jobs()), 2)
        store.close()

    def test_degraded_board_reported_but_not_failed(self):
        result = BoardFetchResult(jobs=[make_job("https://x/1")], companies_total=10, companies_failed=3)
        store, report = self.run_fetch({
            "greenhouse": FakeFetcher(result=result),
            "lever": FakeFetcher(result=BoardFetchResult(companies_total=1)),
            "ashby": FakeFetcher(result=BoardFetchResult(companies_total=1)),
        })
        self.assertEqual(report.degraded_boards, ["greenhouse"])
        self.assertEqual(report.failed_boards, [])
        store.close()

    def test_dry_run_writes_nothing(self):
        result = BoardFetchResult(jobs=[make_job("https://x/1")], companies_total=1)
        store, report = self.run_fetch({
            "greenhouse": FakeFetcher(result=result),
            "lever": FakeFetcher(result=BoardFetchResult(companies_total=1)),
            "ashby": FakeFetcher(result=BoardFetchResult(companies_total=1)),
        }, dry_run=True)
        self.assertEqual(report.inserted, 1)
        self.assertTrue(report.dry_run)
        self.assertEqual(len(store.get_all_jobs()), 0)
        store.close()

    def test_rerun_is_idempotent(self):
        def fetchers():
            return {
                "greenhouse": FakeFetcher(result=BoardFetchResult(jobs=[make_job("https://x/1")], companies_total=1)),
                "lever": FakeFetcher(result=BoardFetchResult(companies_total=1)),
                "ashby": FakeFetcher(result=BoardFetchResult(companies_total=1)),
            }
        store = JobStore(db_path=":memory:")
        fetcher = JobFetcher(store)
        fetcher.fetchers = fetchers()
        first = asyncio.run(fetcher.run_fetch_and_store())
        fetcher.fetchers = fetchers()
        second = asyncio.run(fetcher.run_fetch_and_store())
        self.assertEqual(first.inserted, 1)
        self.assertEqual(second.inserted, 0)
        self.assertEqual(second.updated, 1)
        self.assertEqual(len(store.get_all_jobs()), 1)
        store.close()


if __name__ == "__main__":
    unittest.main()
