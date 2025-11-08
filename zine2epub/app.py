"""Main Textual application for zine2epub."""

from textual.app import App

from zine2epub.models import Zine
from zine2epub.scrapers.clarkesworld import ClarkesworldScraper
from zine2epub.scrapers.uncanny import UncannyMagazineScraper
from zine2epub.scrapers.lightspeed import LightspeedMagazineScraper
from zine2epub.screens.zine_list import ZineListScreen
from zine2epub.screens.issue_list import IssueListScreen
from zine2epub.screens.progress import ProgressScreen
from zine2epub.screens.complete import CompleteScreen


class Zine2EpubApp(App):
    """Main TUI application for zine2epub."""

    TITLE = "zine2epub"
    SUB_TITLE = "Convert online fiction zines to EPUB"

    CSS = """
    Screen {
        background: $surface;
    }
    """

    def __init__(self):
        """Initialize the application."""
        super().__init__()

        # Define available zines
        self.zines = [
            Zine(
                name="clarkesworld",
                display_name="Clarkesworld Magazine",
                base_url="https://clarkesworldmagazine.com",
                scraper_class=ClarkesworldScraper,
            ),
            Zine(
                name="uncanny",
                display_name="Uncanny Magazine",
                base_url="https://uncannymagazine.com",
                scraper_class=UncannyMagazineScraper,
            ),
            Zine(
                name="lightspeed",
                display_name="Lightspeed Magazine",
                base_url="https://lightspeedmagazine.com",
                scraper_class=LightspeedMagazineScraper,
            ),
        ]

    def on_mount(self) -> None:
        """Set up the application when mounted."""
        # Install custom screens
        self.install_screen(ZineListScreen(self.zines), name="zine_list")

        # Push the initial screen
        self.push_screen("zine_list")

    def push_screen(self, screen, *args):
        """Override push_screen to handle screen instantiation.

        Args:
            screen: Screen name or instance
            *args: Arguments to pass to screen constructor
        """
        if screen == "issue_list":
            # args[0] is the selected Zine
            screen_instance = IssueListScreen(args[0])
            super().push_screen(screen_instance)
        elif screen == "progress":
            # args[0] is tuple of (Zine, Issue)
            zine, issue = args[0]
            screen_instance = ProgressScreen(zine, issue)
            super().push_screen(screen_instance)
        elif screen == "complete":
            # args[0] is the epub_path
            screen_instance = CompleteScreen(args[0])
            super().push_screen(screen_instance)
        else:
            super().push_screen(screen, *args)


def run():
    """Run the zine2epub application."""
    app = Zine2EpubApp()
    app.run()
