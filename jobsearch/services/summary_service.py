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
