#!/usr/bin/env python3
"""
Job Search Command Center — Streamlit dashboard
Run from the job-search-command-center/ directory:
    streamlit run app.py
"""

from __future__ import annotations

import logging
import json
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st

logger = logging.getLogger(__name__)

# Ensure imports resolve correctly regardless of CWD
_HERE = Path(__file__).parent
sys.path.insert(0, str(_HERE))
sys.path.insert(0, str(_HERE.parent))  # for careerBoards

from config import APPLICATION_STATUSES, JOB_STATUSES
from jobsearch.apply.profile import profile_readiness
from jobsearch.services import pipeline_service
from jobsearch.services.logo_service import logo_sources as _logo_sources
from jobsearch.services.logo_service import logo_url as _logo_url
from jobsearch.settings import get_settings
from jobsearch.store import JobStore
from jobsearch.ui.components import card_html as _card_html
from jobsearch.ui.components import card_html_immersive as _card_html_immersive
from jobsearch.ui.components import card_html_list as _card_html_list
from jobsearch.ui.components import hero_html, metric_card_html, mini_role_html, surface_header_html

_SETTINGS = get_settings()
DATABASE_PATH = _SETTINGS.database_path
MARKDOWN_EXPORT_PATH = _SETTINGS.markdown_export_path

# Company→domain→logo resolution lives in jobsearch.services.logo_service.

# City covers, badges, and HTML render helpers live in jobsearch.ui.components.

# Cached UI wrappers over the pure resolver in jobsearch.services.logo_service.
logo_sources = st.cache_data(show_spinner=False)(_logo_sources)
logo_url = st.cache_data(show_spinner=False)(_logo_url)

# Cached UI wrappers over the pure card builders in jobsearch.ui.components.
card_html = st.cache_data(show_spinner=False)(_card_html)
card_html_list = st.cache_data(show_spinner=False)(_card_html_list)
card_html_immersive = st.cache_data(show_spinner=False)(_card_html_immersive)

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
JOBS_PAGE_SIZE = 50

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
if "dashboard_page" not in st.session_state:
    st.session_state.dashboard_page = 1
if "keyword_extract_signature" not in st.session_state:
    st.session_state.keyword_extract_signature = ""

# ── Markdown parser helpers ────────────────────────────────────────────────

from typing import Optional

from jobsearch.parsing.markdown import parse_md_jobs as _parse_md_jobs
from jobsearch.parsing.markdown import parse_md_stats as _parse_md_stats
from jobsearch.parsing.query import parse_comp_value, parse_query_chips
from jobsearch.ranking.clustering import cluster_jobs
from jobsearch.ranking.filters import apply_filters
from jobsearch.ranking.keywords import load_keyword_data as _load_keyword_data


@st.cache_data(show_spinner=False)
def parse_md_stats(content: str) -> dict:
    """Cached UI wrapper over the pure stats parser (passes MD_PATH for mtime)."""
    return _parse_md_stats(content, md_path=MD_PATH)


# Cached UI wrapper — the pure parser lives in jobsearch.parsing.markdown.
parse_md_jobs = st.cache_data(show_spinner=False)(_parse_md_jobs)


@st.cache_data(show_spinner=False)
def _feed_jobs_by_mtime(mtime: float) -> list[dict]:
    """Read and parse the markdown feed; result cached until mtime changes."""
    return parse_md_jobs(MD_PATH.read_text())


@st.cache_data(show_spinner=False)
def load_keyword_data() -> dict:
    """Cached UI wrapper over the pure keyword loader."""
    return _load_keyword_data(Path(__file__).parent / "keyword_report.json")


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


# Non-cached render helpers come straight from the components module.


# ── AI summary generator ───────────────────────────────────────────────────
# The UI-agnostic generator lives in jobsearch.services.summary_service.
from jobsearch.services.summary_service import build_briefing_document, provider_label, stream_ai_summary, summary_available

# Both probe the Ollama socket, and Streamlit re-runs this on every widget
# interaction — cache briefly so a stopped server doesn't cost 1.5s a click.
summary_available_cached = st.cache_data(ttl=30, show_spinner=False)(summary_available)
provider_label_cached = st.cache_data(ttl=30, show_spinner=False)(provider_label)


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
                    result = pipeline_service.run_fetch()
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
                from jobsearch.markdown_export import MarkdownExporter

                count, path = MarkdownExporter(store).export(path=str(MD_PATH))
                st.success(f"Exported {count} jobs to `{path.name}`")

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

    page_count = max(1, (len(filtered) + JOBS_PAGE_SIZE - 1) // JOBS_PAGE_SIZE)
    if st.session_state.dashboard_page > page_count:
        st.session_state.dashboard_page = page_count
    if st.session_state.dashboard_page < 1:
        st.session_state.dashboard_page = 1

    page_offset = (st.session_state.dashboard_page - 1) * JOBS_PAGE_SIZE
    page_df = filtered.iloc[page_offset : page_offset + JOBS_PAGE_SIZE].copy()
    page_start = page_offset + 1 if len(filtered) else 0
    page_end = min(page_offset + JOBS_PAGE_SIZE, len(filtered))

    p1, p2, p3, p4, p5 = st.columns([1, 1, 1.2, 2.3, 2.2])
    with p1:
        if st.button("Prev", disabled=st.session_state.dashboard_page <= 1, width="stretch"):
            st.session_state.dashboard_page -= 1
            st.rerun()
    with p2:
        if st.button("Next", disabled=st.session_state.dashboard_page >= page_count, width="stretch"):
            st.session_state.dashboard_page += 1
            st.rerun()
    with p3:
        selected_page = st.number_input(
            "Page",
            min_value=1,
            max_value=page_count,
            value=st.session_state.dashboard_page,
            step=1,
        )
        if int(selected_page) != st.session_state.dashboard_page:
            st.session_state.dashboard_page = int(selected_page)
            st.rerun()
    with p4:
        st.caption(
            f"Showing {page_start}-{page_end} of {len(filtered)} filtered jobs "
            f"({total} total) · offset {page_offset} · limit {JOBS_PAGE_SIZE}"
        )
    with p5:
        page_urls = page_df["url"].dropna().astype(str).tolist() if not page_df.empty else []
        extract_enabled = st.toggle(
            "Extract keywords for visible page",
            disabled=not page_urls,
            key="extract_keywords_visible_page",
        )

    if not extract_enabled:
        st.session_state.keyword_extract_signature = ""
    elif page_urls:
        extract_signature = f"{page_offset}:{JOBS_PAGE_SIZE}:" + "|".join(page_urls)
        if extract_signature != st.session_state.keyword_extract_signature:
            with st.spinner("Extracting keywords for the visible 50-job page..."):
                result = pipeline_service.run_extract_keywords(
                    limit=JOBS_PAGE_SIZE,
                    offset=page_offset,
                    urls=page_urls,
                )
            st.session_state.keyword_extract_signature = extract_signature
            load_keyword_data.clear()
            if result.returncode == 0:
                st.success("Keyword extraction complete for the visible page.")
                if result.stdout:
                    with st.expander("Keyword extraction output"):
                        st.code(result.stdout)
            else:
                st.error("Keyword extraction failed.")
                with st.expander("Keyword extraction error"):
                    st.code(result.stderr or result.stdout)

    if filtered.empty:
        st.info("No jobs match the current filters. Try fetching new jobs above.")
    else:
        display_df = page_df[DISPLAY_COLS].copy()
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
                "Feed search",
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

    apply_kwargs = dict(
        limit=int(apply_limit),
        status=None if apply_status_filter == "Any" else apply_status_filter,
        min_priority=None if apply_min_priority == "Any" else apply_min_priority,
        job_id=int(specific_job_id) or None,
    )

    b1, b2, _ = st.columns([1, 1, 2])
    with b1:
        if st.button("Preview Queue", type="primary", width="stretch"):
            result = pipeline_service.run_auto_apply(**apply_kwargs, dry_run=True)
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
                result = pipeline_service.run_auto_apply(**apply_kwargs)
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

        st.caption("Roles by city (from the source document)")
        st.bar_chart(loc_df.set_index("Location"), horizontal=True, height=200)

    st.divider()

    # ── Generate button ───────────────────────────────────────────────────

    # Anthropic API or a local Ollama server — whichever the settings resolve to.
    has_backend = summary_available_cached()

    col_btn, col_note = st.columns([1, 4])
    with col_btn:
        generate = st.button(
            "Generate AI Summary",
            type="primary",
            disabled=not has_backend,
        )
    with col_note:
        if not has_backend:
            st.warning(
                "No summary backend available. Either set `ANTHROPIC_API_KEY`:\n"
                "```\nexport ANTHROPIC_API_KEY=sk-ant-...\n```\n"
                f"or start a local Ollama server at `{_SETTINGS.ollama_base_url}` "
                f"with `ollama pull {_SETTINGS.ollama_model}`."
            )
        elif st.session_state.ai_summary:
            st.caption(f"{provider_label_cached()} · summary cached — click to regenerate with latest document.")
        else:
            st.caption(f"{provider_label_cached()}")

    # ── Stream or display summary ─────────────────────────────────────────

    if generate:
        st.session_state.ai_summary = ""
        summary_placeholder = st.empty()
        # The full export outgrew the local model's context window, so the
        # briefing runs on the freshest un-triaged roles as a compact digest.
        briefing_doc, included, untriaged_total = build_briefing_document(
            load_jobs(_db_mtime()).to_dict("records")
        )
        with st.spinner(f"Analyzing {included} of {untriaged_total} un-triaged roles…"):
            collected = ""
            for chunk in stream_ai_summary(briefing_doc):
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
