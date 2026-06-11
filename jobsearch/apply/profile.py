from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from jobsearch.settings import get_settings

APPLY_DIR = Path(get_settings().apply_input_dir)
PROFILE_PATH = APPLY_DIR / "candidate_profile.json"
RESUME_PDF_PATH = APPLY_DIR / "resume_master.pdf"
RESUME_TXT_PATH = APPLY_DIR / "resume_master.txt"
QA_PATH = APPLY_DIR / "qa.json"
CONSTRAINTS_PATH = APPLY_DIR / "constraints.json"

DEFAULT_PROFILE: dict[str, Any] = {
    "full_name": "",
    "first_name": "",
    "last_name": "",
    "email": "",
    "phone": "",
    "linkedin_url": "",
    "github_url": "",
    "portfolio_url": "",
    "website_url": "",
    "location_city": "",
    "location_region": "",
    "location_country": "",
    "current_company": "",
    "additional_information": "",
    "checkbox_answers": {},
    "radio_answers": {},
}


def ensure_apply_dir() -> None:
    APPLY_DIR.mkdir(parents=True, exist_ok=True)


def load_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def save_json(path: Path, data: Any) -> None:
    ensure_apply_dir()
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def load_candidate_profile(path: Path = PROFILE_PATH) -> dict[str, Any]:
    profile = load_json(path, {})
    changed = False
    for key, value in DEFAULT_PROFILE.items():
        if key not in profile:
            profile[key] = value
            changed = True

    if not profile.get("full_name") and profile.get("name"):
        profile["full_name"] = profile["name"]
        changed = True
    if not profile.get("name") and profile.get("full_name"):
        profile["name"] = profile["full_name"]
        changed = True
    if not profile.get("location"):
        parts = [profile.get("location_city"), profile.get("location_region"), profile.get("location_country")]
        location = ", ".join(p for p in parts if p)
        if location:
            profile["location"] = location
            changed = True
    if "linkedin" not in profile:
        profile["linkedin"] = profile.get("linkedin_url", "")
        changed = True
    if "github" not in profile:
        profile["github"] = profile.get("github_url", "")
        changed = True
    if "portfolio" not in profile:
        profile["portfolio"] = profile.get("portfolio_url") or profile.get("website_url", "")
        changed = True

    if changed:
        save_json(path, profile)
    return profile


def profile_readiness() -> dict[str, Any]:
    profile = load_candidate_profile()
    required = ["full_name", "first_name", "last_name", "email", "phone", "location"]
    missing = [field for field in required if not profile.get(field)]
    return {
        "apply_dir": str(APPLY_DIR),
        "profile_exists": PROFILE_PATH.exists(),
        "resume_pdf_exists": RESUME_PDF_PATH.exists(),
        "resume_txt_exists": RESUME_TXT_PATH.exists(),
        "qa_exists": QA_PATH.exists(),
        "constraints_exists": CONSTRAINTS_PATH.exists(),
        "missing_profile_fields": missing,
        "ready_for_fill": not missing,
    }

