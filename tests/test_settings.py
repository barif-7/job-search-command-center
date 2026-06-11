import unittest
from unittest import mock

from jobsearch.settings import load_settings


class TestSettings(unittest.TestCase):
    def test_defaults_with_no_env(self):
        with mock.patch.dict("os.environ", {}, clear=True):
            s = load_settings()
        self.assertTrue(s.database_path.endswith("data/jobs.db"))
        self.assertTrue(s.markdown_export_path.endswith("job-search-results.md"))
        self.assertFalse(s.enable_notion_sync)
        self.assertFalse(s.notion_configured)
        self.assertEqual(s.notion_api_key, "")
        self.assertEqual(s.anthropic_api_key, "")

    def test_env_overrides(self):
        env = {
            "DATABASE_PATH": "/tmp/x.db",
            "MARKDOWN_EXPORT_PATH": "/tmp/out.md",
            "ENABLE_NOTION_SYNC": "true",
            "NOTION_API_KEY": "secret",
            "NOTION_JOBS_DATABASE_ID": "dbid",
        }
        with mock.patch.dict("os.environ", env, clear=True):
            s = load_settings()
        self.assertEqual(s.database_path, "/tmp/x.db")
        self.assertEqual(s.markdown_export_path, "/tmp/out.md")
        self.assertTrue(s.enable_notion_sync)
        self.assertTrue(s.notion_configured)

    def test_notion_not_configured_without_credentials(self):
        with mock.patch.dict("os.environ", {"ENABLE_NOTION_SYNC": "1"}, clear=True):
            s = load_settings()
        self.assertTrue(s.enable_notion_sync)
        self.assertFalse(s.notion_configured)


if __name__ == "__main__":
    unittest.main()
