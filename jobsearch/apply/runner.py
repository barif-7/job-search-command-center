from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from config import APPLY_INPUT_DIR
from jobsearch.apply.ats import classify_blocker, detect_ats_provider, resolve_application_url
from jobsearch.apply.field_matching import collect_visible_fields, fill_boolean_answers, fill_text_if_possible
from jobsearch.apply.profile import RESUME_PDF_PATH, load_candidate_profile
from jobsearch.apply.results import ApplyResult
from jobsearch.models import Job
from jobsearch.store import JobStore

RESULTS_DIR = Path(APPLY_INPUT_DIR) / "results"


def build_apply_queue(
    store: JobStore,
    status: str | None = None,
    min_priority: int | None = None,
    limit: int = 5,
    job_id: int | None = None,
) -> list[Job]:
    jobs = store.get_all_jobs()
    allowed_statuses = {"New", "Saved", "Interested"}
    blocked_application_statuses = {"BLOCKED", "SUBMITTED", "SKIPPED"}
    queue: list[Job] = []

    for job in jobs:
        if job_id is not None and job.id != job_id:
            continue
        if status and job.status != status:
            continue
        if not status and (job.status or "New") not in allowed_statuses:
            continue
        if min_priority is not None and (job.priority or 0) < min_priority:
            continue
        if (job.application_status or "NOT_STARTED") in blocked_application_statuses:
            continue
        if not job.url:
            continue
        queue.append(job)

    return queue[: max(1, limit)]


def preview_queue(jobs: list[Job]) -> list[dict[str, Any]]:
    return [
        {
            "id": job.id,
            "company": job.company,
            "title": job.title,
            "status": job.status,
            "priority": job.priority,
            "board": job.board,
            "ats_provider": detect_ats_provider(job.url, job.board),
            "application_url": resolve_application_url(job.url, job.board),
        }
        for job in jobs
    ]


def visible_text(page) -> str:
    try:
        return page.locator("body").inner_text(timeout=5000)
    except Exception:
        return ""


def frame_urls(page) -> list[str]:
    urls = []
    for frame in page.frames:
        try:
            urls.append(frame.url)
        except Exception:
            continue
    return urls


def upload_resume_if_present(frame):
    selectors = [
        "input[type='file']",
        "input[accept*='pdf']",
        "input[name*='resume' i]",
        "input[id*='resume' i]",
        "input[name*='cv' i]",
        "input[id*='cv' i]",
    ]
    for selector in selectors:
        try:
            count = frame.locator(selector).count()
        except Exception:
            continue
        for i in range(count):
            try:
                el = frame.locator(selector).nth(i)
                if not el.is_visible() or not el.is_enabled() or el.get_attribute("type") == "hidden":
                    continue
                if not RESUME_PDF_PATH.exists():
                    return False, f"resume file missing: {RESUME_PDF_PATH}"
                el.set_input_files(str(RESUME_PDF_PATH))
                return True, ""
            except Exception:
                continue
    return False, ""


def fill_page_safely(page, profile: dict[str, Any]) -> dict[str, Any]:
    frames = [page] + [f for f in page.frames if f != page.main_frame]
    detected = []
    filled = []
    skipped = []
    profile_location = profile.get("location") or ", ".join(
        p for p in [profile.get("location_city"), profile.get("location_region"), profile.get("location_country")] if p
    )
    portfolio = profile.get("portfolio_url") or profile.get("website_url") or profile.get("portfolio") or ""
    mapping = [
        {"key": "full_name", "value": profile.get("full_name") or profile.get("name", ""), "hints": ["name", "full name", "candidate name"]},
        {"key": "first_name", "value": profile.get("first_name", ""), "hints": ["first name", "given name"]},
        {"key": "last_name", "value": profile.get("last_name", ""), "hints": ["last name", "family name", "surname"]},
        {"key": "email", "value": profile.get("email", ""), "hints": ["email", "e-mail"]},
        {"key": "phone", "value": profile.get("phone", ""), "hints": ["phone", "mobile", "telephone"]},
        {"key": "location", "value": profile_location, "hints": ["location", "city", "address", "country"]},
        {"key": "linkedin_url", "value": profile.get("linkedin_url") or profile.get("linkedin", ""), "hints": ["linkedin"]},
        {"key": "github_url", "value": profile.get("github_url") or profile.get("github", ""), "hints": ["github"]},
        {"key": "portfolio_url", "value": portfolio, "hints": ["portfolio", "website", "url", "link"]},
        {"key": "current_company", "value": profile.get("current_company", ""), "hints": ["company", "organization", "employer"]},
        {"key": "additional_information", "value": profile.get("additional_information", ""), "hints": ["comments", "additional information", "cover letter", "message"], "kinds": ("textareas", "inputs")},
    ]

    for frame in frames:
        for bucket in ("inputs", "textareas", "selects", "radios", "buttons"):
            detected.extend(collect_visible_fields(frame).get(bucket, []))

    for item in mapping:
        value = item["value"]
        if not value:
            skipped.append({"field": item["key"], "reason": "empty profile value"})
            continue
        done = False
        for frame in frames:
            ok, attrs = fill_text_if_possible(frame, item["hints"], value, kinds=item.get("kinds", ("inputs", "textareas", "selects")))
            if ok:
                filled.append({"field": item["key"], "value": value, "matched": attrs})
                done = True
                break
        if not done:
            skipped.append({"field": item["key"], "reason": "no confident visible match"})

    for frame in frames:
        bool_filled, bool_skipped = fill_boolean_answers(
            frame,
            profile.get("checkbox_answers", {}) or {},
            profile.get("radio_answers", {}) or {},
        )
        filled.extend(bool_filled)
        skipped.extend(bool_skipped)

    resume_uploaded = False
    upload_error = ""
    for frame in frames:
        resume_uploaded, upload_error = upload_resume_if_present(frame)
        if resume_uploaded or upload_error:
            break

    return {
        "detected_count": len(detected),
        "filled": filled,
        "skipped": skipped,
        "resume_uploaded": resume_uploaded,
        "upload_error": upload_error,
    }


def run_apply_batch(
    store: JobStore,
    jobs: list[Job],
    headless: bool = False,
) -> list[ApplyResult]:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise RuntimeError("Playwright is not installed. Run `pip install -r requirements.txt` and `python -m playwright install chromium`.") from exc

    profile = load_candidate_profile()
    results: list[ApplyResult] = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        context = browser.new_context(viewport={"width": 1440, "height": 1800})
        for job in jobs:
            app_url = resolve_application_url(job.url, job.board)
            provider = detect_ats_provider(app_url, job.board)
            result = ApplyResult(
                job_id=job.id,
                company=job.company,
                title=job.title,
                job_url=job.url,
                application_url=app_url,
                ats_provider=provider,
                status="OPENED",
            )
            page = context.new_page()
            try:
                page.goto(app_url, wait_until="domcontentloaded", timeout=30000)
                page.wait_for_timeout(2000)
                blocker = classify_blocker(visible_text(page), frame_urls(page))
                if blocker:
                    result.status = "BLOCKED" if blocker != "closed" else "SKIPPED"
                    result.blockers.append(blocker)
                    result.human_required_reason = blocker
                else:
                    filled = fill_page_safely(page, profile)
                    result.fields_completed = [item["field"] for item in filled["filled"]]
                    result.resume_uploaded = bool(filled["resume_uploaded"])
                    if filled["upload_error"]:
                        result.notes.append(filled["upload_error"])
                    if result.fields_completed or result.resume_uploaded:
                        result.status = "READY_FOR_REVIEW"
                        result.human_required_reason = "final submit approval"
                    else:
                        result.status = "FILLED_PARTIALLY"
                        result.human_required_reason = "manual review required"
            except Exception as exc:
                result.status = "BLOCKED"
                result.blockers.append("automation_error")
                result.human_required_reason = "automation error"
                result.notes.append(str(exc))
            finally:
                store.update_application_state(
                    job.url,
                    application_status=result.status,
                    application_url=result.application_url,
                    ats_provider=result.ats_provider,
                    fields_completed=", ".join(result.fields_completed),
                    resume_uploaded=result.resume_uploaded,
                    blockers=", ".join(result.blockers),
                    apply_notes="; ".join(result.notes),
                    human_required_reason=result.human_required_reason,
                )
                results.append(result)
        browser.close()
    save_results(results)
    return results


def save_results(results: list[ApplyResult]) -> Path:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = RESULTS_DIR / f"apply_results_{stamp}.json"
    path.write_text(json.dumps([r.to_dict() for r in results], indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return path

