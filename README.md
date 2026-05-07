# Job Search Command Center

A local job search pipeline and dashboard for tracking iOS/AI engineering roles. Fetches live postings from Greenhouse, Lever, and Ashby; stores them in SQLite; and surfaces everything through a Streamlit dashboard with three card views, structured filters, AI-powered summaries, and optional Notion sync.

---

## Requirements

- Python 3.11+
- [Streamlit](https://streamlit.io)
- A terminal and a browser

---

## Installation

**1. Clone the repo**

```bash
git clone https://github.com/barif-7/job-search-command-center.git
cd job-search-command-center
```

**2. Create and activate a virtual environment**

```bash
python3 -m venv venv
source venv/bin/activate        # macOS / Linux
# venv\Scripts\activate         # Windows
```

**3. Install dependencies**

```bash
pip install -r requirements.txt
```

**4. Set up environment variables** _(optional — only needed for AI summaries or Notion sync)_

```bash
cp .env.example .env
```

Then edit `.env`:

```env
ANTHROPIC_API_KEY=sk-ant-...          # for AI summaries in the dashboard
LOGO_DEV_TOKEN=pk_...                 # for higher-quality company logos (logo.dev)
NOTION_API_KEY=secret_...            # for Notion sync
NOTION_JOBS_DATABASE_ID=...          # Notion database ID
ENABLE_NOTION_SYNC=false
```

All variables are optional. The dashboard runs without any of them.

---

## Running the app

**Launch the dashboard**

```bash
streamlit run app.py
```

Opens at `http://localhost:8501`. The dashboard has three tabs:

| Tab | What it does |
|-----|-------------|
| **Dashboard** | Metrics, top opportunities, editable job tracker table |
| **Opportunity Feed** | Card-based feed with filters, search, and 3 view modes |
| **AI Summary** | Claude-powered briefing of your full job search document |

---

## Fetching jobs

Jobs can be fetched from inside the dashboard (click **Fetch new jobs**) or directly from the CLI:

```bash
python scripts/run_fetch.py
```

This pulls from all configured Greenhouse, Lever, and Ashby boards defined in `careerBoards.py` and stores results in `data/jobs.db`.

---

## Other scripts

| Script | Description |
|--------|-------------|
| `scripts/export_markdown.py` | Export tracked jobs to `job-search-results.md` |
| `scripts/sync_notion.py` | Sync jobs to a Notion database (requires `.env` config) |

---

## Configuration

**`config.py`** — edit to customize:

- `ROLE_KEYWORDS` — job title substrings to match (e.g. `"ios engineer"`, `"ml engineer"`)
- `LOCATION_KEYWORDS` — locations to include (e.g. `"san francisco"`, `"remote"`)
- `JOB_STATUSES` / `JOB_PRIORITIES` — pipeline stages and priority scale

**`careerBoards.py`** — three dicts (`GREENHOUSE`, `LEVER`, `ASHBY`) mapping company slugs to display names. Add or remove companies here to control which boards are fetched.

---

## Running tests

```bash
pytest
```

---

## Project structure

```
job-search-command-center/
├── app.py                  # Streamlit dashboard (main entry point)
├── config.py               # Global config — keywords, paths, board URLs
├── careerBoards.py         # Company lists per job board
├── requirements.txt
├── data/
│   └── jobs.db             # SQLite database (auto-created on first fetch)
├── jobsearch/
│   ├── models.py           # Job dataclass
│   ├── store.py            # SQLite read/write layer
│   ├── fetcher.py          # Async fetch orchestrator
│   ├── utils.py            # Location normalizer, date parser, URL validator
│   └── boards/
│       ├── greenhouse.py   # Greenhouse API fetcher
│       ├── lever.py        # Lever API fetcher
│       └── ashby.py        # Ashby HTML scraper
├── scripts/
│   ├── run_fetch.py        # CLI: fetch and store jobs
│   ├── export_markdown.py  # CLI: export DB to markdown
│   └── sync_notion.py      # CLI: sync to Notion
└── tests/
    ├── test_store.py
    ├── test_filters.py
    └── test_dedupe.py
```
