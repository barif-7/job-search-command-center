"""Search-query and compensation parsing (pure functions)."""
from __future__ import annotations

import re

_FILTER_KEYS = {"loc", "type", "priority", "skill", "company", "board", "src", "comp"}


def parse_comp_value(comp_str: str) -> int | None:
    """
    Extract the lower-bound salary in dollars from a comp string.
    Examples: "$150K–$200K" → 150000, "$180K base" → 180000, "" → None.
    Returns None when the string is empty, unparseable, or explicitly unlisted.
    """
    if not comp_str:
        return None
    if re.match(r"(?i)^\s*(not\s+listed|n/?a|tbd|\?|market\s+rate|competitive)\s*$", comp_str):
        return None
    m = re.search(r"\$?\s*(\d[\d,]*)\s*([kK])?", comp_str)
    if not m:
        return None
    try:
        raw = int(m.group(1).replace(",", ""))
        if m.group(2):          # explicit K suffix
            return raw * 1000
        if raw < 2000:          # bare small number — treat as thousands
            return raw * 1000
        return raw
    except ValueError:
        return None


def parse_query_chips(query: str) -> tuple[str, list[dict]]:
    """
    Split 'python loc:SF priority:8+ skill:pytorch' into free text + chips.
    Returns (remaining_free_text, [{"key", "value", "label"}, ...]).
    """
    tokens = query.strip().split()
    free_parts, chips = [], []
    for token in tokens:
        if ":" in token:
            key, _, val = token.partition(":")
            if key.lower() in _FILTER_KEYS and val:
                chips.append({"key": key.lower(), "value": val, "label": token.lower()})
                continue
        free_parts.append(token)
    return " ".join(free_parts), chips
