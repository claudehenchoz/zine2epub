"""Scraper for Uncanny Magazine."""

import re
from datetime import datetime

from lxml import html as lxml_html

from zine2epub.models import Issue, Article
from zine2epub.scrapers.base import BaseScraper


# Mapping of written numbers to integers for Uncanny Magazine
WRITTEN_NUMBERS = {
    'one': 1, 'two': 2, 'three': 3, 'four': 4, 'five': 5,
    'six': 6, 'seven': 7, 'eight': 8, 'nine': 9, 'ten': 10,
    'eleven': 11, 'twelve': 12, 'thirteen': 13, 'fourteen': 14, 'fifteen': 15,
    'sixteen': 16, 'seventeen': 17, 'eighteen': 18, 'nineteen': 19, 'twenty': 20,
    'twenty-one': 21, 'twenty-two': 22, 'twenty-three': 23, 'twenty-four': 24,
    'twenty-five': 25, 'twenty-six': 26, 'twenty-seven': 27, 'twenty-eight': 28,
    'twenty-nine': 29, 'thirty': 30, 'thirty-one': 31, 'thirty-two': 32,
    'thirty-three': 33, 'thirty-four': 34, 'thirty-five': 35, 'thirty-six': 36,
    'thirty-seven': 37, 'thirty-eight': 38, 'thirty-nine': 39, 'forty': 40,
    'forty-one': 41, 'forty-two': 42, 'forty-three': 43, 'forty-four': 44,
    'forty-five': 45, 'forty-six': 46, 'forty-seven': 47, 'forty-eight': 48,
    'forty-nine': 49, 'fifty': 50, 'fifty-one': 51, 'fifty-two': 52,
    'fifty-three': 53, 'fifty-four': 54, 'fifty-five': 55, 'fifty-six': 56,
    'fifty-seven': 57, 'fifty-eight': 58, 'fifty-nine': 59, 'sixty': 60,
    'sixty-one': 61, 'sixty-two': 62, 'sixty-three': 63, 'sixty-four': 64,
    'sixty-five': 65, 'sixty-six': 66, 'sixty-seven': 67, 'sixty-eight': 68,
    'sixty-nine': 69, 'seventy': 70,
}


class UncannyMagazineScraper(BaseScraper):
    """Scraper for Uncanny Magazine (uncannymagazine.com)."""

    def get_issues(self) -> list[Issue]:
        """Fetch and parse the list of available issues.

        Returns:
            List of Issue objects sorted by date (most recent first)
        """
        # Uncanny Magazine's issues archive page
        archive_url = f"{self.zine.base_url}/issues/"
        html_content = self.fetch_html(archive_url)
        tree = self.parse_html(html_content)

        issues = []

        # Find all article elements (each represents an issue)
        issue_articles = tree.cssselect('article')

        for article_elem in issue_articles:
            # Get the title (e.g., "Uncanny Magazine Issue Sixty-Seven")
            title_elem = article_elem.cssselect('.entry-title, h2, h3')
            if not title_elem:
                continue

            title = title_elem[0].text_content().strip()

            # Extract written number from title
            written_num_match = re.search(r'Issue\s+([\w-]+)', title, re.I)
            if not written_num_match:
                continue

            written_num = written_num_match.group(1).lower()
            issue_num = WRITTEN_NUMBERS.get(written_num)

            if not issue_num:
                continue

            # Get the issue URL
            links = article_elem.cssselect('a[href*="/issues/uncanny-magazine-issue-"]')
            if not links:
                continue

            href = links[0].get('href', '')
            if not href.startswith('http'):
                href = self.zine.base_url.rstrip('/') + href

            # Try to find date in the article text
            article_text = article_elem.text_content()
            date_match = re.search(r'(January|February|March|April|May|June|July|August|September|October|November|December)[/\s]+(\d{4})', article_text, re.I)

            if date_match:
                month_str, year_str = date_match.groups()
                try:
                    issue_date = datetime.strptime(f"{month_str} {year_str}", "%B %Y").date()
                except ValueError:
                    issue_date = datetime(int(year_str), 1, 1).date()
            else:
                # Fallback: Uncanny started in late 2014, bimonthly
                year = 2014 + ((issue_num - 1) // 6)
                month = ((issue_num - 1) % 6) * 2 + 1
                issue_date = datetime(year, month, 1).date()

            # Get cover image if present
            cover_imgs = article_elem.cssselect('img')
            cover_url = ""
            if cover_imgs:
                cover_url = cover_imgs[0].get('src', '')
                if cover_url and not cover_url.startswith('http'):
                    cover_url = self.zine.base_url.rstrip('/') + cover_url

            issue = Issue(
                number=issue_num,
                title=title,
                issue_date=issue_date,
                cover_url=cover_url,
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
        # Convert issue number back to written form for URL
        written_num = None
        for key, val in WRITTEN_NUMBERS.items():
            if val == issue.number:
                written_num = key
                break

        if not written_num:
            return issue

        # Construct issue URL
        issue_url = f"{self.zine.base_url}/issues/uncanny-magazine-issue-{written_num}/"

        try:
            html_content = self.fetch_html(issue_url)
        except Exception:
            return issue

        tree = self.parse_html(html_content)

        # Update cover image if not set
        if not issue.cover_url:
            cover_img = tree.cssselect('img[alt*="cover"], .entry-content img')
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
