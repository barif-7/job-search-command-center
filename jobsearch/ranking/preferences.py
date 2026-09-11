"""Profile-owned search preferences; built-in presets are editable starting points."""
from copy import deepcopy
import json
from pathlib import Path

from config import SEARCH_PRESETS
from jobsearch.apply.profile import PROFILE_PATH
from jobsearch.ranking.fit import rank_jobs_by_fit


def load_preferences(path: Path = PROFILE_PATH) -> dict:
    profile = json.loads(path.read_text()) if path.exists() else {}
    return {
        'search_presets': deepcopy(profile.get('search_presets', SEARCH_PRESETS)),
        'profile_signals': profile.get('profile_signals', []),
        'target_presets': profile.get('target_presets', []),
        'filter_by_presets': profile.get('filter_by_presets', False),
        'sort_by_fit': profile.get('sort_by_fit', False),
    }


def save_preferences(preferences: dict, path: Path = PROFILE_PATH) -> None:
    presets = preferences['search_presets']
    if not isinstance(presets, dict):
        raise ValueError('Presets must be a mapping.')
    for key, preset in presets.items():
        if not key.strip() or not preset['label'].strip() or not preset['title_keywords']:
            raise ValueError('Each preset needs an ID, label, and at least one keyword.')
    if any(key not in presets for key in preferences['target_presets']):
        raise ValueError('Selected presets must exist.')
    # Read the latest profile so application/contact fields are preserved.
    profile = json.loads(path.read_text()) if path.exists() else {}
    profile.update(preferences)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix('.json.tmp')
    temp.write_text(json.dumps(profile, indent=2, ensure_ascii=False) + '\n')
    temp.replace(path)


def apply_preferences(jobs: list[dict], preferences: dict) -> list[dict]:
    presets = preferences['search_presets']
    keys = preferences['target_presets']
    if preferences['filter_by_presets'] and keys:
        words = [word.lower() for key in keys for word in presets.get(key, {}).get('title_keywords', [])]
        jobs = [job for job in jobs if any(word in str(job.get('title') or '').lower() for word in words)]
    if preferences['sort_by_fit']:
        jobs = rank_jobs_by_fit(jobs, preferences['profile_signals'], keys, presets)
    return jobs
