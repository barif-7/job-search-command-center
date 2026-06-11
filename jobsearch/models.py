from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional, List, Any

@dataclass
class Job:
    id: Optional[int] = None  # Primary key for SQLite
    company: str = ""
    title: str = ""
    location: str = ""
    normalized_location: str = ""
    url: str = ""
    board: str = ""
    description: str = ""
    compensation: Optional[str] = None
    date_found: Optional[datetime] = field(default_factory=lambda: datetime.now(timezone.utc))
    last_seen: Optional[datetime] = field(default_factory=lambda: datetime.now(timezone.utc))
    status: str = "New"
    priority: Optional[int] = None
    fit_score: Optional[float] = None
    fit_summary: Optional[str] = None
    notes: Optional[str] = None
    notion_page_id: Optional[str] = None
    application_status: str = "NOT_STARTED"
    application_url: Optional[str] = None
    ats_provider: Optional[str] = None
    fields_completed: Optional[str] = None
    resume_uploaded: Optional[bool] = None
    blockers: Optional[str] = None
    last_apply_attempt_at: Optional[datetime] = None
    apply_notes: Optional[str] = None
    human_required_reason: Optional[str] = None
    created_at: Optional[datetime] = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: Optional[datetime] = field(default_factory=lambda: datetime.now(timezone.utc))

    def __post_init__(self):
        # Ensure datetime fields are indeed datetimes if they come in as strings
        if isinstance(self.date_found, str):
            self.date_found = datetime.fromisoformat(self.date_found)
        if isinstance(self.last_seen, str):
            self.last_seen = datetime.fromisoformat(self.last_seen)
        if isinstance(self.created_at, str):
            self.created_at = datetime.fromisoformat(self.created_at)
        if isinstance(self.updated_at, str):
            self.updated_at = datetime.fromisoformat(self.updated_at)
        if isinstance(self.last_apply_attempt_at, str):
            self.last_apply_attempt_at = datetime.fromisoformat(self.last_apply_attempt_at)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "company": self.company,
            "title": self.title,
            "location": self.location,
            "normalized_location": self.normalized_location,
            "url": self.url,
            "board": self.board,
            "description": self.description,
            "compensation": self.compensation,
            "date_found": self.date_found.isoformat() if self.date_found else None,
            "last_seen": self.last_seen.isoformat() if self.last_seen else None,
            "status": self.status,
            "priority": self.priority,
            "fit_score": self.fit_score,
            "fit_summary": self.fit_summary,
            "notes": self.notes,
            "notion_page_id": self.notion_page_id,
            "application_status": self.application_status,
            "application_url": self.application_url,
            "ats_provider": self.ats_provider,
            "fields_completed": self.fields_completed,
            "resume_uploaded": self.resume_uploaded,
            "blockers": self.blockers,
            "last_apply_attempt_at": self.last_apply_attempt_at.isoformat() if self.last_apply_attempt_at else None,
            "apply_notes": self.apply_notes,
            "human_required_reason": self.human_required_reason,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> 'Job':
        return Job(**data)
