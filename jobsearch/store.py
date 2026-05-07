import logging
import sqlite3
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any

from .models import Job
from .utils import clean_text
from config import DATABASE_PATH

logger = logging.getLogger(__name__)

class JobStore:
    def __init__(self, db_path: str = DATABASE_PATH):
        self.db_path = db_path
        self.conn = None
        self.cursor = None
        self._ensure_connected()
        self.create_tables()

    def _ensure_connected(self):
        if self.conn is None:
            from pathlib import Path
            Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
            self.conn = sqlite3.connect(self.db_path)
            self.conn.row_factory = sqlite3.Row # Access columns by name
            self.cursor = self.conn.cursor()

    def create_tables(self):
        """Creates the jobs table if it doesn't exist."""
        query = """
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
            created_at TEXT,
            updated_at TEXT
        );
        """
        try:
            self._ensure_connected()
            self.cursor.execute(query)
            self.conn.commit()
        except sqlite3.Error as e:
            logger.error(f"Error creating tables: {e}")

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
            
            # Fields to preserve from existing job if they are not None or are user-managed
            fields_to_preserve = [
                'status', 'priority', 'fit_score', 'fit_summary', 'notes', 'notion_page_id', 'created_at'
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

    def close(self):
        """Closes the database connection."""
        if self.conn:
            self.conn.close()
            self.conn = None
            self.cursor = None

