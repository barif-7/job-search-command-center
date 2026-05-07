# Configuration for the Job Search Command Center
import sys
from pathlib import Path

# ── Paths ──────────────────────────────────────────────────────────────────

_HERE = Path(__file__).parent

# Pull company lists from the workspace-level careerBoards.py
sys.path.insert(0, str(_HERE.parent))
try:
    from careerBoards import GREENHOUSE, LEVER, ASHBY
except ImportError:
    GREENHOUSE: dict = {}
    LEVER: dict = {}
    ASHBY: dict = {}

# ── Database ───────────────────────────────────────────────────────────────

DATABASE_PATH = str(_HERE / "data" / "jobs.db")

# ── Markdown export ────────────────────────────────────────────────────────

MARKDOWN_EXPORT_PATH = str(_HERE.parent / "job-search-results.md")

# ── Notion (disabled by default) ───────────────────────────────────────────

NOTION_API_KEY = ""
NOTION_JOBS_DATABASE_ID = ""
ENABLE_NOTION_SYNC = False

# ── HTTP ───────────────────────────────────────────────────────────────────

REQUEST_TIMEOUT = 10
USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"

# ── Role keywords (case-insensitive substring match on job title) ───────────

ROLE_KEYWORDS = [
    "ios engineer",
    "ios developer",
    "ios software engineer",
    "mobile engineer",
    "mobile developer",
    "software engineer, ios",
    "software engineer ios",
    "swift engineer",
    "ai engineer",
    "applied ai",
    "ai product engineer",
    "ml engineer",
    "machine learning engineer",
    "product engineer",
    "product growth engineer",
    "forward deployed engineer",
]

# ── Location keywords — only keep postings that mention at least one ────────

LOCATION_KEYWORDS = [
    "san francisco",
    "new york",
    "nyc",
    "seattle",
    "toronto",
    "vancouver",
    "remote",
    "canada",
    "california",
    "ontario",
    "british columbia",
    "palo alto",
    "bellevue",
    "montreal",
]

# ── Board configuration ────────────────────────────────────────────────────
# Each board entry is passed as `config` to its fetcher's fetch() method.

DEFAULT_BOARD_CONFIG = {
    "greenhouse": {
        "api_base": "https://boards-api.greenhouse.io/v1/boards",
        "companies": GREENHOUSE,
    },
    "lever": {
        "api_base": "https://api.lever.co/v0/postings",
        "companies": LEVER,
    },
    "ashby": {
        "api_base": "https://jobs.ashbyhq.com",
        "companies": ASHBY,
    },
}

# ── Job tracking metadata ──────────────────────────────────────────────────

JOB_STATUSES = [
    "New",
    "Saved",
    "Interested",
    "Applied",
    "Interviewing",
    "Offer",
    "Rejected",
    "Archived",
]

JOB_PRIORITIES = [1, 2, 3, 4, 5]

# ── AI fit scoring (optional) ──────────────────────────────────────────────

OPENAI_API_KEY = ""
