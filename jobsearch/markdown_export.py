"""Render the job tracker to a Markdown snapshot.

Single source for Markdown export — the CLI script and the UI button both
go through MarkdownExporter so their output can never drift.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import List, Optional

from .models import Job
from .settings import get_settings
from .store import JobStore

logger = logging.getLogger(__name__)


class MarkdownExporter:
    def __init__(self, store: JobStore):
        self.store = store

    def render_job(self, j: Job) -> List[str]:
        date_str = j.date_found.strftime("%Y-%m-%d") if j.date_found else "?"
        lines = [
            f"- **[{j.company}]** {j.title} — {j.location} ({j.board}, {date_str})",
            f"  {j.url}",
        ]
        if j.notes:
            lines.append(f"  _Notes: {j.notes}_")
        lines.append("")
        return lines

    def render(self, group_by: str = "status") -> str:
        jobs = self.store.get_all_jobs()
        groups: dict[str, List[Job]] = {}
        for j in jobs:
            key = getattr(j, group_by, None) or "Unknown"
            groups.setdefault(key, []).append(j)

        lines: List[str] = []
        for key, group in sorted(groups.items()):
            lines.append(f"\n## {key}\n")
            for j in group:
                lines.extend(self.render_job(j))
        return "# Job Search Results\n" + "\n".join(lines)

    def export(self, path: Optional[str] = None, group_by: str = "status") -> tuple[int, Path]:
        """Writes the rendered Markdown. Returns (job_count, path written)."""
        export_path = Path(path or get_settings().markdown_export_path)
        content = self.render(group_by=group_by)
        export_path.parent.mkdir(parents=True, exist_ok=True)
        export_path.write_text(content, encoding="utf-8")
        count = len(self.store.get_all_jobs())
        logger.info("Exported %d jobs to %s", count, export_path)
        return count, export_path
