import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List

from config import LOCATION_KEYWORDS, ROLE_KEYWORDS

logger = logging.getLogger(__name__)

CONCURRENCY = 12
COURTESY_DELAY = 0.1


class LeverFetcher:
    async def fetch(self, client, config: Dict[str, Any]) -> List[Dict[str, Any]]:
        companies: Dict[str, str] = config.get("companies", {})
        api_base: str = config.get("api_base", "https://api.lever.co/v0/postings")

        sem = asyncio.Semaphore(CONCURRENCY)
        tasks = [
            _fetch_one(client, sem, api_base, slug, name)
            for slug, name in companies.items()
        ]
        batches = await asyncio.gather(*tasks)
        return [job for batch in batches for job in batch]


async def _fetch_one(
    client, sem: asyncio.Semaphore, api_base: str, slug: str, name: str
) -> List[Dict[str, Any]]:
    async with sem:
        try:
            r = await client.get(f"{api_base}/{slug}?mode=json&limit=250")
            if r.status_code != 200:
                logger.warning("[lever] ✗ %s (%s) — HTTP %s", name, slug, r.status_code)
                return []
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
                    "description": "",
                    "date_found": datetime.now(timezone.utc),
                })
            logger.info("[lever] ✓ %s: %d match(es) of %d", name, len(results), len(postings))
            return results
        except Exception as e:
            logger.error("[lever] ✗ %s (%s) — %s", name, slug, e)
            return []
        finally:
            await asyncio.sleep(COURTESY_DELAY)


def _matches_role(title: str) -> bool:
    t = title.lower()
    return any(kw in t for kw in ROLE_KEYWORDS)


def _location_wanted(loc: str) -> bool:
    if not LOCATION_KEYWORDS:
        return True
    return any(kw in loc.lower() for kw in LOCATION_KEYWORDS)
