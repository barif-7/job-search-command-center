import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List

import httpx

from .models import Job
from .utils import normalize_location
from .boards import BoardFetchResult
from .boards.greenhouse import GreenhouseFetcher
from .boards.lever import LeverFetcher
from .boards.ashby import AshbyFetcher
from .store import JobStore
from config import DEFAULT_BOARD_CONFIG, USER_AGENT

logger = logging.getLogger(__name__)


@dataclass
class BoardReport:
    board: str
    job_count: int = 0
    companies_total: int = 0
    companies_failed: int = 0
    error: str = ""

    @property
    def failed(self) -> bool:
        """True when the board produced nothing trustworthy: a board-level
        error or every one of its companies failing."""
        if self.error:
            return True
        return self.companies_total > 0 and self.companies_failed >= self.companies_total


@dataclass
class FetchReport:
    boards: List[BoardReport] = field(default_factory=list)
    inserted: int = 0
    updated: int = 0
    store_errors: int = 0
    skipped: int = 0
    dry_run: bool = False

    @property
    def failed_boards(self) -> List[str]:
        return [b.board for b in self.boards if b.failed]

    @property
    def degraded_boards(self) -> List[str]:
        return [b.board for b in self.boards if not b.failed and b.companies_failed > 0]

    @property
    def total_fetched(self) -> int:
        return sum(b.job_count for b in self.boards)

    @property
    def ok(self) -> bool:
        return not self.failed_boards and self.store_errors == 0

    def summary_lines(self) -> List[str]:
        lines = []
        for b in self.boards:
            if b.error:
                status = f"FAILED ({b.error})"
            elif b.failed:
                status = "FAILED (all companies failed)"
            elif b.companies_failed:
                status = f"DEGRADED ({b.companies_failed}/{b.companies_total} companies failed)"
            else:
                status = "ok"
            lines.append(f"  {b.board:<12} {b.job_count:>4} jobs   {status}")
        action = "would store" if self.dry_run else "stored"
        lines.append(
            f"  total: {self.total_fetched} fetched | {action}: "
            f"{self.inserted} new, {self.updated} updated, "
            f"{self.skipped} skipped, {self.store_errors} errors"
        )
        return lines


class JobFetcher:
    def __init__(self, store: JobStore):
        self.store = store
        self.fetchers = {
            "greenhouse": GreenhouseFetcher(),
            "lever": LeverFetcher(),
            "ashby": AshbyFetcher(),
        }

    async def fetch_jobs_from_board(
        self, board_name: str, client: httpx.AsyncClient, config: Dict[str, Any]
    ) -> tuple[List[Job], BoardReport]:
        """Fetches jobs from a specific board using its respective fetcher."""
        report = BoardReport(board=board_name)
        fetcher = self.fetchers.get(board_name)
        if not fetcher:
            report.error = "no fetcher registered"
            logger.warning("No fetcher found for board: %s", board_name)
            return [], report

        logger.info("Fetching jobs from %s...", board_name)
        try:
            board_result: BoardFetchResult = await fetcher.fetch(client=client, config=config)
            report.companies_total = board_result.companies_total
            report.companies_failed = board_result.companies_failed
            processed_jobs: List[Job] = []
            for job_data in board_result.jobs:
                normalized_loc = normalize_location(job_data.get('location', ''))
                job = Job(
                    company=job_data.get('company', ''),
                    title=job_data.get('title', ''),
                    location=job_data.get('location', ''),
                    normalized_location=normalized_loc,
                    url=job_data.get('url', ''),
                    board=board_name,
                    description=job_data.get('description', ''),
                    compensation=job_data.get('compensation'),
                    date_found=job_data.get('date_found', datetime.now(timezone.utc)),
                )
                processed_jobs.append(job)
            report.job_count = len(processed_jobs)
            logger.info("Found %d jobs from %s.", len(processed_jobs), board_name)
            return processed_jobs, report
        except httpx.HTTPStatusError as e:
            report.error = f"HTTP {e.response.status_code}"
            logger.error("HTTP error fetching from %s: %s - %s", board_name, e.response.status_code, e.request.url)
        except httpx.RequestError as e:
            report.error = f"request error: {e}"
            logger.error("Request error fetching from %s: %s", board_name, e)
        except Exception as e:
            report.error = f"unexpected error: {e}"
            logger.error("An unexpected error occurred while fetching from %s: %s", board_name, e)
        return [], report

    async def fetch_all_boards(self) -> tuple[List[Job], List[BoardReport]]:
        """Fetches jobs from all configured boards concurrently."""
        all_jobs: List[Job] = []
        reports: List[BoardReport] = []
        board_names = list(DEFAULT_BOARD_CONFIG.keys())

        async with httpx.AsyncClient(
            headers={"User-Agent": USER_AGENT},
            timeout=httpx.Timeout(timeout=10.0, connect=5.0),
        ) as client:
            tasks = [
                self.fetch_jobs_from_board(name, client, DEFAULT_BOARD_CONFIG[name])
                for name in board_names
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)

        for board_name, result in zip(board_names, results):
            if isinstance(result, BaseException):
                logger.error("Fetch task for %s failed: %s", board_name, result)
                reports.append(BoardReport(board=board_name, error=str(result)))
                continue
            jobs, report = result
            all_jobs.extend(jobs)
            reports.append(report)

        return all_jobs, reports

    async def run_fetch_and_store(self, dry_run: bool = False) -> FetchReport:
        """Fetches all jobs and stores them in the database.

        Returns a FetchReport so callers can tell '2 of 3 boards down'
        apart from 'no new jobs'.
        """
        logger.info("Starting job fetch process...")
        fetched_jobs, board_reports = await self.fetch_all_boards()
        report = FetchReport(boards=board_reports, dry_run=dry_run)

        for job in fetched_jobs:
            if not job.url:
                logger.warning("Skipping job with missing URL: %s at %s", job.title, job.company)
                report.skipped += 1
                continue

            if job.date_found is None:
                job.date_found = datetime.now(timezone.utc)
            job.last_seen = datetime.now(timezone.utc)

            if dry_run:
                existing = self.store.get_job_by_url(job.url)
                if existing is None:
                    report.inserted += 1
                else:
                    report.updated += 1
                continue

            result = self.store.insert_or_update_job(job)
            if result is True:
                report.inserted += 1
            elif result is False:
                report.updated += 1
            else:
                report.store_errors += 1
                logger.error("Failed to insert/update job: %s (%s)", job.title, job.company)

        logger.info(
            "Job fetch completed. Inserted: %d, Updated: %d, Failed boards: %s",
            report.inserted, report.updated, report.failed_boards or "none",
        )
        return report
