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
        issues = []

        # First, get the current issue from the homepage
        try:
            homepage_html = self.fetch_html(self.zine.base_url)
            homepage_tree = self.parse_html(homepage_html)

            # Get current issue number from meta description
            meta_desc = homepage_tree.cssselect('meta[name="description"]')
            if meta_desc:
                desc = meta_desc[0].get('content', '')
                issue_match = re.search(r'Issue\s+(\d+)', desc, re.I)
                if issue_match:
                    current_issue_num = int(issue_match.group(1))

                    # Calculate current date (use current month/year)
                    current_date = datetime.now().date()

                    # Create current issue
                    current_issue = Issue(
                        number=current_issue_num,
                        title=f"ISSUE {current_issue_num} – {current_date.strftime('%B %Y')}",
                        issue_date=current_date,
                        cover_url=f"{self.zine.base_url}/covers/cw_{current_issue_num}_large.jpg",
                    )
                    issues.append(current_issue)
        except Exception:
            # If we can't get the current issue, just continue with back issues
            pass

        # Now get back issues from the archive
        archive_url = f"{self.zine.base_url}/prior/"
        html_content = self.fetch_html(archive_url)
        tree = self.parse_html(html_content)

        # Find all issue links
        # Format: <a href="https://clarkesworldmagazine.com/issue_220">ISSUE 220 – January 2025</a>
        issue_links = tree.cssselect('a[href*="/issue_"]')

        for link in issue_links:
            href = link.get('href', '')
            text = link.text_content().strip()

            # Extract issue number from URL (e.g., /issue_220 -> 220)
            issue_num_match = re.search(r'/issue_(\d+)', href)
            if not issue_num_match:
                continue

            issue_num = int(issue_num_match.group(1))

            # Skip if we already have this issue (current issue)
            if any(i.number == issue_num for i in issues):
                continue

            # Extract date from text (e.g., "ISSUE 220 – January 2025")
            date_match = re.search(r'(\w+)\s+(\d{4})', text)
            if date_match:
                month_str, year_str = date_match.groups()
                try:
                    issue_date = datetime.strptime(f"{month_str} {year_str}", "%B %Y").date()
                except ValueError:
                    # If parsing fails, use a default date
                    issue_date = datetime(int(year_str), 1, 1).date()
            else:
                # Fallback: use issue number to approximate date (started Oct 2006 as issue 1)
                months_since_start = issue_num - 1
                year = 2006 + (months_since_start // 12)
                month = (months_since_start % 12) + 10  # Started in October
                if month > 12:
                    month -= 12
                    year += 1
                issue_date = datetime(year, month, 1).date()

            # Create Issue object (cover URL and articles will be populated later)
            issue = Issue(
                number=issue_num,
                title=text,
                issue_date=issue_date,
                cover_url=f"{self.zine.base_url}/covers/cw_{issue_num}_large.jpg",
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
        # Try to fetch the issue page
        # Current issue might be on homepage, back issues have their own pages
        issue_url = f"{self.zine.base_url}/issue_{issue.number}"

        try:
            html_content = self.fetch_html(issue_url)
        except Exception:
            # If issue page doesn't exist, try the homepage (for current issue)
            issue_url = self.zine.base_url
            html_content = self.fetch_html(issue_url)

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
