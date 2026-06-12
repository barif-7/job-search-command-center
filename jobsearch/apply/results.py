from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class ApplyResult:
    job_id: int | None
    company: str
    title: str
    job_url: str
    application_url: str
    ats_provider: str
    status: str
    attempted_at: str = ""
    fields_completed: list[str] = field(default_factory=list)
    detected_count: int = 0
    detected_fields: list[dict[str, Any]] = field(default_factory=list)
    filled_fields: list[dict[str, Any]] = field(default_factory=list)
    skipped_fields: list[dict[str, Any]] = field(default_factory=list)
    resume_uploaded: bool = False
    blockers: list[str] = field(default_factory=list)
    human_required_reason: str = ""
    notes: list[str] = field(default_factory=list)
    review_dir: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
