#!/usr/bin/env python3
"""Export the job tracker to a Markdown snapshot.

Exit codes:
  0  export written (or dry run completed)
  1  fatal error
"""
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def main() -> int:
    parser = argparse.ArgumentParser(description="Export all tracked jobs to a Markdown file.")
    parser.add_argument(
        "--output", "-o", default=None,
        help="Output path (default: MARKDOWN_EXPORT_PATH from env/.env).",
    )
    parser.add_argument(
        "--group-by", default="status", choices=["status", "board", "company"],
        help="Field to group jobs under (default: status).",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Render and print a summary without writing the file.",
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="Debug logging.")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
    )

    from jobsearch.markdown_export import MarkdownExporter
    from jobsearch.settings import get_settings
    from jobsearch.store import JobStore

    store = JobStore()
    try:
        exporter = MarkdownExporter(store)
        if args.dry_run:
            content = exporter.render(group_by=args.group_by)
            count = len(store.get_all_jobs())
            target = args.output or get_settings().markdown_export_path
            print(f"Dry run: would export {count} jobs ({len(content)} chars) to {target}")
            return 0
        count, path = exporter.export(path=args.output, group_by=args.group_by)
        print(f"Exported {count} jobs to {path}")
        return 0
    finally:
        store.close()


if __name__ == "__main__":
    raise SystemExit(main())
