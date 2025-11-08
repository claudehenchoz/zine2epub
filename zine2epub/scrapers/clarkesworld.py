"""Scraper for Clarkesworld Magazine."""

import re
from datetime import datetime

from lxml import html as lxml_html

from zine2epub.models import Issue, Article
from zine2epub.scrapers.base import BaseScraper


class ClarkesworldScraper(BaseScraper):
    """Scraper for Clarkesworld Magazine (clarkesworldmagazine.com)."""

    def get_issues(self) -> list[Issue]:
        """Fetch and parse the list of available issues.

        Returns:
            List of Issue objects sorted by date (most recent first)
        """
        # Clarkesworld's issue archive page
        archive_url = f"{self.zine.base_url}/issue-archive/"
        html_content = self.fetch_html(archive_url)
        tree = self.parse_html(html_content)

        issues = []

        # Find all issue links in the archive
        # Typical structure: <a href="/issue-NNN">Issue NNN - Month Year</a>
        issue_links = tree.cssselect('a[href*="/issue-"]')

        for link in issue_links:
            href = link.get('href', '')
            text = link.text_content().strip()

            # Extract issue number from URL (e.g., /issue-201 -> 201)
            issue_num_match = re.search(r'/issue-(\d+)', href)
            if not issue_num_match:
                continue

            issue_num = int(issue_num_match.group(1))

            # Extract date from text (e.g., "Issue 201 - November 2023")
            date_match = re.search(r'(\w+)\s+(\d{4})', text)
            if date_match:
                month_str, year_str = date_match.groups()
                try:
                    issue_date = datetime.strptime(f"{month_str} {year_str}", "%B %Y").date()
                except ValueError:
                    # If parsing fails, use a default date
                    issue_date = datetime(int(year_str), 1, 1).date()
            else:
                # Fallback: use issue number to approximate date
                issue_date = datetime(2006 + (issue_num // 12), (issue_num % 12) + 1, 1).date()

            # Construct full URL
            if not href.startswith('http'):
                href = self.zine.base_url.rstrip('/') + href

            # Create Issue object (cover URL and articles will be populated later)
            issue = Issue(
                number=issue_num,
                title=text,
                issue_date=issue_date,
                cover_url=f"{self.zine.base_url}/issue-{issue_num}-cover/",  # Placeholder
            )
            issues.append(issue)

        # Sort by date, most recent first
        issues.sort(key=lambda x: x.issue_date, reverse=True)

        return issues

    def get_issue_details(self, issue: Issue) -> Issue:
        """Fetch full details for an issue, including article list.

        Args:
            issue: Issue object with basic metadata

        Returns:
            Issue object populated with articles
        """
        # Construct issue URL
        issue_url = f"{self.zine.base_url}/issue-{issue.number}/"
        html_content = self.fetch_html(issue_url)
        tree = self.parse_html(html_content)

        # Extract cover image URL
        cover_img = tree.cssselect('img.issue-cover, img[alt*="cover"], .entry-content img')
        if cover_img:
            cover_url = cover_img[0].get('src', '')
            if cover_url and not cover_url.startswith('http'):
                cover_url = self.zine.base_url.rstrip('/') + cover_url
            if cover_url:
                issue.cover_url = cover_url

        # Extract articles from the issue page
        # Look for article links in the content area
        articles = []

        # Find all article links (typically in a list or content area)
        article_links = tree.cssselect('.entry-content a[href*="fiction"], .entry-content a[href*="story"]')

        for link in article_links:
            title = link.text_content().strip()
            url = link.get('href', '')

            if not url.startswith('http'):
                url = self.zine.base_url.rstrip('/') + url

            # Try to extract author from the text near the link
            parent_text = link.getparent().text_content() if link.getparent() is not None else ''
            author_match = re.search(r'by\s+([\w\s.]+)', parent_text, re.IGNORECASE)
            author = author_match.group(1).strip() if author_match else "Unknown"

            # Check if article is available
            is_available = 'coming soon' not in parent_text.lower()

            article = Article(
                title=title,
                author=author,
                content_url=url,
                article_type="fiction",
                is_available=is_available,
            )
            articles.append(article)

        # Also look for non-fiction content
        nonfiction_links = tree.cssselect('.entry-content a[href*="non-fiction"], .entry-content a[href*="essay"]')

        for link in nonfiction_links:
            title = link.text_content().strip()
            url = link.get('href', '')

            if not url.startswith('http'):
                url = self.zine.base_url.rstrip('/') + url

            parent_text = link.getparent().text_content() if link.getparent() is not None else ''
            author_match = re.search(r'by\s+([\w\s.]+)', parent_text, re.IGNORECASE)
            author = author_match.group(1).strip() if author_match else "Unknown"

            is_available = 'coming soon' not in parent_text.lower()

            article = Article(
                title=title,
                author=author,
                content_url=url,
                article_type="non-fiction",
                is_available=is_available,
            )
            articles.append(article)

        issue.articles = articles
        return issue

    def get_article_content(self, article: Article) -> str:
        """Fetch and clean the HTML content for an article.

        Args:
            article: Article object with content_url

        Returns:
            Cleaned HTML content for the article
        """
        if not article.is_available:
            return ""

        html_content = self.fetch_html(article.content_url)
        tree = self.parse_html(html_content)

        # Extract the main article content
        # Try multiple selectors to find the content
        content_selectors = [
            '.entry-content',
            'article .content',
            '.story-content',
            '.post-content',
        ]

        content_element = None
        for selector in content_selectors:
            elements = tree.cssselect(selector)
            if elements:
                content_element = elements[0]
                break

        if content_element is None:
            # Fallback: try to find any article or main content
            content_element = tree.cssselect('article, main')
            if content_element:
                content_element = content_element[0]
            else:
                return "<p>Content not found</p>"

        # Clean up the content - remove unwanted elements
        for unwanted in content_element.cssselect('script, style, .social-share, .author-bio, nav, footer'):
            unwanted.getparent().remove(unwanted)

        # Get the cleaned HTML
        cleaned_html = lxml_html.tostring(content_element, encoding='unicode', method='html')

        return cleaned_html
