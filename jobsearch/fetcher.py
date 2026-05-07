import asyncio
import logging
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

import httpx

from .models import Job
from .utils import normalize_location, clean_text
from .boards.greenhouse import GreenhouseFetcher
from .boards.lever import LeverFetcher
from .boards.ashby import AshbyFetcher
from .store import JobStore
from config import DEFAULT_BOARD_CONFIG, USER_AGENT

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class JobFetcher:
    def __init__(self, store: JobStore):
        self.store = store
        self.fetchers = {
            "greenhouse": GreenhouseFetcher(),
            "lever": LeverFetcher(),
            "ashby": AshbyFetcher(),
        }

    async def fetch_jobs_from_board(self, board_name: str, client: httpx.AsyncClient, config: Dict[str, Any]) -> List[Job]:
        """Fetches jobs from a specific board using its respective fetcher."""
        fetcher = self.fetchers.get(board_name)
        if not fetcher:
            logging.warning(f"No fetcher found for board: {board_name}")
            return []

        logging.info(f"Fetching jobs from {board_name}...")
        try:
            jobs_data = await fetcher.fetch(client=client, config=config)
            processed_jobs: List[Job] = []
            for job_data in jobs_data:
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
            logging.info(f"Found {len(processed_jobs)} jobs from {board_name}.")
            return processed_jobs
        except httpx.HTTPStatusError as e:
            logging.error(f"HTTP error fetching from {board_name}: {e.response.status_code} - {e.request.url}")
        except httpx.RequestError as e:
            logging.error(f"Request error fetching from {board_name}: {e}")
        except Exception as e:
            logging.error(f"An unexpected error occurred while fetching from {board_name}: {e}")
        return []

    async def fetch_all_boards(self) -> List[Job]:
        """Fetches jobs from all configured boards concurrently."""
        all_jobs: List[Job] = []
        tasks = []

        async with httpx.AsyncClient(headers={"User-Agent": USER_AGENT}, timeout=httpx.Timeout(timeout=10.0, connect=5.0)) as client:
            for board_name, config in DEFAULT_BOARD_CONFIG.items():
                tasks.append(self.fetch_jobs_from_board(board_name, client, config))

            results = await asyncio.gather(*tasks, return_exceptions=True)

            for result in results:
                if isinstance(result, Exception):
                    logging.error(f"A fetch task failed with an exception: {result}")
                elif isinstance(result, list):
                    all_jobs.extend(result)

        return all_jobs

    async def run_fetch_and_store(self):
        """Fetches all jobs and stores them in the database."""
        logging.info("Starting job fetch process...")
        fetched_jobs = await self.fetch_all_boards()

        if not fetched_jobs:
            logging.warning("No jobs were fetched.")
            return 0, 0

        inserted_count = 0
        updated_count = 0

        for job in fetched_jobs:
            if not job.url:
                logging.warning(f"Skipping job with missing URL: {job.title} at {job.company}")
                continue

            if job.date_found is None:
                job.date_found = datetime.now(timezone.utc)
            job.last_seen = datetime.now(timezone.utc)

            result = self.store.insert_or_update_job(job)
            if result is True:
                inserted_count += 1
                logging.debug(f"Inserted job: {job.title} ({job.company})")
            elif result is False:
                updated_count += 1
                logging.debug(f"Updated job: {job.title} ({job.company})")
            else:
                logging.error(f"Failed to insert/update job: {job.title} ({job.company})")

        logging.info(f"Job fetch completed. Inserted: {inserted_count}, Updated: {updated_count}")
        return inserted_count, updated_count
