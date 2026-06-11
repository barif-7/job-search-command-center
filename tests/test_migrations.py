import sqlite3
import tempfile
import unittest
from pathlib import Path

from jobsearch.store import JobStore


def index_names(store: JobStore) -> set[str]:
    store.cursor.execute("SELECT name FROM sqlite_master WHERE type = 'index'")
    return {row["name"] for row in store.cursor.fetchall()}


class TestMigrations(unittest.TestCase):
    def test_fresh_db_reaches_latest_version_with_indexes(self):
        store = JobStore(db_path=":memory:")
        self.assertGreaterEqual(store.schema_version(), 2)
        names = index_names(store)
        for expected in (
            "idx_jobs_status",
            "idx_jobs_application_status",
            "idx_jobs_date_found",
            "idx_jobs_priority",
            "idx_jobs_last_seen",
        ):
            self.assertIn(expected, names)
        store.close()

    def test_migrations_idempotent_on_rerun(self):
        with tempfile.TemporaryDirectory() as tmp:
            db_path = str(Path(tmp) / "jobs.db")
            store = JobStore(db_path=db_path)
            version = store.schema_version()
            store.close()
            store2 = JobStore(db_path=db_path)
            self.assertEqual(store2.schema_version(), version)
            store2.close()

    def test_legacy_db_is_upgraded_without_data_loss(self):
        with tempfile.TemporaryDirectory() as tmp:
            db_path = str(Path(tmp) / "jobs.db")
            conn = sqlite3.connect(db_path)
            conn.executescript(
                """
                CREATE TABLE jobs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    company TEXT, title TEXT, location TEXT,
                    normalized_location TEXT,
                    url TEXT UNIQUE NOT NULL,
                    board TEXT, description TEXT, compensation TEXT,
                    date_found TEXT, last_seen TEXT,
                    status TEXT DEFAULT 'New',
                    priority INTEGER, fit_score REAL, fit_summary TEXT,
                    notes TEXT, notion_page_id TEXT,
                    created_at TEXT, updated_at TEXT
                );
                INSERT INTO jobs (company, title, location, url, board, status)
                VALUES ('Acme', 'iOS Engineer', 'Remote', 'https://example.com/1', 'lever', 'Interested');
                """
            )
            conn.commit()
            conn.close()

            store = JobStore(db_path=db_path)
            self.assertGreaterEqual(store.schema_version(), 2)
            job = store.get_job_by_url("https://example.com/1")
            self.assertEqual(job.company, "Acme")
            self.assertEqual(job.status, "Interested")
            self.assertEqual(job.application_status, "NOT_STARTED")
            self.assertIn("idx_jobs_status", index_names(store))
            store.close()


if __name__ == "__main__":
    unittest.main()
