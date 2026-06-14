# Changelog

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
