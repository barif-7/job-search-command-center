"""Load the optional keyword_report.json produced by extract_keywords.py."""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


def load_keyword_data(kw_path: Optional[Path] = None) -> dict:
    """
    Load keyword_report.json into {url: set_of_all_keywords_across_categories}.

    Returns {} when no path is given or the file is missing/unreadable.
    """
    if kw_path is None or not kw_path.exists():
        return {}
    try:
        raw = json.loads(kw_path.read_text(encoding="utf-8"))
        result = {}
        for entry in raw:
            url = entry.get("url", "")
            all_kw: set[str] = set()
            for kw_list in entry.get("keywords", {}).values():
                all_kw.update(kw_list)
            result[url] = all_kw
        return result
    except Exception as exc:
        logger.warning("Could not load keyword_report.json: %s", exc)
        return {}
