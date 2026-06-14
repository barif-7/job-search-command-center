"""Free-text and structured chip filtering over job dicts (pure functions)."""
from __future__ import annotations

from jobsearch.parsing.query import parse_comp_value


def apply_filters(
    jobs: list[dict],
    free_text: str,
    chips: list[dict],
    kw_data: dict,
) -> list[dict]:
    """Apply free-text and structured chip filters."""
    result = jobs

    if free_text:
        q = free_text.lower()
        result = [
            j for j in result
            if q in j["company"].lower()
            or q in j["title"].lower()
            or any(q in kw for kw in kw_data.get(j["url"], set()))
        ]

    for chip in chips:
        key, val = chip["key"], chip["value"].lower()

        if key == "loc":
            result = [j for j in result if val in j["location"].lower()]

        elif key == "type":
            t = {"ai": "ai", "ios": "ios", "top": "top", "new": "new"}.get(val)
            if t:
                result = [j for j in result if j["type"] == t]

        elif key == "priority":
            try:
                if val.endswith("+"):
                    thresh = int(val[:-1])
                    result = [j for j in result if j["priority"] >= thresh]
                elif "-" in val:
                    lo, hi = val.split("-", 1)
                    result = [j for j in result if int(lo) <= j["priority"] <= int(hi)]
                else:
                    result = [j for j in result if j["priority"] == int(val)]
            except ValueError:
                pass

        elif key == "skill":
            result = [
                j for j in result
                if val in {k.lower() for k in kw_data.get(j["url"], set())}
            ]

        elif key == "company":
            result = [j for j in result if val in j["company"].lower()]

        elif key == "board":
            result = [j for j in result if val in j["board"].lower()]

        elif key == "src":
            if val == "new":
                result = [j for j in result if j["type"] == "new"]
            elif val == "curated":
                result = [j for j in result if j["type"] != "new"]

        elif key == "comp":
            # comp:100k+  comp:150k+  comp:100k-200k
            try:
                v = val.replace("k", "").replace("K", "").replace("$", "").strip()
                if v.endswith("+"):
                    thresh = int(v[:-1]) * 1000
                    result = [
                        j for j in result
                        if (cv := parse_comp_value(j.get("comp", ""))) is not None
                        and cv >= thresh
                    ]
                elif "-" in v:
                    lo_s, hi_s = v.split("-", 1)
                    lo, hi = int(lo_s.strip()) * 1000, int(hi_s.strip()) * 1000
                    result = [
                        j for j in result
                        if (cv := parse_comp_value(j.get("comp", ""))) is not None
                        and lo <= cv <= hi
                    ]
            except (ValueError, AttributeError):
                pass

    return result
