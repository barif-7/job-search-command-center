"""Per-attempt review bundle: a folder a human opens before deciding to submit.

Each auto-apply attempt gets its own directory containing:
  summary.json   — the full ApplyResult, machine-readable
  review.md      — human-readable checklist of what was detected/filled/skipped
  before.png     — screenshot after page load, before any filling (when a browser ran)
  after.png      — screenshot after filling stopped (when a browser ran)
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path

from jobsearch.apply.results import ApplyResult


def _slug(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", (text or "").lower()).strip("-")
    return slug[:40] or "unknown"


def create_review_dir(base_dir: Path, result: ApplyResult) -> Path:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    name = f"{stamp}_{result.job_id if result.job_id is not None else 'na'}_{_slug(result.company)}"
    path = base_dir / name
    path.mkdir(parents=True, exist_ok=True)
    return path


def write_review_bundle(result: ApplyResult) -> Path:
    """Writes summary.json and review.md into result.review_dir."""
    review_dir = Path(result.review_dir)
    review_dir.mkdir(parents=True, exist_ok=True)

    summary_path = review_dir / "summary.json"
    summary_path.write_text(
        json.dumps(result.to_dict(), indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    (review_dir / "review.md").write_text(render_review_md(result), encoding="utf-8")
    return review_dir


def render_review_md(result: ApplyResult) -> str:
    lines = [
        f"# Apply review — {result.company}: {result.title}",
        "",
        f"- **Status:** {result.status}",
        f"- **Attempted:** {result.attempted_at}",
        f"- **Application URL:** {result.application_url}",
        f"- **ATS provider:** {result.ats_provider}",
        f"- **Resume uploaded:** {'yes' if result.resume_uploaded else 'no'}",
        f"- **Fields detected on page:** {result.detected_count}",
        f"- **Human action needed:** {result.human_required_reason or 'review'}",
        "",
    ]

    if result.blockers:
        lines += ["## Blockers", ""]
        lines += [f"- {b}" for b in result.blockers]
        lines.append("")

    if result.detected_fields:
        lines += [f"## Detected fields ({len(result.detected_fields)})", ""]
        for item in result.detected_fields:
            label = item.get("label") or item.get("name") or "(unnamed)"
            required = " (required)" if item.get("required") else ""
            lines.append(f"- {label} — {item.get('kind')}/{item.get('type') or 'text'}{required}")
        lines.append("")

    lines += [f"## Filled ({len(result.filled_fields)})", ""]
    if result.filled_fields:
        for item in result.filled_fields:
            matched = item.get("matched") or {}
            where = matched.get("label") or matched.get("name") or matched.get("id") or "?"
            score = item.get("score")
            confidence = f", confidence {score}" if score is not None else ""
            lines.append(f"- **{item.get('field')}** → `{item.get('value')}` (matched: {where}{confidence})")
    else:
        lines.append("_Nothing was filled._")
    lines.append("")

    lines += [f"## Skipped ({len(result.skipped_fields)})", ""]
    if result.skipped_fields:
        for item in result.skipped_fields:
            lines.append(f"- **{item.get('field')}** — {item.get('reason')}")
    else:
        lines.append("_Nothing was skipped._")
    lines.append("")

    if result.notes:
        lines += ["## Notes", ""]
        lines += [f"- {n}" for n in result.notes]
        lines.append("")

    lines += [
        "## Next step",
        "",
        "Open the application in a browser, verify every field, and submit manually.",
        "The runner never clicks final submit.",
        "",
    ]
    return "\n".join(lines)
