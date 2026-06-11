from datetime import datetime, timezone, timedelta
import re
from typing import Optional
from urllib.parse import urlparse

def normalize_location(location: str) -> str:
    """
    Normalizes location strings to a consistent format.
    """
    if not location:
        return ""

    location = location.lower()
    # Prioritize remote keywords
    if "remote" in location:
        return "Remote"

    # Basic normalization for city, country
    location = re.sub(r'[,\-]', ' ', location)
    location = re.sub(r'\s+', ' ', location).strip()

    if "toronto" in location:
        return "Toronto"
    if "vancouver" in location:
        return "Vancouver"
    if "new york" in location or "nyc" in location:
        return "New York"
    if "san francisco" in location or "sf" in location:
        return "San Francisco"
    if "canada" in location:
        return "Canada"

    return location.title()

def parse_html_date(date_str: str) -> Optional[datetime]:
    """
    Parses various date string formats found in HTML job postings.
    Example formats: "Posted 3 days ago", "2 days ago", "March 15, 2023"
    """
    if not date_str:
        return None

    date_str = date_str.lower().strip()

    match = re.search(r'(\d+)\s+(days?|hours?)\s+ago', date_str)
    if match:
        num = int(match.group(1))
        unit = match.group(2)
        if "day" in unit:
            return datetime.now(timezone.utc) - timedelta(days=num)
        else:
            return datetime.now(timezone.utc) - timedelta(hours=num)

    try:
        formats_to_try = [
            "%B %d, %Y",  # March 15, 2023
            "%b %d, %Y",  # Mar 15, 2023
            "%Y-%m-%d",   # 2023-03-15
            "%m/%d/%Y",   # 03/15/2023
        ]
        for fmt in formats_to_try:
            try:
                return datetime.strptime(date_str, fmt).replace(tzinfo=timezone.utc)
            except ValueError:
                continue
    except Exception:
        pass

    return None

def clean_text(text: str) -> str:
    """
    Cleans HTML content by removing extra whitespace and tags.
    """
    if not text:
        return ""
    text = re.sub(r'<[^>]+>', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def is_valid_url(url: str) -> bool:
    """
    Checks if a given string is a valid URL.
    """
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc]) and result.scheme in ['http', 'https']
    except ValueError:
        return False
