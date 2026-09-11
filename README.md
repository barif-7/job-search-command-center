# Job Search Command Center

**Local job search pipeline + dashboard for iOS/AI roles. Greenhouse/Lever/Ashby fetcher, SQLite, Streamlit UI, AI summaries, safe auto-apply.**

[![Python](https://img.shields.io/badge/Python-3.x-blue)](https://python.org) [![Streamlit](https://img.shields.io/badge/Streamlit-orange)](https://streamlit.io)

## Features
- Live job board scraping.
- Dashboard with filters and AI insights.
- Safe auto-apply tooling.

## Quick Start
`streamlit run app.py` after setup (see original detailed instructions).

Excellent for tracking applications!
### Profile search preferences

In **Feed → Search preferences**, edit or add preset IDs, labels, comma-separated title keywords, and descriptions. Select presets with **Use preset**, enter your fit signals, then save. Enable preset filtering or profile-fit sorting independently; both are off by default. Preset filtering matches any selected preset and combines with the existing feed filters. No selected presets leaves the feed unfiltered.

Preferences are stored in the active candidate profile (`candidate_profile.json` under the configured apply input directory), preserving application/contact fields. Each installation uses its configured candidate profile; these are not per-browser accounts. Existing `profile_signals` and `target_presets` are respected. Built-in presets seed profiles without saved `search_presets`; an explicitly empty set stays empty. This filters the fetched feed, not the board ingestion pipeline.
