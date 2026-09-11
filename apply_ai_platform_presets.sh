#!/usr/bin/env bash
# Apply AI Platform search presets + fit scoring to job-search-command-center
# Run from the repo root on your Mac.
set -euo pipefail

if [[ ! -f config.py ]] || [[ ! -d jobsearch ]]; then
  echo "ERROR: run this from the job-search-command-center repo root" >&2
  exit 1
fi

# This one-time installer predates profile configuration and the Ollama backend.
# Do not overwrite the integrated implementation if it is already installed.
if [[ -f jobsearch/ranking/fit.py ]]; then
  echo "AI presets are already installed. Configure them in Feed > Search preferences."
  exit 0
fi

git checkout main
git pull --ff-only || true
git checkout -B feature/ai-platform-search-presets

echo "Writing files..."

mkdir -p "$(dirname 'config.py')"
cat > 'config.py' << 'EOF_CONFIG_PY'
# Configuration for the Job Search Command Center
import sys
from pathlib import Path

# ── Paths ──────────────────────────────────────────────────────────────────

_HERE = Path(__file__).parent

# Pull company lists from careerBoards.py (project-local copy)
sys.path.insert(0, str(_HERE))
try:
    from careerBoards import GREENHOUSE, LEVER, ASHBY
except ImportError:
    GREENHOUSE: dict = {}
    LEVER: dict = {}
    ASHBY: dict = {}

# Paths, credentials, and feature toggles live in jobsearch.settings
# (env + .env). This module holds only static domain configuration.

# ── HTTP ───────────────────────────────────────────────────────────────────

REQUEST_TIMEOUT = 10
USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"

# ── Role keywords (case-insensitive substring match on job title) ───────────
# Expanded for AI Platform / MLOps / RAG / Agentic / Applied AI search (2026).

ROLE_KEYWORDS = [
    # iOS / mobile (existing)
    "ios engineer",
    "ios developer",
    "ios software engineer",
    "mobile engineer",
    "mobile developer",
    "software engineer, ios",
    "software engineer ios",
    "swift engineer",
    # Applied / product AI
    "ai engineer",
    "applied ai",
    "ai product engineer",
    "ml engineer",
    "machine learning engineer",
    "product engineer",
    "product growth engineer",
    "forward deployed engineer",
    # AI platform / infrastructure (highest ROI for current work)
    "ai platform engineer",
    "llm platform",
    "ai infrastructure",
    "ml infrastructure",
    "ml infra",
    "mlops",
    "ml ops",
    "ai systems engineer",
    "llm ops",
    "inference engineer",
    "model serving",
    # Retrieval / knowledge
    "rag engineer",
    "retrieval engineer",
    "knowledge retrieval",
    "search engineer",
    "vector search",
    # Agents / orchestration
    "agentic",
    "agent orchestration",
    "ai agent",
    "agent engineer",
    "tool use",
    # Speech / multimodal (CaptionLocalizer overlap)
    "speech engineer",
    "speech ai",
    "multimodal",
    "asr",
    "tts",
]

# ── Named search presets (UI / scripting convenience) ───────────────────────
# Use these as free-text or chip seeds when filtering for AI-platform roles.

SEARCH_PRESETS = {
    "ai_platform": {
        "label": "AI Platform / MLOps",
        "title_keywords": [
            "ai platform",
            "llm platform",
            "ai infrastructure",
            "ml infrastructure",
            "mlops",
            "ml ops",
            "ai systems",
            "inference",
            "model serving",
        ],
        "description": "Private/edge inference, GPU orchestration, model gateways, serving reliability",
    },
    "rag_retrieval": {
        "label": "RAG / Retrieval",
        "title_keywords": [
            "rag",
            "retrieval",
            "knowledge",
            "vector search",
            "search engineer",
            "embeddings",
        ],
        "description": "Vector + hybrid search, evaluation harnesses, embedding pipelines",
    },
    "agentic": {
        "label": "Agentic / Agent Orchestration",
        "title_keywords": [
            "agentic",
            "agent orchestration",
            "ai agent",
            "agent engineer",
            "tool use",
            "multi-agent",
        ],
        "description": "Tool-calling agents, MCP-style surfaces, workflow orchestration",
    },
    "applied_ai": {
        "label": "Applied AI / Generative",
        "title_keywords": [
            "applied ai",
            "generative ai",
            "llm engineer",
            "ai engineer",
            "genai",
        ],
        "description": "Shipping LLM features, localization, speech, product-facing AI",
    },
    "speech_multimodal": {
        "label": "Speech / Multimodal",
        "title_keywords": [
            "speech",
            "asr",
            "tts",
            "multimodal",
            "voice ai",
            "audio ai",
        ],
        "description": "STT/TTS, timed captions, lyric/localization pipelines",
    },
}

# ── Location keywords — only keep postings that mention at least one ────────

LOCATION_KEYWORDS = [
    "san francisco",
    "new york",
    "nyc",
    "seattle",
    "toronto",
    "vancouver",
    "remote",
    "canada",
    "california",
    "ontario",
    "british columbia",
    "palo alto",
    "bellevue",
    "montreal",
]

# ── Board configuration ────────────────────────────────────────────────────
# Each board entry is passed as `config` to its fetcher's fetch() method.

DEFAULT_BOARD_CONFIG = {
    "greenhouse": {
        "api_base": "https://boards-api.greenhouse.io/v1/boards",
        "companies": GREENHOUSE,
    },
    "lever": {
        "api_base": "https://api.lever.co/v0/postings",
        "companies": LEVER,
    },
    "ashby": {
        "api_base": "https://jobs.ashbyhq.com",
        "companies": ASHBY,
    },
}

# ── Job tracking metadata ──────────────────────────────────────────────────

JOB_STATUSES = [
    "New",
    "Saved",
    "Interested",
    "Applied",
    "Interviewing",
    "Offer",
    "Rejected",
    "Archived",
]

JOB_PRIORITIES = [1, 2, 3, 4, 5]

# ── Auto-apply metadata ───────────────────────────────────────────────────

APPLICATION_STATUSES = [
    "NOT_STARTED",
    "QUEUED",
    "OPENED",
    "FILLED_PARTIALLY",
    "READY_FOR_REVIEW",
    "READY_TO_SUBMIT",
    "SUBMITTED",
    "BLOCKED",
    "SKIPPED",
]

EOF_CONFIG_PY

mkdir -p "$(dirname 'jobsearch/config.py')"
cat > 'jobsearch/config.py' << 'EOF_JOBSEARCH_CONFIG_PY'
# Re-export static config values from the root config module for
# package-level access. Runtime settings (paths, credentials, toggles)
# live in jobsearch.settings.
from config import (
    LOCATION_KEYWORDS,
    ROLE_KEYWORDS,
    SEARCH_PRESETS,
    REQUEST_TIMEOUT,
    DEFAULT_BOARD_CONFIG,
    JOB_STATUSES,
    JOB_PRIORITIES,
    APPLICATION_STATUSES,
    USER_AGENT,
)

# Alias for backwards compatibility
DEFAULT_LOCATIONS = LOCATION_KEYWORDS

EOF_JOBSEARCH_CONFIG_PY

mkdir -p "$(dirname 'jobsearch/ranking/fit.py')"
cat > 'jobsearch/ranking/fit.py' << 'EOF_JOBSEARCH_RANKING_FIT_PY'
"""Lightweight fit scoring against a candidate profile and search presets.

Pure functions over job dicts + optional profile JSON. Designed so the UI or
scripts can rank roles that match the AI Platform / RAG / Agentic skill set
without calling an external LLM.
"""
from __future__ import annotations

from typing import Any, Optional

from config import SEARCH_PRESETS

# Signals that map well to the current portfolio (cluster, HistoryKit, CaptionLocalizer, music).
DEFAULT_PROFILE_SIGNALS = [
    "ai platform",
    "llm",
    "mlops",
    "infrastructure",
    "rag",
    "retrieval",
    "vector",
    "embedding",
    "agent",
    "agentic",
    "orchestration",
    "tool",
    "inference",
    "ollama",
    "whisper",
    "speech",
    "transcription",
    "localization",
    "fastapi",
    "kubernetes",
    "distributed",
    "gpu",
    "edge",
    "on-prem",
    "on device",
    "private ai",
]


def _blob(job: dict) -> str:
    parts = [
        str(job.get("title") or ""),
        str(job.get("company") or ""),
        str(job.get("location") or ""),
        str(job.get("comp") or ""),
        str(job.get("description") or ""),
        str(job.get("url") or ""),
    ]
    return " ".join(parts).lower()


def score_job_fit(
    job: dict,
    profile_signals: Optional[list[str]] = None,
    preset_keys: Optional[list[str]] = None,
) -> dict[str, Any]:
    """Return a simple fit score and matched signals for a job dict.

    Score is 0–100. Higher means more keyword overlap with the candidate
    profile and optional search presets.
    """
    text = _blob(job)
    signals = [s.lower() for s in (profile_signals or DEFAULT_PROFILE_SIGNALS)]
    matched = [s for s in signals if s in text]

    preset_hits: list[str] = []
    if preset_keys:
        for key in preset_keys:
            preset = SEARCH_PRESETS.get(key)
            if not preset:
                continue
            for kw in preset.get("title_keywords", []):
                if kw.lower() in text:
                    preset_hits.append(f"{key}:{kw}")
                    break

    # Base from profile signal density; boost when a named preset hits.
    base = min(70, len(matched) * 8)
    boost = min(30, len(preset_hits) * 12)
    score = min(100, base + boost)

    return {
        "fit_score": score,
        "matched_signals": matched[:12],
        "preset_hits": preset_hits,
    }


def rank_jobs_by_fit(
    jobs: list[dict],
    profile_signals: Optional[list[str]] = None,
    preset_keys: Optional[list[str]] = None,
) -> list[dict]:
    """Attach fit_score / matched_signals and sort descending by score."""
    ranked = []
    for job in jobs:
        scored = dict(job)
        meta = score_job_fit(job, profile_signals=profile_signals, preset_keys=preset_keys)
        scored.update(meta)
        ranked.append(scored)
    ranked.sort(key=lambda j: j.get("fit_score", 0), reverse=True)
    return ranked

EOF_JOBSEARCH_RANKING_FIT_PY

mkdir -p "$(dirname 'jobsearch/ranking/__init__.py')"
cat > 'jobsearch/ranking/__init__.py' << 'EOF_JOBSEARCH_RANKING___INIT___PY'
"""Filtering, clustering, and keyword-loading logic extracted from the UI.

Pure functions over plain job dicts — no Streamlit. ``load_keyword_data`` is
the one I/O helper and takes an explicit path.
"""
from jobsearch.ranking.clustering import (
    STOP_WORDS,
    cluster_jobs,
    jaccard,
    title_tokens,
)
from jobsearch.ranking.filters import apply_filters
from jobsearch.ranking.keywords import load_keyword_data
from jobsearch.ranking.fit import rank_jobs_by_fit, score_job_fit

__all__ = [
    "STOP_WORDS",
    "cluster_jobs",
    "jaccard",
    "title_tokens",
    "apply_filters",
    "load_keyword_data",
    "score_job_fit",
    "rank_jobs_by_fit",
]

EOF_JOBSEARCH_RANKING___INIT___PY

mkdir -p "$(dirname 'jobsearch/services/summary_service.py')"
cat > 'jobsearch/services/summary_service.py' << 'EOF_JOBSEARCH_SERVICES_SUMMARY_SERVICE_PY'
"""Claude-backed job-search briefing generator (UI-agnostic).

``stream_ai_summary`` is a generator yielding text chunks. It degrades
gracefully: a missing ``anthropic`` package or unset API key yields a single
human-readable message instead of raising, so the UI can stream it directly.
"""
from __future__ import annotations

from typing import Iterator, Optional

from jobsearch.settings import get_settings

SUMMARY_MODEL = "claude-sonnet-4-6"

SUMMARY_PROMPT = """\
You are analyzing a job search document for Basil Arif, an Applied AI / systems engineer. \
Background: 3 years at Slack (shipped features to 30M+ DAU), strong iOS/SwiftUI, plus deep recent \
work on private AI infrastructure and productized LLM systems:
- Heterogeneous local AI cluster (Tailscale mesh, M4 Mac Mini + RTX 4090, Ollama, token budgets)
- HistoryKit: self-hosted retrieval with vector search, sqlite-vec, recall@k evaluation harness
- CaptionLocalizer: multilingual ad-pack / caption / lyric localization service with agent tools
- dev-music-service: real-time lyrics translation and bilingual music product features
Primary target roles: AI Platform Engineer, MLOps / AI Infrastructure, RAG / Retrieval Engineer, \
Agentic Systems Engineer, Applied AI Engineer.

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


def stream_ai_summary(content: str, api_key: Optional[str] = None) -> Iterator[str]:
    """Generator that streams the Claude response token by token.

    ``api_key`` defaults to the configured ANTHROPIC_API_KEY from settings.
    """
    try:
        import anthropic
    except ImportError:
        yield "❌ `anthropic` package not installed. Run: `pip install anthropic`"
        return

    if api_key is None:
        api_key = get_settings().anthropic_api_key
    if not api_key:
        yield "❌ `ANTHROPIC_API_KEY` environment variable not set."
        return

    client = anthropic.Anthropic(api_key=api_key)

    try:
        with client.messages.stream(
            model=SUMMARY_MODEL,
            max_tokens=2048,
            system=SUMMARY_PROMPT,
            messages=[{"role": "user", "content": content}],
        ) as stream:
            for text in stream.text_stream:
                yield text
    except Exception as e:
        yield f"\n\n❌ API error: {e}"

EOF_JOBSEARCH_SERVICES_SUMMARY_SERVICE_PY

mkdir -p "$(dirname 'examples/apply/candidate_profile.ai_platform.json')"
cat > 'examples/apply/candidate_profile.ai_platform.json' << 'EOF_EXAMPLES_APPLY_CANDIDATE_PROFILE_AI_PLATFORM_JSON'
{
  "full_name": "Basil Arif",
  "first_name": "Basil",
  "last_name": "Arif",
  "email": "",
  "phone": "",
  "linkedin_url": "",
  "github_url": "https://github.com/barif-7",
  "portfolio_url": "",
  "website_url": "",
  "location_city": "Milton",
  "location_region": "ON",
  "location_country": "Canada",
  "current_company": "",
  "additional_information": "Applied AI / systems engineer. Built a heterogeneous private AI cluster (Tailscale, M4 Mac Mini, RTX 4090, Ollama), HistoryKit retrieval with vector search + reproducible eval harness, CaptionLocalizer multilingual ad and lyric packs with agent-callable tools, and real-time lyrics translation in dev-music-service. Seeking AI Platform, MLOps, RAG, Agentic, or Applied AI roles.",
  "education_summary": "",
  "profile_signals": [
    "ai platform",
    "llm",
    "mlops",
    "rag",
    "retrieval",
    "vector",
    "agentic",
    "orchestration",
    "inference",
    "ollama",
    "fastapi",
    "distributed",
    "gpu",
    "speech",
    "transcription",
    "localization"
  ],
  "target_presets": [
    "ai_platform",
    "rag_retrieval",
    "agentic",
    "applied_ai",
    "speech_multimodal"
  ],
  "checkbox_answers": {
    "I agree to the privacy policy": true
  },
  "radio_answers": {
    "Are you legally authorized to work in Canada?": "Yes"
  }
}

EOF_EXAMPLES_APPLY_CANDIDATE_PROFILE_AI_PLATFORM_JSON

mkdir -p "$(dirname 'tests/test_fit.py')"
cat > 'tests/test_fit.py' << 'EOF_TESTS_TEST_FIT_PY'
"""Tests for jobsearch.ranking.fit."""
from __future__ import annotations

import unittest

from jobsearch.ranking.fit import rank_jobs_by_fit, score_job_fit


class FitScoringTests(unittest.TestCase):
    def test_platform_role_scores_higher_than_unrelated(self):
        platform = {
            "title": "Senior AI Platform Engineer",
            "company": "Example",
            "location": "Remote",
            "description": "Own LLM inference, RAG pipelines, and agent tooling on GPU clusters.",
            "url": "https://example.com/a",
        }
        unrelated = {
            "title": "Junior Marketing Coordinator",
            "company": "Example",
            "location": "Remote",
            "description": "Social media calendar and brand guidelines.",
            "url": "https://example.com/b",
        }
        s1 = score_job_fit(platform, preset_keys=["ai_platform", "rag_retrieval"])
        s2 = score_job_fit(unrelated, preset_keys=["ai_platform", "rag_retrieval"])
        self.assertGreater(s1["fit_score"], s2["fit_score"])
        self.assertGreaterEqual(s1["fit_score"], 20)
        self.assertTrue(s1["matched_signals"] or s1["preset_hits"])

    def test_rank_jobs_by_fit_orders_descending(self):
        jobs = [
            {"title": "Marketing Intern", "company": "X", "location": "", "url": "u1"},
            {
                "title": "MLOps Engineer",
                "company": "Y",
                "location": "Toronto",
                "description": "Kubernetes, model serving, inference",
                "url": "u2",
            },
        ]
        ranked = rank_jobs_by_fit(jobs, preset_keys=["ai_platform"])
        self.assertEqual(ranked[0]["url"], "u2")
        self.assertIn("fit_score", ranked[0])


if __name__ == "__main__":
    unittest.main()

EOF_TESTS_TEST_FIT_PY


echo "Running fit tests..."
python -m pytest tests/test_fit.py -q || python3 -m pytest tests/test_fit.py -q

git add \
  config.py \
  jobsearch/config.py \
  jobsearch/ranking/fit.py \
  jobsearch/ranking/__init__.py \
  jobsearch/services/summary_service.py \
  examples/apply/candidate_profile.ai_platform.json \
  tests/test_fit.py

git status

git commit -m "$(cat <<'EOF'
Add AI Platform / RAG / Agentic search presets and fit scoring

Highest-ROI job-search improvements for targeting AI Platform, MLOps,
RAG, Agentic, and Applied AI roles:

- Expand ROLE_KEYWORDS so board fetchers keep platform/RAG/agent titles
- Add SEARCH_PRESETS for quick UI/script filters by role family
- Add jobsearch.ranking.fit with score_job_fit / rank_jobs_by_fit
- Update AI summary prompt to emphasize cluster, HistoryKit, CaptionLocalizer
- Add candidate_profile.ai_platform.json with profile_signals + target_presets
- Unit tests for fit scoring

EOF
)" || echo "Commit may have failed if identity is unset — set git user.name/email and re-run git commit"

echo ""
echo "Done. Branch: feature/ai-platform-search-presets"
echo "Push when ready:  git push -u origin feature/ai-platform-search-presets"
