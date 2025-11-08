"""URL parser to detect zine and issue from URL."""

import re
from typing import Optional, Tuple
from urllib.parse import urlparse

from zine2epub.scrapers.uncanny import WRITTEN_NUMBERS


def parse_zine_url(url: str) -> Optional[Tuple[str, int]]:
    """Parse a zine URL and extract zine name and issue number.

    Args:
        url: URL to a zine issue

    Returns:
        Tuple of (zine_name, issue_number) or None if not recognized

    Examples:
        >>> parse_zine_url("https://clarkesworldmagazine.com/")
        ("clarkesworld", <current_issue>)

        >>> parse_zine_url("https://clarkesworldmagazine.com/issue_229")
        ("clarkesworld", 229)

        >>> parse_zine_url("https://www.uncannymagazine.com/issues/uncanny-magazine-issue-sixty-seven/")
        ("uncanny", 67)

        >>> parse_zine_url("https://www.lightspeedmagazine.com/issues/nov-2025-issue-186/")
        ("lightspeed", 186)
    """
    parsed = urlparse(url)
    domain = parsed.netloc.lower()
    path = parsed.path.lower()

    # Clarkesworld Magazine
    if "clarkesworldmagazine.com" in domain or "clarkesworld" in domain:
        # Homepage - current issue
        if path in ['/', '']:
            return ("clarkesworld", None)  # Will be determined by scraper

        # Prior issue: /issue_NNN or /prior/issue_NNN/
        issue_match = re.search(r'issue_(\d+)', path)
        if issue_match:
            return ("clarkesworld", int(issue_match.group(1)))

    # Uncanny Magazine
    elif "uncannymagazine.com" in domain or "uncanny" in domain:
        # Issue URL: /issues/uncanny-magazine-issue-WRITTEN/
        issue_match = re.search(r'uncanny-magazine-issue-([\w-]+)', path)
        if issue_match:
            written_num = issue_match.group(1)
            issue_num = WRITTEN_NUMBERS.get(written_num)
            if issue_num:
                return ("uncanny", issue_num)

    # Lightspeed Magazine
    elif "lightspeedmagazine.com" in domain or "lightspeed" in domain:
        # Issue URL: /issues/MMM-YYYY-issue-NNN/
        issue_match = re.search(r'issue-(\d+)', path)
        if issue_match:
            return ("lightspeed", int(issue_match.group(1)))

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
