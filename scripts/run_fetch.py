#!/usr/bin/env python3
"""Fetch jobs from all configured boards and store them in SQLite.

Exit codes:
  0  fetch completed, all boards healthy
  1  fatal error (could not run at all)
  2  fetch completed but at least one board failed entirely
"""
from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

logger = logging.getLogger("run_fetch")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Fetch jobs from Greenhouse/Lever/Ashby boards into the local database."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Fetch and report what would be inserted/updated without writing to the database.",
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="Debug logging.")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
    )

    from jobsearch.fetcher import JobFetcher
    from jobsearch.store import JobStore

    store = JobStore()
    fetcher = JobFetcher(store)
    try:
        report = asyncio.run(fetcher.run_fetch_and_store(dry_run=args.dry_run))
    finally:
        store.close()

    print("Fetch summary" + (" (dry run)" if args.dry_run else ""))
    for line in report.summary_lines():
        print(line)

    if report.failed_boards:
        print(f"WARNING: board(s) failed entirely: {', '.join(report.failed_boards)} — "
              f"results above are incomplete, not 'no new jobs'.")
        return 2
    if report.store_errors:
        print(f"WARNING: {report.store_errors} job(s) failed to store.")
        return 2
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        raise SystemExit(130)
