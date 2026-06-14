"""HTML render helpers for the dashboard (pure string builders).

Moved verbatim out of app.py. They consume the logo service and return HTML
fragments; Streamlit's st.markdown(..., unsafe_allow_html=True) renders them.
No Streamlit imports here, so they can be unit-tested directly.
"""
from __future__ import annotations

import html
import re

from jobsearch.services.logo_service import logo_sources

# ── City cover images for immersive view ──────────────────────────────────
# Each entry has an Unsplash search query and a CSS gradient fallback so cards
# always look polished even when the network image fails to load.

CITY_COVERS: dict[str, dict] = {
    "san francisco": {
        "query": "san+francisco+golden+gate+skyline",
        "gradient": "linear-gradient(160deg, #c94b4b 0%, #4b134f 100%)",
        "label": "San Francisco", "emoji": "🌉",
    },
    "new york": {
        "query": "new+york+city+manhattan+skyline+night",
        "gradient": "linear-gradient(160deg, #0f2027 0%, #203a43 50%, #2c5364 100%)",
        "label": "New York", "emoji": "🗽",
    },
    "nyc": {
        "query": "new+york+city+skyline",
        "gradient": "linear-gradient(160deg, #0f2027 0%, #2c5364 100%)",
        "label": "New York", "emoji": "🗽",
    },
    "seattle": {
        "query": "seattle+space+needle+skyline+pacific",
        "gradient": "linear-gradient(160deg, #134e5e 0%, #71b280 100%)",
        "label": "Seattle", "emoji": "🌧️",
    },
    "toronto": {
        "query": "toronto+cn+tower+canada+skyline",
        "gradient": "linear-gradient(160deg, #c0392b 0%, #8e44ad 100%)",
        "label": "Toronto", "emoji": "🍁",
    },
    "vancouver": {
        "query": "vancouver+mountains+ocean+harbour+canada",
        "gradient": "linear-gradient(160deg, #005c97 0%, #363795 100%)",
        "label": "Vancouver", "emoji": "🏔️",
    },
    "palo alto": {
        "query": "silicon+valley+california+tech+campus",
        "gradient": "linear-gradient(160deg, #f7971e 0%, #c0392b 100%)",
        "label": "Palo Alto", "emoji": "☀️",
    },
    "bellevue": {
        "query": "bellevue+washington+pacific+northwest+skyline",
        "gradient": "linear-gradient(160deg, #1a3a4a 0%, #2d7d9a 100%)",
        "label": "Bellevue", "emoji": "🌲",
    },
    "montreal": {
        "query": "montreal+canada+old+city+skyline",
        "gradient": "linear-gradient(160deg, #1e3799 0%, #0c2461 100%)",
        "label": "Montréal", "emoji": "🏙️",
    },
    "remote": {
        "query": "minimal+home+office+laptop+productivity",
        "gradient": "linear-gradient(160deg, #396afc 0%, #2948ff 100%)",
        "label": "Remote", "emoji": "🌐",
    },
    "canada": {
        "query": "canada+landscape+mountains+nature",
        "gradient": "linear-gradient(160deg, #d31027 0%, #ea384d 100%)",
        "label": "Canada", "emoji": "🍁",
    },
}
DEFAULT_CITY_COVER = {
    "query": "modern+tech+office+city",
    "gradient": "linear-gradient(160deg, #2d3436 0%, #636e72 100%)",
    "label": "", "emoji": "🏢",
}

TYPE_BADGE: dict[str, tuple[str, str]] = {
    "top": ("background:#fff0d8;color:#b45309;border:1px solid rgba(217,119,6,0.32)", "Top Pick"),
    "ai":  ("background:#efe8ff;color:#6d28d9;border:1px solid rgba(124,58,237,0.22)", "AI"),
    "ios": ("background:#e7f0ff;color:#1d4ed8;border:1px solid rgba(37,99,235,0.18)", "iOS"),
    "new": ("background:#f3f4f6;color:#475569;border:1px solid rgba(71,85,105,0.16)", "New"),
}


def inline_initials(company: str) -> str:
    initials = "".join(part[:1] for part in re.findall(r"[A-Za-z0-9]+", company)[:2]).upper()
    return initials or "?"


def logo_img_html(company: str, job_url: str = "", size: int = 46) -> str:
    sources = logo_sources(company, job_url=job_url, size=size)
    primary = html.escape(sources[0], quote=True) if sources else ""
    fallback_str = html.escape("|".join(sources[1:]), quote=True)
    initials = html.escape(inline_initials(company))
    company_attr = html.escape(company)
    return (
        '<div class="company-mark">'
        f'<img src="{primary}" alt="{company_attr} logo" data-fallbacks="{fallback_str}" data-idx="0" '
        'onerror="const fallbacks=(this.dataset.fallbacks||\'\').split(\'|\').filter(Boolean);'
        'const idx=Number(this.dataset.idx||0);'
        'if(idx < fallbacks.length){this.dataset.idx=String(idx+1);this.src=fallbacks[idx];}'
        'else{this.style.display=\'none\';const fb=this.nextElementSibling;if(fb){fb.style.display=\'flex\';}}" />'
        f'<span class="company-mark__fallback">{initials}</span>'
        '</div>'
    )


def city_cover_config(location: str) -> dict:
    """Return the city cover config dict for a location string."""
    loc = location.lower()
    for key, cfg in CITY_COVERS.items():
        if key in loc:
            return cfg
    return DEFAULT_CITY_COVER


def city_cover_html(location: str) -> str:
    """Render a city cover image strip (gradient bg + Unsplash photo overlay)."""
    cfg = city_cover_config(location)
    query = cfg["query"]
    gradient = cfg["gradient"]
    label = cfg["label"] or location
    emoji = cfg["emoji"]
    # Unsplash source API — if the image fails to load, the CSS gradient shows through
    img_url = f"https://source.unsplash.com/featured/800x260/?{query}"
    return (
        f'<div class="immersive-card__cover" style="background:{gradient}">'
        f'<img class="immersive-card__photo" src="{img_url}" '
        f'alt="{html.escape(label)} skyline" loading="lazy" '
        f'onerror="this.style.display=\'none\'" />'
        f'<div class="immersive-card__overlay">'
        f'<span class="immersive-card__city-label">{emoji}&nbsp; {html.escape(label.upper())}</span>'
        f'</div>'
        f'</div>'
    )


def priority_badge(priority: int) -> tuple[str, str]:
    """Return (css_style, label) for a priority badge."""
    if priority >= 9:
        return (
            "background:#dcfce7;color:#166534;border:1px solid rgba(22,163,74,0.24)",
            f"{priority}/10",
        )
    if priority >= 7:
        return (
            "background:#fff4d4;color:#b45309;border:1px solid rgba(217,119,6,0.24)",
            f"{priority}/10",
        )
    if priority >= 1:
        return (
            "background:#f8fafc;color:#475569;border:1px solid rgba(71,85,105,0.16)",
            f"{priority}/10",
        )
    return (
        "background:#f8fafc;color:#64748b;border:1px solid rgba(71,85,105,0.16)",
        "Unrated",
    )


def card_html(
    company: str, title: str, url: str, comp: str,
    location: str, board: str, fit: str, concerns: str,
    priority: int, job_type: str,
) -> str:
    job = {
        "company": company, "title": title, "url": url, "comp": comp,
        "location": location, "board": board, "fit": fit,
        "concerns": concerns, "priority": priority, "type": job_type,
    }

    p_style, p_label = priority_badge(priority)
    t_style, t_label = TYPE_BADGE.get(job["type"], TYPE_BADGE["ios"])
    logo_html = logo_img_html(job["company"], job["url"], size=48)

    # Meta pills
    meta_parts = []
    if job["location"]:
        meta_parts.append(job["location"])
    if job["comp"]:
        meta_parts.append(job["comp"])
    if job["board"]:
        meta_parts.append(job["board"].upper())
    meta_html = (
        '<div class="job-card__meta">'
        + "".join(f'<span class="job-card__pill">{html.escape(p)}</span>' for p in meta_parts)
        + "</div>"
    ) if meta_parts else ""

    # Fit snippet — strip markdown, clamp to 3 lines
    fit_html = ""
    if job["fit"]:
        snippet = re.sub(r"\*{1,2}([^*]+)\*{1,2}", r"\1", job["fit"])[:240]
        if len(job["fit"]) > 240:
            snippet += "…"
        fit_html = f'<p class="job-card__copy">{html.escape(snippet)}</p>'

    # Concerns snippet
    concerns_html = ""
    if job["concerns"]:
        c = re.sub(r"\*{1,2}([^*]+)\*{1,2}", r"\1", job["concerns"])[:140]
        concerns_html = f'<p class="job-card__warning">Watch-out: {html.escape(c)}</p>'

    apply_html = (
        f'<a class="job-card__cta" href="{html.escape(job["url"], quote=True)}" target="_blank">Open posting <span aria-hidden="true">↗</span></a>'
    ) if job["url"] else ""

    return (
        '<div class="job-card">'
        '<div class="job-card__header">'
          '<div class="job-card__identity">'
            f'{logo_html}'
            '<div style="min-width:0">'
              f'<div class="job-card__company">{html.escape(job["company"])}</div>'
              f'<div class="job-card__title">{html.escape(job["title"])}</div>'
            '</div>'
          '</div>'
          '<div class="job-card__badge-row">'
            f'<span style="{t_style};padding:0.35rem 0.65rem;border-radius:999px;font-size:0.69rem;font-weight:800;white-space:nowrap">{t_label}</span>'
            f'<span style="{p_style};padding:0.35rem 0.65rem;border-radius:999px;font-size:0.69rem;font-weight:800;white-space:nowrap">{p_label}</span>'
          '</div>'
        '</div>'
        f"{meta_html}"
        f"{fit_html}"
        f"{concerns_html}"
        f"{apply_html}"
        '</div>'
    )


def card_html_list(
    company: str, title: str, url: str, comp: str,
    location: str, board: str, priority: int, job_type: str,
) -> str:
    """Compact single-row card for the list view."""
    logo = logo_img_html(company, url, size=34)
    p_style, p_label = priority_badge(priority)
    t_style, t_label = TYPE_BADGE.get(job_type, TYPE_BADGE["ios"])

    meta_parts = [html.escape(company)]
    if location:
        meta_parts.append(html.escape(location))
    if board:
        meta_parts.append(board.upper())
    meta_str = " · ".join(meta_parts)

    comp_html = (
        f'<span class="list-item__comp">{html.escape(comp)}</span>'
    ) if comp else ""
    link_html = (
        f'<a class="list-item__link" href="{html.escape(url, quote=True)}" target="_blank">Open ↗</a>'
    ) if url else ""

    return (
        '<div class="list-item">'
        f'{logo}'
        '<div class="list-item__info">'
        f'<div class="list-item__title">{html.escape(title)}</div>'
        f'<div class="list-item__meta">{meta_str}</div>'
        '</div>'
        '<div class="list-item__right">'
        f'{comp_html}'
        f'<span class="list-item__badge" style="{t_style}">{t_label}</span>'
        f'<span class="list-item__badge" style="{p_style}">{p_label}</span>'
        f'{link_html}'
        '</div>'
        '</div>'
    )


def card_html_immersive(
    company: str, title: str, url: str, comp: str,
    location: str, board: str, fit: str, concerns: str,
    priority: int, job_type: str,
) -> str:
    """Card with a city cover image at the top for the immersive view."""
    cover = city_cover_html(location)
    p_style, p_label = priority_badge(priority)
    t_style, t_label = TYPE_BADGE.get(job_type, TYPE_BADGE["ios"])
    logo = logo_img_html(company, url, size=44)

    meta_parts = []
    if location:
        meta_parts.append(location)
    if comp:
        meta_parts.append(comp)
    if board:
        meta_parts.append(board.upper())
    meta_html = (
        '<div class="job-card__meta">'
        + "".join(f'<span class="job-card__pill">{html.escape(p)}</span>' for p in meta_parts)
        + "</div>"
    ) if meta_parts else ""

    fit_html = ""
    if fit:
        snippet = re.sub(r"\*{1,2}([^*]+)\*{1,2}", r"\1", fit)[:200]
        if len(fit) > 200:
            snippet += "…"
        fit_html = f'<p class="job-card__copy">{html.escape(snippet)}</p>'

    concerns_html = ""
    if concerns:
        c = re.sub(r"\*{1,2}([^*]+)\*{1,2}", r"\1", concerns)[:120]
        concerns_html = f'<p class="job-card__warning">⚠ {html.escape(c)}</p>'

    apply_html = (
        f'<a class="job-card__cta" href="{html.escape(url, quote=True)}" target="_blank">'
        f'Open posting <span aria-hidden="true">↗</span></a>'
    ) if url else ""

    return (
        '<div class="immersive-card">'
        f'{cover}'
        '<div class="immersive-card__body">'
          '<div class="job-card__header">'
            '<div class="job-card__identity">'
              f'{logo}'
              '<div style="min-width:0">'
                f'<div class="job-card__company">{html.escape(company)}</div>'
                f'<div class="job-card__title">{html.escape(title)}</div>'
              '</div>'
            '</div>'
            '<div class="job-card__badge-row">'
              f'<span style="{t_style};padding:0.32rem 0.6rem;border-radius:999px;font-size:0.67rem;font-weight:800;white-space:nowrap">{t_label}</span>'
              f'<span style="{p_style};padding:0.32rem 0.6rem;border-radius:999px;font-size:0.67rem;font-weight:800;white-space:nowrap">{p_label}</span>'
            '</div>'
          '</div>'
          f'{meta_html}'
          f'{fit_html}'
          f'{concerns_html}'
          f'{apply_html}'
        '</div>'
        '</div>'
    )


def metric_card_html(label: str, value: str, note: str) -> str:
    return (
        '<div class="metric-shell">'
        f'<div class="metric-label">{html.escape(label)}</div>'
        f'<div class="metric-value">{html.escape(value)}</div>'
        f'<div class="metric-note">{html.escape(note)}</div>'
        '</div>'
    )


def surface_header_html(title: str, copy: str) -> str:
    return (
        '<div class="surface-shell">'
        f'<div class="surface-title">{html.escape(title)}</div>'
        f'<p class="surface-copy">{html.escape(copy)}</p>'
        '</div>'
    )


def hero_html(title: str, copy: str, pills: list[str], eyebrow: str = "Live Pipeline") -> str:
    pills_html = "".join(f'<span class="hero-pill">{html.escape(p)}</span>' for p in pills)
    return (
        '<div class="hero-shell">'
        f'<p class="hero-eyebrow">{html.escape(eyebrow)}</p>'
        f'<h1 class="hero-title">{html.escape(title)}</h1>'
        f'<p class="hero-copy">{html.escape(copy)}</p>'
        f'<div class="hero-pills">{pills_html}</div>'
        '</div>'
    )


def mini_role_html(company: str, title: str, location: str, score: int | float | None, job_url: str) -> str:
    badge = f"{int(score)}/10" if score and score > 0 else "Unrated"
    title_html = html.escape(title)
    company_html = html.escape(company)
    location_html = html.escape(location or "Location not specified")
    link_open = f'<a href="{html.escape(job_url, quote=True)}" target="_blank" style="text-decoration:none">' if job_url else ""
    link_close = "</a>" if job_url else ""
    return (
        f'{link_open}<div class="mini-role">'
        f'{logo_img_html(company, job_url=job_url, size=42)}'
        '<div style="min-width:0">'
        f'<p class="mini-role__title">{company_html} — {title_html}</p>'
        f'<div class="mini-role__meta">{location_html}</div>'
        '</div>'
        f'<div class="mini-role__score">{html.escape(badge)}</div>'
        f'</div>{link_close}'
    )
