#!/usr/bin/env python3
"""Extract lightweight keyword metadata for a page of tracked jobs.

Writes keyword_report.json in the repo root. The dashboard uses that artifact
to power skill: filters and grouping in the Opportunity Feed.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from jobsearch.models import Job
from jobsearch.store import JobStore

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUTPUT = REPO_ROOT / "keyword_report.json"

KEYWORD_PATTERNS: dict[str, dict[str, list[str]]] = {
    "languages": {
        "python": [r"\bpython\b"],
        "swift": [r"\bswift\b"],
        "typescript": [r"\btypescript\b", r"\bts\b"],
        "javascript": [r"\bjavascript\b", r"\bjs\b"],
        "go": [r"\bgolang\b", r"\bgo\b"],
        "java": [r"\bjava\b"],
        "kotlin": [r"\bkotlin\b"],
        "rust": [r"\brust\b"],
        "sql": [r"\bsql\b"],
    },
    "frameworks": {
        "swiftui": [r"\bswiftui\b"],
        "uikit": [r"\buikit\b"],
        "react": [r"\breact\b"],
        "next.js": [r"\bnext\.?js\b"],
        "node.js": [r"\bnode\.?js\b"],
        "django": [r"\bdjango\b"],
        "fastapi": [r"\bfastapi\b"],
        "pytorch": [r"\bpytorch\b"],
        "tensorflow": [r"\btensorflow\b"],
    },
    "platforms": {
        "ios": [r"\bios\b", r"\biphone\b", r"\bipad\b"],
        "mobile": [r"\bmobile\b"],
        "android": [r"\bandroid\b"],
        "backend": [r"\bbackend\b", r"\bback-end\b"],
        "frontend": [r"\bfrontend\b", r"\bfront-end\b"],
        "full-stack": [r"\bfull[- ]stack\b"],
        "cloud": [r"\bcloud\b"],
    },
    "tools": {
        "aws": [r"\baws\b", r"\bamazon web services\b"],
        "gcp": [r"\bgcp\b", r"\bgoogle cloud\b"],
        "azure": [r"\bazure\b"],
        "docker": [r"\bdocker\b"],
        "kubernetes": [r"\bkubernetes\b", r"\bk8s\b"],
        "postgres": [r"\bpostgres(?:ql)?\b"],
        "sqlite": [r"\bsqlite\b"],
        "graphql": [r"\bgraphql\b"],
    },
    "domains": {
        "ai": [r"\bai\b", r"\bartificial intelligence\b"],
        "machine learning": [r"\bmachine learning\b", r"\bml\b"],
        "llm": [r"\bllm\b", r"\blarge language model"],
        "product": [r"\bproduct\b"],
        "growth": [r"\bgrowth\b"],
        "infrastructure": [r"\binfrastructure\b", r"\bplatform\b"],
        "security": [r"\bsecurity\b"],
        "fintech": [r"\bfintech\b", r"\bpayments?\b"],
    },
}


def _matches(text: str, patterns: list[str]) -> bool:
    return any(re.search(pattern, text, flags=re.IGNORECASE) for pattern in patterns)


def extract_keywords(job: Job) -> dict[str, list[str]]:
    text = " ".join(
        value
        for value in [job.title, job.description, job.location, job.board]
        if value
    )
    keywords: dict[str, list[str]] = {}
    for category, candidates in KEYWORD_PATTERNS.items():
        hits = [
            keyword
            for keyword, patterns in candidates.items()
            if _matches(text, patterns)
        ]
        if hits:
            keywords[category] = sorted(hits)
    return keywords


def _select_jobs(jobs: list[Job], urls: list[str], limit: int, offset: int) -> list[Job]:
    if urls:
        by_url = {job.url: job for job in jobs}
        return [by_url[url] for url in urls if url in by_url][:limit]
    return jobs[offset : offset + limit]


def build_report(jobs: list[Job]) -> list[dict]:
    report = []
    for job in jobs:
        report.append(
            {
                "company": job.company,
                "title": job.title,
                "url": job.url,
                "keywords": extract_keywords(job),
            }
        )
    return report


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Extract keyword metadata from tracked jobs into keyword_report.json."
    )
    parser.add_argument("--limit", type=int, default=50, help="Maximum jobs to process.")
    parser.add_argument("--offset", type=int, default=0, help="Zero-based job offset.")
    parser.add_argument("--url", action="append", default=[], help="Exact job URL to include.")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT, help="Output JSON path.")
    args = parser.parse_args()

    limit = max(1, int(args.limit))
    offset = max(0, int(args.offset))

    store = JobStore()
    try:
        selected = _select_jobs(store.get_all_jobs(), args.url, limit, offset)
    finally:
        store.close()

    report = build_report(selected)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")

    with_keywords = sum(1 for entry in report if entry["keywords"])
    print(
        f"Extracted keywords for {len(report)} job(s) "
        f"({with_keywords} with at least one keyword) -> {args.output}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
