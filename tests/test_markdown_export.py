import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from jobsearch.markdown_export import MarkdownExporter
from jobsearch.models import Job
from jobsearch.store import JobStore


def seeded_store() -> JobStore:
    store = JobStore(db_path=":memory:")
    store.insert_or_update_job(Job(
        company="Acme", title="iOS Engineer", location="Remote",
        url="https://example.com/1", board="lever",
        date_found=datetime(2026, 1, 5, tzinfo=timezone.utc),
    ))
    store.insert_or_update_job(Job(
        company="Globex", title="ML Engineer", location="Toronto",
        url="https://example.com/2", board="greenhouse",
        date_found=datetime(2026, 1, 6, tzinfo=timezone.utc),
        status="Interested", notes="ping referral",
    ))
    return store


class TestMarkdownExport(unittest.TestCase):
    def test_render_structure_uses_real_newlines(self):
        store = seeded_store()
        content = MarkdownExporter(store).render()
        store.close()

        self.assertNotIn("\\n", content)
        lines = content.splitlines()
        self.assertEqual(lines[0], "# Job Search Results")
        self.assertIn("## Interested", lines)
        self.assertIn("## New", lines)
        self.assertIn("- **[Acme]** iOS Engineer — Remote (lever, 2026-01-05)", lines)
        self.assertIn("  https://example.com/1", lines)
        self.assertIn("  _Notes: ping referral_", lines)
        # statuses are sorted alphabetically
        self.assertLess(lines.index("## Interested"), lines.index("## New"))

    def test_export_honors_explicit_path(self):
        store = seeded_store()
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "nested" / "out.md"
            count, path = MarkdownExporter(store).export(path=str(target))
            self.assertEqual(count, 2)
            self.assertEqual(path, target)
            self.assertTrue(target.exists())
            self.assertTrue(target.read_text().startswith("# Job Search Results"))
        store.close()

    def test_export_honors_settings_path(self):
        from unittest import mock
        store = seeded_store()
        with tempfile.TemporaryDirectory() as tmp:
            target = str(Path(tmp) / "settings-out.md")
            with mock.patch("jobsearch.markdown_export.get_settings") as gs:
                gs.return_value.markdown_export_path = target
                count, path = MarkdownExporter(store).export()
            self.assertEqual(str(path), target)
            self.assertTrue(Path(target).exists())
        store.close()

    def test_group_by_board(self):
        store = seeded_store()
        content = MarkdownExporter(store).render(group_by="board")
        store.close()
        self.assertIn("## lever", content)
        self.assertIn("## greenhouse", content)


if __name__ == "__main__":
    unittest.main()
