import unittest
from unittest import mock

from jobsearch.models import Job
from jobsearch.notion_sync import upsert_job_to_notion, _job_properties


def make_job(**kwargs) -> Job:
    defaults = dict(company="Acme", title="iOS Engineer", location="Remote",
                    url="https://example.com/1", board="lever")
    defaults.update(kwargs)
    return Job(**defaults)


class TestNotionSync(unittest.TestCase):
    def test_skipped_when_unconfigured(self):
        with mock.patch.dict("os.environ", {}, clear=True):
            with mock.patch("jobsearch.notion_sync.get_settings") as gs:
                gs.return_value.notion_configured = False
                outcome, page_id = upsert_job_to_notion(make_job())
        self.assertEqual(outcome, "skipped")
        self.assertIsNone(page_id)

    def test_updates_existing_page_found_by_url(self):
        client = mock.MagicMock()
        client.databases.query.return_value = {"results": [{"id": "page-123"}]}
        with mock.patch("jobsearch.notion_sync.get_settings") as gs:
            gs.return_value.notion_jobs_database_id = "db-1"
            outcome, page_id = upsert_job_to_notion(make_job(status="Interested"), client=client)

        self.assertEqual(outcome, "updated")
        self.assertEqual(page_id, "page-123")
        client.pages.update.assert_called_once()
        kwargs = client.pages.update.call_args.kwargs
        self.assertEqual(kwargs["page_id"], "page-123")
        self.assertEqual(kwargs["properties"]["Status"], {"select": {"name": "Interested"}})
        client.pages.create.assert_not_called()

    def test_uses_stored_page_id_without_querying(self):
        client = mock.MagicMock()
        with mock.patch("jobsearch.notion_sync.get_settings") as gs:
            gs.return_value.notion_jobs_database_id = "db-1"
            outcome, page_id = upsert_job_to_notion(
                make_job(notion_page_id="page-known"), client=client
            )
        self.assertEqual((outcome, page_id), ("updated", "page-known"))
        client.databases.query.assert_not_called()

    def test_creates_page_when_missing(self):
        client = mock.MagicMock()
        client.databases.query.return_value = {"results": []}
        client.pages.create.return_value = {"id": "page-new"}
        with mock.patch("jobsearch.notion_sync.get_settings") as gs:
            gs.return_value.notion_jobs_database_id = "db-1"
            outcome, page_id = upsert_job_to_notion(make_job(), client=client)
        self.assertEqual((outcome, page_id), ("created", "page-new"))

    def test_api_error_reports_failed(self):
        client = mock.MagicMock()
        client.databases.query.side_effect = RuntimeError("api down")
        with mock.patch("jobsearch.notion_sync.get_settings") as gs:
            gs.return_value.notion_jobs_database_id = "db-1"
            outcome, page_id = upsert_job_to_notion(make_job(), client=client)
        self.assertEqual((outcome, page_id), ("failed", None))

    def test_properties_drop_top_level_none(self):
        props = _job_properties(make_job())
        self.assertIn("Company", props)
        self.assertNotIn(None, props.values())


if __name__ == "__main__":
    unittest.main()
