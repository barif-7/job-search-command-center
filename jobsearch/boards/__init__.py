from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List


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
