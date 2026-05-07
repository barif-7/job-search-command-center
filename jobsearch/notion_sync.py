from __future__ import annotations
import os
from typing import Optional

try:
    from notion_client import Client
except Exception:
    Client = None  # type: ignore

from .models import Job

NOTION_API_KEY = os.environ.get("NOTION_API_KEY", "")
NOTION_JOBS_DATABASE_ID = os.environ.get("NOTION_JOBS_DATABASE_ID", "")
ENABLE_NOTION_SYNC = os.environ.get("ENABLE_NOTION_SYNC", "false").lower() in ("1", "true", "yes")


def _notion_client() -> Optional[object]:
    if not ENABLE_NOTION_SYNC:
        return None
    if not NOTION_API_KEY:
        return None
    if Client is None:
        return None
    return Client(auth=NOTION_API_KEY)


def upsert_job_to_notion(job: Job) -> Optional[str]:
    """Upsert a Job into Notion database. Returns notion page_id if created/updated, else None."""
    if not ENABLE_NOTION_SYNC:
        return None
    if not NOTION_API_KEY or not NOTION_JOBS_DATABASE_ID:
        return None

    client = _notion_client()
    if client is None:
        return None

    # Try to find existing page by URL
    try:
        results = client.databases.query(
            database_id=NOTION_JOBS_DATABASE_ID,
            filter={
                "property": "URL",
                "url": {"equals": job.url},
            },
        )
        if results and results.get("results"):
            page_id = results["results"][0]["id"]
        else:
            # Create new page in the database
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
            # Remove None values
            properties = {k: v for k, v in properties.items() if v is not None}
            page = client.pages.create(parent={"database_id": NOTION_JOBS_DATABASE_ID}, properties=properties)
            page_id = page.get("id") if page else None
        return page_id
    except Exception as e:
        # Log but do not crash the caller
        try:
            print(f"Notion sync error for {job.url}: {e}")
        except Exception:
            pass
        return None
