import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from jobsearch.store import JobStore

store = JobStore()
jobs = store.get_all_jobs()

lines = []
for j in jobs:
    lines.append(f"- [{j.company}] {j.title} - {j.location} ({j.board})\n  {j.url}\n")

Path("job-search-results.md").write_text("# Job Search Results\n\n" + "\n".join(lines))
print("Exported", len(lines), "jobs to job-search-results.md")
