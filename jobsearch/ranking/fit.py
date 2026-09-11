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
    presets: Optional[dict] = None,
) -> dict[str, Any]:
    """Return a simple fit score and matched signals for a job dict.

    Score is 0–100. Higher means more keyword overlap with the candidate
    profile and optional search presets.
    """
    text = _blob(job)
    signals = [s.lower() for s in (DEFAULT_PROFILE_SIGNALS if profile_signals is None else profile_signals)]
    matched = [s for s in signals if s in text]

    preset_hits: list[str] = []
    if preset_keys:
        for key in preset_keys:
            preset = (SEARCH_PRESETS if presets is None else presets).get(key)
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
    presets: Optional[dict] = None,
) -> list[dict]:
    """Attach fit_score / matched_signals and sort descending by score."""
    ranked = []
    for job in jobs:
        scored = dict(job)
        meta = score_job_fit(job, profile_signals=profile_signals, preset_keys=preset_keys, presets=presets)
        scored.update(meta)
        ranked.append(scored)
    ranked.sort(key=lambda j: j.get("fit_score", 0), reverse=True)
    return ranked

