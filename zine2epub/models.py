"""Data models for zine2epub."""

from dataclasses import dataclass, field
from datetime import date
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from zine2epub.scrapers.base import BaseScraper


@dataclass
class Article:
    """Represents a single article in a zine issue."""

    title: str
    author: str
    content_url: str
    article_type: str = "fiction"  # fiction, non-fiction, editorial, etc.
    html_content: Optional[str] = None
    is_available: bool = True  # False if marked as "coming soon"


@dataclass
class Issue:
    """Represents a single issue of a zine."""

    number: int | str  # int for most zines, str for written numbers (e.g., "sixty-seven")
    title: str
    issue_date: date
    cover_url: str
    articles: list[Article] = field(default_factory=list)
    cover_image_data: Optional[bytes] = None


@dataclass
class Zine:
    """Represents a fiction zine with metadata and scraper."""

    name: str  # Internal name (e.g., "clarkesworld")
    display_name: str  # Display name (e.g., "Clarkesworld Magazine")
    base_url: str
    scraper_class: type["BaseScraper"]

    def __post_init__(self):
        """Validate zine data."""
        if not self.name or not self.display_name:
            raise ValueError("Zine must have name and display_name")

    def get_scraper(self) -> "BaseScraper":
        """Instantiate and return the scraper for this zine."""
        return self.scraper_class(self)
