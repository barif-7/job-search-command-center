-- One row per auto-apply attempt. The jobs table keeps only the latest
-- application state; this table preserves the full history for audit.
CREATE TABLE IF NOT EXISTS application_attempts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id INTEGER,
    job_url TEXT NOT NULL,
    attempted_at TEXT NOT NULL,
    application_url TEXT,
    ats_provider TEXT,
    status TEXT,
    detected_count INTEGER,
    fields_completed TEXT,
    skipped_fields TEXT,
    resume_uploaded INTEGER,
    blockers TEXT,
    human_required_reason TEXT,
    notes TEXT,
    review_dir TEXT
);
CREATE INDEX IF NOT EXISTS idx_attempts_job_url ON application_attempts (job_url);
CREATE INDEX IF NOT EXISTS idx_attempts_attempted_at ON application_attempts (attempted_at);
