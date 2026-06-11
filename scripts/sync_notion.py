#!/usr/bin/env python3
"""Sync all jobs from the local SQLite database to Notion.

Requires NOTION_API_KEY and NOTION_JOBS_DATABASE_ID (env or .env) and
ENABLE_NOTION_SYNC=true. When sync is disabled or unconfigured this is a
clean no-op, not an error.

Exit codes:
  0  sync completed (or cleanly disabled)
  1  fatal error
  2  sync completed but some jobs failed
"""
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

# Allow running from the scripts/ directory or the project root
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

logger = logging.getLogger("sync_notion")


def main() -> int:
    parser = argparse.ArgumentParser(description="Sync tracked jobs to a Notion database.")
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Report what would be synced without calling Notion.",
    )
    parser.add_argument(
        "--limit", type=int, default=None,
        help="Sync at most N jobs (useful for testing credentials).",
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="Debug logging.")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
    )

    from jobsearch.notion_sync import notion_sync_enabled, upsert_job_to_notion
    from jobsearch.store import JobStore

    if not notion_sync_enabled():
        print(
            "Notion sync is disabled or unconfigured "
            "(needs ENABLE_NOTION_SYNC=true, NOTION_API_KEY, NOTION_JOBS_DATABASE_ID). Nothing to do."
        )
        return 0

    store = JobStore()
    try:
        jobs = store.get_all_jobs()
        if args.limit is not None:
            jobs = jobs[: args.limit]

        if not jobs:
            print("No jobs found in the database.")
            return 0

        if args.dry_run:
            with_page = sum(1 for j in jobs if j.notion_page_id)
            print(
                f"Dry run: would sync {len(jobs)} jobs "
                f"({with_page} with a known Notion page, {len(jobs) - with_page} without)."
            )
            return 0

        created = updated = failed = 0
        for job in jobs:
            outcome, page_id = upsert_job_to_notion(job)
            if outcome == "created":
                created += 1
            elif outcome == "updated":
                updated += 1
            else:
                failed += 1
            if page_id and page_id != job.notion_page_id:
                store.set_notion_page_id(job.url, page_id)

        print(
            f"Notion sync complete. Created: {created}, Updated: {updated}, Failed: {failed} "
            f"(of {len(jobs)} jobs)"
        )
        return 2 if failed else 0
    finally:
        store.close()


if __name__ == "__main__":
    raise SystemExit(main())
