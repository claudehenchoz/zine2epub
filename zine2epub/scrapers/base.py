"""Base scraper class for all zine scrapers."""

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from curl_cffi import requests
from lxml import html

from zine2epub.cache import get_cache
from zine2epub.models import Issue, Article

if TYPE_CHECKING:
    from zine2epub.models import Zine


class BaseScraper(ABC):
    """Abstract base class for zine scrapers."""

    def __init__(self, zine: "Zine"):
        """Initialize scraper with zine metadata.

        Args:
            zine: The Zine object this scraper is for
        """
        self.zine = zine
        self.cache = get_cache()
        self.session = None

    def _get_session(self) -> requests.Session:
        """Get or create a curl_cffi session with Chrome 136 impersonation.

        Returns:
            Configured requests session
        """
        if self.session is None:
            self.session = requests.Session(impersonate="chrome136")
        return self.session

    def fetch_html(self, url: str, use_cache: bool = True) -> str:
        """Fetch HTML content from a URL with caching.

        Args:
            url: The URL to fetch
            use_cache: Whether to use cached content if available

        Returns:
            HTML content as string

        Raises:
            requests.RequestException: If the request fails
        """
        # Try cache first
        if use_cache:
            cached = self.cache.get(url, binary=False)
            if cached:
                return cached

        # Fetch from web
        session = self._get_session()
        response = session.get(url)
        response.raise_for_status()
        html_content = response.text

        # Cache the result
        self.cache.set(url, html_content, binary=False)

        return html_content

    def fetch_image(self, url: str, use_cache: bool = True) -> bytes:
        """Fetch image data from a URL with caching.

        Args:
            url: The URL to fetch
            use_cache: Whether to use cached content if available

        Returns:
            Image data as bytes

        Raises:
            requests.RequestException: If the request fails
        """
        # Try cache first
        if use_cache:
            cached = self.cache.get(url, binary=True)
            if cached:
                return cached

        # Fetch from web
        session = self._get_session()
        response = session.get(url)
        response.raise_for_status()
        image_data = response.content

        # Cache the result
        self.cache.set(url, image_data, binary=True)

        return image_data

    def parse_html(self, html_content: str) -> html.HtmlElement:
        """Parse HTML content into an lxml tree.

        Args:
            html_content: HTML string to parse

        Returns:
            lxml HtmlElement tree
        """
        return html.fromstring(html_content)

    @abstractmethod
    def get_issue_details(self, issue: Issue) -> Issue:
        """Fetch full details for an issue, including article list.

        Args:
            issue: Issue object with basic metadata

        Returns:
            Issue object populated with articles
        """
        pass

    @abstractmethod
    def get_article_content(self, article: Article) -> str:
        """Fetch and clean the HTML content for an article.

        Args:
            article: Article object with content_url

        Returns:
            Cleaned HTML content for the article
        """
        pass

    def fetch_cover_image(self, issue: Issue) -> bytes:
        """Fetch the cover image for an issue.

        Args:
            issue: Issue object with cover_url

        Returns:
            Cover image data as bytes
        """
        return self.fetch_image(issue.cover_url)

    def close(self):
        """Close the session and clean up resources."""
        if self.session:
            self.session.close()
            self.session = None
