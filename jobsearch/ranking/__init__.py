"""Filtering, clustering, and keyword-loading logic extracted from the UI.

Pure functions over plain job dicts — no Streamlit. ``load_keyword_data`` is
the one I/O helper and takes an explicit path.
"""
from jobsearch.ranking.clustering import (
    STOP_WORDS,
    cluster_jobs,
    jaccard,
    title_tokens,
)
from jobsearch.ranking.filters import apply_filters
from jobsearch.ranking.keywords import load_keyword_data
from jobsearch.ranking.fit import rank_jobs_by_fit, score_job_fit

__all__ = [
    "STOP_WORDS",
    "cluster_jobs",
    "jaccard",
    "title_tokens",
    "apply_filters",
    "load_keyword_data",
    "score_job_fit",
    "rank_jobs_by_fit",
]

