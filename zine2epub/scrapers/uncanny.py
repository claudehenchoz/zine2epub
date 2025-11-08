"""Scraper for Uncanny Magazine."""

import re
from datetime import datetime

from lxml import html as lxml_html

from zine2epub.models import Issue, Article
from zine2epub.scrapers.base import BaseScraper


class UncannyMagazineScraper(BaseScraper):
    """Scraper for Uncanny Magazine (uncannymagazine.com)."""

    def get_issues(self) -> list[Issue]:
        """Fetch and parse the list of available issues.

        Returns:
            List of Issue objects sorted by date (most recent first)
        """
        # Uncanny Magazine's archive page
        archive_url = f"{self.zine.base_url}/issues/"
        html_content = self.fetch_html(archive_url)
        tree = self.parse_html(html_content)

        issues = []

        # Find all issue entries
        # Typical structure might have issue links or cards
        issue_elements = tree.cssselect('.issue-card, .issue-entry, article.issue')

        for element in issue_elements:
            # Extract issue title and link
            title_link = element.cssselect('a[href*="/issue"], h2 a, h3 a')
            if not title_link:
                continue

            link = title_link[0]
            title = link.text_content().strip()
            href = link.get('href', '')

            # Extract issue number from title or URL
            issue_num_match = re.search(r'(?:Issue|#)\s*(\d+)', title, re.IGNORECASE)
            if issue_num_match:
                issue_num = int(issue_num_match.group(1))
            else:
                # Try to extract from URL
                url_match = re.search(r'/issue[/-](\d+)', href)
                if url_match:
                    issue_num = int(url_match.group(1))
                else:
                    continue

            # Extract date
            date_match = re.search(r'(\w+)[/-](\w+)\s+(\d{4})', title)
            if date_match:
                month_str, _, year_str = date_match.groups()
                try:
                    issue_date = datetime.strptime(f"{month_str} {year_str}", "%B %Y").date()
                except ValueError:
                    # Try abbreviated month
                    try:
                        issue_date = datetime.strptime(f"{month_str} {year_str}", "%b %Y").date()
                    except ValueError:
                        issue_date = datetime(int(year_str), 1, 1).date()
            else:
                # Fallback date estimation
                issue_date = datetime(2014 + (issue_num // 6), ((issue_num * 2) % 12) + 1, 1).date()

            # Construct full URL
            if not href.startswith('http'):
                href = self.zine.base_url.rstrip('/') + href

            issue = Issue(
                number=issue_num,
                title=title,
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
        # Construct issue URL (try multiple patterns)
        possible_urls = [
            f"{self.zine.base_url}/issue-{issue.number}/",
            f"{self.zine.base_url}/issue/{issue.number}/",
            f"{self.zine.base_url}/issues/issue-{issue.number}/",
        ]

        html_content = None
        for url in possible_urls:
            try:
                html_content = self.fetch_html(url)
                break
            except Exception:
                continue

        if not html_content:
            return issue

        tree = self.parse_html(html_content)

        # Extract cover image
        cover_img = tree.cssselect('img.issue-cover, .featured-image img, article img')
        if cover_img:
            cover_url = cover_img[0].get('src', '')
            if cover_url and not cover_url.startswith('http'):
                cover_url = self.zine.base_url.rstrip('/') + cover_url
            if cover_url:
                issue.cover_url = cover_url

        # Extract articles
        articles = []

        # Look for article listings
        article_entries = tree.cssselect('.entry-content .article-entry, .issue-content article, .story-listing')

        for entry in article_entries:
            # Find article title and link
            title_links = entry.cssselect('a[href*="fiction"], a[href*="story"], h3 a, h4 a')
            if not title_links:
                continue

            link = title_links[0]
            title = link.text_content().strip()
            url = link.get('href', '')

            if not url.startswith('http'):
                url = self.zine.base_url.rstrip('/') + url

            # Extract author
            author_elem = entry.cssselect('.author, .byline, [class*="author"]')
            if author_elem:
                author = author_elem[0].text_content().strip()
                author = re.sub(r'^by\s+', '', author, flags=re.IGNORECASE).strip()
            else:
                # Try to find author in text
                text = entry.text_content()
                author_match = re.search(r'by\s+([\w\s.]+)', text, re.IGNORECASE)
                author = author_match.group(1).strip() if author_match else "Unknown"

            # Check availability
            is_available = 'coming soon' not in entry.text_content().lower()

            # Determine article type
            article_type = "fiction"
            if any(word in title.lower() for word in ['essay', 'interview', 'editorial', 'review']):
                article_type = "non-fiction"

            article = Article(
                title=title,
                author=author,
                content_url=url,
                article_type=article_type,
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
            'main article',
        ]

        content_element = None
        for selector in content_selectors:
            elements = tree.cssselect(selector)
            if elements:
                content_element = elements[0]
                break

        if content_element is None:
            content_element = tree.cssselect('article, main')
            if content_element:
                content_element = content_element[0]
            else:
                return "<p>Content not found</p>"

        # Remove unwanted elements
        for unwanted in content_element.cssselect('script, style, .social-share, .author-bio, nav, footer, .sharedaddy'):
            unwanted.getparent().remove(unwanted)

        # Get cleaned HTML
        cleaned_html = lxml_html.tostring(content_element, encoding='unicode', method='html')

        return cleaned_html
