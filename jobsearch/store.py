import logging
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional, Dict, Any

from .models import Job
from .settings import get_settings
from .utils import clean_text

logger = logging.getLogger(__name__)

MIGRATIONS_DIR = Path(__file__).resolve().parent.parent / "migrations"

# Columns added after the original schema; backfilled into legacy
# databases before versioned migrations run, so index migrations can
# assume they exist.
_LEGACY_COLUMN_BACKFILL = {
    "application_status": "TEXT DEFAULT 'NOT_STARTED'",
    "application_url": "TEXT",
    "ats_provider": "TEXT",
    "fields_completed": "TEXT",
    "resume_uploaded": "INTEGER",
    "blockers": "TEXT",
    "last_apply_attempt_at": "TEXT",
    "apply_notes": "TEXT",
    "human_required_reason": "TEXT",
}


class JobStore:
    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path if db_path is not None else get_settings().database_path
        self.conn = None
        self.cursor = None
        self._ensure_connected()
        self.run_migrations()

    def _ensure_connected(self):
        if self.conn is None:
            if self.db_path != ":memory:":
                Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
            self.conn = sqlite3.connect(self.db_path)
            self.conn.row_factory = sqlite3.Row # Access columns by name
            self.cursor = self.conn.cursor()

    def schema_version(self) -> int:
        self._ensure_connected()
        return int(self.cursor.execute("PRAGMA user_version").fetchone()[0])

    def run_migrations(self):
        """Brings the database schema up to date.

        Applies ordered migrations/NNN_*.sql files whose number exceeds the
        database's PRAGMA user_version. Schema failures raise — a store with
        a broken schema must not be used silently.
        """
        self._ensure_connected()
        self._backfill_legacy_columns()
        current = self.schema_version()
        for path in sorted(MIGRATIONS_DIR.glob("[0-9][0-9][0-9]_*.sql")):
            version = int(path.name[:3])
            if version <= current:
                continue
            self.cursor.executescript(path.read_text(encoding="utf-8"))
            self.cursor.execute(f"PRAGMA user_version = {version:d}")
            self.conn.commit()
            logger.info("Applied migration %s", path.name)

    def _backfill_legacy_columns(self):
        """Adds newer columns to pre-migration databases in place (idempotent)."""
        self.cursor.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name = 'jobs'"
        )
        if not self.cursor.fetchone():
            return
        self.cursor.execute("PRAGMA table_info(jobs)")
        existing = {row["name"] for row in self.cursor.fetchall()}
        for name, definition in _LEGACY_COLUMN_BACKFILL.items():
            if name not in existing:
                self.cursor.execute(f"ALTER TABLE jobs ADD COLUMN {name} {definition}")
        self.conn.commit()

    def job_to_db_row(self, job: Job) -> Dict[str, Any]:
        """Converts a Job object to a dictionary suitable for database insertion/update."""
        return {
            "company": clean_text(job.company),
            "title": clean_text(job.title),
            "location": clean_text(job.location),
            "normalized_location": clean_text(job.normalized_location),
            "url": job.url,
            "board": job.board,
            "description": clean_text(job.description),
            "compensation": clean_text(job.compensation) if job.compensation else None,
            "date_found": job.date_found.isoformat() if job.date_found else None,
            "last_seen": job.last_seen.isoformat() if job.last_seen else None,
            "status": job.status,
            "priority": job.priority,
            "fit_score": job.fit_score,
            "fit_summary": clean_text(job.fit_summary) if job.fit_summary else None,
            "notes": clean_text(job.notes) if job.notes else None,
            "notion_page_id": job.notion_page_id,
            "application_status": job.application_status or "NOT_STARTED",
            "application_url": job.application_url,
            "ats_provider": job.ats_provider,
            "fields_completed": clean_text(job.fields_completed) if job.fields_completed else None,
            "resume_uploaded": int(bool(job.resume_uploaded)) if job.resume_uploaded is not None else None,
            "blockers": clean_text(job.blockers) if job.blockers else None,
            "last_apply_attempt_at": job.last_apply_attempt_at.isoformat() if job.last_apply_attempt_at else None,
            "apply_notes": clean_text(job.apply_notes) if job.apply_notes else None,
            "human_required_reason": clean_text(job.human_required_reason) if job.human_required_reason else None,
            "created_at": job.created_at.isoformat() if job.created_at else None,
            "updated_at": job.updated_at.isoformat() if job.updated_at else None,
        }

    def db_row_to_job(self, row: sqlite3.Row) -> Job:
        """Converts a database row (sqlite3.Row) to a Job object."""
        data = dict(row)
        # Convert ISO format strings back to datetime objects
        data['date_found'] = datetime.fromisoformat(data['date_found']) if data.get('date_found') else None
        data['last_seen'] = datetime.fromisoformat(data['last_seen']) if data.get('last_seen') else None
        data['created_at'] = datetime.fromisoformat(data['created_at']) if data.get('created_at') else None
        data['updated_at'] = datetime.fromisoformat(data['updated_at']) if data.get('updated_at') else None
        return Job(**data)

    def insert_or_update_job(self, job: Job) -> bool:
        """
        Inserts a new job or updates an existing one if the URL already exists.
        Updates 'last_seen', 'updated_at', and non-user-managed fields.
        Preserves user-managed fields (status, priority, fit_score, etc.).
        Returns True if inserted, False if updated, None on error.
        """
        self._ensure_connected()
        db_row = self.job_to_db_row(job)
        
        # Check if job with this URL already exists
        self.cursor.execute("SELECT * FROM jobs WHERE url = ?", (job.url,))
        existing_row = self.cursor.fetchone()

        now = datetime.now(timezone.utc)
        db_row['updated_at'] = now.isoformat()
        if not job.created_at: # If creating a new job, set created_at
             db_row['created_at'] = now.isoformat()

        if existing_row:
            # Job exists, update it
            existing_job = self.db_row_to_job(existing_row)
            
            # Fields to preserve from existing job if they are not None or are user-managed.
            # date_found records when the job was FIRST seen and must survive re-fetches.
            fields_to_preserve = [
                'status', 'priority', 'fit_score', 'fit_summary', 'notes', 'notion_page_id',
                'application_status', 'application_url', 'ats_provider', 'fields_completed',
                'resume_uploaded', 'blockers', 'last_apply_attempt_at', 'apply_notes',
                'human_required_reason', 'created_at', 'date_found'
            ]
            
            for field in fields_to_preserve:
                value = getattr(existing_job, field)
                if value is not None:
                    # Convert datetime fields back to ISO strings for SQLite storage
                    if isinstance(value, datetime):
                        value = value.isoformat()
                    db_row[field] = value

            # Always update last_seen
            db_row['last_seen'] = now.isoformat()

            # Construct the UPDATE query
            update_fields = [f"{key} = :{key}" for key in db_row.keys()]
            query = f"UPDATE jobs SET {', '.join(update_fields)} WHERE url = :url"
            
            try:
                self.cursor.execute(query, db_row)
                self.conn.commit()
                return False # Updated
            except sqlite3.Error as e:
                logger.error(f"Error updating job {job.url}: {e}")
                self.conn.rollback()
                return None
        else:
            # Job does not exist, insert it
            fields = ', '.join(db_row.keys())
            placeholders = ', '.join([f":{key}" for key in db_row.keys()])
            query = f"INSERT INTO jobs ({fields}) VALUES ({placeholders})"

            try:
                self.cursor.execute(query, db_row)
                self.conn.commit()
                return True # Inserted
            except sqlite3.Error as e:
                logger.error(f"Error inserting job {job.url}: {e}")
                self.conn.rollback()
                return None

    def get_job_by_url(self, url: str) -> Optional[Job]:
        """Retrieves a single job by its URL."""
        self._ensure_connected()
        self.cursor.execute("SELECT * FROM jobs WHERE url = ?", (url,))
        row = self.cursor.fetchone()
        return self.db_row_to_job(row) if row else None

    def get_all_jobs(self, status_filter: Optional[str] = None, board_filter: Optional[str] = None) -> List[Job]:
        """Retrieves all jobs, with optional filtering by status and board."""
        self._ensure_connected()
        query = "SELECT * FROM jobs"
        conditions = []
        params = []

        if status_filter:
            conditions.append("status = ?")
            params.append(status_filter)
        if board_filter:
            conditions.append("board = ?")
            params.append(board_filter)

        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        
        query += " ORDER BY date_found DESC" # Default sort order

        try:
            self.cursor.execute(query, params)
            rows = self.cursor.fetchall()
            return [self.db_row_to_job(row) for row in rows]
        except sqlite3.Error as e:
            logger.error(f"Error retrieving jobs: {e}")
            return []

    def update_job_status(self, url: str, status: str, new_page_id: Optional[str] = None) -> bool:
        """Updates the status and optionally notion_page_id of a job.

        notion_page_id is only overwritten when new_page_id is explicitly provided.
        """
        self._ensure_connected()
        now = datetime.now(timezone.utc)
        try:
            if new_page_id is not None:
                query = "UPDATE jobs SET status = ?, updated_at = ?, notion_page_id = ? WHERE url = ?"
                self.cursor.execute(query, (status, now.isoformat(), new_page_id, url))
            else:
                query = "UPDATE jobs SET status = ?, updated_at = ? WHERE url = ?"
                self.cursor.execute(query, (status, now.isoformat(), url))
            self.conn.commit()
            return self.cursor.rowcount > 0
        except sqlite3.Error as e:
            logger.error(f"Error updating job status for {url}: {e}")
            self.conn.rollback()
            return False

    def set_notion_page_id(self, url: str, page_id: str) -> bool:
        """Persists the Notion page id for a job without touching its status."""
        self._ensure_connected()
        now = datetime.now(timezone.utc)
        try:
            self.cursor.execute(
                "UPDATE jobs SET notion_page_id = ?, updated_at = ? WHERE url = ?",
                (page_id, now.isoformat(), url),
            )
            self.conn.commit()
            return self.cursor.rowcount > 0
        except sqlite3.Error as e:
            logger.error(f"Error setting notion_page_id for {url}: {e}")
            self.conn.rollback()
            return False

    def update_job_details(self, url: str, priority: Optional[int] = None, fit_score: Optional[float] = None, fit_summary: Optional[str] = None, notes: Optional[str] = None) -> bool:
        """Updates user-managed details of a job."""
        self._ensure_connected()
        now = datetime.now(timezone.utc)
        
        # Build the SET clause dynamically
        set_clauses = ["updated_at = ?"]
        params = [now.isoformat()]
        
        if priority is not None:
            set_clauses.append("priority = ?")
            params.append(priority)
        if fit_score is not None:
            set_clauses.append("fit_score = ?")
            params.append(fit_score)
        if fit_summary is not None:
            set_clauses.append("fit_summary = ?")
            params.append(clean_text(fit_summary))
        if notes is not None:
            set_clauses.append("notes = ?")
            params.append(clean_text(notes))
            
        if len(set_clauses) < 2: # Only updated_at was changed, no meaningful data update
            return False

        query = f"UPDATE jobs SET {', '.join(set_clauses)} WHERE url = ?"
        params.append(url)

        try:
            self.cursor.execute(query, tuple(params))
            self.conn.commit()
            return self.cursor.rowcount > 0
        except sqlite3.Error as e:
            logger.error(f"Error updating job details for {url}: {e}")
            self.conn.rollback()
            return False

    def update_application_state(
        self,
        url: str,
        application_status: Optional[str] = None,
        application_url: Optional[str] = None,
        ats_provider: Optional[str] = None,
        fields_completed: Optional[str] = None,
        resume_uploaded: Optional[bool] = None,
        blockers: Optional[str] = None,
        apply_notes: Optional[str] = None,
        human_required_reason: Optional[str] = None,
        touch_attempt: bool = True,
    ) -> bool:
        """Updates auto-apply metadata for a job."""
        self._ensure_connected()
        now = datetime.now(timezone.utc)
        set_clauses = ["updated_at = ?"]
        params = [now.isoformat()]

        updates = {
            "application_status": application_status,
            "application_url": application_url,
            "ats_provider": ats_provider,
            "fields_completed": clean_text(fields_completed) if fields_completed else fields_completed,
            "resume_uploaded": int(bool(resume_uploaded)) if resume_uploaded is not None else None,
            "blockers": clean_text(blockers) if blockers else blockers,
            "apply_notes": clean_text(apply_notes) if apply_notes else apply_notes,
            "human_required_reason": clean_text(human_required_reason) if human_required_reason else human_required_reason,
        }
        for column, value in updates.items():
            if value is not None:
                set_clauses.append(f"{column} = ?")
                params.append(value)

        if touch_attempt:
            set_clauses.append("last_apply_attempt_at = ?")
            params.append(now.isoformat())

        if len(set_clauses) == 1:
            return False

        query = f"UPDATE jobs SET {', '.join(set_clauses)} WHERE url = ?"
        params.append(url)
        try:
            self.cursor.execute(query, tuple(params))
            self.conn.commit()
            return self.cursor.rowcount > 0
        except sqlite3.Error as e:
            logger.error(f"Error updating application state for {url}: {e}")
            self.conn.rollback()
            return False

    def record_application_attempt(
        self,
        job_url: str,
        attempted_at: str,
        job_id: Optional[int] = None,
        application_url: Optional[str] = None,
        ats_provider: Optional[str] = None,
        status: Optional[str] = None,
        detected_count: Optional[int] = None,
        fields_completed: Optional[str] = None,
        skipped_fields: Optional[str] = None,
        resume_uploaded: Optional[bool] = None,
        blockers: Optional[str] = None,
        human_required_reason: Optional[str] = None,
        notes: Optional[str] = None,
        review_dir: Optional[str] = None,
    ) -> Optional[int]:
        """Appends one row to the per-attempt audit trail. Returns the row id."""
        self._ensure_connected()
        try:
            self.cursor.execute(
                """
                INSERT INTO application_attempts (
                    job_id, job_url, attempted_at, application_url, ats_provider,
                    status, detected_count, fields_completed, skipped_fields,
                    resume_uploaded, blockers, human_required_reason, notes, review_dir
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    job_id, job_url, attempted_at, application_url, ats_provider,
                    status, detected_count, fields_completed, skipped_fields,
                    int(bool(resume_uploaded)) if resume_uploaded is not None else None,
                    blockers, human_required_reason, notes, review_dir,
                ),
            )
            self.conn.commit()
            return self.cursor.lastrowid
        except sqlite3.Error as e:
            logger.error(f"Error recording application attempt for {job_url}: {e}")
            self.conn.rollback()
            return None

    def get_application_attempts(self, job_url: str) -> List[Dict[str, Any]]:
        """Returns the attempt history for a job, most recent first."""
        self._ensure_connected()
        self.cursor.execute(
            "SELECT * FROM application_attempts WHERE job_url = ? ORDER BY attempted_at DESC",
            (job_url,),
        )
        return [dict(row) for row in self.cursor.fetchall()]

    def close(self):
        """Closes the database connection."""
        if self.conn:
            self.conn.close()
            self.conn = None
            self.cursor = None
