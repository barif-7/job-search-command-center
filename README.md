# Job Search Command Center

This project is a local job-search dashboard that helps you manage your job applications. It includes a job fetcher, SQLite database, Streamlit dashboard, and optional Notion sync.

## Setup

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd job-search-command-center
   ```

2. **Create a virtual environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables (optional):**
   Copy `.env.example` to `.env` and fill in your Notion API key and database ID if you plan to use Notion sync.

   ```bash
   cp .env.example .env
   ```
   Update the `.env` file with your credentials:
   ```
   NOTION_API_KEY=your_notion_api_key
   NOTION_JOBS_DATABASE_ID=your_notion_database_id
   ENABLE_NOTION_SYNC=true  # or false
   ```

## Usage

### Fetch Jobs

To fetch jobs from Greenhouse, Lever, and Ashby, run:

```bash
python scripts/run_fetch.py
```

This will populate the `data/jobs.db` SQLite database.

### Launch Dashboard

To start the Streamlit dashboard, run:

```bash
streamlit run app.py
```

### Export to Markdown

To export current job data to a Markdown file (`job-search-results.md`):

```bash
python scripts/export_markdown.py
```

### Sync to Notion

To sync jobs to Notion (if configured in `.env`):

```bash
python scripts/sync_notion.py
```

## Configuration

- **`config.py`**: Contains general configuration, including default locations and role keywords.
- **`.env`**: Contains sensitive credentials like Notion API keys.

## Database Schema

The `data/jobs.db` SQLite database stores job information. Key fields include:

- `id` (INTEGER PRIMARY KEY AUTOINCREMENT)
- `company` (TEXT)
- `title` (TEXT)
- `location` (TEXT)
- `normalized_location` (TEXT)
- `url` (TEXT UNIQUE)
- `board` (TEXT)
- `description` (TEXT)
- `compensation` (TEXT)
- `date_found` (TEXT)
- `last_seen` (TEXT)
- `status` (TEXT)
- `priority` (INTEGER)
- `fit_score` (REAL)
- `fit_summary` (TEXT)
- `notes` (TEXT)
- `notion_page_id` (TEXT)
- `created_at` (TEXT)
- `updated_at` (TEXT)

## Future Work

- **AI Fit Scoring**: Integrate LLM-based scoring for job relevance.
- **FastAPI Backend**: Expose job data via a FastAPI service for a potential mobile app.
