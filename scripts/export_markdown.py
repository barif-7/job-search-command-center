import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from jobsearch.settings import get_settings
from jobsearch.store import JobStore

MARKDOWN_EXPORT_PATH = get_settings().markdown_export_path

store = JobStore()
jobs = store.get_all_jobs()

lines = []
groups = {}
for job in jobs:
    groups.setdefault(job.status or "Unknown", []).append(job)

for status, group in sorted(groups.items()):
    lines.append(f"\n## {status}\n")
    for j in group:
        date_str = j.date_found.strftime("%Y-%m-%d") if j.date_found else "?"
        lines.append(f"- **[{j.company}]** {j.title} — {j.location} ({j.board}, {date_str})")
        lines.append(f"  {j.url}")
        if j.notes:
            lines.append(f"  _Notes: {j.notes}_")
        lines.append("")

export_path = Path(MARKDOWN_EXPORT_PATH)
export_path.write_text("# Job Search Results\n" + "\n".join(lines))
print(f"Exported {len(jobs)} jobs to {export_path}")
