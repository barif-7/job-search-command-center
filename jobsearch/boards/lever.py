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


class LeverFetcher:
    async def fetch(self, client, config: Dict[str, Any]) -> BoardFetchResult:
        companies: Dict[str, str] = config.get("companies", {})
        api_base: str = config.get("api_base", "https://api.lever.co/v0/postings")

        sem = asyncio.Semaphore(CONCURRENCY)
        tasks = [
            _fetch_one(client, sem, api_base, slug, name)
            for slug, name in companies.items()
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
    client, sem: asyncio.Semaphore, api_base: str, slug: str, name: str
) -> List[Dict[str, Any]] | None:
    async with sem:
        try:
            r = await client.get(f"{api_base}/{slug}?mode=json&limit=250")
            if r.status_code != 200:
                logger.warning("[lever] ✗ %s (%s) — HTTP %s", name, slug, r.status_code)
                return None
            postings = r.json()
            if not isinstance(postings, list):
                postings = postings.get("postings", [])
            results = []
            for p in postings:
                title = p.get("text", "")
                if not _matches_role(title):
                    continue
                cats = p.get("categories", {})
                loc_raw = cats.get("location") or ""
                if not loc_raw:
                    all_locs = cats.get("allLocations", [])
                    loc_raw = all_locs[0] if all_locs else ""
                if not _location_wanted(loc_raw):
                    continue
                results.append({
                    "company":    name,
                    "title":      title,
                    "location":   loc_raw,
                    "url":        p.get("hostedUrl", ""),
                    "board":      "lever",
                    "description": _description(p),
                    "date_found": datetime.now(timezone.utc),
                })
            logger.info("[lever] ✓ %s: %d match(es) of %d", name, len(results), len(postings))
            return results
        except Exception as e:
            logger.error("[lever] ✗ %s (%s) — %s", name, slug, e)
            return None
        finally:
            await asyncio.sleep(COURTESY_DELAY)


def _description(posting: dict) -> str:
    """Lever splits a posting across the body, its bullet lists, and a
    trailing "additional" block. Keyword extraction wants all three."""
    parts = [posting.get("descriptionPlain") or posting.get("description") or ""]
    for lst in posting.get("lists") or []:
        parts.append(lst.get("text") or "")
        parts.append(lst.get("content") or "")
    parts.append(posting.get("additionalPlain") or posting.get("additional") or "")
    return description_text(" ".join(part for part in parts if part))
