#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from jobsearch.apply.runner import build_apply_queue, preview_queue, run_apply_batch
from jobsearch.store import JobStore


def main() -> int:
    parser = argparse.ArgumentParser(description="Safely open and fill job applications without submitting.")
    parser.add_argument("--limit", type=int, default=5)
    parser.add_argument("--status", default=None, help="Filter tracker status, e.g. Interested")
    parser.add_argument("--min-priority", type=int, default=None)
    parser.add_argument("--job-id", type=int, default=None)
    parser.add_argument("--dry-run", action="store_true", help="Print the queue without opening a browser.")
    parser.add_argument("--headless", action="store_true", help="Run Chromium headless. Headed is safer for review.")
    args = parser.parse_args()

    store = JobStore()
    jobs = build_apply_queue(
        store,
        status=args.status,
        min_priority=args.min_priority,
        limit=args.limit,
        job_id=args.job_id,
    )
    if args.dry_run:
        print(json.dumps({"queue": preview_queue(jobs)}, indent=2, ensure_ascii=False))
        return 0
    if not jobs:
        print(json.dumps({"results": [], "message": "No jobs matched the queue filters."}, indent=2))
        return 0

    results = run_apply_batch(store, jobs, headless=args.headless)
    print(json.dumps({"results": [r.to_dict() for r in results]}, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
