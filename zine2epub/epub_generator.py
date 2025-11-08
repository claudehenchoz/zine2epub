"""EPUB2 generator for zine issues."""

from pathlib import Path
from typing import Callable

from ebooklib import epub
from jinja2 import Environment, FileSystemLoader

from zine2epub.models import Issue, Article


class EPUBGenerator:
    """Generate EPUB2-compliant ebooks from zine issues."""

    def __init__(self, zine_name: str):
        """Initialize EPUB generator.

        Args:
            zine_name: Name of the zine (for metadata)
        """
        self.zine_name = zine_name

        # Set up Jinja2 environment
        template_dir = Path(__file__).parent / "templates"
        self.jinja_env = Environment(loader=FileSystemLoader(str(template_dir)))

    def generate(
        self,
        issue: Issue,
        output_path: str,
        progress_callback: Callable[[str, float], None] | None = None,
    ) -> str:
        """Generate an EPUB file from an issue.

        Args:
            issue: Issue object with articles and cover image
            output_path: Path where the EPUB should be saved
            progress_callback: Optional callback function(message, percentage)

        Returns:
            Path to the generated EPUB file
        """
        if progress_callback:
            progress_callback("Creating EPUB structure", 0.0)

        # Create EPUB book
        book = epub.EpubBook()

        # Set metadata
        book.set_identifier(f"{self.zine_name.lower()}-issue-{issue.number}")
        book.set_title(f"{self.zine_name} - {issue.title}")
        book.set_language("en")

        # Add authors from all articles
        authors = list(set(article.author for article in issue.articles if article.author))
        if authors:
            for author in authors[:5]:  # Limit to first 5 authors
                book.add_author(author)

        # Add publication date
        book.add_metadata("DC", "date", issue.issue_date.isoformat())

        if progress_callback:
            progress_callback("Adding cover image", 0.1)

        # Add cover image if available
        if issue.cover_image_data:
            book.set_cover("cover.jpg", issue.cover_image_data)

        if progress_callback:
            progress_callback("Adding stylesheet", 0.15)

        # Add CSS stylesheet
        css_path = Path(__file__).parent / "templates" / "styles.css"
        with open(css_path, "r", encoding="utf-8") as f:
            css_content = f.read()

        nav_css = epub.EpubItem(
            uid="style_nav",
            file_name="styles.css",
            media_type="text/css",
            content=css_content,
        )
        book.add_item(nav_css)

        # Process articles
        epub_items = []
        total_articles = len(issue.articles)

        for idx, article in enumerate(issue.articles):
            progress = 0.2 + (0.6 * (idx / total_articles))
            if progress_callback:
                progress_callback(f"Processing: {article.title}", progress)

            # Generate filename for the article
            filename = f"article_{idx:03d}.xhtml"

            if article.is_available and article.html_content:
                # Use article template
                template = self.jinja_env.get_template("article.xhtml")
                content = template.render(
                    title=article.title,
                    author=article.author,
                    content=article.html_content,
                )
            else:
                # Use placeholder template
                template = self.jinja_env.get_template("placeholder.xhtml")
                content = template.render(
                    title=article.title,
                    author=article.author,
                    url=article.content_url,
                )

            # Create EPUB item
            epub_item = epub.EpubHtml(
                title=article.title,
                file_name=filename,
                lang="en",
            )
            epub_item.content = content.encode("utf-8")
            epub_item.add_item(nav_css)

            book.add_item(epub_item)
            epub_items.append(epub_item)

        if progress_callback:
            progress_callback("Creating table of contents", 0.85)

        # Create table of contents
        toc_items = []
        for idx, article in enumerate(issue.articles):
            toc_items.append(
                epub.Link(
                    f"article_{idx:03d}.xhtml",
                    article.title,
                    f"article_{idx}",
                )
            )

        book.toc = tuple(toc_items)

        # Add navigation files
        book.add_item(epub.EpubNcx())
        book.add_item(epub.EpubNav())

        if progress_callback:
            progress_callback("Building spine", 0.9)

        # Define book spine (reading order)
        book.spine = ["nav"] + epub_items

        if progress_callback:
            progress_callback("Writing EPUB file", 0.95)

        # Write EPUB file
        epub.write_epub(output_path, book, {})

        if progress_callback:
            progress_callback("EPUB generation complete", 1.0)

        return output_path


def generate_filename(zine_name: str, issue: Issue) -> str:
    """Generate the filename for an EPUB.

    Args:
        zine_name: Name of the zine
        issue: Issue object

    Returns:
        Filename in format: ZineName_IssueNNN_YYYY-MM.epub
    """
    # Clean zine name (remove spaces, special chars)
    clean_name = zine_name.replace(" ", "")

    return f"{clean_name}_Issue{issue.number:03d}_{issue.date_str}.epub"
