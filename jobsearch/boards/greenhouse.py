import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List

from config import LOCATION_KEYWORDS, ROLE_KEYWORDS
from jobsearch.boards import BoardFetchResult

logger = logging.getLogger(__name__)

CONCURRENCY = 12
COURTESY_DELAY = 0.1


class GreenhouseFetcher:
    async def fetch(self, client, config: Dict[str, Any]) -> BoardFetchResult:
        companies: Dict[str, str] = config.get("companies", {})
        api_base: str = config.get("api_base", "https://boards-api.greenhouse.io/v1/boards")

        sem = asyncio.Semaphore(CONCURRENCY)
        tasks = [
            _fetch_one(client, sem, api_base, token, name)
            for token, name in companies.items()
        ]
        batches = await asyncio.gather(*tasks)
        result = BoardFetchResult(companies_total=len(companies))
        for batch in batches:
            if batch is None:
                result.companies_failed += 1
            else:
                result.jobs.extend(batch)
        return result


async def _fetch_one(
    client, sem: asyncio.Semaphore, api_base: str, token: str, name: str
) -> List[Dict[str, Any]] | None:
    async with sem:
        try:
            r = await client.get(f"{api_base}/{token}/jobs")
            if r.status_code != 200:
                logger.warning("[greenhouse] ✗ %s (%s) — HTTP %s", name, token, r.status_code)
                return None
            jobs = r.json().get("jobs", [])
            results = []
            for j in jobs:
                title = j.get("title", "")
                if not _matches_role(title):
                    continue
                loc = j.get("location", {}).get("name", "") or ""
                if not _location_wanted(loc):
                    continue
                results.append({
                    "company":    name,
                    "title":      title,
                    "location":   loc,
                    "url":        j.get("absolute_url", ""),
                    "board":      "greenhouse",
                    "description": "",
                    "date_found": datetime.now(timezone.utc),
                })
            logger.info("[greenhouse] ✓ %s: %d match(es) of %d", name, len(results), len(jobs))
            return results
        except Exception as e:
            logger.error("[greenhouse] ✗ %s (%s) — %s", name, token, e)
            return None
        finally:
            await asyncio.sleep(COURTESY_DELAY)


def _matches_role(title: str) -> bool:
    t = title.lower()
    return any(kw in t for kw in ROLE_KEYWORDS)


def _location_wanted(loc: str) -> bool:
    if not LOCATION_KEYWORDS:
        return True
    return any(kw in loc.lower() for kw in LOCATION_KEYWORDS)
