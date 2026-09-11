# Re-export static config values from the root config module for
# package-level access. Runtime settings (paths, credentials, toggles)
# live in jobsearch.settings.
from config import (
    LOCATION_KEYWORDS,
    ROLE_KEYWORDS,
    SEARCH_PRESETS,
    REQUEST_TIMEOUT,
    DEFAULT_BOARD_CONFIG,
    JOB_STATUSES,
    JOB_PRIORITIES,
    APPLICATION_STATUSES,
    USER_AGENT,
)

# Alias for backwards compatibility
DEFAULT_LOCATIONS = LOCATION_KEYWORDS

