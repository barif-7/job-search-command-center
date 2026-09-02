import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List

from jobsearch.boards import BoardFetchResult, description_text
from jobsearch.boards import location_wanted as _location_wanted
from jobsearch.boards import matches_role as _matches_role

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
            # content=true returns the posting body; without it every
            # description comes back empty and keyword extraction sees
            # nothing but the title. Same request count either way.
            r = await client.get(f"{api_base}/{token}/jobs", params={"content": "true"})
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
                    "description": description_text(j.get("content", "")),
                    "date_found": datetime.now(timezone.utc),
                })
            logger.info("[greenhouse] ✓ %s: %d match(es) of %d", name, len(results), len(jobs))
            return results
        except Exception as e:
            logger.error("[greenhouse] ✗ %s (%s) — %s", name, token, e)
            return None
        finally:
            await asyncio.sleep(COURTESY_DELAY)
