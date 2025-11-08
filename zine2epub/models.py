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

    def __post_init__(self):
        """Validate article data."""
        if not self.title or not self.author:
            raise ValueError("Article must have title and author")


@dataclass
class Issue:
    """Represents a single issue of a zine."""

    number: int
    title: str
    issue_date: date
    cover_url: str
    articles: list[Article] = field(default_factory=list)
    cover_image_data: Optional[bytes] = None

    @property
    def is_complete(self) -> bool:
        """Check if all articles in the issue are available."""
        return all(article.is_available for article in self.articles)

    @property
    def date_str(self) -> str:
        """Return formatted date string (YYYY-MM)."""
        return self.issue_date.strftime("%Y-%m")

    @property
    def filename(self) -> str:
        """Generate the EPUB filename for this issue."""
        # Will be overridden with zine name in the scraper
        return f"Issue{self.number:03d}_{self.date_str}.epub"


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
