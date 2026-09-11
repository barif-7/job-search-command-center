# Configuration for the Job Search Command Center
import sys
from pathlib import Path

# ── Paths ──────────────────────────────────────────────────────────────────

_HERE = Path(__file__).parent

# Pull company lists from careerBoards.py (project-local copy)
sys.path.insert(0, str(_HERE))
try:
    from careerBoards import GREENHOUSE, LEVER, ASHBY
except ImportError:
    GREENHOUSE: dict = {}
    LEVER: dict = {}
    ASHBY: dict = {}

# Paths, credentials, and feature toggles live in jobsearch.settings
# (env + .env). This module holds only static domain configuration.

# ── HTTP ───────────────────────────────────────────────────────────────────

REQUEST_TIMEOUT = 10
USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"

# ── Role keywords (case-insensitive substring match on job title) ───────────
# Broadened 2026-09-02 from iOS-only to general software engineering.

ROLE_KEYWORDS = [
    # iOS / mobile
    "ios engineer",
    "ios developer",
    "ios software engineer",
    "mobile engineer",
    "mobile developer",
    "software engineer, ios",
    "software engineer ios",
    # Titles that put the platform after the role or in parens — e.g.
    # "Senior Software Engineer (iOS), SDK", "Principal Engineer, iOS
    # Performance", "Senior/Staff Design Engineer, iOS".
    "engineer, ios",
    "engineer (ios)",
    "engineer - ios",
    "ios/android",
    "engineer, mobile",
    "swift engineer",
    # AI / ML
    "ai engineer",
    "applied ai",
    "ai product engineer",
    "ml engineer",
    "machine learning engineer",
    "forward deployed engineer",
    # Product
    "product engineer",
    "product growth engineer",
    # Backend / platform / infrastructure
    "backend engineer",
    "back-end engineer",
    "backend software engineer",
    "platform engineer",
    "infrastructure engineer",
    "distributed systems engineer",
    "systems engineer",
    # Full-stack / frontend
    "full stack engineer",
    "full-stack engineer",
    "fullstack engineer",
    "frontend engineer",
    "front-end engineer",
    "web engineer",
    # Generic — catches "Senior Software Engineer, Payments" and similar
    # titles that name no specialty. ROLE_EXCLUSIONS keeps these to IC roles.
    "software engineer",
    "software developer",
    "staff engineer",
    "senior engineer",
    "principal engineer",
    'ai platform engineer',
    'llm platform',
    'ai infrastructure',
    'ml infrastructure',
    'ml infra',
    'mlops',
    'ml ops',
    'ai systems engineer',
    'llm ops',
    'inference engineer',
    'model serving',
    'rag engineer',
    'retrieval engineer',
    'knowledge retrieval',
    'search engineer',
    'vector search',
    'agentic',
    'agent orchestration',
    'ai agent',
    'agent engineer',
    'tool use',
    'speech engineer',
    'speech ai',
    'multimodal',
    'asr',
    'tts',
]

# ── Role exclusions — dropped even when a ROLE_KEYWORD matches ──────────────
# The generic keywords above otherwise sweep in people-management, early
# career, and customer-facing titles that are not IC software engineering.

ROLE_EXCLUSIONS = [
    "manager",
    "director",
    "head of",
    "vp,",
    "vp of",
    "vice president",
    "intern",
    "internship",
    "new grad",
    "new graduate",
    "co-op",
    "apprentice",
    "sales engineer",
    "solutions engineer",
    "support engineer",
    "recruiter",
    "technical recruiter",
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

# ── Auto-apply metadata ───────────────────────────────────────────────────

APPLICATION_STATUSES = [
    "NOT_STARTED",
    "QUEUED",
    "OPENED",
    "FILLED_PARTIALLY",
    "READY_FOR_REVIEW",
    "READY_TO_SUBMIT",
    "SUBMITTED",
    "BLOCKED",
    "SKIPPED",
]


SEARCH_PRESETS = {
    "ai_platform": {
        "label": "AI Platform / MLOps",
        "title_keywords": [
            "ai platform",
            "llm platform",
            "ai infrastructure",
            "ml infrastructure",
            "mlops",
            "ml ops",
            "ai systems",
            "inference",
            "model serving",
        ],
        "description": "Private/edge inference, GPU orchestration, model gateways, serving reliability",
    },
    "rag_retrieval": {
        "label": "RAG / Retrieval",
        "title_keywords": [
            "rag",
            "retrieval",
            "knowledge",
            "vector search",
            "search engineer",
            "embeddings",
        ],
        "description": "Vector + hybrid search, evaluation harnesses, embedding pipelines",
    },
    "agentic": {
        "label": "Agentic / Agent Orchestration",
        "title_keywords": [
            "agentic",
            "agent orchestration",
            "ai agent",
            "agent engineer",
            "tool use",
            "multi-agent",
        ],
        "description": "Tool-calling agents, MCP-style surfaces, workflow orchestration",
    },
    "applied_ai": {
        "label": "Applied AI / Generative",
        "title_keywords": [
            "applied ai",
            "generative ai",
            "llm engineer",
            "ai engineer",
            "genai",
        ],
        "description": "Shipping LLM features, localization, speech, product-facing AI",
    },
    "speech_multimodal": {
        "label": "Speech / Multimodal",
        "title_keywords": [
            "speech",
            "asr",
            "tts",
            "multimodal",
            "voice ai",
            "audio ai",
        ],
        "description": "STT/TTS, timed captions, lyric/localization pipelines",
    },
}
