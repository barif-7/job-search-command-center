"""Markdown feed and stats parsing (pure functions).

Walks the exported Markdown tracker and turns it back into structured job
dicts. No Streamlit and no implicit file reads — callers pass content in. The
one place that needs the file's mtime (``parse_md_stats`` last-modified label)
takes the path explicitly.
"""
from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path
from typing import Optional


def parse_md_stats(content: str, md_path: Optional[Path] = None) -> dict:
    """Extract quick stats from the markdown document.

    ``md_path`` is used only for the human-readable "last modified" label; when
    omitted the label is "Unknown".
    """
    stats: dict = {}

    # Count curated (manually reviewed) entries — numbered headings like "### 1." or "### AI-SF-1."
    curated = re.findall(r"^###\s+(?:\d+\.|AI-[A-Z]+-\d+\.|TS-\d+\.)", content, re.MULTILINE)
    stats["curated"] = len(curated)

    # Count newly fetched entries
    new_entries = re.findall(r"^###\s+NEW-\d+\.", content, re.MULTILINE)
    stats["new_fetched"] = len(new_entries)

    stats["total"] = stats["curated"] + stats["new_fetched"]

    # Priority 9–10 roles
    must_apply = re.findall(r"\*\*Priority:\s*(9|10)/10\*\*", content)
    stats["top_priority"] = len(must_apply)

    # Location breakdown — parse markdown table rows: | City... | n | n | total |
    loc_rows = re.findall(
        r"\|\s*(San Francisco|New York(?:\s*City)?|Seattle|Toronto|Vancouver)[^|]*\|[^|]*\|[^|]*\|\s*(\d+)\s*\|",
        content, re.IGNORECASE,
    )
    if loc_rows:
        seen: dict = {}
        for city, count in loc_rows:
            key = city.strip().title()
            if "New York" in key:
                key = "New York"
            if key not in seen:
                seen[key] = int(count)
        stats["by_location"] = seen

    # Last modified
    mtime = md_path.stat().st_mtime if (md_path and md_path.exists()) else None
    stats["last_modified"] = datetime.fromtimestamp(mtime).strftime("%b %d, %Y %H:%M") if mtime else "Unknown"

    return stats


def parse_job_entry(heading: str, body: str, section: str) -> Optional[dict]:
    """Parse a single ### / #### job entry into a structured dict."""
    at_idx = heading.rfind("@")
    if at_idx == -1:
        return None

    title_raw   = heading[:at_idx].strip()
    company_raw = heading[at_idx + 1:].strip()

    # Strip "_(see also #X)_" footnotes and trailing underscores from company
    company = re.sub(r"\s*_\(.*?\)_.*$", "", company_raw).strip().strip("_").strip()
    # Strip entry-number prefix and emoji from title
    title = re.sub(
        r"^(?:NEW-\d+\.|AI-[A-Z]+-\d+\.|TS-\d+\.|\d+\.|🔥\s*)",
        "", title_raw,
    ).strip()

    if not company or not title:
        return None

    def field(key: str) -> str:
        m = re.search(rf"\*\*{re.escape(key)}:\*\*\s*(.+?)(?:\n|$)", body, re.IGNORECASE)
        return m.group(1).strip() if m else ""

    # URL — first https link in the Link field
    link_raw = field("Link")
    url_m = re.search(r"https?://[^\s|),>]+", link_raw)
    url = url_m.group(0).rstrip(".,)") if url_m else ""

    comp = field("Comp")
    if re.match(r"not fetched", comp, re.I):
        comp = ""

    location = field("Location")
    board    = field("Board")
    fit      = field("Fit")
    if re.match(r"_?review needed_?", fit, re.I):
        fit = ""
    concerns = field("Concerns")

    # Priority — integer, 0 = unknown/unreviewed
    p_m = re.search(r"\*\*Priority:\s*(\?|\d+)/10\*\*", body)
    try:
        priority = int(p_m.group(1)) if p_m and p_m.group(1) != "?" else 0
    except (ValueError, AttributeError):
        priority = 0

    # Status
    s_m = re.search(r"Status:\s*\*{0,2}([^*\n|]+?)\*{0,2}(?:\n|\|)", body)
    status = s_m.group(1).strip() if s_m else "Saved"

    # Job type from heading prefix + section context
    section_l = section.lower()
    if re.match(r"NEW-\d+\.", title_raw):
        job_type = "new"
    elif "🔥" in heading or "must apply" in section_l:
        job_type = "top"
    elif re.match(r"AI-[A-Z]+-\d+\.", title_raw) or "ai " in section_l or "ai engineer" in section_l:
        job_type = "ai"
    else:
        job_type = "ios"

    # Infer city from section header when Location field is absent
    if not location:
        for city in ["San Francisco", "New York", "Seattle", "Toronto", "Vancouver", "Remote"]:
            if city.lower() in section_l:
                location = city
                break

    return {
        "company":  company,
        "title":    title,
        "url":      url,
        "comp":     comp,
        "location": location,
        "board":    board,
        "fit":      fit,
        "concerns": concerns,
        "priority": priority,
        "status":   status,
        "type":     job_type,
        "section":  section,
    }


def parse_exported_job_bullet(line: str, next_line: str, section: str) -> Optional[dict]:
    """Parse the bullet format produced by the dashboard markdown export."""
    match = re.match(
        r"^-\s+(?:\*\*)?\[(?P<company>[^\]]+)\](?:\*\*)?\s+"
        r"(?P<title>.+?)\s+(?:—|-)\s+(?P<location>.*?)\s+"
        r"\((?P<meta>[^)]*)\)\s*$",
        line,
    )
    if not match:
        return None

    company = match.group("company").strip()
    title = match.group("title").strip()
    location = match.group("location").strip()
    meta = [part.strip() for part in match.group("meta").split(",")]
    board = meta[0] if meta else ""

    url_m = re.search(r"https?://\S+", next_line or "")
    url = url_m.group(0).rstrip(".,)") if url_m else ""

    section_l = section.lower()
    title_l = title.lower()
    if any(term in title_l for term in ("ai", "machine learning", "ml engineer", "forward deployed")):
        job_type = "ai"
    elif any(term in title_l for term in ("ios", "mobile", "swift", "react native")):
        job_type = "ios"
    elif "new" in section_l:
        job_type = "new"
    else:
        job_type = "new"

    return {
        "company": company,
        "title": title,
        "url": url,
        "comp": "",
        "location": location,
        "board": board,
        "fit": "",
        "concerns": "",
        "priority": 0,
        "status": section or "New",
        "type": job_type,
        "section": section,
    }


def parse_md_jobs(content: str) -> list[dict]:
    """
    Walk the markdown line-by-line, track section context from ## / ### headers
    that don't contain '@', and parse every ### / #### heading that does.
    """
    jobs: list[dict] = []
    lines = content.split("\n")
    current_section = ""
    i = 0

    while i < len(lines):
        if lines[i].startswith("- "):
            job = parse_exported_job_bullet(
                lines[i],
                lines[i + 1] if i + 1 < len(lines) else "",
                current_section,
            )
            if job:
                jobs.append(job)
            i += 1
            continue

        h = re.match(r"^(#{2,4})\s+(.*)", lines[i])
        if not h:
            i += 1
            continue

        level        = len(h.group(1))
        heading_text = h.group(2).strip()

        if "@" not in heading_text:
            # Section header — update context (## and ### levels only)
            if level <= 3:
                current_section = heading_text
            i += 1
            continue

        # Job entry — collect body until next heading at same/higher level
        body_lines: list[str] = []
        j = i + 1
        while j < len(lines):
            nh = re.match(r"^(#{2,})", lines[j])
            if nh and len(nh.group(1)) <= level:
                break
            body_lines.append(lines[j])
            j += 1

        job = parse_job_entry(heading_text, "\n".join(body_lines), current_section)
        if job:
            jobs.append(job)
        i = j

    return jobs
