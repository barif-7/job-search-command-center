"""Sync all jobs from the local SQLite database to Notion.

Requires NOTION_API_KEY and NOTION_JOBS_DATABASE_ID to be set in the
environment (or a .env file at the project root).  Set ENABLE_NOTION_SYNC=true
to activate the sync; otherwise this script exits with a notice.
"""
import sys
from pathlib import Path

# Allow running from the scripts/ directory or the project root
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv
load_dotenv()

from jobsearch.store import JobStore
from jobsearch.notion_sync import upsert_job_to_notion, ENABLE_NOTION_SYNC

def main():
    if not ENABLE_NOTION_SYNC:
        print("Notion sync is disabled. Set ENABLE_NOTION_SYNC=true in .env to enable it.")
        return

    store = JobStore()
    jobs = store.get_all_jobs()
    store.close()

    if not jobs:
        print("No jobs found in the database.")
        return

    synced = 0
    failed = 0
    for job in jobs:
        page_id = upsert_job_to_notion(job)
        if page_id:
            synced += 1
        else:
            failed += 1

    print(f"Notion sync complete. Synced: {synced}, Failed/Skipped: {failed}")

if __name__ == "__main__":
    main()
