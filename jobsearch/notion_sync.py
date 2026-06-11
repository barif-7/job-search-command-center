from __future__ import annotations

import logging
from typing import Optional

try:
    from notion_client import Client
except Exception:
    Client = None  # type: ignore

from .models import Job
from .settings import get_settings

logger = logging.getLogger(__name__)


def notion_sync_enabled() -> bool:
    return get_settings().notion_configured


def _notion_client() -> Optional[object]:
    settings = get_settings()
    if not settings.notion_configured:
        return None
    if Client is None:
        logger.warning("notion-client is not installed; Notion sync unavailable.")
        return None
    return Client(auth=settings.notion_api_key)


def _job_properties(job: Job) -> dict:
    properties = {
        "Company": {"title": [{"text": {"content": job.company}}]},
        "Role": {"rich_text": [{"text": {"content": job.title}}]},
        "Location": {"rich_text": [{"text": {"content": job.location}}]},
        "URL": {"url": job.url},
        "Board": {"rich_text": [{"text": {"content": job.board}}]},
        "Status": {"select": {"name": job.status or "New"}},
        "Priority": {"number": job.priority or 0},
        "Fit Score": {"number": float(job.fit_score) if job.fit_score is not None else None},
        "Date Found": {"date": {"start": job.date_found.isoformat()} if job.date_found else None},
        "Last Seen": {"date": {"start": job.last_seen.isoformat()} if job.last_seen else None},
        "Notes": {"rich_text": [{"text": {"content": job.notes or ""}}]},
        "URL Copy": {"url": job.url},
    }
    return {k: v for k, v in properties.items() if v is not None}


def _find_page_id(client, database_id: str, job: Job) -> Optional[str]:
    if job.notion_page_id:
        return job.notion_page_id
    results = client.databases.query(
        database_id=database_id,
        filter={"property": "URL", "url": {"equals": job.url}},
    )
    if results and results.get("results"):
        return results["results"][0]["id"]
    return None


def upsert_job_to_notion(job: Job, client=None) -> tuple[str, Optional[str]]:
    """Creates or updates the Notion page for a job.

    Returns (outcome, page_id) where outcome is one of
    'created', 'updated', 'skipped' (sync disabled/unconfigured), 'failed'.
    """
    client = client or _notion_client()
    if client is None:
        return "skipped", None

    database_id = get_settings().notion_jobs_database_id
    try:
        page_id = _find_page_id(client, database_id, job)
        properties = _job_properties(job)
        if page_id:
            client.pages.update(page_id=page_id, properties=properties)
            return "updated", page_id
        page = client.pages.create(
            parent={"database_id": database_id}, properties=properties
        )
        page_id = page.get("id") if page else None
        return ("created", page_id) if page_id else ("failed", None)
    except Exception as e:
        logger.error("Notion sync error for %s: %s", job.url, e)
        return "failed", None
