# Re-export all config values from the root config module for package-level access.
from config import (
    LOCATION_KEYWORDS,
    ROLE_KEYWORDS,
    DATABASE_PATH,
    MARKDOWN_EXPORT_PATH,
    NOTION_API_KEY,
    NOTION_JOBS_DATABASE_ID,
    ENABLE_NOTION_SYNC,
    REQUEST_TIMEOUT,
    DEFAULT_BOARD_CONFIG,
    JOB_STATUSES,
    JOB_PRIORITIES,
    OPENAI_API_KEY,
    USER_AGENT,
)

# Alias for backwards compatibility
DEFAULT_LOCATIONS = LOCATION_KEYWORDS
