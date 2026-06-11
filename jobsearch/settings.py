"""Single source of truth for runtime configuration.

Values come from the environment, with a `.env` file at the project root
loaded first. Every key is optional — the app must run with none set.
Static domain configuration (role keywords, board lists, statuses) lives
in the root `config.py`; anything secret or machine-specific lives here.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in ("1", "true", "yes", "on")


@dataclass(frozen=True)
class Settings:
    database_path: str
    markdown_export_path: str
    apply_input_dir: str

    notion_api_key: str
    notion_jobs_database_id: str
    enable_notion_sync: bool

    anthropic_api_key: str
    logo_dev_token: str

    @property
    def notion_configured(self) -> bool:
        """True only when sync is enabled AND both credentials are present."""
        return (
            self.enable_notion_sync
            and bool(self.notion_api_key)
            and bool(self.notion_jobs_database_id)
        )


def load_settings() -> Settings:
    load_dotenv(PROJECT_ROOT / ".env")
    return Settings(
        database_path=os.environ.get("DATABASE_PATH", str(PROJECT_ROOT / "data" / "jobs.db")),
        markdown_export_path=os.environ.get(
            "MARKDOWN_EXPORT_PATH", str(PROJECT_ROOT.parent / "job-search-results.md")
        ),
        apply_input_dir=os.environ.get("APPLY_INPUT_DIR", str(PROJECT_ROOT / "data" / "apply")),
        notion_api_key=os.environ.get("NOTION_API_KEY", ""),
        notion_jobs_database_id=os.environ.get("NOTION_JOBS_DATABASE_ID", ""),
        enable_notion_sync=_env_bool("ENABLE_NOTION_SYNC", False),
        anthropic_api_key=os.environ.get("ANTHROPIC_API_KEY", ""),
        logo_dev_token=os.environ.get("LOGO_DEV_TOKEN", ""),
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return load_settings()
