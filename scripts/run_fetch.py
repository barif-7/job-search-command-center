import sys
from pathlib import Path

# Ensure the project root (job-search-command-center/) is on sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from jobsearch.fetcher import JobFetcher
from jobsearch.store import JobStore

store = JobStore()
fetcher = JobFetcher(store)

import asyncio

async def main():
    inserted, updated = await fetcher.run_fetch_and_store()
    print(f"Inserted: {inserted}, Updated: {updated}")

if __name__ == '__main__':
    asyncio.run(main())
