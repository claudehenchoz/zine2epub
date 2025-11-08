"""Scraper for Lightspeed Magazine."""

import re
from datetime import datetime

from lxml import html as lxml_html

from zine2epub.models import Issue, Article
from zine2epub.scrapers.base import BaseScraper


class LightspeedMagazineScraper(BaseScraper):
    """Scraper for Lightspeed Magazine (lightspeedmagazine.com)."""

    def get_issue_details(self, issue: Issue) -> Issue:
        """Fetch full details for an issue, including article list.

        Args:
            issue: Issue object with basic metadata

        Returns:
            Issue object populated with articles
        """
        # Try multiple possible URL patterns
        # Lightspeed uses /issues/{month}-{year}-issue-{number}/ format
        # We need to try different patterns or get the URL from the issue title
        possible_urls = [
            f"{self.zine.base_url}/issue-{issue.number}/",
            f"{self.zine.base_url}/issues/issue-{issue.number}/",
        ]

        # If we have the issue date, construct the full URL format
        if issue.issue_date:
            month_abbr = issue.issue_date.strftime('%b').lower()
            year = issue.issue_date.year
            possible_urls.insert(0, f"{self.zine.base_url}/issues/{month_abbr}-{year}-issue-{issue.number}/")

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
        cover_img = tree.cssselect('img.issue-cover, .entry-content img, article img, .featured-image img')
        if cover_img:
            cover_url = cover_img[0].get('src', '')
            if cover_url and not cover_url.startswith('http'):
                cover_url = self.zine.base_url.rstrip('/') + cover_url
            if cover_url:
                issue.cover_url = cover_url

        # Extract articles
        articles = []

        # Lightspeed shows articles as <div class="post"> elements with <h2 class="posttitle"> headers
        # Skip the first post which is the issue title itself
        posts = tree.cssselect('.post')

        for post in posts[1:]:  # Skip first post (issue title)
            # Get title element
            title_elem = post.cssselect('.posttitle')
            if not title_elem:
                continue

            title_elem = title_elem[0]

            # Get link if available
            links = title_elem.cssselect('a')
            if not links:
                # Some articles might not have links (subscriber-only content)
                title = title_elem.text_content().strip()
                if title:
                    article = Article(
                        title=title,
                        author="Unknown",
                        content_url="",
                        article_type="fiction",
                        is_available=False,
                    )
                    articles.append(article)
                continue

            link = links[0]
            title = link.text_content().strip()
            url = link.get('href', '')

            if not title or not url:
                continue

            # Skip if this is a link back to the issues page
            if '/issues/' in url and 'issue-' in url:
                continue

            if not url.startswith('http'):
                url = self.zine.base_url.rstrip('/') + url

            # Try to find author in postmetadata element
            # Format: <p class="postmetadata"><em>by </em><a href="...">Author Name</a></p>
            author = "Unknown"
            metadata_elems = post.cssselect('p.postmetadata')
            for meta in metadata_elems:
                # Look for author links (not spotlight links)
                author_links = meta.cssselect('a[href*="/authors/"]')
                if author_links:
                    author = author_links[0].text_content().strip()
                    break

            # Fallback: try to extract from text if not found
            if author == "Unknown":
                post_text = post.text_content()
                author_match = re.search(r'by\s+([A-Z][A-Za-z\s.\'-]+?)(?=\s{2,}|\n|$)', post_text)
                if author_match:
                    author = author_match.group(1).strip()

            # Check availability
            is_available = True  # If there's a link, assume it's available

            # Determine article type from URL
            article_type = "fiction"
            if any(word in url.lower() for word in ['/nonfiction/', '/non-fiction/', '/editorial/']):
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
