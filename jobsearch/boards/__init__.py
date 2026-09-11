from __future__ import annotations

import html
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List

from config import LOCATION_KEYWORDS, ROLE_EXCLUSIONS, ROLE_KEYWORDS

# Descriptions feed keyword extraction and the AI briefing, not display, so
# they are stored as plain text. Boards hand us either escaped HTML
# (Greenhouse) or already-plain text (Lever, Ashby); this normalises both.
MAX_DESCRIPTION_CHARS = 20_000


def description_text(raw: str | None) -> str:
    """Unescape entities, strip tags, and collapse whitespace."""
    if not raw:
        return ""
    text = html.unescape(raw)
    text = re.sub(r"<(script|style)\b[^>]*>.*?</\1>", " ", text, flags=re.IGNORECASE | re.DOTALL)
    # Keep block boundaries as spaces so words don't run together.
    text = re.sub(r"<[^>]+>", " ", text)
    # A second unescape: Greenhouse double-escapes entities inside content.
    text = html.unescape(text)
    text = re.sub(r"\s+", " ", text).strip()
    # Tags become spaces, which strands punctuation ("AWS ." from "AWS</b>.").
    text = re.sub(r"\s+([,.;:!?)])", r"\1", text)
    text = re.sub(r"(\()\s+", r"\1", text)
    return text[:MAX_DESCRIPTION_CHARS]


@dataclass
class BoardFetchResult:
    """Outcome of fetching one board: matched jobs plus per-company failure
    counts, so a board that is down is distinguishable from one with no
    matching postings."""

    jobs: List[Dict[str, Any]] = field(default_factory=list)
    companies_total: int = 0
    companies_failed: int = 0

    @property
    def all_failed(self) -> bool:
        return self.companies_total > 0 and self.companies_failed >= self.companies_total


def matches_role(title: str) -> bool:
    """True when a title looks like a role worth tracking.

    A ROLE_KEYWORD must match and no ROLE_EXCLUSION may — the generic keywords
    ("software engineer") otherwise sweep in manager, intern, and sales titles.
    Exclusions win over keywords.
    """
    t = (title or "").lower()
    if not any(kw in t for kw in ROLE_KEYWORDS):
        return False
    return not any(bad in t for bad in ROLE_EXCLUSIONS)


def location_wanted(location: str) -> bool:
    """True when a location mentions somewhere we care about.

    An empty LOCATION_KEYWORDS means "no location filter".
    """
    if not LOCATION_KEYWORDS:
        return True
    return any(kw in (location or "").lower() for kw in LOCATION_KEYWORDS)
