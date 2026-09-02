"""Job-search briefing generator (UI-agnostic).

Two backends: the Anthropic API, and a local Ollama server for running
entirely offline. ``resolve_provider`` picks one — honouring an explicit
``SUMMARY_PROVIDER`` of ``anthropic``/``ollama``, otherwise preferring
Anthropic when a key is set and falling back to Ollama when its server
answers.

``stream_ai_summary`` is a generator yielding text chunks. It degrades
gracefully: a missing package, unset API key, or unreachable Ollama yields a
single human-readable message instead of raising, so the UI can stream it
directly.
"""
from __future__ import annotations

import json
from typing import Iterator, Optional

from jobsearch.settings import get_settings

SUMMARY_MODEL = "claude-sonnet-4-6"
MAX_SUMMARY_TOKENS = 2048

# Seconds to wait for the Ollama server to answer /api/tags. Short — this
# runs behind a UI gate on every render of the AI Summary tab.
OLLAMA_PROBE_TIMEOUT = 1.5
# Local generation is slow; a first token can take a minute on a cold model.
OLLAMA_STREAM_TIMEOUT = 600.0

# ── Briefing input sizing ──────────────────────────────────────────────────
# The full markdown export outgrew the local model's context window (486k
# chars against a 32k-token window), which silently truncated the document.
# The briefing runs on un-triaged roles only, newest first, as a compact
# digest — the model needs company/title/location to pick, not full postings.
UNTRIAGED_STATUSES = ("New", "")
BRIEFING_MAX_ROLES = 400
# Conservative: URL- and punctuation-heavy text tokenises worse than prose.
CHARS_PER_TOKEN = 3.0
# Room for the system prompt, the reinforcement block, and the reply.
CONTEXT_RESERVE_TOKENS = 3000

# Local models reliably lose a system prompt behind a 20k-token document and
# drift into chat ("How can I assist you today?"). Restating the contract after
# the document — where recency works for us — pulls them back on format.
OLLAMA_REINFORCEMENT = """\

---

The document above is the complete job list. Now write the briefing.

Output ONLY markdown using exactly these six section headers, in this order, \
with real companies and roles taken from the document above:

## 🔥 Apply This Week
## 🎯 Strongest Fit Signals
## 📍 Location Strategy
## ✨ Hidden Gems in New Findings
## ⚠️ Roles to Deprioritize
## 📋 This Week's Action Plan

Do not greet, do not introduce yourself, do not describe what you are about to \
do, and do not ask any questions at the end. Start your reply with the \
characters "## 🔥".\
"""

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


def briefing_char_budget(num_ctx: Optional[int] = None) -> int:
    """Characters of document that fit alongside the prompt and the reply."""
    if num_ctx is None:
        num_ctx = get_settings().ollama_num_ctx
    usable = max(num_ctx - CONTEXT_RESERVE_TOKENS, 1000)
    return int(usable * CHARS_PER_TOKEN)


def build_briefing_document(
    jobs: list,
    max_roles: int = BRIEFING_MAX_ROLES,
    char_budget: Optional[int] = None,
) -> tuple[str, int, int]:
    """Compact digest of the freshest un-triaged roles.

    ``jobs`` is a sequence of mappings with company/title/location/status and
    optionally date_found. Returns ``(document, included, total_untriaged)`` so
    the caller can tell the reader how much of the pool was covered.
    """
    if char_budget is None:
        char_budget = briefing_char_budget()

    untriaged = [
        j for j in jobs
        if str(j.get("status") or "").strip() in UNTRIAGED_STATUSES
    ]
    total = len(untriaged)

    # Newest first: an un-triaged backlog is worth reviewing from the top.
    def _key(j):
        return str(j.get("date_found") or "")
    untriaged.sort(key=_key, reverse=True)

    lines: list[str] = []
    used = 0
    for job in untriaged[:max_roles]:
        company = str(job.get("company") or "").strip()
        title = str(job.get("title") or "").strip()
        location = str(job.get("location") or "").strip()
        if not (company and title):
            continue
        line = f"- {company} — {title} | {location}" if location else f"- {company} — {title}"
        if used + len(line) + 1 > char_budget:
            break
        lines.append(line)
        used += len(line) + 1

    header = (
        f"Un-triaged roles in the tracker: {total}. "
        f"Showing the {len(lines)} most recently found.\n"
    )
    return header + "\n" + "\n".join(lines) + "\n", len(lines), total


def ollama_available(base_url: Optional[str] = None) -> bool:
    """True when a local Ollama server answers on ``base_url``."""
    import httpx

    if base_url is None:
        base_url = get_settings().ollama_base_url
    try:
        resp = httpx.get(f"{base_url}/api/tags", timeout=OLLAMA_PROBE_TIMEOUT)
        return resp.status_code == 200
    except Exception:
        return False


def resolve_provider() -> Optional[str]:
    """Return the backend to use: ``"anthropic"``, ``"ollama"``, or None.

    None means nothing is configured — the UI should disable the generate
    button rather than let the user click into an error message.
    """
    settings = get_settings()
    choice = settings.summary_provider

    if choice == "anthropic":
        return "anthropic" if settings.anthropic_api_key else None
    if choice == "ollama":
        return "ollama" if ollama_available(settings.ollama_base_url) else None

    # "auto": a paid key beats the local model, but either beats nothing.
    if settings.anthropic_api_key:
        return "anthropic"
    if ollama_available(settings.ollama_base_url):
        return "ollama"
    return None


def summary_available() -> bool:
    """UI gate — whether a summary can be generated at all right now."""
    return resolve_provider() is not None


def provider_label() -> str:
    """Human-readable description of the active backend, for the UI."""
    settings = get_settings()
    provider = resolve_provider()
    if provider == "anthropic":
        return f"Anthropic API · {SUMMARY_MODEL}"
    if provider == "ollama":
        return f"Local Ollama · {settings.ollama_model}"
    return "No summary backend configured"


def _stream_anthropic(content: str, api_key: str) -> Iterator[str]:
    try:
        import anthropic
    except ImportError:
        yield "❌ `anthropic` package not installed. Run: `pip install anthropic`"
        return

    if not api_key:
        yield "❌ `ANTHROPIC_API_KEY` environment variable not set."
        return

    client = anthropic.Anthropic(api_key=api_key)

    try:
        with client.messages.stream(
            model=SUMMARY_MODEL,
            max_tokens=MAX_SUMMARY_TOKENS,
            system=SUMMARY_PROMPT,
            messages=[{"role": "user", "content": content}],
        ) as stream:
            for text in stream.text_stream:
                yield text
    except Exception as e:
        yield f"\n\n❌ API error: {e}"


def _stream_ollama(
    content: str,
    base_url: Optional[str] = None,
    model: Optional[str] = None,
    num_ctx: Optional[int] = None,
) -> Iterator[str]:
    """Stream a briefing from a local Ollama server via /api/chat.

    Responses are NDJSON — one JSON object per line, each carrying an
    incremental ``message.content``.
    """
    import httpx

    settings = get_settings()
    base_url = base_url if base_url is not None else settings.ollama_base_url
    model = model if model is not None else settings.ollama_model
    num_ctx = num_ctx if num_ctx is not None else settings.ollama_num_ctx

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": SUMMARY_PROMPT},
            {"role": "user", "content": content + OLLAMA_REINFORCEMENT},
        ],
        "stream": True,
        # Thinking-capable models otherwise burn the budget reasoning aloud.
        "think": False,
        "options": {
            "num_ctx": num_ctx,
            "num_predict": MAX_SUMMARY_TOKENS,
            # Lower than the API default — this is a format-following task.
            "temperature": 0.3,
        },
    }

    try:
        with httpx.stream(
            "POST",
            f"{base_url}/api/chat",
            json=payload,
            timeout=OLLAMA_STREAM_TIMEOUT,
        ) as resp:
            if resp.status_code != 200:
                resp.read()
                yield f"❌ Ollama error {resp.status_code}: {resp.text.strip()}"
                return
            for line in resp.iter_lines():
                if not line:
                    continue
                try:
                    event = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if event.get("error"):
                    yield f"\n\n❌ Ollama error: {event['error']}"
                    return
                chunk = (event.get("message") or {}).get("content", "")
                if chunk:
                    yield chunk
                if event.get("done"):
                    return
    except Exception as e:
        yield f"\n\n❌ Ollama error: {e}"


def stream_ai_summary(
    content: str,
    api_key: Optional[str] = None,
    provider: Optional[str] = None,
) -> Iterator[str]:
    """Generator that streams the briefing token by token.

    ``provider`` forces a backend; otherwise ``resolve_provider`` decides.
    Passing ``api_key`` explicitly means "use Anthropic with this key".
    """
    if provider is None:
        provider = "anthropic" if api_key is not None else resolve_provider()

    if provider == "ollama":
        yield from _stream_ollama(content)
        return

    if provider is None:
        settings = get_settings()
        yield (
            "❌ No summary backend available. Set `ANTHROPIC_API_KEY`, or start a "
            f"local Ollama server at `{settings.ollama_base_url}` "
            f"with the `{settings.ollama_model}` model pulled."
        )
        return

    if api_key is None:
        api_key = get_settings().anthropic_api_key
    yield from _stream_anthropic(content, api_key)
