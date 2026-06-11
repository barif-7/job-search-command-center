import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List

from config import LOCATION_KEYWORDS, ROLE_KEYWORDS
from jobsearch.boards import BoardFetchResult

logger = logging.getLogger(__name__)


class AshbyFetcher:
    async def fetch(self, client, config: Dict[str, Any]) -> BoardFetchResult:
        companies: Dict[str, str] = config.get("companies", {})
        api_base: str = config.get("api_base", "https://jobs.ashbyhq.com")
        result = BoardFetchResult(companies_total=len(companies))
        results = result.jobs

        for slug, name in companies.items():
            try:
                r = await client.get(f"{api_base}/{slug}")
                if r.status_code != 200:
                    logger.warning("[ashby] ✗ %s (%s) — HTTP %s", name, slug, r.status_code)
                    result.companies_failed += 1
                    await asyncio.sleep(0.3)
                    continue

                html = r.text
                marker = '"jobPostings":'
                pos = html.find(marker)
                if pos == -1:
                    logger.warning("[ashby] ✗ %s (%s) — jobPostings not found in HTML", name, slug)
                    result.companies_failed += 1
                    await asyncio.sleep(0.3)
                    continue

                array_start = pos + len(marker)
                while array_start < len(html) and html[array_start] in (' ', '\n', '\r', '\t'):
                    array_start += 1

                try:
                    jobs, _ = json.JSONDecoder().raw_decode(html, array_start)
                except json.JSONDecodeError as e:
                    logger.error("[ashby] ✗ %s (%s) — JSON parse error: %s", name, slug, e)
                    result.companies_failed += 1
                    await asyncio.sleep(0.3)
                    continue

                count = 0
                for j in jobs:
                    title = j.get("title", "")
                    if not _matches_role(title):
                        continue

                    # Collect primary + secondary locations
                    primary = j.get("locationName") or j.get("location") or ""
                    secondary = [
                        ll.get("locationName", "")
                        for ll in j.get("secondaryLocations", [])
                    ]
                    all_locs = [primary] + secondary
                    wanted = [l for l in all_locs if _location_wanted(l)]
                    if not wanted:
                        continue

                    loc_str = " / ".join(dict.fromkeys(l for l in wanted if l))
                    job_url = f"{api_base}/{slug}/{j.get('id', '')}"
                    results.append({
                        "company": name,
                        "title": title,
                        "location": loc_str,
                        "url": job_url,
                        "board": "ashby",
                        "description": "",
                        "date_found": datetime.now(timezone.utc),
                    })
                    count += 1

                logger.info("[ashby] ✓ %s: %d match(es) of %d", name, count, len(jobs))
            except Exception as e:
                logger.error("[ashby] ✗ %s (%s) — %s", name, slug, e)
                result.companies_failed += 1
            await asyncio.sleep(0.3)

        return result


def _matches_role(title: str) -> bool:
    t = title.lower()
    return any(kw in t for kw in ROLE_KEYWORDS)


def _location_wanted(loc: str) -> bool:
    if not LOCATION_KEYWORDS:
        return True
    return any(kw in loc.lower() for kw in LOCATION_KEYWORDS)
