"""URL parser to detect zine and issue from URL."""

import re
from datetime import datetime, date
from typing import Optional, Tuple
from urllib.parse import urlparse


def parse_zine_url(url: str) -> Optional[Tuple[str, Optional[int | str], Optional[date]]]:
    """Parse a zine URL and extract zine name, issue number, and date.

    Args:
        url: URL to a zine issue

    Returns:
        Tuple of (zine_name, issue_number, issue_date) or None if not recognized
        issue_number can be int or str (str for Uncanny Magazine's written numbers)
        issue_date will be None if it can't be determined from the URL

    Examples:
        >>> parse_zine_url("https://clarkesworldmagazine.com/")
        ("clarkesworld", None, None)

        >>> parse_zine_url("https://clarkesworldmagazine.com/issue_229")
        ("clarkesworld", 229, None)

        >>> parse_zine_url("https://www.uncannymagazine.com/issues/uncanny-magazine-issue-sixty-seven/")
        ("uncanny", "sixty-seven", None)

        >>> parse_zine_url("https://www.lightspeedmagazine.com/issues/nov-2025-issue-186/")
        ("lightspeed", 186, date(2025, 11, 1))
    """
    parsed = urlparse(url)
    domain = parsed.netloc.lower()
    path = parsed.path.lower()

    # Clarkesworld Magazine
    if "clarkesworldmagazine.com" in domain or "clarkesworld" in domain:
        # Homepage - current issue
        if path in ['/', '']:
            return ("clarkesworld", None, None)  # Will be determined by scraper

        # Prior issue: /issue_NNN or /prior/issue_NNN/
        issue_match = re.search(r'issue_(\d+)', path)
        if issue_match:
            return ("clarkesworld", int(issue_match.group(1)), None)

    # Uncanny Magazine
    elif "uncannymagazine.com" in domain or "uncanny" in domain:
        # Issue URL: /issues/uncanny-magazine-issue-WRITTEN/
        # We keep the written form (e.g., "sixty-seven") as the issue number
        issue_match = re.search(r'uncanny-magazine-issue-([\w-]+)', path)
        if issue_match:
            written_num = issue_match.group(1)  # e.g., "sixty-seven"
            return ("uncanny", written_num, None)

    # Lightspeed Magazine
    elif "lightspeedmagazine.com" in domain or "lightspeed" in domain:
        # Issue URL: /issues/MMM-YYYY-issue-NNN/
        # Extract date from URL if present
        date_match = re.search(r'/(\w+)-(\d{4})-issue-(\d+)', path)
        if date_match:
            month_str = date_match.group(1)
            year_str = date_match.group(2)
            issue_num = int(date_match.group(3))

            # Parse the date
            try:
                issue_date = datetime.strptime(f"{month_str} {year_str}", "%b %Y").date()
            except ValueError:
                try:
                    issue_date = datetime.strptime(f"{month_str} {year_str}", "%B %Y").date()
                except ValueError:
                    issue_date = None

            return ("lightspeed", issue_num, issue_date)

        # Fallback: just issue number
        issue_match = re.search(r'issue-(\d+)', path)
        if issue_match:
            return ("lightspeed", int(issue_match.group(1)), None)

    return None


def get_zine_display_name(zine_name: str) -> str:
    """Get the display name for a zine.

    Args:
        zine_name: Internal zine name

    Returns:
        Display name
    """
    names = {
        "clarkesworld": "Clarkesworld",
        "uncanny": "Uncanny Magazine",
        "lightspeed": "Lightspeed Magazine",
    }
    return names.get(zine_name, zine_name.title())


def get_zine_base_url(zine_name: str) -> str:
    """Get the base URL for a zine.

    Args:
        zine_name: Internal zine name

    Returns:
        Base URL
    """
    urls = {
        "clarkesworld": "https://clarkesworldmagazine.com",
        "uncanny": "https://uncannymagazine.com",
        "lightspeed": "https://lightspeedmagazine.com",
    }
    return urls.get(zine_name, "")
