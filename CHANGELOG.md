# Changelog

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
