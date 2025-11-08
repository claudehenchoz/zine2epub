"""Scraper for Clarkesworld Magazine."""

import re
from datetime import datetime

from lxml import html as lxml_html

from zine2epub.models import Issue, Article
from zine2epub.scrapers.base import BaseScraper


class ClarkesworldScraper(BaseScraper):
    """Scraper for Clarkesworld Magazine (clarkesworldmagazine.com)."""

    def get_issue_details(self, issue: Issue) -> Issue:
        """Fetch full details for an issue, including article list.

        Args:
            issue: Issue object with basic metadata

        Returns:
            Issue object populated with articles
        """
        # Try to fetch the issue page
        # Current issue might be on homepage, back issues at /issue_NNN or /prior/issue_NNN/
        possible_urls = [
            f"{self.zine.base_url}/issue_{issue.number}",
            f"{self.zine.base_url}/prior/issue_{issue.number}/",
            self.zine.base_url,  # Homepage for current issue
        ]

        html_content = None
        for issue_url in possible_urls:
            try:
                html_content = self.fetch_html(issue_url)
                break
            except Exception:
                continue

        if not html_content:
            return issue

        tree = self.parse_html(html_content)

        # Extract cover image URL (already set in get_issues, but update if found)
        cover_img = tree.cssselect('img.cover, img[alt*="cover"]')
        if cover_img:
            cover_url = cover_img[0].get('src', '')
            if cover_url and not cover_url.startswith('http'):
                cover_url = self.zine.base_url.rstrip('/') + cover_url
            if cover_url:
                issue.cover_url = cover_url

        # Extract articles from the issue page
        # Stories are in <p class="story"> tags
        articles = []

        story_paragraphs = tree.cssselect('p.story')

        for story_p in story_paragraphs:
            # Get the link
            links = story_p.cssselect('a')
            if not links:
                continue

            link = links[0]
            title = link.text_content().strip()
            url = link.get('href', '')

            if not url:
                continue

            if not url.startswith('http'):
                url = self.zine.base_url.rstrip('/') + url

            # Get author from the next <p class="byline"> element
            next_sibling = story_p.getnext()
            author = "Unknown"

            if next_sibling is not None and 'byline' in next_sibling.get('class', ''):
                author_spans = next_sibling.cssselect('span.authorname')
                if author_spans:
                    author = author_spans[0].text_content().strip()

            # Check if article is available (assume available unless marked otherwise)
            is_available = True

            # Determine type based on section or URL
            article_type = "fiction"

            article = Article(
                title=title,
                author=author,
                content_url=url,
                article_type=article_type,
                is_available=is_available,
            )
            articles.append(article)

        # Also look for non-fiction content (interviews, essays, etc.)
        # These might be in different sections
        section_headers = tree.cssselect('p.section')
        current_section = "fiction"

        for elem in tree.cssselect('p.story, p.section'):
            if 'section' in elem.get('class', ''):
                section_text = elem.text_content().strip().lower()
                if 'interview' in section_text or 'essay' in section_text or 'article' in section_text:
                    current_section = "non-fiction"
                elif 'fiction' in section_text:
                    current_section = "fiction"
            elif 'story' in elem.get('class', ''):
                # We've already processed fiction above; skip if we already have this URL
                links = elem.cssselect('a')
                if links:
                    url = links[0].get('href', '')
                    if url and not any(a.content_url == url or url in a.content_url for a in articles):
                        # Process as non-fiction
                        link = links[0]
                        title = link.text_content().strip()

                        if not url.startswith('http'):
                            url = self.zine.base_url.rstrip('/') + url

                        next_sibling = elem.getnext()
                        author = "Unknown"

                        if next_sibling is not None and 'byline' in next_sibling.get('class', ''):
                            author_spans = next_sibling.cssselect('span.authorname')
                            if author_spans:
                                author = author_spans[0].text_content().strip()

                        article = Article(
                            title=title,
                            author=author,
                            content_url=url,
                            article_type=current_section,
                            is_available=True,
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
        # Content is in <div class="story-text">
        content_element = tree.cssselect('div.story-text')

        if not content_element:
            # Fallback selectors
            content_element = tree.cssselect('.entry-content, article, main')

        if not content_element:
            return "<p>Content not found</p>"

        content_element = content_element[0]

        # Clean up the content - remove unwanted elements
        for unwanted in content_element.cssselect(
            'script, style, .addtoany_share_save_container, .m-a-box, '
            '.author-bio, nav, footer, .aboutinfo, .social-share'
        ):
            if unwanted.getparent() is not None:
                unwanted.getparent().remove(unwanted)

        # Get the cleaned HTML
        cleaned_html = lxml_html.tostring(content_element, encoding='unicode', method='html')

        return cleaned_html
