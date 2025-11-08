"""Entry point for zine2epub CLI application."""

import sys
from pathlib import Path

import click

from zine2epub.url_parser import parse_zine_url, get_zine_display_name, get_zine_base_url
from zine2epub.models import Zine
from zine2epub.scrapers.clarkesworld import ClarkesworldScraper
from zine2epub.scrapers.uncanny import UncannyMagazineScraper
from zine2epub.scrapers.lightspeed import LightspeedMagazineScraper
from zine2epub.epub_generator import EPUBGenerator, generate_filename


SCRAPER_MAP = {
    "clarkesworld": ClarkesworldScraper,
    "uncanny": UncannyMagazineScraper,
    "lightspeed": LightspeedMagazineScraper,
}


@click.command()
@click.argument('url')
@click.option('-o', '--output', type=click.Path(), help='Output directory (default: current directory)')
def main(url: str, output: str = None):
    """Generate an EPUB from a zine issue URL.

    Supported zines:
    - Clarkesworld Magazine
    - Uncanny Magazine
    - Lightspeed Magazine

    Examples:

        zine2epub https://clarkesworldmagazine.com/

        zine2epub https://clarkesworldmagazine.com/issue_229

        zine2epub https://www.uncannymagazine.com/issues/uncanny-magazine-issue-sixty-seven/

        zine2epub https://www.lightspeedmagazine.com/issues/nov-2025-issue-186/
    """
    # Parse the URL
    click.echo(f"Parsing URL: {url}")
    parsed = parse_zine_url(url)

    if not parsed:
        click.echo(click.style("Error: URL not recognized", fg="red"), err=True)
        click.echo("\nSupported URL formats:")
        click.echo("  Clarkesworld: https://clarkesworldmagazine.com/ or https://clarkesworldmagazine.com/issue_NNN")
        click.echo("  Uncanny: https://www.uncannymagazine.com/issues/uncanny-magazine-issue-WRITTEN/")
        click.echo("  Lightspeed: https://www.lightspeedmagazine.com/issues/MMM-YYYY-issue-NNN/")
        sys.exit(1)

    zine_name, issue_num = parsed
    display_name = get_zine_display_name(zine_name)
    base_url = get_zine_base_url(zine_name)

    click.echo(f"Detected: {display_name}")

    # Create zine object
    scraper_class = SCRAPER_MAP.get(zine_name)
    if not scraper_class:
        click.echo(click.style(f"Error: No scraper found for {zine_name}", fg="red"), err=True)
        sys.exit(1)

    zine = Zine(
        name=zine_name,
        display_name=display_name,
        base_url=base_url,
        scraper_class=scraper_class,
    )

    scraper = zine.get_scraper()

    try:
        # Determine issue number if homepage URL
        if issue_num is None:
            click.echo("Fetching current issue information...")
            # For Clarkesworld homepage, get the current issue number from meta tag
            from curl_cffi import requests
            from lxml import html as lxml_html
            import re

            response = requests.Session(impersonate="chrome136").get(base_url)
            tree = lxml_html.fromstring(response.text)
            meta_desc = tree.cssselect('meta[name="description"]')
            if meta_desc:
                desc = meta_desc[0].get('content', '')
                issue_match = re.search(r'Issue\s+(\d+)', desc, re.I)
                if issue_match:
                    issue_num = int(issue_match.group(1))

            if issue_num is None:
                click.echo(click.style("Error: Could not determine issue number", fg="red"), err=True)
                sys.exit(1)

        click.echo(f"Issue: {issue_num}")

        # Fetch issue details
        click.echo("Fetching issue details...")
        from zine2epub.models import Issue
        from datetime import datetime

        # Create a basic Issue object
        issue = Issue(
            number=issue_num,
            title=f"Issue {issue_num}",
            issue_date=datetime.now().date(),
            cover_url="",
        )

        # Get full details
        issue_with_articles = scraper.get_issue_details(issue)

        if not issue_with_articles.articles:
            click.echo(click.style("Error: No articles found in issue", fg="red"), err=True)
            sys.exit(1)

        click.echo(f"Found {len(issue_with_articles.articles)} articles")

        # Fetch cover image
        click.echo("Downloading cover image...")
        try:
            issue_with_articles.cover_image_data = scraper.fetch_cover_image(issue_with_articles)
        except Exception as e:
            click.echo(click.style(f"Warning: Could not fetch cover image: {e}", fg="yellow"))

        # Fetch article content
        for idx, article in enumerate(issue_with_articles.articles, 1):
            if article.is_available:
                click.echo(f"Downloading article {idx}/{len(issue_with_articles.articles)}: {article.title}")
                try:
                    article.html_content = scraper.get_article_content(article)
                except Exception as e:
                    click.echo(click.style(f"Warning: Could not fetch article '{article.title}': {e}", fg="yellow"))
            else:
                click.echo(f"Skipping unavailable article {idx}/{len(issue_with_articles.articles)}: {article.title}")

        # Generate EPUB
        click.echo("Generating EPUB...")
        generator = EPUBGenerator(display_name)
        filename = generate_filename(display_name, issue_with_articles)

        # Determine output path
        if output:
            output_dir = Path(output)
            output_dir.mkdir(parents=True, exist_ok=True)
            output_path = str(output_dir / filename)
        else:
            output_path = str(Path.cwd() / filename)

        epub_path = generator.generate(issue_with_articles, output_path)

        click.echo(click.style(f"\nSuccess! EPUB saved to: {epub_path}", fg="green", bold=True))

    except Exception as e:
        click.echo(click.style(f"Error: {e}", fg="red"), err=True)
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        scraper.close()


if __name__ == "__main__":
    main()
