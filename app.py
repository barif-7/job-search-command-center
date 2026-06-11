#!/usr/bin/env python3
"""
Job Search Command Center — Streamlit dashboard
Run from the job-search-command-center/ directory:
    streamlit run app.py
"""

from __future__ import annotations

import logging
import os
import re
import json
import html
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

import pandas as pd
import streamlit as st

logger = logging.getLogger(__name__)

# Ensure imports resolve correctly regardless of CWD
_HERE = Path(__file__).parent
sys.path.insert(0, str(_HERE))
sys.path.insert(0, str(_HERE.parent))  # for careerBoards

from config import APPLICATION_STATUSES, JOB_STATUSES
from jobsearch.apply.profile import profile_readiness
from jobsearch.settings import get_settings
from jobsearch.store import JobStore

_SETTINGS = get_settings()
DATABASE_PATH = _SETTINGS.database_path
MARKDOWN_EXPORT_PATH = _SETTINGS.markdown_export_path

# ── Company → domain mapping (for logo providers) ─────────────────────────

COMPANY_DOMAINS: dict[str, str] = {
    "Anthropic":              "anthropic.com",
    "OpenAI":                 "openai.com",
    "Perplexity":             "perplexity.ai",
    "Reddit":                 "reddit.com",
    "Strava":                 "strava.com",
    "Mercury":                "mercury.com",
    "Gusto":                  "gusto.com",
    "Headway":                "headway.com",
    "AssemblyAI":             "assemblyai.com",
    "Automattic":             "automattic.com",
    "Tailscale":              "tailscale.com",
    "HeyGen":                 "heygen.com",
    "Speechify":              "speechify.com",
    "Luma AI":                "lumalabs.ai",
    "EarnIn":                 "earnin.com",
    "MyFitnessPal":           "myfitnesspal.com",
    "Faire":                  "faire.com",
    "TouchBistro":            "touchbistro.com",
    "Warp":                   "warp.dev",
    "Notion":                 "notion.so",
    "Figma":                  "figma.com",
    "xAI":                    "x.ai",
    "The New York Times":     "nytimes.com",
    "DoorDash USA":           "doordash.com",
    "Canonical":              "canonical.com",
    "GitLab":                 "gitlab.com",
    "The Trade Desk":         "thetradedesk.com",
    "MLB":                    "mlb.com",
    "Breeze Airways":         "flybreeze.com",
    "Impact.com":             "impact.com",
    "Wealthsimple":           "wealthsimple.com",
    "Lime":                   "li.me",
    "January AI":             "january.ai",
    "Palantir":               "palantir.com",
    "Ro":                     "ro.co",
    "Dun & Bradstreet":       "dnb.com",
    "Binance":                "binance.com",
    "JumpCloud":              "jumpcloud.com",
    "HighLevel":              "gohighlevel.com",
    "PermitFlow":             "permitflow.com",
    "Ramp":                   "ramp.com",
    "Linear":                 "linear.app",
    "Sentry":                 "sentry.io",
    "Cohere":                 "cohere.com",
    "Ideogram":               "ideogram.ai",
    "Sesame AI":              "sesame.com",
    "Speak":                  "speak.com",
    "RevenueCat":             "revenuecat.com",
    "Pika":                   "pika.art",
    "ElevenLabs":             "elevenlabs.io",
    "Rogo":                   "rogo.ai",
    "Suno":                   "suno.com",
    "Whatnot":                "whatnot.com",
    "Bankjoy":                "bankjoy.com",
    "Copilot Money":          "copilot.money",
    "Ground News":            "ground.news",
    "Mem0":                   "mem0.ai",
    "Writer":                 "writer.com",
    "Gradient":               "gradient.ai",
    "Nord Security":          "nordvpn.com",
    "Bevel":                  "bevel.com",
    "Pocket Prep":            "pocketprep.com",
    "Notable":                "notablehealth.com",
    "Clipboard":              "clipboard.health",
    "Reedsy":                 "reedsy.com",
    "The Browser Company":    "arc.net",
    "Nomic":                  "nomic.ai",
    "Stream":                 "getstream.io",
    "Abridge":                "abridge.com",
    "Replit":                 "replit.com",
    "EliseAI":                "eliseai.com",
    "Dust":                   "dust.tt",
    "Ashby":                  "ashby.com",
    "Shopify":                "shopify.com",
    "Airbnb":                 "airbnb.com",
    "Zapier":                 "zapier.com",
    "Ada":                    "ada.cx",
    "Braze":                  "braze.com",
    "Intuit":                 "intuit.com",
    "Samsara":                "samsara.com",
}

BOARD_HOSTS = {
    "boards.greenhouse.io",
    "job-boards.greenhouse.io",
    "jobs.ashbyhq.com",
    "boards.eu.greenhouse.io",
    "jobs.lever.co",
}

DOMAIN_GUESSES = [".com", ".ai", ".co", ".app", ".dev", ".io", ".so"]

_LOGO_DEV_TOKEN = _SETTINGS.logo_dev_token

# ── City cover images for immersive view ──────────────────────────────────
# Each entry has an Unsplash search query and a CSS gradient fallback so cards
# always look polished even when the network image fails to load.

_CITY_COVERS: dict[str, dict] = {
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
_DEFAULT_CITY_COVER = {
    "query": "modern+tech+office+city",
    "gradient": "linear-gradient(160deg, #2d3436 0%, #636e72 100%)",
    "label": "", "emoji": "🏢",
}


@st.cache_data(show_spinner=False)
def _normalize_company_name(company: str) -> str:
    return re.sub(r"\s+", " ", company.strip()).lower()


@st.cache_data(show_spinner=False)
def _base_logo_url(domain: str, size: int) -> str:
    url = f"https://img.logo.dev/{domain}?format=png&size={size}"
    if _LOGO_DEV_TOKEN:
        url += f"&token={_LOGO_DEV_TOKEN}"
    return url


@st.cache_data(show_spinner=False)
def _google_favicon_url(domain: str, size: int) -> str:
    return (
        "https://t1.gstatic.com/faviconV2"
        f"?client=SOCIAL&type=FAVICON&fallback_opts=TYPE,SIZE,URL&url=http://{domain}&size={size}"
    )


@st.cache_data(show_spinner=False)
def resolve_company_domain(company: str, job_url: str = "") -> str:
    """Resolve the most likely domain for a company, preferring curated mappings."""
    normalized = _normalize_company_name(company)
    for known_company, domain in COMPANY_DOMAINS.items():
        if _normalize_company_name(known_company) == normalized:
            return domain

    if job_url:
        parsed = urlparse(job_url)
        host = parsed.netloc.lower().split(":")[0]
        if host and host not in BOARD_HOSTS and "." in host:
            return host.removeprefix("www.")

    slug = re.sub(r"[^a-z0-9]", "", normalized)
    if slug:
        return f"{slug}.com"
    return ""


@st.cache_data(show_spinner=False)
def logo_sources(company: str, job_url: str = "", size: int = 64) -> list[str]:
    """
    Build multiple logo candidates so the frontend can fall back gracefully.

    Priority order:
      1. Google favicon (t1.gstatic) — reliable, no auth required
      2. logo.dev — higher quality, but only added when LOGO_DEV_TOKEN is set
      3. Google s2/favicons — last resort (follows redirect to t0.gstatic)

    The first URL is also used by the data_editor ImageColumn, which is proxied
    server-side with no JS fallback, so it must be a URL that resolves without auth.
    """
    sources: list[str] = []
    normalized = _normalize_company_name(company)
    domain = resolve_company_domain(company, job_url)
    candidate_domains = []

    if domain:
        candidate_domains.append(domain)

    if domain and domain.endswith(".com"):
        slug = domain[:-4]
        for suffix in DOMAIN_GUESSES[1:]:
            candidate_domains.append(f"{slug}{suffix}")

    slug = re.sub(r"[^a-z0-9]", "", normalized)
    if slug:
        for suffix in DOMAIN_GUESSES:
            candidate_domains.append(f"{slug}{suffix}")

    seen_domains = set()
    for candidate in candidate_domains:
        if not candidate or candidate in seen_domains:
            continue
        seen_domains.add(candidate)
        # Google favicon first — works without any API key
        sources.append(_google_favicon_url(candidate, size))
        # logo.dev second — best quality, but 404s without a valid token
        if _LOGO_DEV_TOKEN:
            sources.append(_base_logo_url(candidate, size))
        # Google s2/favicons as final fallback (redirects to t0.gstatic)
        sources.append(f"https://www.google.com/s2/favicons?sz={size}&domain={candidate}")

    return sources


@st.cache_data(show_spinner=False)
def logo_url(company: str, job_url: str = "", size: int = 40) -> str:
    """Return the primary logo URL for image columns and simple previews.

    Always returns the Google favicon URL (first in sources) so the data_editor
    ImageColumn — which proxies server-side with no JS fallback — reliably loads.
    """
    sources = logo_sources(company, job_url=job_url, size=size)
    return sources[0] if sources else ""


def _inline_initials(company: str) -> str:
    initials = "".join(part[:1] for part in re.findall(r"[A-Za-z0-9]+", company)[:2]).upper()
    return initials or "?"


def _logo_img_html(company: str, job_url: str = "", size: int = 46) -> str:
    sources = logo_sources(company, job_url=job_url, size=size)
    primary = html.escape(sources[0], quote=True) if sources else ""
    fallback_str = html.escape("|".join(sources[1:]), quote=True)
    initials = html.escape(_inline_initials(company))
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

# ── Page config ────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="Job Search Command Center",
    page_icon="🔍",
    layout="wide",
)

APP_CSS = """
<style>
    :root {
        --bg: #f4efe6;
        --surface: rgba(255,255,255,0.78);
        --surface-strong: rgba(255,255,255,0.92);
        --border: rgba(29, 53, 87, 0.12);
        --ink: #14213d;
        --muted: #5c677d;
        --accent: #0f766e;
        --accent-soft: #d7f3ef;
        --gold: #d97706;
        --shadow: 0 18px 50px rgba(20, 33, 61, 0.08);
    }

    .stApp {
        background:
            radial-gradient(circle at top left, rgba(15,118,110,0.18), transparent 28%),
            radial-gradient(circle at top right, rgba(217,119,6,0.14), transparent 24%),
            linear-gradient(180deg, #fcfaf5 0%, var(--bg) 56%, #efe7d8 100%);
    }

    .block-container {
        padding-top: 2.2rem;
        padding-bottom: 3rem;
        max-width: 1260px;
    }

    h1, h2, h3 {
        color: var(--ink);
        letter-spacing: -0.02em;
    }

    p, label, .stCaption, .stMarkdown, .stTextInput, .stSelectbox, .stMultiSelect {
        color: var(--ink);
    }

    .stTabs [data-baseweb="tab-list"] {
        gap: 0.55rem;
        background: rgba(255,255,255,0.5);
        padding: 0.35rem;
        border-radius: 999px;
        border: 1px solid var(--border);
    }

    .stTabs [data-baseweb="tab"] {
        height: 2.65rem;
        border-radius: 999px;
        padding: 0 1rem;
        color: var(--muted);
        font-weight: 600;
    }

    .stTabs [aria-selected="true"] {
        background: var(--surface-strong);
        color: var(--ink);
        box-shadow: 0 8px 20px rgba(20, 33, 61, 0.08);
    }

    .hero-shell,
    .surface-shell,
    .metric-shell,
    .summary-shell {
        border: 1px solid var(--border);
        background: var(--surface);
        backdrop-filter: blur(14px);
        -webkit-backdrop-filter: blur(14px);
        box-shadow: var(--shadow);
    }

    .hero-shell {
        border-radius: 28px;
        padding: 1.6rem 1.8rem;
        margin-bottom: 1rem;
    }

    .hero-eyebrow {
        margin: 0 0 0.35rem 0;
        text-transform: uppercase;
        letter-spacing: 0.14em;
        font-size: 0.74rem;
        font-weight: 700;
        color: var(--accent);
    }

    .hero-title {
        margin: 0;
        font-size: clamp(1.9rem, 4vw, 3rem);
        line-height: 1.02;
    }

    .hero-copy {
        margin: 0.6rem 0 1rem 0;
        color: var(--muted);
        max-width: 48rem;
        line-height: 1.6;
    }

    .hero-pills {
        display: flex;
        gap: 0.6rem;
        flex-wrap: wrap;
    }

    .hero-pill {
        padding: 0.45rem 0.8rem;
        border-radius: 999px;
        background: rgba(255,255,255,0.75);
        border: 1px solid var(--border);
        color: var(--ink);
        font-size: 0.84rem;
        font-weight: 600;
    }

    .metric-shell {
        border-radius: 22px;
        padding: 1rem 1.1rem;
        min-height: 7.6rem;
    }

    .metric-label {
        color: var(--muted);
        font-size: 0.82rem;
        font-weight: 600;
    }

    .metric-value {
        font-size: 2rem;
        line-height: 1;
        font-weight: 800;
        color: var(--ink);
        margin: 0.55rem 0 0.35rem 0;
    }

    .metric-note {
        color: var(--muted);
        font-size: 0.82rem;
        line-height: 1.45;
    }

    .surface-shell,
    .summary-shell {
        border-radius: 24px;
        padding: 1.15rem 1.2rem;
        margin-bottom: 1rem;
    }

    .surface-title {
        margin: 0 0 0.2rem 0;
        font-size: 1rem;
        font-weight: 700;
        color: var(--ink);
    }

    .surface-copy {
        margin: 0;
        color: var(--muted);
        font-size: 0.88rem;
        line-height: 1.55;
    }

    .mini-role {
        display: flex;
        gap: 0.75rem;
        align-items: flex-start;
        padding: 0.8rem 0;
        border-bottom: 1px solid rgba(29, 53, 87, 0.08);
    }

    .mini-role:last-child {
        border-bottom: none;
        padding-bottom: 0;
    }

    .mini-role__title {
        margin: 0;
        color: var(--ink);
        font-weight: 700;
        font-size: 0.95rem;
        line-height: 1.35;
    }

    .mini-role__meta {
        color: var(--muted);
        font-size: 0.82rem;
        margin-top: 0.2rem;
    }

    .mini-role__score {
        margin-left: auto;
        padding: 0.35rem 0.6rem;
        border-radius: 999px;
        background: var(--accent-soft);
        color: var(--accent);
        font-size: 0.78rem;
        font-weight: 800;
        white-space: nowrap;
    }

    .job-card {
        border: 1px solid var(--border);
        border-radius: 22px;
        padding: 1rem;
        margin-bottom: 0.95rem;
        background: linear-gradient(180deg, rgba(255,255,255,0.95), rgba(251,248,240,0.88));
        box-shadow: 0 16px 34px rgba(20, 33, 61, 0.08);
    }

    .job-card__header {
        display: flex;
        justify-content: space-between;
        gap: 0.8rem;
        align-items: flex-start;
    }

    .job-card__identity {
        display: flex;
        gap: 0.85rem;
        min-width: 0;
        flex: 1;
    }

    .job-card__company {
        color: var(--muted);
        font-size: 0.78rem;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        font-weight: 700;
    }

    .job-card__title {
        color: var(--ink);
        font-size: 1rem;
        font-weight: 800;
        margin-top: 0.12rem;
        line-height: 1.35;
    }

    .job-card__badge-row {
        display: flex;
        gap: 0.35rem;
        flex-wrap: wrap;
        justify-content: flex-end;
    }

    .job-card__meta {
        display: flex;
        flex-wrap: wrap;
        gap: 0.55rem;
        margin-top: 0.9rem;
    }

    .job-card__pill {
        border-radius: 999px;
        padding: 0.38rem 0.65rem;
        background: rgba(15, 118, 110, 0.08);
        color: var(--ink);
        font-size: 0.76rem;
        font-weight: 600;
    }

    .job-card__copy {
        color: var(--muted);
        font-size: 0.84rem;
        line-height: 1.6;
        margin: 0.85rem 0 0 0;
    }

    .job-card__warning {
        color: #b45309;
        font-size: 0.78rem;
        font-weight: 600;
        margin-top: 0.55rem;
    }

    .job-card__cta {
        display: inline-flex;
        align-items: center;
        gap: 0.45rem;
        margin-top: 0.95rem;
        color: var(--accent);
        text-decoration: none;
        font-weight: 700;
        font-size: 0.83rem;
    }

    .company-mark {
        width: 2.85rem;
        height: 2.85rem;
        border-radius: 16px;
        overflow: hidden;
        flex-shrink: 0;
        position: relative;
        border: 1px solid rgba(29, 53, 87, 0.08);
        background: linear-gradient(135deg, rgba(15,118,110,0.14), rgba(217,119,6,0.12));
    }

    .company-mark img,
    .company-mark__fallback {
        width: 100%;
        height: 100%;
    }

    .company-mark img {
        object-fit: contain;
        background: rgba(255,255,255,0.78);
    }

    .company-mark__fallback {
        display: none;
        align-items: center;
        justify-content: center;
        font-weight: 800;
        color: var(--ink);
        font-size: 0.96rem;
    }

    .summary-empty {
        border: 1px dashed rgba(29, 53, 87, 0.22);
        border-radius: 22px;
        padding: 2rem;
        text-align: center;
        color: var(--muted);
        background: rgba(255,255,255,0.54);
    }

    @media (max-width: 900px) {
        .hero-shell {
            padding: 1.25rem;
        }

        .metric-shell {
            min-height: auto;
        }

        .job-card__header {
            flex-direction: column;
        }

        .job-card__badge-row {
            justify-content: flex-start;
        }
    }

    /* ── Button theme — teal primary, glass secondary ───────────────────── */

    .stButton > button {
        border-radius: 999px !important;
        font-weight: 600 !important;
        transition: all 0.16s ease !important;
        letter-spacing: 0.01em;
    }

    .stButton > button[kind="primary"] {
        background: var(--accent) !important;
        border-color: var(--accent) !important;
        color: white !important;
    }

    .stButton > button[kind="primary"]:hover {
        background: #0a6158 !important;
        border-color: #0a6158 !important;
        box-shadow: 0 4px 16px rgba(15, 118, 110, 0.38) !important;
    }

    .stButton > button[kind="secondary"] {
        background: rgba(255,255,255,0.62) !important;
        border: 1px solid var(--border) !important;
        color: var(--muted) !important;
    }

    .stButton > button[kind="secondary"]:hover {
        background: rgba(255,255,255,0.92) !important;
        border-color: rgba(15, 118, 110, 0.32) !important;
        color: var(--accent) !important;
    }

    /* ── Filter group labels ─────────────────────────────────────────────── */

    .filter-group-label {
        margin: 0.6rem 0 0.3rem 0;
        font-size: 0.69rem;
        font-weight: 800;
        letter-spacing: 0.11em;
        text-transform: uppercase;
        color: var(--muted);
    }

    /* ── Immersive / city card ───────────────────────────────────────────── */

    .immersive-card {
        border: 1px solid var(--border);
        border-radius: 22px;
        overflow: hidden;
        margin-bottom: 0.95rem;
        background: linear-gradient(180deg, rgba(255,255,255,0.96), rgba(251,248,240,0.9));
        box-shadow: 0 16px 34px rgba(20, 33, 61, 0.08);
        transition: transform 0.18s ease, box-shadow 0.18s ease;
    }

    .immersive-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 26px 50px rgba(20, 33, 61, 0.14);
    }

    .immersive-card__cover {
        position: relative;
        height: 130px;
        overflow: hidden;
    }

    .immersive-card__photo {
        width: 100%;
        height: 100%;
        object-fit: cover;
        display: block;
        filter: brightness(0.8) saturate(1.15);
    }

    .immersive-card__overlay {
        position: absolute;
        inset: 0;
        background: linear-gradient(
            to bottom,
            rgba(0,0,0,0.06) 0%,
            rgba(0,0,0,0.58) 100%
        );
        display: flex;
        align-items: flex-end;
        padding: 0.6rem 0.85rem;
    }

    .immersive-card__city-label {
        color: rgba(255,255,255,0.95);
        font-size: 0.7rem;
        font-weight: 800;
        letter-spacing: 0.1em;
        text-transform: uppercase;
        text-shadow: 0 1px 6px rgba(0,0,0,0.55);
    }

    .immersive-card__body {
        padding: 0.85rem 1rem 1rem;
    }

    /* ── List-view item ──────────────────────────────────────────────────── */

    .list-item {
        display: flex;
        align-items: center;
        gap: 0.75rem;
        padding: 0.62rem 0.9rem;
        border: 1px solid var(--border);
        border-radius: 16px;
        background: rgba(255,255,255,0.7);
        margin-bottom: 0.4rem;
        transition: background 0.14s ease, box-shadow 0.14s ease;
    }

    .list-item:hover {
        background: rgba(255,255,255,0.95);
        box-shadow: 0 6px 18px rgba(20, 33, 61, 0.07);
    }

    .list-item__info {
        flex: 1;
        min-width: 0;
    }

    .list-item__title {
        font-size: 0.87rem;
        font-weight: 700;
        color: var(--ink);
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }

    .list-item__meta {
        font-size: 0.74rem;
        color: var(--muted);
        margin-top: 0.1rem;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }

    .list-item__right {
        display: flex;
        align-items: center;
        gap: 0.4rem;
        flex-shrink: 0;
    }

    .list-item__comp {
        font-size: 0.74rem;
        color: var(--accent);
        font-weight: 700;
        white-space: nowrap;
    }

    .list-item__badge {
        border-radius: 999px;
        padding: 0.22rem 0.5rem;
        font-size: 0.64rem;
        font-weight: 800;
        white-space: nowrap;
    }

    .list-item__link {
        color: var(--accent);
        font-size: 0.76rem;
        font-weight: 700;
        text-decoration: none;
        white-space: nowrap;
        padding: 0.26rem 0.65rem;
        border-radius: 999px;
        border: 1px solid var(--accent);
        transition: background 0.14s ease;
    }

    .list-item__link:hover {
        background: var(--accent-soft);
    }

    @media (max-width: 900px) {
        .immersive-card__cover { height: 100px; }
        .list-item { flex-wrap: wrap; }
    }
</style>
"""

st.markdown(APP_CSS, unsafe_allow_html=True)

MD_PATH = Path(MARKDOWN_EXPORT_PATH)

# ── Store (singleton) ──────────────────────────────────────────────────────

@st.cache_resource
def get_store() -> JobStore:
    return JobStore(db_path=DATABASE_PATH)


store = get_store()

# ── Data loader ────────────────────────────────────────────────────────────

@st.cache_data(show_spinner=False)
def load_jobs(db_mtime: float) -> pd.DataFrame:
    """Cache keyed by DB mtime — auto-invalidates when the DB file changes."""
    jobs = get_store().get_all_jobs()
    if not jobs:
        return pd.DataFrame(columns=[
            "id", "company", "title", "location", "board",
            "date_found", "status", "priority", "notes", "url",
            "application_status", "application_url", "ats_provider",
            "last_apply_attempt_at", "blockers", "human_required_reason",
        ])
    rows = [j.to_dict() for j in jobs]
    df = pd.DataFrame(rows)
    df["date_found"] = pd.to_datetime(df["date_found"], utc=True, errors="coerce")
    if "last_apply_attempt_at" in df:
        df["last_apply_attempt_at"] = pd.to_datetime(df["last_apply_attempt_at"], utc=True, errors="coerce")
    return df


def _db_mtime() -> float:
    p = Path(DATABASE_PATH)
    return p.stat().st_mtime if p.exists() else 0.0


DISPLAY_COLS = [
    "company", "title", "location", "board", "date_found", "status", "priority",
    "application_status", "blockers", "human_required_reason", "notes", "url",
]

# ── Session state ──────────────────────────────────────────────────────────

if "ai_summary" not in st.session_state:
    st.session_state.ai_summary = ""
if "feed_chips" not in st.session_state:
    st.session_state.feed_chips = []   # list of {"key", "value", "label"}
if "feed_group" not in st.session_state:
    st.session_state.feed_group = False
if "feed_view" not in st.session_state:
    st.session_state.feed_view = "grid"   # "grid" | "list" | "immersive"
if "feed_sort" not in st.session_state:
    st.session_state.feed_sort = "priority"  # "priority" | "comp" | "company"

# ── Markdown parser helpers ────────────────────────────────────────────────

@st.cache_data(show_spinner=False)
def parse_md_stats(content: str) -> dict:
    """Extract quick stats from the markdown document."""
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
    mtime = MD_PATH.stat().st_mtime if MD_PATH.exists() else None
    stats["last_modified"] = datetime.fromtimestamp(mtime).strftime("%b %d, %Y %H:%M") if mtime else "Unknown"

    return stats


# ── Markdown job feed parser ───────────────────────────────────────────────

from typing import Optional

def _parse_job_entry(heading: str, body: str, section: str) -> Optional[dict]:
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


def _parse_exported_job_bullet(line: str, next_line: str, section: str) -> Optional[dict]:
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


@st.cache_data(show_spinner=False)
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
            job = _parse_exported_job_bullet(
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

        job = _parse_job_entry(heading_text, "\n".join(body_lines), current_section)
        if job:
            jobs.append(job)
        i = j

    return jobs


@st.cache_data(show_spinner=False)
def _feed_jobs_by_mtime(mtime: float) -> list[dict]:
    """Read and parse the markdown feed; result cached until mtime changes."""
    return parse_md_jobs(MD_PATH.read_text())


# ── Search & filter helpers ────────────────────────────────────────────────

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


_FILTER_KEYS = {"loc", "type", "priority", "skill", "company", "board", "src", "comp"}
_STOP_WORDS = {
    "engineer", "senior", "staff", "lead", "principal", "associate",
    "and", "of", "at", "for", "a", "an", "the", "in", "with", "applied",
}


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


@st.cache_data(show_spinner=False)
def load_keyword_data() -> dict:
    """
    Load keyword_report.json produced by extract_keywords.py.
    Returns {url: set_of_all_keywords_across_categories}.
    """
    kw_path = Path(__file__).parent.parent / "keyword_report.json"
    if not kw_path.exists():
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


def city_cover_config(location: str) -> dict:
    """Return the city cover config dict for a location string."""
    loc = location.lower()
    for key, cfg in _CITY_COVERS.items():
        if key in loc:
            return cfg
    return _DEFAULT_CITY_COVER


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


def _title_tokens(title: str) -> set[str]:
    return {
        w.lower() for w in re.split(r"[\s,/()\-@&]+", title)
        if w.lower() not in _STOP_WORDS and len(w) > 2
    }


def _jaccard(a: set, b: set) -> float:
    union = a | b
    return len(a & b) / len(union) if union else 0.0


def cluster_jobs(jobs: list[dict], kw_data: dict, threshold: float = 0.25) -> list[dict]:
    """
    Greedy single-linkage clustering by keyword Jaccard similarity.
    Falls back to title-token similarity when keyword data is absent.
    Returns [{"label": str, "keywords": list[str], "jobs": list[dict]}, ...].
    """
    if not jobs:
        return []

    features = [
        kw_data.get(j["url"]) or _title_tokens(j["title"])
        for j in jobs
    ]

    n = len(jobs)
    assigned = [-1] * n
    clusters = []

    for i in range(n):
        if assigned[i] != -1:
            continue
        cid = len(clusters)
        assigned[i] = cid
        members = [i]

        for j in range(i + 1, n):
            if assigned[j] != -1:
                continue
            if _jaccard(features[i], features[j]) >= threshold:
                assigned[j] = cid
                members.append(j)

        # Label: terms shared across every member; fall back to title tokens
        shared = set.intersection(*(features[m] for m in members))
        if not shared:
            title_sets = [_title_tokens(jobs[m]["title"]) for m in members]
            shared = set.intersection(*title_sets) if title_sets else set()

        label_terms = sorted(shared - _STOP_WORDS)[:4]
        label = " · ".join(t.title() for t in label_terms) or jobs[members[0]]["title"]

        clusters.append({
            "label": label,
            "jobs": [jobs[m] for m in members],
            "keywords": sorted(shared)[:8],
        })

    # Highest-priority cluster first
    clusters.sort(key=lambda c: -max((j["priority"] or 0) for j in c["jobs"]))
    return clusters


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


# ── Card renderer ──────────────────────────────────────────────────────────

_TYPE_BADGE: dict[str, tuple[str, str]] = {
    "top": ("background:#fff0d8;color:#b45309;border:1px solid rgba(217,119,6,0.32)", "Top Pick"),
    "ai":  ("background:#efe8ff;color:#6d28d9;border:1px solid rgba(124,58,237,0.22)", "AI"),
    "ios": ("background:#e7f0ff;color:#1d4ed8;border:1px solid rgba(37,99,235,0.18)", "iOS"),
    "new": ("background:#f3f4f6;color:#475569;border:1px solid rgba(71,85,105,0.16)", "New"),
}


def _priority_badge(priority: int) -> tuple[str, str]:
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


@st.cache_data(show_spinner=False)
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

    p_style, p_label = _priority_badge(priority)
    t_style, t_label = _TYPE_BADGE.get(job["type"], _TYPE_BADGE["ios"])
    logo_html = _logo_img_html(job["company"], job["url"], size=48)

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


@st.cache_data(show_spinner=False)
def card_html_list(
    company: str, title: str, url: str, comp: str,
    location: str, board: str, priority: int, job_type: str,
) -> str:
    """Compact single-row card for the list view."""
    logo = _logo_img_html(company, url, size=34)
    p_style, p_label = _priority_badge(priority)
    t_style, t_label = _TYPE_BADGE.get(job_type, _TYPE_BADGE["ios"])

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


@st.cache_data(show_spinner=False)
def card_html_immersive(
    company: str, title: str, url: str, comp: str,
    location: str, board: str, fit: str, concerns: str,
    priority: int, job_type: str,
) -> str:
    """Card with a city cover image at the top for the immersive view."""
    cover = city_cover_html(location)
    p_style, p_label = _priority_badge(priority)
    t_style, t_label = _TYPE_BADGE.get(job_type, _TYPE_BADGE["ios"])
    logo = _logo_img_html(company, url, size=44)

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


def _render_cards(jobs: list[dict], view: str) -> None:
    """Render job cards in the requested view mode (grid / list / immersive)."""
    if view == "list":
        for job in jobs:
            st.markdown(
                card_html_list(
                    job["company"], job["title"], job["url"], job.get("comp", ""),
                    job["location"], job["board"], job["priority"], job["type"],
                ),
                unsafe_allow_html=True,
            )
    elif view == "immersive":
        left_col, right_col = st.columns(2, gap="medium")
        for idx, job in enumerate(jobs):
            with (left_col if idx % 2 == 0 else right_col):
                st.markdown(
                    card_html_immersive(
                        job["company"], job["title"], job["url"], job.get("comp", ""),
                        job["location"], job["board"], job.get("fit", ""),
                        job.get("concerns", ""), job["priority"], job["type"],
                    ),
                    unsafe_allow_html=True,
                )
    else:  # grid (default)
        left_col, right_col = st.columns(2, gap="medium")
        for idx, job in enumerate(jobs):
            with (left_col if idx % 2 == 0 else right_col):
                st.markdown(
                    card_html(
                        job["company"], job["title"], job["url"], job.get("comp", ""),
                        job["location"], job["board"], job.get("fit", ""),
                        job.get("concerns", ""), job["priority"], job["type"],
                    ),
                    unsafe_allow_html=True,
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
        f'{_logo_img_html(company, job_url=job_url, size=42)}'
        '<div style="min-width:0">'
        f'<p class="mini-role__title">{company_html} — {title_html}</p>'
        f'<div class="mini-role__meta">{location_html}</div>'
        '</div>'
        f'<div class="mini-role__score">{html.escape(badge)}</div>'
        f'</div>{link_close}'
    )


# ── AI summary generator ───────────────────────────────────────────────────

SUMMARY_PROMPT = """\
You are analyzing a job search document for Basil Arif, an iOS + AI Software Engineer \
(3 years at Slack, shipped features to 30M+ DAU, iOS + SwiftUI + Swift expert, Slack AI \
service architecture, voice/audio side projects including PikaProjiOS).

The document contains: hand-curated job listings with fit analyses and priority ratings \
(1–10), a master priority table, GitHub project context, and a bulk "New Findings" section \
with freshly fetched roles that haven't been reviewed yet.

Generate a sharp, actionable job search briefing in markdown. Use this structure exactly:

## 🔥 Apply This Week
3–5 specific roles that warrant immediate action. For each: **Company — Role** with one \
sentence on why NOW and one concrete action (e.g., "draft cover letter leading with PikaProjiOS").

## 🎯 Strongest Fit Signals
Basil's 3–4 clearest competitive advantages that appear across multiple listings. \
Be specific — name the companies and skills.

## 📍 Location Strategy
Where to focus energy across SF / NYC / Toronto / Vancouver / Remote, given comp ranges \
and role availability in the document.

## ✨ Hidden Gems in New Findings
3–5 newly fetched roles (NEW-xx entries) that stand out and deserve a closer look. \
Give a one-line reason for each.

## ⚠️ Roles to Deprioritize
2–3 roles that look appealing on the surface but have real red flags for this profile. \
Be direct.

## 📋 This Week's Action Plan
Numbered list of 5 concrete next steps. Be specific (company names, what to write, what to check).

Keep it tight, honest, and specific to Basil. No generic job-search advice.\
"""


def stream_ai_summary(content: str):
    """Generator that streams the Claude response token by token."""
    try:
        import anthropic
    except ImportError:
        yield "❌ `anthropic` package not installed. Run: `pip install anthropic`"
        return

    api_key = _SETTINGS.anthropic_api_key
    if not api_key:
        yield "❌ `ANTHROPIC_API_KEY` environment variable not set."
        return

    client = anthropic.Anthropic(api_key=api_key)

    try:
        with client.messages.stream(
            model="claude-sonnet-4-6",
            max_tokens=2048,
            system=SUMMARY_PROMPT,
            messages=[{"role": "user", "content": content}],
        ) as stream:
            for text in stream.text_stream:
                yield text
    except Exception as e:
        yield f"\n\n❌ API error: {e}"


# ══════════════════════════════════════════════════════════════════════════════
# Layout
# ══════════════════════════════════════════════════════════════════════════════

db_path = Path(DATABASE_PATH)
db_last_updated = (
    datetime.fromtimestamp(db_path.stat().st_mtime).strftime("%b %d, %Y %H:%M")
    if db_path.exists()
    else "Not fetched yet"
)

st.markdown(
    hero_html(
        title="Job Search Command Center",
        copy="Triage fresh roles faster, keep your pipeline tidy, and scan the best matches without digging through raw tables first.",
        pills=[
            f"Database updated {db_last_updated}",
            "iOS + AI pipeline",
            "Editable job tracker",
        ],
    ),
    unsafe_allow_html=True,
)

tab_dashboard, tab_feed, tab_apply, tab_summary = st.tabs(["Dashboard", "Opportunity Feed", "Auto-Apply", "AI Summary"])

# ══════════════════════════════════════════════════════════════════════════════
# Tab 1 — Dashboard
# ══════════════════════════════════════════════════════════════════════════════

with tab_dashboard:

    df = load_jobs(_db_mtime())
    total = len(df)
    new_count        = int((df["status"] == "New").sum())        if total else 0
    applied_count    = int((df["status"] == "Applied").sum())    if total else 0
    review_count = int((df["application_status"] == "READY_FOR_REVIEW").sum()) if total and "application_status" in df else 0
    latest_found = (
        df["date_found"].dropna().max().tz_convert(None).strftime("%b %d, %Y")
        if total and df["date_found"].notna().any()
        else "No fetch yet"
    )

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(metric_card_html("Tracked roles", str(total), f"Latest role found {latest_found}"), unsafe_allow_html=True)
    with c2:
        st.markdown(metric_card_html("Needs triage", str(new_count), "Fresh entries still marked New"), unsafe_allow_html=True)
    with c3:
        st.markdown(metric_card_html("Applied", str(applied_count), "Roles already moved into action"), unsafe_allow_html=True)
    with c4:
        st.markdown(metric_card_html("Apply review", str(review_count), "Auto-filled roles waiting for human review"), unsafe_allow_html=True)

    left_lane, right_lane = st.columns([1.3, 1], gap="large")
    with left_lane:
        st.markdown(
            surface_header_html(
                "Actions",
                "Refresh the boards when you want new roles, then export the current tracker if you need a markdown snapshot for review or AI analysis.",
            ),
            unsafe_allow_html=True,
        )

        btn1, btn2, _ = st.columns([1, 1, 2.2])

        with btn1:
            if st.button("Fetch new jobs", type="primary", width="stretch"):
                with st.spinner("Fetching jobs from all boards…"):
                    result = subprocess.run(
                        [sys.executable, str(_HERE / "scripts" / "run_fetch.py")],
                        capture_output=True,
                        text=True,
                        cwd=str(_HERE),
                    )
                if result.returncode == 0:
                    st.success("Fetch complete. Table refreshed.")
                    if result.stdout:
                        with st.expander("Fetch output"):
                            st.code(result.stdout)
                elif result.returncode == 2:
                    st.warning("Fetch completed, but some boards failed — results are incomplete.")
                    with st.expander("Fetch output"):
                        st.code(result.stdout or result.stderr)
                else:
                    st.error("Fetch failed.")
                    with st.expander("Error output"):
                        st.code(result.stderr or result.stdout)

        with btn2:
            if st.button("Export to Markdown", width="stretch"):
                jobs = store.get_all_jobs()
                groups: dict = {}
                for j in jobs:
                    groups.setdefault(j.status or "Unknown", []).append(j)
                lines = ["# Job Search Results\n"]
                for status, group in sorted(groups.items()):
                    lines.append(f"\n## {status}\n")
                    for j in group:
                        date_str = j.date_found.strftime("%Y-%m-%d") if j.date_found else "?"
                        lines.append(f"- **[{j.company}]** {j.title} — {j.location} ({j.board}, {date_str})")
                        lines.append(f"  {j.url}")
                        if j.notes:
                            lines.append(f"  _Notes: {j.notes}_")
                        lines.append("")
                MD_PATH.write_text("\n".join(lines))
                st.success(f"Exported {len(jobs)} jobs to `{MD_PATH.name}`")

    with right_lane:
        st.markdown(
            surface_header_html(
                "Top opportunities",
                "This short list keeps the strongest roles visible before you get into table editing.",
            ),
            unsafe_allow_html=True,
        )
        if total:
            preview_df = df.copy()
            preview_df["priority_sort"] = preview_df["priority"].fillna(0)
            preview_df = preview_df.sort_values(["priority_sort", "date_found"], ascending=[False, False]).head(5)
            for row in preview_df.itertuples():
                st.markdown(
                    mini_role_html(
                        company=row.company,
                        title=row.title,
                        location=row.location,
                        score=row.priority,
                        job_url=row.url,
                    ),
                    unsafe_allow_html=True,
                )
        else:
            st.info("No roles yet. Run a fetch to populate the tracker.")

    st.markdown(
        surface_header_html(
            "Filter and edit",
            "Use broad filters first, then update status, priority, and notes directly in the tracker table below.",
        ),
        unsafe_allow_html=True,
    )
    f1, f2, f3, f4 = st.columns([1, 1, 1, 2])
    with f1:
        board_filter = st.selectbox("Board", ["All", "greenhouse", "lever", "ashby"])
    with f2:
        status_filter = st.selectbox("Status", ["All"] + JOB_STATUSES)
    with f3:
        company_search = st.text_input("Company", placeholder="filter…")
    with f4:
        location_search = st.text_input("Location", placeholder="filter…")

    filtered = df.copy()
    if total:
        if board_filter != "All":
            filtered = filtered[filtered["board"] == board_filter]
        if status_filter != "All":
            filtered = filtered[filtered["status"] == status_filter]
        if company_search:
            filtered = filtered[filtered["company"].str.contains(company_search, case=False, na=False)]
        if location_search:
            filtered = filtered[filtered["location"].str.contains(location_search, case=False, na=False)]

    st.caption(f"Showing {len(filtered)} of {total} jobs")

    if filtered.empty:
        st.info("No jobs match the current filters. Try fetching new jobs above.")
    else:
        display_df = filtered[DISPLAY_COLS].copy()
        display_df.insert(
            0,
            "logo",
            display_df.apply(lambda row: logo_url(row["company"], row["url"]), axis=1),
        )

        edited_df = st.data_editor(
            display_df,
            column_config={
                "logo":       st.column_config.ImageColumn(" ", width="small"),
                "company":    st.column_config.TextColumn("Company",  disabled=True),
                "title":      st.column_config.TextColumn("Title",    disabled=True),
                "location":   st.column_config.TextColumn("Location", disabled=True),
                "board":      st.column_config.TextColumn("Board",    disabled=True),
                "date_found": st.column_config.DatetimeColumn("Found", disabled=True, format="YYYY-MM-DD"),
                "status":     st.column_config.SelectboxColumn("Status",   options=JOB_STATUSES, required=True),
                "priority":   st.column_config.NumberColumn("Priority", min_value=1, max_value=5, step=1),
                "application_status": st.column_config.SelectboxColumn("Application", options=APPLICATION_STATUSES, disabled=True),
                "blockers":    st.column_config.TextColumn("Blockers", disabled=True),
                "human_required_reason": st.column_config.TextColumn("Human Gate", disabled=True),
                "notes":      st.column_config.TextColumn("Notes"),
                "url":        st.column_config.LinkColumn("URL", disabled=True),
            },
            hide_index=True,
            width="stretch",
            key="job_editor",
        )

        if st.button("Save Changes"):
            changed = 0
            for orig_row, edited_row in zip(display_df.itertuples(), edited_df.itertuples()):
                url = orig_row.url
                status_changed   = orig_row.status   != edited_row.status
                priority_changed = orig_row.priority != edited_row.priority
                notes_changed    = orig_row.notes    != edited_row.notes

                if status_changed:
                    store.update_job_status(url, edited_row.status)
                if priority_changed or notes_changed:
                    store.update_job_details(
                        url,
                        priority=edited_row.priority if priority_changed else None,
                        notes=edited_row.notes    if notes_changed    else None,
                    )
                if status_changed or priority_changed or notes_changed:
                    changed += 1

            if changed:
                st.success(f"Saved changes to {changed} job(s).")
                st.rerun()
            else:
                st.info("No changes detected.")


# ══════════════════════════════════════════════════════════════════════════════
# Tab 2 — Feed (Slack-style search)
# ══════════════════════════════════════════════════════════════════════════════

with tab_feed:

    if not MD_PATH.exists():
        st.info(f"`{MD_PATH.name}` not found. Run `job-search.py` first.")
    else:
        st.markdown(
            surface_header_html(
                "Opportunity feed",
                "Search, filter, and explore roles. Use the quick filters below, or type structured queries like loc:SF · type:ai · priority:8+ · comp:150k+ · skill:swift · company:anthropic",
            ),
            unsafe_allow_html=True,
        )
        all_feed_jobs: list[dict] = _feed_jobs_by_mtime(MD_PATH.stat().st_mtime)
        kw_data = load_keyword_data()

        # ── Search bar ────────────────────────────────────────────────────

        search_col, clear_col = st.columns([8, 1])
        with search_col:
            raw_query = st.text_input(
                "",
                placeholder="🔍  loc:SF  type:ai  priority:8+  comp:150k+  skill:swift  company:anthropic  src:new …",
                key="feed_search_bar",
                label_visibility="collapsed",
            )
        with clear_col:
            if st.button("Clear", use_container_width=True):
                st.session_state.feed_chips = []
                st.rerun()

        # Parse key:value tokens from search bar into chips
        free_text, bar_chips = parse_query_chips(raw_query)
        for chip in bar_chips:
            if not any(c["label"] == chip["label"] for c in st.session_state.feed_chips):
                st.session_state.feed_chips.append(chip)

        # ── Quick-filter groups ───────────────────────────────────────────

        _QUICK_FILTER_GROUPS: list[tuple[str, list]] = [
            ("Type", [
                ("AI",       {"key": "type",     "value": "ai",           "label": "type:ai"}),
                ("iOS",      {"key": "type",     "value": "ios",          "label": "type:ios"}),
                ("Top Pick", {"key": "type",     "value": "top",          "label": "type:top"}),
                ("New",      {"key": "src",      "value": "new",          "label": "src:new"}),
                ("Curated",  {"key": "src",      "value": "curated",      "label": "src:curated"}),
            ]),
            ("Location", [
                ("SF",        {"key": "loc", "value": "san francisco", "label": "loc:san francisco"}),
                ("NYC",       {"key": "loc", "value": "new york",      "label": "loc:new york"}),
                ("Remote",    {"key": "loc", "value": "remote",        "label": "loc:remote"}),
                ("Toronto",   {"key": "loc", "value": "toronto",       "label": "loc:toronto"}),
                ("Vancouver", {"key": "loc", "value": "vancouver",     "label": "loc:vancouver"}),
                ("Seattle",   {"key": "loc", "value": "seattle",       "label": "loc:seattle"}),
            ]),
            ("Priority", [
                ("7+", {"key": "priority", "value": "7+", "label": "priority:7+"}),
                ("8+", {"key": "priority", "value": "8+", "label": "priority:8+"}),
                ("9+", {"key": "priority", "value": "9+", "label": "priority:9+"}),
            ]),
            ("Comp", [
                ("100k+", {"key": "comp", "value": "100k+", "label": "comp:100k+"}),
                ("150k+", {"key": "comp", "value": "150k+", "label": "comp:150k+"}),
                ("200k+", {"key": "comp", "value": "200k+", "label": "comp:200k+"}),
            ]),
        ]

        for group_name, filters in _QUICK_FILTER_GROUPS:
            st.markdown(f'<p class="filter-group-label">{group_name}</p>', unsafe_allow_html=True)
            cols = st.columns(len(filters))
            for col, (btn_label, chip) in zip(cols, filters):
                with col:
                    active = any(c["label"] == chip["label"] for c in st.session_state.feed_chips)
                    if st.button(
                        btn_label,
                        key=f"qf_{group_name}_{btn_label}",
                        type="primary" if active else "secondary",
                        use_container_width=True,
                    ):
                        if active:
                            st.session_state.feed_chips = [
                                c for c in st.session_state.feed_chips
                                if c["label"] != chip["label"]
                            ]
                        else:
                            st.session_state.feed_chips.append(chip)
                        st.rerun()

        # ── Active chip pills (click to remove) ───────────────────────────

        if st.session_state.feed_chips:
            current_labels = [c["label"] for c in st.session_state.feed_chips]
            remaining = st.multiselect(
                "Active filters",
                options=current_labels,
                default=current_labels,
                label_visibility="collapsed",
                key="active_chips_select",
            )
            removed = set(current_labels) - set(remaining)
            if removed:
                st.session_state.feed_chips = [
                    c for c in st.session_state.feed_chips if c["label"] not in removed
                ]
                st.rerun()

        # ── Apply filters ─────────────────────────────────────────────────

        feed = apply_filters(all_feed_jobs, free_text, st.session_state.feed_chips, kw_data)

        # ── Sort ──────────────────────────────────────────────────────────

        sort_mode = st.session_state.feed_sort

        def _sort_fn(j: dict) -> tuple:
            if sort_mode == "comp":
                return (-(parse_comp_value(j.get("comp", "")) or 0),)
            if sort_mode == "company":
                return (j.get("company", "").lower(),)
            # priority (default) — top picks first, then by numeric priority
            type_order = {"top": 0, "ai": 1, "ios": 1, "new": 2}
            return (type_order.get(j["type"], 1), -(j["priority"] or 0))

        feed = sorted(feed, key=_sort_fn)

        # ── Cluster (group mode) ──────────────────────────────────────────

        view       = st.session_state.feed_view
        group_mode = st.session_state.feed_group
        clusters   = cluster_jobs(feed, kw_data) if group_mode else None

        # ── Controls row ──────────────────────────────────────────────────

        ctrl_left, ctrl_mid, ctrl_right = st.columns([4, 2, 3])

        with ctrl_right:
            v1, v2, v3 = st.columns(3)
            with v1:
                if st.button("⊞ Grid",   key="view_grid",      type="primary" if view == "grid"      else "secondary", use_container_width=True):
                    st.session_state.feed_view = "grid";      st.rerun()
            with v2:
                if st.button("≡ List",   key="view_list",      type="primary" if view == "list"      else "secondary", use_container_width=True):
                    st.session_state.feed_view = "list";      st.rerun()
            with v3:
                if st.button("🌆 Cities", key="view_immersive", type="primary" if view == "immersive" else "secondary", use_container_width=True):
                    st.session_state.feed_view = "immersive"; st.rerun()

        with ctrl_mid:
            _sort_options  = ["Priority", "Comp ↓", "Company A–Z"]
            _sort_keys     = ["priority", "comp", "company"]
            _sort_idx      = _sort_keys.index(sort_mode) if sort_mode in _sort_keys else 0
            _sort_selected = st.selectbox(
                "Sort",
                options=_sort_options,
                index=_sort_idx,
                label_visibility="collapsed",
                key="sort_select",
            )
            _new_sort = _sort_keys[_sort_options.index(_sort_selected)]
            if _new_sort != sort_mode:
                st.session_state.feed_sort = _new_sort
                st.rerun()

        has_kw     = bool(kw_data)
        kw_note    = "" if has_kw else "  ·  _run `extract_keywords.py` to enable `skill:` & smarter grouping_"
        group_note = f" in **{len(clusters)}** groups" if clusters is not None else ""

        with ctrl_left:
            st.caption(
                f"**{len(feed)}** of {len(all_feed_jobs)} roles{group_note}"
                f"  ·  {datetime.fromtimestamp(MD_PATH.stat().st_mtime).strftime('%b %d, %Y')}"
                + kw_note
            )
            group_mode = st.toggle(
                "Group similar roles",
                value=st.session_state.feed_group,
                key="feed_group_toggle",
            )
            if group_mode != st.session_state.feed_group:
                st.session_state.feed_group = group_mode
                st.rerun()

        st.divider()

        # ── Results ───────────────────────────────────────────────────────

        if not feed:
            st.info("No roles match the current filters — try removing one.")

        elif group_mode and clusters:
            for cluster in clusters:
                n        = len(cluster["jobs"])
                kw_pills = "  ".join(f"`{k}`" for k in cluster["keywords"][:6])
                header   = f"**{cluster['label']}** — {n} role{'s' if n != 1 else ''}"
                with st.expander(header, expanded=(n <= 4)):
                    if kw_pills:
                        st.caption(kw_pills)
                    _render_cards(cluster["jobs"], view)

        else:
            _render_cards(feed, view)


# ══════════════════════════════════════════════════════════════════════════════
# Tab 3 — Auto-Apply
# ══════════════════════════════════════════════════════════════════════════════

with tab_apply:
    df = load_jobs(_db_mtime())
    readiness = profile_readiness()

    st.markdown(
        surface_header_html(
            "Safe auto-apply",
            "Build a queue from tracked jobs, open the application forms, fill only known safe fields, upload a resume when available, and stop before final submit.",
        ),
        unsafe_allow_html=True,
    )

    r1, r2, r3, r4 = st.columns(4)
    with r1:
        st.markdown(metric_card_html("Profile", "Ready" if readiness["ready_for_fill"] else "Missing", "Required autofill fields"), unsafe_allow_html=True)
    with r2:
        st.markdown(metric_card_html("Resume PDF", "Found" if readiness["resume_pdf_exists"] else "Missing", "Needed for upload fields"), unsafe_allow_html=True)
    with r3:
        blocked_count = int((df["application_status"] == "BLOCKED").sum()) if not df.empty and "application_status" in df else 0
        st.markdown(metric_card_html("Blocked", str(blocked_count), "Captcha, OTP, account gates, or errors"), unsafe_allow_html=True)
    with r4:
        submitted_count = int((df["application_status"] == "SUBMITTED").sum()) if not df.empty and "application_status" in df else 0
        st.markdown(metric_card_html("Submitted", str(submitted_count), "Manually confirmed submissions"), unsafe_allow_html=True)

    if readiness["missing_profile_fields"]:
        st.warning("Missing profile fields: " + ", ".join(readiness["missing_profile_fields"]))
    if not readiness["resume_pdf_exists"]:
        st.info(f"Add `resume_master.pdf` under `{readiness['apply_dir']}` before expecting resume upload to work.")

    st.markdown(
        surface_header_html(
            "Queue builder",
            "Use small batches. Dry run first, then open and fill only when the queue looks right.",
        ),
        unsafe_allow_html=True,
    )

    q1, q2, q3, q4 = st.columns([1, 1, 1, 1])
    with q1:
        apply_status_filter = st.selectbox("Tracker status", ["Any", "New", "Saved", "Interested", "Applied"], index=0)
    with q2:
        apply_min_priority = st.selectbox("Min priority", ["Any", "1", "2", "3", "4", "5"], index=0)
    with q3:
        apply_limit = st.number_input("Batch limit", min_value=1, max_value=20, value=3, step=1)
    with q4:
        specific_job_id = st.number_input("Job ID", min_value=0, value=0, step=1, help="0 means use queue filters.")

    cli_args = [
        sys.executable,
        str(_HERE / "scripts" / "run_auto_apply.py"),
        "--limit",
        str(int(apply_limit)),
    ]
    if apply_status_filter != "Any":
        cli_args.extend(["--status", apply_status_filter])
    if apply_min_priority != "Any":
        cli_args.extend(["--min-priority", apply_min_priority])
    if specific_job_id:
        cli_args.extend(["--job-id", str(int(specific_job_id))])

    b1, b2, _ = st.columns([1, 1, 2])
    with b1:
        if st.button("Preview Queue", type="primary", width="stretch"):
            result = subprocess.run(cli_args + ["--dry-run"], capture_output=True, text=True, cwd=str(_HERE))
            if result.returncode == 0:
                try:
                    queue_data = json.loads(result.stdout or "{}").get("queue", [])
                except json.JSONDecodeError:
                    queue_data = []
                if queue_data:
                    st.dataframe(pd.DataFrame(queue_data), width="stretch", hide_index=True)
                else:
                    st.info("No jobs matched the queue filters.")
            else:
                st.error("Queue preview failed.")
                st.code(result.stderr or result.stdout)

    with b2:
        fill_disabled = bool(readiness["missing_profile_fields"])
        if st.button("Open & Fill", disabled=fill_disabled, width="stretch"):
            with st.spinner("Opening browser and filling safe fields. No final submit will be clicked."):
                result = subprocess.run(cli_args, capture_output=True, text=True, cwd=str(_HERE))
            if result.returncode == 0:
                try:
                    result_data = json.loads(result.stdout or "{}").get("results", [])
                except json.JSONDecodeError:
                    result_data = []
                if result_data:
                    st.success(f"Processed {len(result_data)} job(s).")
                    st.dataframe(pd.DataFrame(result_data), width="stretch", hide_index=True)
                else:
                    st.info("No jobs were processed.")
            else:
                st.error("Auto-apply run failed.")
                st.code(result.stderr or result.stdout)

    st.markdown(
        surface_header_html(
            "Application tracker",
            "Current application-state view from SQLite. Final submissions should be marked manually after review.",
        ),
        unsafe_allow_html=True,
    )
    if df.empty:
        st.info("No jobs in the tracker yet.")
    else:
        app_cols = [
            "id", "company", "title", "status", "priority", "application_status",
            "ats_provider", "application_url", "blockers", "human_required_reason",
            "last_apply_attempt_at",
        ]
        available_cols = [col for col in app_cols if col in df.columns]
        app_df = df[available_cols].copy()
        st.dataframe(app_df, width="stretch", hide_index=True)

        st.markdown("**Manual confirmation**")
        m1, m2, _ = st.columns([1, 1, 2])
        with m1:
            submitted_job_id = st.number_input("Submitted job ID", min_value=0, value=0, step=1)
        with m2:
            if st.button("Mark Submitted", disabled=not submitted_job_id, width="stretch"):
                match = df[df["id"] == int(submitted_job_id)]
                if match.empty:
                    st.error("No job found with that ID.")
                else:
                    submitted_url = match.iloc[0]["url"]
                    store.update_application_state(
                        submitted_url,
                        application_status="SUBMITTED",
                        human_required_reason="",
                        apply_notes="Marked submitted after human confirmation.",
                        touch_attempt=False,
                    )
                    store.update_job_status(submitted_url, "Applied")
                    st.success("Marked application as submitted and tracker status as Applied.")
                    st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# Tab 4 — AI Summary
# ══════════════════════════════════════════════════════════════════════════════

with tab_summary:

    if not MD_PATH.exists():
        st.warning(
            f"`{MD_PATH.name}` not found at `{MD_PATH}`.\n\n"
            "Run **Export to Markdown** from the Dashboard tab, or run the original "
            "`job-search.py` script first."
        )
        st.stop()

    md_content = MD_PATH.read_text()
    stats = parse_md_stats(md_content)  # cached by content hash

    # ── Header strip ──────────────────────────────────────────────────────

    st.markdown(
        surface_header_html(
            "Job search intelligence",
            f"Source: {MD_PATH.name} · last modified {stats['last_modified']}. Generate a briefing when you want synthesis rather than raw listings.",
        ),
        unsafe_allow_html=True,
    )

    # ── Quick stats ───────────────────────────────────────────────────────

    s1, s2, s3, s4, s5 = st.columns(5)
    s1.metric("Total Roles", stats["total"])
    s2.metric("Curated", stats["curated"], help="Hand-reviewed with fit analysis")
    s3.metric("New Fetched", stats["new_fetched"], help="Awaiting review")
    s4.metric("Priority 9–10", stats["top_priority"])
    s5.metric("Locations", len(stats.get("by_location", {})))

    # ── Location bar chart ────────────────────────────────────────────────

    if "by_location" in stats:
        st.divider()
        loc_df = pd.DataFrame(
            list(stats["by_location"].items()),
            columns=["Location", "Roles"],
        ).sort_values("Roles", ascending=False)

        st.caption("Roles by city (from summary table in document)")
        st.bar_chart(loc_df.set_index("Location"), horizontal=True, height=200)

    st.divider()

    # ── Generate button ───────────────────────────────────────────────────

    has_key = bool(_SETTINGS.anthropic_api_key)

    col_btn, col_note = st.columns([1, 4])
    with col_btn:
        generate = st.button(
            "Generate AI Summary",
            type="primary",
            disabled=not has_key,
        )
    with col_note:
        if not has_key:
            st.warning(
                "Set `ANTHROPIC_API_KEY` in your environment to enable AI summaries.\n"
                "```\nexport ANTHROPIC_API_KEY=sk-ant-...\n```"
            )
        elif st.session_state.ai_summary:
            st.caption("Summary cached — click to regenerate with latest document.")

    # ── Stream or display summary ─────────────────────────────────────────

    if generate:
        st.session_state.ai_summary = ""
        summary_placeholder = st.empty()
        with st.spinner("Analyzing your job search…"):
            collected = ""
            for chunk in stream_ai_summary(md_content):
                collected += chunk
                summary_placeholder.markdown(collected + "▌")
            st.session_state.ai_summary = collected
            summary_placeholder.markdown(collected)

    elif st.session_state.ai_summary:
        st.markdown(st.session_state.ai_summary)

    else:
        # Placeholder state — no summary yet
        st.markdown(
            '<div class="summary-empty">'
            '<p style="font-size:1.35rem;margin:0 0 0.45rem 0;">Focused briefing, on demand</p>'
            '<p style="font-size:0.96rem;margin:0;">Generate an AI summary when you want the roles, signals, and next moves condensed into one plan.</p>'
            '</div>',
            unsafe_allow_html=True,
        )

    # ── Raw document viewer ───────────────────────────────────────────────

    st.divider()
    with st.expander("View raw job-search-results.md"):
        # Show with line numbers in a scrollable code block
        st.markdown(md_content)
