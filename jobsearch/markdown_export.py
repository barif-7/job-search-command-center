from jobsearch.store import JobStore
from datetime import datetime

class MarkdownExporter:
    def __init__(self, store: JobStore):
        self.store = store

    def render_job(self, j):
        return f"- [{j.company}] {j.title} - {j.location} ({j.board})\\n  {j.url}\\n"

    def export(self, group_by: str = 'status'):
        jobs = self.store.get_all_jobs()
        groups = {}
        for j in jobs:
            key = getattr(j, group_by, 'Unknown')
            groups.setdefault(key, []).append(j)
        lines = []
        for k, lst in groups.items():
            lines.append(f"## {k}\n")
            for j in lst:
                lines.append(self.render_job(j))
                lines.append("")
        with open("job-search-results.md", "w") as f:
            f.write("# Job Search Results\n\n" + "\n".join(lines))
        return len(jobs)
