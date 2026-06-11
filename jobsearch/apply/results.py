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
    fields_completed: list[str] = field(default_factory=list)
    resume_uploaded: bool = False
    blockers: list[str] = field(default_factory=list)
    human_required_reason: str = ""
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

