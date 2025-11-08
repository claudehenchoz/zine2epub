"""EPUB generation progress screen."""

from pathlib import Path

from textual.app import ComposeResult
from textual.containers import Container
from textual.screen import Screen
from textual.widgets import Header, Footer, ProgressBar, Label
from textual.worker import WorkerState

from zine2epub.models import Zine, Issue
from zine2epub.epub_generator import EPUBGenerator, generate_filename


class ProgressScreen(Screen):
    """Screen showing EPUB generation progress."""

    CSS = """
    ProgressScreen {
        align: center middle;
    }

    #progress-container {
        width: 70;
        height: auto;
        border: solid $accent;
        padding: 2;
    }

    #title {
        text-align: center;
        text-style: bold;
        padding: 1;
        color: $accent;
    }

    #status {
        text-align: center;
        padding: 1;
        color: $text;
    }

    ProgressBar {
        margin: 2 0;
    }
    """

    def __init__(self, zine: Zine, issue: Issue):
        """Initialize progress screen.

        Args:
            zine: The selected zine
            issue: The selected issue
        """
        super().__init__()
        self.zine = zine
        self.issue = issue
        self.epub_path: str | None = None

    def compose(self) -> ComposeResult:
        """Compose the screen layout."""
        yield Header()
        with Container(id="progress-container"):
            yield Label(f"Generating EPUB: {self.issue.title}", id="title")
            yield Label("Initializing...", id="status")
            yield ProgressBar(total=100, show_eta=False, id="progress")
        yield Footer()

    def on_mount(self) -> None:
        """Start EPUB generation when screen is mounted."""
        self.run_worker(self._generate_epub, thread=True)

    def _generate_epub(self) -> str:
        """Generate the EPUB file.

        Returns:
            Path to the generated EPUB file
        """
        scraper = self.zine.get_scraper()

        try:
            # Step 1: Get issue details (article list)
            self.call_from_thread(self.update_progress, "Fetching issue details...", 0.05)
            issue_with_articles = scraper.get_issue_details(self.issue)

            # Step 2: Fetch cover image
            self.call_from_thread(self.update_progress, "Downloading cover image...", 0.1)
            issue_with_articles.cover_image_data = scraper.fetch_cover_image(
                issue_with_articles
            )

            # Step 3: Fetch article content
            total_articles = len(issue_with_articles.articles)
            for idx, article in enumerate(issue_with_articles.articles):
                progress = 0.15 + (0.5 * (idx / total_articles))
                self.call_from_thread(self.update_progress, f"Downloading: {article.title}", progress)

                if article.is_available:
                    article.html_content = scraper.get_article_content(article)

            # Step 4: Generate EPUB
            self.call_from_thread(self.update_progress, "Generating EPUB...", 0.7)

            generator = EPUBGenerator(self.zine.display_name)
            filename = generate_filename(self.zine.display_name, issue_with_articles)
            output_path = str(Path.cwd() / filename)

            def epub_progress_callback(message: str, percentage: float):
                """Update progress from EPUB generator."""
                progress = 0.7 + (0.3 * percentage)
                self.call_from_thread(self.update_progress, message, progress)

            epub_path = generator.generate(
                issue_with_articles, output_path, epub_progress_callback
            )

            return epub_path

        finally:
            scraper.close()

    def update_progress(self, message: str, percentage: float) -> None:
        """Update the progress bar and status message.

        Args:
            message: Status message to display
            percentage: Progress percentage (0.0 to 1.0)
        """
        if not self.is_mounted:
            return

        progress_bar = self.query_one("#progress", ProgressBar)
        status_label = self.query_one("#status", Label)

        progress_bar.update(progress=int(percentage * 100))
        status_label.update(message)

    def on_worker_state_changed(self, event) -> None:
        """Handle worker state changes.

        Args:
            event: State change event
        """
        if event.worker.name == "_generate_epub":
            if event.state == WorkerState.SUCCESS:
                self.epub_path = event.worker.result
                # Switch to complete screen
                self.app.push_screen("complete", self.epub_path)
            elif event.state == WorkerState.ERROR:
                error = event.worker.error
                self.notify(f"Failed to generate EPUB: {error}", severity="error")
                self.app.pop_screen()
