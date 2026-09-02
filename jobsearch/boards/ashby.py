import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from jobsearch.boards import BoardFetchResult, description_text
from jobsearch.boards import location_wanted as _location_wanted
from jobsearch.boards import matches_role as _matches_role

logger = logging.getLogger(__name__)

# The public posting API carries descriptionPlain; the job-board HTML does not
# (its embedded jobPostings JSON has only title/location/team fields). We try
# the API first and fall back to scraping so a board missing from the API still
# yields jobs — just without descriptions.
POSTING_API_BASE = "https://api.ashbyhq.com/posting-api/job-board"


class AshbyFetcher:
    async def fetch(self, client, config: Dict[str, Any]) -> BoardFetchResult:
        companies: Dict[str, str] = config.get("companies", {})
        api_base: str = config.get("api_base", "https://jobs.ashbyhq.com")
        posting_api_base: str = config.get("posting_api_base", POSTING_API_BASE)
        result = BoardFetchResult(companies_total=len(companies))

        for slug, name in companies.items():
            jobs = await _fetch_posting_api(client, posting_api_base, api_base, slug, name)
            if jobs is None:
                jobs = await _fetch_html(client, api_base, slug, name)
            if jobs is None:
                result.companies_failed += 1
            else:
                result.jobs.extend(jobs)
            await asyncio.sleep(0.3)

        return result


async def _fetch_posting_api(
    client, posting_api_base: str, api_base: str, slug: str, name: str
) -> Optional[List[Dict[str, Any]]]:
    """Fetch via the public posting API. None means "try the fallback"."""
    try:
        r = await client.get(f"{posting_api_base}/{slug}")
        if r.status_code != 200:
            logger.info(
                "[ashby] posting API unavailable for %s (%s) — HTTP %s, falling back to HTML",
                name, slug, r.status_code,
            )
            return None
        postings = r.json().get("jobs", [])
    except Exception as e:
        logger.info("[ashby] posting API error for %s (%s) — %s, falling back to HTML", name, slug, e)
        return None

    results = []
    for j in postings:
        if j.get("isListed") is False:
            continue
        title = j.get("title", "")
        if not _matches_role(title):
            continue
        loc_str = _wanted_locations(j)
        if not loc_str:
            continue
        results.append({
            "company": name,
            "title": title,
            "location": loc_str,
            # jobUrl is exactly {api_base}/{slug}/{id} — the same URL the HTML
            # path builds, so dedupe survives the switch between them.
            "url": j.get("jobUrl") or f"{api_base}/{slug}/{j.get('id', '')}",
            "board": "ashby",
            "description": description_text(
                j.get("descriptionPlain") or j.get("descriptionHtml") or ""
            ),
            "date_found": datetime.now(timezone.utc),
        })

    logger.info("[ashby] ✓ %s: %d match(es) of %d (posting API)", name, len(results), len(postings))
    return results


async def _fetch_html(
    client, api_base: str, slug: str, name: str
) -> Optional[List[Dict[str, Any]]]:
    """Scrape the job-board page's embedded JSON. Yields no descriptions."""
    try:
        r = await client.get(f"{api_base}/{slug}")
        if r.status_code != 200:
            logger.warning("[ashby] ✗ %s (%s) — HTTP %s", name, slug, r.status_code)
            return None

        html = r.text
        marker = '"jobPostings":'
        pos = html.find(marker)
        if pos == -1:
            logger.warning("[ashby] ✗ %s (%s) — jobPostings not found in HTML", name, slug)
            return None

        array_start = pos + len(marker)
        while array_start < len(html) and html[array_start] in (' ', '\n', '\r', '\t'):
            array_start += 1

        try:
            jobs, _ = json.JSONDecoder().raw_decode(html, array_start)
        except json.JSONDecodeError as e:
            logger.error("[ashby] ✗ %s (%s) — JSON parse error: %s", name, slug, e)
            return None

        results = []
        for j in jobs:
            title = j.get("title", "")
            if not _matches_role(title):
                continue
            loc_str = _wanted_locations(j)
            if not loc_str:
                continue
            results.append({
                "company": name,
                "title": title,
                "location": loc_str,
                "url": f"{api_base}/{slug}/{j.get('id', '')}",
                "board": "ashby",
                "description": "",
                "date_found": datetime.now(timezone.utc),
            })

        logger.info("[ashby] ✓ %s: %d match(es) of %d (HTML)", name, len(results), len(jobs))
        return results
    except Exception as e:
        logger.error("[ashby] ✗ %s (%s) — %s", name, slug, e)
        return None


def _wanted_locations(posting: dict) -> str:
    """Primary + secondary locations that pass the filter, joined for display.

    The two sources name these fields differently: the posting API uses
    ``location``/``secondaryLocations[].location``, the embedded HTML JSON uses
    ``locationName``/``secondaryLocations[].locationName``.
    """
    primary = posting.get("locationName") or posting.get("location") or ""
    secondary = [
        (sl.get("locationName") or sl.get("location") or "")
        for sl in posting.get("secondaryLocations") or []
    ]
    wanted = [loc for loc in [primary] + secondary if loc and _location_wanted(loc)]
    return " / ".join(dict.fromkeys(wanted))
