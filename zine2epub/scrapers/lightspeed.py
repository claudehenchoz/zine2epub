"""Scraper for Lightspeed Magazine."""

import re
from datetime import datetime

from lxml import html as lxml_html

from zine2epub.models import Issue, Article
from zine2epub.scrapers.base import BaseScraper


class LightspeedMagazineScraper(BaseScraper):
    """Scraper for Lightspeed Magazine (lightspeedmagazine.com)."""

    def get_issues(self) -> list[Issue]:
        """Fetch and parse the list of available issues.

        Returns:
            List of Issue objects sorted by date (most recent first)
        """
        # Lightspeed Magazine's archive/issues page
        archive_url = f"{self.zine.base_url}/issues/"
        html_content = self.fetch_html(archive_url)
        tree = self.parse_html(html_content)

        issues = []

        # Find all issue links
        issue_links = tree.cssselect('a[href*="/issue-"]')

        for link in issue_links:
            href = link.get('href', '')
            text = link.text_content().strip()

            # Extract issue number
            issue_num_match = re.search(r'issue[/-](\d+)', href, re.IGNORECASE)
            if not issue_num_match:
                issue_num_match = re.search(r'(?:Issue|#)\s*(\d+)', text, re.IGNORECASE)

            if not issue_num_match:
                continue

            issue_num = int(issue_num_match.group(1))

            # Extract date from text
            date_match = re.search(r'(\w+)\s+(\d{4})', text)
            if date_match:
                month_str, year_str = date_match.groups()
                try:
                    issue_date = datetime.strptime(f"{month_str} {year_str}", "%B %Y").date()
                except ValueError:
                    try:
                        issue_date = datetime.strptime(f"{month_str} {year_str}", "%b %Y").date()
                    except ValueError:
                        issue_date = datetime(int(year_str), 1, 1).date()
            else:
                # Fallback estimation (Lightspeed started in 2010, monthly)
                year = 2010 + (issue_num // 12)
                month = (issue_num % 12) or 12
                issue_date = datetime(year, month, 1).date()

            # Construct full URL
            if not href.startswith('http'):
                href = self.zine.base_url.rstrip('/') + href

            issue = Issue(
                number=issue_num,
                title=text or f"Issue {issue_num}",
                issue_date=issue_date,
                cover_url="",  # Will be populated later
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

        # Extract cover image
        cover_img = tree.cssselect('img.issue-cover, .entry-content img, article img, .featured-image img')
        if cover_img:
            cover_url = cover_img[0].get('src', '')
            if cover_url and not cover_url.startswith('http'):
                cover_url = self.zine.base_url.rstrip('/') + cover_url
            if cover_url:
                issue.cover_url = cover_url

        # Extract articles
        articles = []

        # Look for fiction and non-fiction sections
        content_area = tree.cssselect('.entry-content, .issue-content, main')
        if not content_area:
            return issue

        content = content_area[0]

        # Find all article links in the content
        article_links = content.cssselect('a[href*="fiction"], a[href*="story"]')

        for link in article_links:
            title = link.text_content().strip()
            url = link.get('href', '')

            if not title or not url:
                continue

            if not url.startswith('http'):
                url = self.zine.base_url.rstrip('/') + url

            # Try to find author
            parent = link.getparent()
            parent_text = parent.text_content() if parent is not None else ''
            author_match = re.search(r'by\s+([\w\s.]+)', parent_text, re.IGNORECASE)

            if not author_match:
                # Look for author in adjacent elements
                siblings = list(parent) if parent is not None else []
                for sibling in siblings:
                    sibling_text = sibling.text_content()
                    author_match = re.search(r'by\s+([\w\s.]+)', sibling_text, re.IGNORECASE)
                    if author_match:
                        break

            author = author_match.group(1).strip() if author_match else "Unknown"

            # Check availability
            is_available = 'coming soon' not in parent_text.lower()

            # Determine article type
            article_type = "fiction"
            if any(word in url.lower() for word in ['non-fiction', 'nonfiction', 'essay', 'interview']):
                article_type = "non-fiction"

            article = Article(
                title=title,
                author=author,
                content_url=url,
                article_type=article_type,
                is_available=is_available,
            )
            articles.append(article)

        # Also check for non-fiction explicitly
        nonfiction_links = content.cssselect('a[href*="non-fiction"], a[href*="nonfiction"], a[href*="essay"]')

        for link in nonfiction_links:
            title = link.text_content().strip()
            url = link.get('href', '')

            if not title or not url:
                continue

            if not url.startswith('http'):
                url = self.zine.base_url.rstrip('/') + url

            parent = link.getparent()
            parent_text = parent.text_content() if parent is not None else ''
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

        # Extract main content
        content_selectors = [
            '.entry-content',
            'article .content',
            '.story-content',
            '.post-content',
            'article',
            'main',
        ]

        content_element = None
        for selector in content_selectors:
            elements = tree.cssselect(selector)
            if elements:
                content_element = elements[0]
                break

        if content_element is None:
            return "<p>Content not found</p>"

        # Remove unwanted elements
        for unwanted in content_element.cssselect(
            'script, style, .social-share, .author-bio, nav, footer, .sharedaddy, .addtoany_share_save_container'
        ):
            unwanted.getparent().remove(unwanted)

        # Get cleaned HTML
        cleaned_html = lxml_html.tostring(content_element, encoding='unicode', method='html')

        return cleaned_html
