from __future__ import annotations

from urllib.parse import urlparse


def detect_ats_provider(url: str, board: str = "") -> str:
    host = urlparse(url or "").netloc.lower()
    board_l = (board or "").lower()
    if "lever.co" in host or board_l == "lever":
        return "Lever"
    if "ashbyhq.com" in host or board_l == "ashby":
        return "Ashby"
    if "greenhouse.io" in host or board_l == "greenhouse":
        return "Greenhouse"
    if "ycombinator.com" in host:
        return "Y Combinator"
    return "Unknown"


def resolve_application_url(job_url: str, board: str = "") -> str:
    """Best-effort application URL resolution for common ATS providers."""
    url = (job_url or "").strip()
    if not url:
        return ""

    provider = detect_ats_provider(url, board)
    if provider == "Lever" and not url.rstrip("/").endswith("/apply"):
        return url.rstrip("/") + "/apply"
    if provider == "Ashby" and not url.rstrip("/").endswith("/application"):
        return url.rstrip("/") + "/application"
    return url


def classify_blocker(text: str, frame_urls: list[str] | None = None) -> str | None:
    hay = " ".join([text or "", " ".join(frame_urls or [])]).lower()
    checks = {
        "captcha": ["hcaptcha", "captcha", "recaptcha", "verify you are human", "anti-bot"],
        "otp": ["one-time passcode", "one time passcode", "verification code", "enter code"],
        "forced_account": ["sign in to apply", "create an account", "log in to apply"],
        "closed": ["job is no longer available", "position has been filled", "job has been closed"],
    }
    for blocker, markers in checks.items():
        if any(marker in hay for marker in markers):
            return blocker
    return None

