-- Indexes for the columns the dashboard and apply-queue queries
-- actually filter and sort on.
CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs (status);
CREATE INDEX IF NOT EXISTS idx_jobs_application_status ON jobs (application_status);
CREATE INDEX IF NOT EXISTS idx_jobs_company ON jobs (company);
CREATE INDEX IF NOT EXISTS idx_jobs_date_found ON jobs (date_found);
CREATE INDEX IF NOT EXISTS idx_jobs_priority ON jobs (priority);
CREATE INDEX IF NOT EXISTS idx_jobs_last_seen ON jobs (last_seen);
CREATE INDEX IF NOT EXISTS idx_jobs_board ON jobs (board);
