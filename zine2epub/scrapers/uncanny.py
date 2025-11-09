"""Scraper for Uncanny Magazine."""

import re
from datetime import datetime

from lxml import html as lxml_html

from zine2epub.models import Issue, Article
from zine2epub.scrapers.base import BaseScraper


class UncannyMagazineScraper(BaseScraper):
    """Scraper for Uncanny Magazine (uncannymagazine.com)."""

    def get_issue_details(self, issue: Issue) -> Issue:
        """Fetch full details for an issue, including article list.

        Args:
            issue: Issue object with basic metadata (number is written form like "sixty-seven")

        Returns:
            Issue object populated with articles
        """
        # Construct issue URL using the written number directly
        issue_url = f"{self.zine.base_url}/issues/uncanny-magazine-issue-{issue.number}/"

        try:
            html_content = self.fetch_html(issue_url)
        except Exception:
            return issue

        tree = self.parse_html(html_content)

        # Update cover image if not set
        if not issue.cover_url:
            cover_img = tree.cssselect('div.featured_issue_thumbnail a img')
            if cover_img:
                cover_url = cover_img[0].get('src', '')
                if cover_url and not cover_url.startswith('http'):
                    cover_url = self.zine.base_url.rstrip('/') + cover_url
                if cover_url:
                    issue.cover_url = cover_url

        # Extract articles from "In The Issue" section
        articles = []

        # Find all <p> tags that contain article links
        # Format: <p><a href="...">Title</a> by <a href="...">Author</a></p>
        # Content is in .issue_content, not .entry-content
        article_paragraphs = tree.cssselect('.issue_content p')

        for p in article_paragraphs:
            # Get article link (first link in paragraph)
            article_links = p.cssselect('a[href*="/article/"]')
            if not article_links:
                continue

            article_link = article_links[0]
            title = article_link.text_content().strip()
            url = article_link.get('href', '')

            if not url or not title:
                continue

            if not url.startswith('http'):
                url = self.zine.base_url.rstrip('/') + url

            # Extract author (second link or text after "by")
            author = "Unknown"
            author_links = p.cssselect('a[href*="/authors/"]')
            if author_links:
                # Author might be in a separate link
                for author_link in author_links:
                    if author_link != article_link:
                        author = author_link.text_content().strip()
                        break

            if author == "Unknown":
                # Try to extract from text
                p_text = p.text_content()
                author_match = re.search(r'by\s+([^(]+?)(?:\s*\(|$)', p_text, re.I)
                if author_match:
                    author = author_match.group(1).strip()

            # Check availability
            p_text = p.text_content()
            is_available = 'available' not in p_text.lower() or title in article_link.get('href', '')

            # Determine article type based on URL or title
            article_type = "fiction"
            if any(word in url.lower() or word in title.lower()
                   for word in ['interview', 'essay', 'editorial', 'valley', 'thank-you']):
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
        content_element = tree.cssselect('.entry-content')

        if not content_element:
            # Fallback selectors
            content_element = tree.cssselect('article, main, .post-content')

        if not content_element:
            return "<p>Content not found</p>"

        content_element = content_element[0]

        # Remove unwanted elements
        for unwanted in content_element.cssselect(
            'script, style, .sharedaddy, .social-share, .author-bio, '
            'nav, footer, .addtoany_share, .jp-relatedposts'
        ):
            if unwanted.getparent() is not None:
                unwanted.getparent().remove(unwanted)

        # Get cleaned HTML
        cleaned_html = lxml_html.tostring(content_element, encoding='unicode', method='html')

        return cleaned_html
