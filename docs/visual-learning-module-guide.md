# Visual Learning Module Guide

Create and maintain a self-contained `learning-module.html` that explains this repository visually and makes the codebase easy to review in 10–15 minutes.

## Output

- `learning-module.html` — offline single-file interactive guide
- `docs/visual-learning-module-guide.md` — this repeatable workflow and prompt

## Repository teaching model

Treat Job Search Command Center as a **local-first Discover → Decide → Apply system**, not merely a scraper:

1. **Discover** — async Greenhouse, Lever, and Ashby adapters ingest external roles.
2. **Normalize + persist** — jobs become a shared model and are upserted into SQLite while preserving user-managed state.
3. **Decide** — filters, search preferences, deterministic fit ranking, keyword extraction, and AI briefings help triage the feed.
4. **Apply safely** — Playwright prepares application forms, records blockers and skipped fields, creates review artifacts, and stops for human approval.
5. **Audit** — migrations protect schema evolution and `application_attempts` preserves per-run history.

## Workflow

1. Read the complete tree first: root entry points, `jobsearch/`, `scripts/`, `migrations/`, `tests/`, examples and docs.
2. Start with `README.md` and `app.py` to establish product purpose and UI composition.
3. Trace ingestion through `scripts/run_fetch.py` → `jobsearch/fetcher.py` → `jobsearch/boards/*` → `Job` → `jobsearch/store.py`.
4. Trace decision support through `jobsearch/ranking/*`, parsing, search preferences, keyword extraction, and `services/summary_service.py`.
5. Trace application automation through `services/pipeline_service.py` → `scripts/run_auto_apply.py` → `jobsearch/apply/runner.py` → ATS/field-matching/review helpers → store audit state.
6. Read migrations and tests to identify invariants, failure semantics and intended extension seams.
7. Update the visual module with architecture, data flows, persistence, error paths, test strategy, setup/debug notes, extension points and interview talking points.
8. Keep the HTML offline-first: embedded CSS, minimal vanilla JS, no CDN dependencies, system fonts.

## Required visual sections

```text
learning-module.html
├── Hero: repo purpose + stack
├── Mental model: Discover → Decide → Apply
├── Architecture: entry points → services → domain → persistence
├── Data flows
│   ├── Job ingestion
│   ├── AI briefing
│   └── Safe application preparation
├── State/persistence map
├── Key files in recommended reading order
├── Patterns and architectural boundaries
├── Error handling paths
├── Test strategy
├── Setup + debugging notes
├── Extension/refactor seams
└── Interview talking points + 10-minute review route
```

## Repository-specific facts to verify on every refresh

- Which ATS board adapters are registered.
- Whether ingestion remains concurrent and how partial board failures are surfaced.
- Which fields are board-owned versus user-owned during an upsert.
- Current SQLite migrations and audit tables.
- Current ranking/filter strategy and whether it requires an LLM.
- Current AI summary providers, context-budget behavior and fallback semantics.
- Whether auto-apply still stops for human review and what artifacts it records.
- Current CLI scripts and the service path used by Streamlit buttons.
- Test coverage by subsystem and the current smoke/integration path.

## Coding-agent prompt

```text
Analyze this repository and refresh `learning-module.html` as a self-contained offline visual guide. Do not infer the architecture from filenames alone: read the implementation, migrations, scripts, tests, config, examples and docs.

Teach the repository as a local-first Discover → Decide → Apply system. Trace these concrete flows end-to-end:
1) job-board ingestion and normalization,
2) SQLite persistence/upsert and state preservation,
3) filtering/ranking/search preferences,
4) Anthropic/local-Ollama AI briefing generation,
5) Playwright application preparation and human-review/audit flow.

Identify entry points, module boundaries, domain models, networking, concurrency, state ownership, persistence, migrations, provider abstractions, error handling, safety boundaries and test strategy. Call out the exact files that implement each responsibility.

Generate diagrams for the module/dependency map, ingestion flow, AI summary flow, application flow, persistence/state map and error paths. Include a recommended file-reading order, setup/run/test/debug commands, extension seams, refactor opportunities, architectural tradeoffs and concise interview talking points.

Use embedded CSS and minimal vanilla JavaScript only; no CDNs or external assets. The HTML must work by opening it directly from disk. Keep it specific to the current repository and useful enough that someone can reconstruct the architecture in 10–15 minutes without opening every source file.
```

## Quality bar

The guide is complete when a reviewer can answer these questions without opening the code:

- What problem does the repo solve?
- What are the main runtime entry points?
- How does a role move from an external ATS into durable local state?
- What state survives a re-fetch and why?
- How are roles ranked and summarized?
- Where are cloud/local AI choices made?
- What exactly does the application agent automate, and where does a human take over?
- How are failures and application attempts made observable?
- Which files should be changed to add a board, ranking method, AI provider or execution backend?
- What are the most important architectural tradeoffs to explain in an interview?
