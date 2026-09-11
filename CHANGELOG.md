# Changelog

## 2026-09-02 — Size the AI briefing input to the context window

After the registry expansion the markdown export reached 486K chars (~121K
tokens) against a 32K-token local context window, so the briefing was silently
seeing a truncated document.

### Changed

- `jobsearch/services/summary_service.py` — new `build_briefing_document()`
  renders un-triaged roles only (status "New"), newest first, as a compact
  `company — title | location` digest, capped by `BRIEFING_MAX_ROLES` (400) and
  a `briefing_char_budget()` computed from `OLLAMA_NUM_CTX` less room for the
  prompt and reply. Returns the included/total counts so the UI can say how much
  of the backlog was covered.
- `app.py` — the AI Summary tab builds the briefing from the live tracker rather
  than re-reading the full markdown export, and reports "Analyzing N of M
  un-triaged roles".

### Result

Briefing input 485,855 → 30,367 chars (94% smaller, ~10K tokens), comfortably
inside the window. Output quality improved as a side effect: the earlier run
returned bare role lists, and the same prompt over the digest now produces the
per-role rationale the prompt asks for in every section. As roles get triaged
out of "New", the pool shrinks and more of it fits.


## 2026-09-02 — Company registry expansion (sources were not the bottleneck)

Asked whether to add job board sources. Probed seven ATS platforms and measured
where the missing postings actually are.

### Findings

- Workable, Rippling and SmartRecruiters all expose usable public APIs and were
  verified working. But of 75 boards detected across a sample of target
  companies: greenhouse 40, ashby 28, lever 4, smartrecruiters 2, rippling 1.
- 7,140 untracked postings were reachable with the *existing* three fetchers
  versus ~720 behind new ones. The registry, not the source list, was the limit.
- Neither Greenhouse, Lever nor Ashby exposes a list-all-companies endpoint
  (verified: 404/401 on every index path, and Ashby's GraphQL still requires a
  single organization). The registry has to be curated.

### Changed

- `careerBoards.py` — 457 → 514 companies. 52 added from an ATS probe
  (Stripe, Databricks, Snowflake, Datadog, MongoDB, Cloudflare, Pinterest,
  Coinbase, Airbnb, Plaid, Vercel, Miro, Modal, LangChain, Temporal, …), plus 6
  recovered from prior ATS research found in conversation history
  (Cursor, Lyft, Deliveroo, Discord, Flock, and Notion's live Ashby board).
- Removed the `notion` Greenhouse entry: that board 404s and had been counted as
  a failed company on every fetch. Notion's live board is on Ashby (134 jobs).

### Result

1894 → 2801 jobs (907 new); Toronto/Ontario 140 → 204. 95% carry a description.


## 2026-09-02 — Broaden role criteria beyond iOS

The tracker targeted iOS + AI/ML + product engineer only. Broadened to general
software engineering, with an exclusion list so the generic keywords stay on IC
roles.

### Changed

- `config.py` — `ROLE_KEYWORDS` 21 → 39: added backend, platform,
  infrastructure, distributed systems, full-stack, frontend, web, and the
  generic `software engineer` / `software developer` / `staff|senior|principal
  engineer`. New `ROLE_EXCLUSIONS` (17 entries) drops manager, director, head
  of, VP, intern, new grad, co-op, and sales/solutions/support engineer titles.
- `jobsearch/boards/__init__.py` — `matches_role()` and `location_wanted()` now
  live here. All three board modules had byte-identical private copies, so the
  exclusion rule would otherwise have been written three times. Exclusions win
  over keywords.
- `jobsearch/boards/{greenhouse,lever,ashby}.py` — import the shared matchers.

### Result

474 → 1894 jobs; Toronto-area 25 → 140, Canada-wide 294. Mix is ~820 generic
SWE, 496 AI/ML, 337 backend/infra, 137 full-stack, 77 iOS/mobile, 72
frontend/web, 56 product. 93% carry a description; keyword report regenerated
over all 1894.

Note: 28 pre-existing rows have manager/director titles that the new exclusions
reject. They predate the exclusion list, were not re-fetched, and are all still
status "New" — left in place rather than deleted.


## 2026-09-02 — Canadian board coverage and iOS title matching

Toronto iOS roles were scarce in the tracker. Measuring rather than guessing: a
scan of all 15,686 live postings across every configured board found only 43
iOS engineering roles in any wanted location, so the scarcity is mostly real —
but two fixable gaps were hiding some.

### Changed

- `config.py` — `ROLE_KEYWORDS` matched "iOS Engineer" and "Software Engineer,
  iOS" but not the platform-last and parenthesised forms that are just as
  common: added `engineer, ios`, `engineer (ios)`, `engineer - ios`,
  `ios/android`, `engineer, mobile`. Verified against the full 15,686-posting
  scan: 6 new matches, no false positives.
- `careerBoards.py` — added 31 Canadian/Toronto-area boards (426 → 457
  companies). Each was verified live and kept only if ≥25% of its postings are
  in Canada or it has ≥3 Toronto-area roles; 6 probed slugs turned out to be
  unrelated US companies (`relay`, `ritual`, `koho`, `lightspeed`, and two
  duplicates) and were dropped.

### Result

Toronto-area iOS/mobile roles 6 → 7; the addition is Sentry's "Senior Software
Engineer (iOS), SDK" in Toronto, which the title filter had been dropping. 19
new rows overall. Note that Greenhouse, Lever and Ashby expose no
list-all-companies endpoint — every API is keyed by a company slug — so the
registry has to be curated; it cannot be enumerated.


## 2026-09-02 — Fetch job descriptions, and fix the keyword patterns they exposed

All three board fetchers hardcoded `"description": ""`, so keyword extraction
only ever read job *titles* — `aws`, `docker`, `kubernetes`, `postgres` and
`graphql` scored zero across 455 jobs, and `python` and `swift` never matched
at all.

### Changed

- `jobsearch/boards/greenhouse.py` — request `?content=true`; the list endpoint
  omits the posting body without it. Same request count.
- `jobsearch/boards/lever.py` — build the description from `descriptionPlain`,
  the bullet `lists`, and `additionalPlain`, all already in the response the
  code was discarding.
- `jobsearch/boards/ashby.py` — the job-board HTML's embedded `jobPostings`
  JSON carries no description at any depth, so fetch from the public posting
  API (`api.ashbyhq.com/posting-api/job-board/{slug}`) and fall back to the
  HTML scrape when a board is not on it. `jobUrl` is byte-identical to the URL
  the HTML path built, so dedupe survives the switch.
- `jobsearch/boards/__init__.py` — new `description_text()` normalises escaped
  HTML, plain text, and stray tags to one plain-text form, capped at 20k chars.
- `scripts/extract_keywords.py` — patterns that were harmless against titles
  became noisy against prose. `\bgo\b` matched "go deep" and "go-to-market"
  (130 hits, ~24 real), `\bts\b` matched "TS/SCI" clearances, and `\bjs\b`
  matched the "js" inside "Node.js"/"Next.js" — a dot is a word boundary.

### Result

353 of 455 jobs now carry a description (avg 6.3k chars); the rest are stale
rows for delisted postings. Jobs with no keyword at all fell from 68 to 13.


## 2026-09-02 — Local Ollama backend for AI summaries

The briefing generator was hard-wired to the Anthropic API, so the "Generate AI
Summary" button sat disabled without an `ANTHROPIC_API_KEY`. It now also speaks
to a local Ollama server, letting the summary run entirely offline.

### Changed

- `jobsearch/services/summary_service.py` — split into `_stream_anthropic` and
  `_stream_ollama` (NDJSON streaming over `/api/chat`) behind the unchanged
  `stream_ai_summary` generator. New `resolve_provider`, `summary_available`,
  and `provider_label` helpers pick and describe the active backend.
- `jobsearch/settings.py` — added `SUMMARY_PROVIDER` (`auto`/`anthropic`/
  `ollama`), `OLLAMA_BASE_URL`, `OLLAMA_MODEL`, `OLLAMA_NUM_CTX`. `auto`
  prefers Anthropic when a key is set and falls back to a reachable Ollama.
- `app.py` — the AI Summary tab gates on `summary_available()` rather than the
  Anthropic key alone, and captions which backend is in use.


## 2026-06-14 — Extract a testable core out of app.py (Phase 2)

A pure refactor: move business/parsing/ranking/rendering logic out of the
~2,400-line Streamlit script into importable, unit-tested modules. No behavior,
visual, or database-effect change — `app.py` is now Streamlit wiring, layout,
CSS, and thin cached wrappers. Each slice was pinned by golden-master
characterization tests captured from the original in-app code before the move,
and `pytest` stayed green throughout (32 → 96 tests).

### New modules

- `jobsearch/parsing/` — `markdown.py` (parse_md_jobs/parse_md_stats/
  parse_job_entry/parse_exported_job_bullet) and `query.py` (parse_comp_value,
  parse_query_chips).
- `jobsearch/ranking/` — `filters.py` (apply_filters), `clustering.py`
  (cluster_jobs, jaccard, title_tokens), `keywords.py` (load_keyword_data).
- `jobsearch/services/` — `logo_service.py` (company→domain→logo URL
  resolution), `summary_service.py` (the Claude briefing generator),
  `pipeline_service.py` (single subprocess execution path for the CLI scripts).
- `jobsearch/ui/components.py` — card/hero/metric/badge/logo HTML builders as
  pure string functions.

### Changed

- The dashboard's three inline `subprocess.run` calls now route through
  `pipeline_service`, so the UI and CLI share one execution path.
- `app.py` shrank from ~2,440 to ~1,380 lines and now imports its logic;
  caching is preserved via `st.cache_data` wrappers so output is unchanged.

### Intentionally out of scope

No visual redesign, no new screens, no behavior change. `models.py` was left in
place (a `domain/` package would have churned many imports for no behavior
gain) and the large `APP_CSS` constant stays in the UI layer (`app.py`).

## 2026-06-12 — Script & workflow hardening (Phase 1)

The goal of this pass: make the workflow loop (fetch → store → export/sync →
fill-and-pause apply) reliable, idempotent, observable, and safe to re-run
unattended on one machine.

### Changed

- **One config path.** All runtime settings (DB path, export path, Notion and
  API credentials, apply input dir) are read through a single typed settings
  object (`jobsearch/settings.py`) from env + `.env`. The dead empty constants
  in `config.py` are gone, so the scripts and the UI can no longer disagree.
  Everything stays optional — a fresh clone with no `.env` still runs.
- **Consistent CLIs.** All four scripts (`run_fetch.py`, `run_auto_apply.py`,
  `export_markdown.py`, `sync_notion.py`) use `argparse`, support `--dry-run`
  where they have side effects, log through `logging`, print an end-of-run
  summary, and return meaningful exit codes.
- **Partial fetch failure is visible.** A fetch reports per-board
  success/failure counts and exits non-zero when boards fail, so "2 of 3
  boards down" can never be mistaken for "no new jobs." One bad board still
  doesn't abort the run.
- **Versioned schema migrations.** `migrations/NNN_*.sql` with a tracked
  `schema_version`, applied idempotently on connect; added the indexes the
  dashboard and apply-queue queries actually use.
- **Idempotent re-runs.** Re-fetching never duplicates rows and never clobbers
  user-managed fields (`status`, `priority`, `notes`) or `date_found`
  (regression-tested).
- **Export fixed.** Markdown export honors `MARKDOWN_EXPORT_PATH`, emits real
  newlines, and the CLI and UI share one exporter code path.
- **Notion sync robustness.** True upsert, failures are logged and counted in
  the sync summary instead of aborting, and a disabled/unconfigured state is a
  clean no-op.
- **Apply audit trail.** Every auto-apply attempt writes one row to the new
  `application_attempts` table and a per-job review folder under
  `data/apply/reviews/` (`summary.json`, `review.md`, before/after
  screenshots, detected vs filled vs skipped fields). Field filling is gated
  on a confidence threshold (a strong identifying attribute must match);
  checkbox/radio answers require the question text itself to match. All safety
  stops kept: CAPTCHA, OTP, forced account creation, demographic/legal
  questions — and the runner **never clicks final submit**.
- **End-to-end smoke test.** One test drives mocked fetch → store → export →
  apply queue build/preview against a temp DB, guarding the whole loop.
- **Hygiene.** `data/`, apply inputs, and `.venv` are untracked; runnable
  templates live in `examples/apply/`; the `job_apply_agent/` runbook was
  updated to match the real script contracts.

### Intentionally out of scope

Fit scoring, resume generation, Gmail/Calendar integrations, any auto-submit
path, anti-bot/CAPTCHA evasion, new board sources, and the `app.py` UI
refactor (that is Phase 2, not started here).
