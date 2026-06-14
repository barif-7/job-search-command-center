"""Company → domain → logo-URL resolution (pure, UI-agnostic).

Builds a prioritized list of logo candidate URLs so the frontend can fall back
gracefully when one fails to load. The logo.dev token is read from settings at
import time, matching the original in-app behavior; tests may override the
module-level ``LOGO_DEV_TOKEN`` to exercise the token path.
"""
from __future__ import annotations

import re
from urllib.parse import urlparse

from jobsearch.settings import get_settings

# ── Company → domain mapping (for logo providers) ─────────────────────────

COMPANY_DOMAINS: dict[str, str] = {
    "Anthropic":              "anthropic.com",
    "OpenAI":                 "openai.com",
    "Perplexity":             "perplexity.ai",
    "Reddit":                 "reddit.com",
    "Strava":                 "strava.com",
    "Mercury":                "mercury.com",
    "Gusto":                  "gusto.com",
    "Headway":                "headway.com",
    "AssemblyAI":             "assemblyai.com",
    "Automattic":             "automattic.com",
    "Tailscale":              "tailscale.com",
    "HeyGen":                 "heygen.com",
    "Speechify":              "speechify.com",
    "Luma AI":                "lumalabs.ai",
    "EarnIn":                 "earnin.com",
    "MyFitnessPal":           "myfitnesspal.com",
    "Faire":                  "faire.com",
    "TouchBistro":            "touchbistro.com",
    "Warp":                   "warp.dev",
    "Notion":                 "notion.so",
    "Figma":                  "figma.com",
    "xAI":                    "x.ai",
    "The New York Times":     "nytimes.com",
    "DoorDash USA":           "doordash.com",
    "Canonical":              "canonical.com",
    "GitLab":                 "gitlab.com",
    "The Trade Desk":         "thetradedesk.com",
    "MLB":                    "mlb.com",
    "Breeze Airways":         "flybreeze.com",
    "Impact.com":             "impact.com",
    "Wealthsimple":           "wealthsimple.com",
    "Lime":                   "li.me",
    "January AI":             "january.ai",
    "Palantir":               "palantir.com",
    "Ro":                     "ro.co",
    "Dun & Bradstreet":       "dnb.com",
    "Binance":                "binance.com",
    "JumpCloud":              "jumpcloud.com",
    "HighLevel":              "gohighlevel.com",
    "PermitFlow":             "permitflow.com",
    "Ramp":                   "ramp.com",
    "Linear":                 "linear.app",
    "Sentry":                 "sentry.io",
    "Cohere":                 "cohere.com",
    "Ideogram":               "ideogram.ai",
    "Sesame AI":              "sesame.com",
    "Speak":                  "speak.com",
    "RevenueCat":             "revenuecat.com",
    "Pika":                   "pika.art",
    "ElevenLabs":             "elevenlabs.io",
    "Rogo":                   "rogo.ai",
    "Suno":                   "suno.com",
    "Whatnot":                "whatnot.com",
    "Bankjoy":                "bankjoy.com",
    "Copilot Money":          "copilot.money",
    "Ground News":            "ground.news",
    "Mem0":                   "mem0.ai",
    "Writer":                 "writer.com",
    "Gradient":               "gradient.ai",
    "Nord Security":          "nordvpn.com",
    "Bevel":                  "bevel.com",
    "Pocket Prep":            "pocketprep.com",
    "Notable":                "notablehealth.com",
    "Clipboard":              "clipboard.health",
    "Reedsy":                 "reedsy.com",
    "The Browser Company":    "arc.net",
    "Nomic":                  "nomic.ai",
    "Stream":                 "getstream.io",
    "Abridge":                "abridge.com",
    "Replit":                 "replit.com",
    "EliseAI":                "eliseai.com",
    "Dust":                   "dust.tt",
    "Ashby":                  "ashby.com",
    "Shopify":                "shopify.com",
    "Airbnb":                 "airbnb.com",
    "Zapier":                 "zapier.com",
    "Ada":                    "ada.cx",
    "Braze":                  "braze.com",
    "Intuit":                 "intuit.com",
    "Samsara":                "samsara.com",
}

BOARD_HOSTS = {
    "boards.greenhouse.io",
    "job-boards.greenhouse.io",
    "jobs.ashbyhq.com",
    "boards.eu.greenhouse.io",
    "jobs.lever.co",
}

DOMAIN_GUESSES = [".com", ".ai", ".co", ".app", ".dev", ".io", ".so"]

LOGO_DEV_TOKEN = get_settings().logo_dev_token


def normalize_company_name(company: str) -> str:
    return re.sub(r"\s+", " ", company.strip()).lower()


def base_logo_url(domain: str, size: int) -> str:
    url = f"https://img.logo.dev/{domain}?format=png&size={size}"
    if LOGO_DEV_TOKEN:
        url += f"&token={LOGO_DEV_TOKEN}"
    return url


def google_favicon_url(domain: str, size: int) -> str:
    return (
        "https://t1.gstatic.com/faviconV2"
        f"?client=SOCIAL&type=FAVICON&fallback_opts=TYPE,SIZE,URL&url=http://{domain}&size={size}"
    )


def resolve_company_domain(company: str, job_url: str = "") -> str:
    """Resolve the most likely domain for a company, preferring curated mappings."""
    normalized = normalize_company_name(company)
    for known_company, domain in COMPANY_DOMAINS.items():
        if normalize_company_name(known_company) == normalized:
            return domain

    if job_url:
        parsed = urlparse(job_url)
        host = parsed.netloc.lower().split(":")[0]
        if host and host not in BOARD_HOSTS and "." in host:
            return host.removeprefix("www.")

    slug = re.sub(r"[^a-z0-9]", "", normalized)
    if slug:
        return f"{slug}.com"
    return ""


def logo_sources(company: str, job_url: str = "", size: int = 64) -> list[str]:
    """
    Build multiple logo candidates so the frontend can fall back gracefully.

    Priority order:
      1. Google favicon (t1.gstatic) — reliable, no auth required
      2. logo.dev — higher quality, but only added when LOGO_DEV_TOKEN is set
      3. Google s2/favicons — last resort (follows redirect to t0.gstatic)

    The first URL is also used by the data_editor ImageColumn, which is proxied
    server-side with no JS fallback, so it must be a URL that resolves without auth.
    """
    sources: list[str] = []
    normalized = normalize_company_name(company)
    domain = resolve_company_domain(company, job_url)
    candidate_domains = []

    if domain:
        candidate_domains.append(domain)

    if domain and domain.endswith(".com"):
        slug = domain[:-4]
        for suffix in DOMAIN_GUESSES[1:]:
            candidate_domains.append(f"{slug}{suffix}")

    slug = re.sub(r"[^a-z0-9]", "", normalized)
    if slug:
        for suffix in DOMAIN_GUESSES:
            candidate_domains.append(f"{slug}{suffix}")

    seen_domains = set()
    for candidate in candidate_domains:
        if not candidate or candidate in seen_domains:
            continue
        seen_domains.add(candidate)
        # Google favicon first — works without any API key
        sources.append(google_favicon_url(candidate, size))
        # logo.dev second — best quality, but 404s without a valid token
        if LOGO_DEV_TOKEN:
            sources.append(base_logo_url(candidate, size))
        # Google s2/favicons as final fallback (redirects to t0.gstatic)
        sources.append(f"https://www.google.com/s2/favicons?sz={size}&domain={candidate}")

    return sources


def logo_url(company: str, job_url: str = "", size: int = 40) -> str:
    """Return the primary logo URL for image columns and simple previews.

    Always returns the Google favicon URL (first in sources) so the data_editor
    ImageColumn — which proxies server-side with no JS fallback — reliably loads.
    """
    sources = logo_sources(company, job_url=job_url, size=size)
    return sources[0] if sources else ""
