"""Title tokenization and greedy keyword clustering (pure functions)."""
from __future__ import annotations

import re

STOP_WORDS = {
    "engineer", "senior", "staff", "lead", "principal", "associate",
    "and", "of", "at", "for", "a", "an", "the", "in", "with", "applied",
}


def title_tokens(title: str) -> set[str]:
    return {
        w.lower() for w in re.split(r"[\s,/()\-@&]+", title)
        if w.lower() not in STOP_WORDS and len(w) > 2
    }


def jaccard(a: set, b: set) -> float:
    union = a | b
    return len(a & b) / len(union) if union else 0.0


def cluster_jobs(jobs: list[dict], kw_data: dict, threshold: float = 0.25) -> list[dict]:
    """
    Greedy single-linkage clustering by keyword Jaccard similarity.
    Falls back to title-token similarity when keyword data is absent.
    Returns [{"label": str, "keywords": list[str], "jobs": list[dict]}, ...].
    """
    if not jobs:
        return []

    features = [
        kw_data.get(j["url"]) or title_tokens(j["title"])
        for j in jobs
    ]

    n = len(jobs)
    assigned = [-1] * n
    clusters = []

    for i in range(n):
        if assigned[i] != -1:
            continue
        cid = len(clusters)
        assigned[i] = cid
        members = [i]

        for j in range(i + 1, n):
            if assigned[j] != -1:
                continue
            if jaccard(features[i], features[j]) >= threshold:
                assigned[j] = cid
                members.append(j)

        # Label: terms shared across every member; fall back to title tokens
        shared = set.intersection(*(features[m] for m in members))
        if not shared:
            title_sets = [title_tokens(jobs[m]["title"]) for m in members]
            shared = set.intersection(*title_sets) if title_sets else set()

        label_terms = sorted(shared - STOP_WORDS)[:4]
        label = " · ".join(t.title() for t in label_terms) or jobs[members[0]]["title"]

        clusters.append({
            "label": label,
            "jobs": [jobs[m] for m in members],
            "keywords": sorted(shared)[:8],
        })

    # Highest-priority cluster first
    clusters.sort(key=lambda c: -max((j["priority"] or 0) for j in c["jobs"]))
    return clusters
