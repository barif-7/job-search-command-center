-- Full jobs schema. No-op on databases that already have the table;
-- legacy databases get missing columns backfilled by JobStore before
-- migrations run.
CREATE TABLE IF NOT EXISTS jobs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company TEXT,
    title TEXT,
    location TEXT,
    normalized_location TEXT,
    url TEXT UNIQUE NOT NULL,
    board TEXT,
    description TEXT,
    compensation TEXT,
    date_found TEXT,
    last_seen TEXT,
    status TEXT DEFAULT 'New',
    priority INTEGER,
    fit_score REAL,
    fit_summary TEXT,
    notes TEXT,
    notion_page_id TEXT,
    application_status TEXT DEFAULT 'NOT_STARTED',
    application_url TEXT,
    ats_provider TEXT,
    fields_completed TEXT,
    resume_uploaded INTEGER,
    blockers TEXT,
    last_apply_attempt_at TEXT,
    apply_notes TEXT,
    human_required_reason TEXT,
    created_at TEXT,
    updated_at TEXT
);
