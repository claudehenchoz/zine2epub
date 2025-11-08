"""Test the fixed Clarkesworld scraper."""

from zine2epub.models import Zine
from zine2epub.scrapers.clarkesworld import ClarkesworldScraper

def test_clarkesworld_scraper():
    """Test Clarkesworld scraper functionality."""

    # Create zine
    zine = Zine(
        name="clarkesworld",
        display_name="Clarkesworld Magazine",
        base_url="https://clarkesworldmagazine.com",
        scraper_class=ClarkesworldScraper,
    )

    scraper = zine.get_scraper()

    print("Testing Clarkesworld scraper...\n")

    # Test 1: Get issues
    print("1. Fetching issues...")
    try:
        issues = scraper.get_issues()
        print(f"   SUCCESS: Found {len(issues)} issues")
        if issues:
            print(f"   Latest: {issues[0].title} ({issues[0].issue_date})")
            print(f"   URL: {issues[0].cover_url}\n")
    except Exception as e:
        print(f"   FAILED: {e}\n")
        return

    # Test 2: Get issue details
    if issues:
        test_issue = issues[0]
        print(f"2. Fetching details for {test_issue.title}...")
        try:
            issue_with_articles = scraper.get_issue_details(test_issue)
            print(f"   SUCCESS: Found {len(issue_with_articles.articles)} articles")
            for i, article in enumerate(issue_with_articles.articles[:5], 1):
                print(f"   {i}. {article.title}")
                print(f"      by {article.author}")
                print(f"      {article.content_url}\n")
        except Exception as e:
            print(f"   FAILED: {e}\n")
            return

        # Test 3: Get article content
        if issue_with_articles.articles:
            test_article = issue_with_articles.articles[0]
            print(f"3. Fetching content for '{test_article.title}'...")
            try:
                content = scraper.get_article_content(test_article)
                print(f"   SUCCESS: Retrieved {len(content)} characters")
                print(f"   Preview: {content[:200]}...\n")
            except Exception as e:
                print(f"   FAILED: {e}\n")
                return

    scraper.close()
    print("All tests passed!")

if __name__ == "__main__":
    test_clarkesworld_scraper()
