"""Issue selection screen."""

from textual.app import ComposeResult
from textual.containers import Container
from textual.screen import Screen
from textual.widgets import Header, Footer, DataTable, Label, LoadingIndicator
from textual.binding import Binding
from textual.worker import WorkerState

from zine2epub.models import Zine, Issue


class IssueListScreen(Screen):
    """Screen for selecting an issue from a zine."""

    BINDINGS = [
        Binding("escape", "back", "Back"),
        Binding("q", "quit", "Quit"),
    ]

    CSS = """
    IssueListScreen {
        align: center middle;
    }

    #issue-container {
        width: 80;
        height: auto;
        border: solid $accent;
        padding: 1 2;
    }

    #title {
        text-align: center;
        text-style: bold;
        padding: 1;
        color: $accent;
    }

    #loading {
        text-align: center;
        padding: 2;
    }

    DataTable {
        height: auto;
        max-height: 25;
    }
    """

    def __init__(self, zine: Zine):
        """Initialize issue list screen.

        Args:
            zine: The selected zine
        """
        super().__init__()
        self.zine = zine
        self.issues: list[Issue] = []

    def compose(self) -> ComposeResult:
        """Compose the screen layout."""
        yield Header()
        with Container(id="issue-container"):
            yield Label(f"{self.zine.display_name} - Select Issue", id="title")
            yield LoadingIndicator(id="loading")
            yield DataTable(id="issue-table", show_cursor=True)
        yield Footer()

    def on_mount(self) -> None:
        """Load issues when screen is mounted."""
        # Configure the data table
        table = self.query_one(DataTable)
        table.add_columns("Issue #", "Date", "Title", "Status")
        table.cursor_type = "row"
        table.display = False  # Hide until data is loaded

        # Load issues in background
        self.run_worker(self._load_issues, thread=True)

    def _load_issues(self) -> list[Issue]:
        """Load issues from the zine scraper.

        Returns:
            List of issues
        """
        scraper = self.zine.get_scraper()
        try:
            return scraper.get_issues()
        finally:
            scraper.close()

    def on_worker_state_changed(self, event) -> None:
        """Handle worker state changes.

        Args:
            event: State change event
        """
        if event.worker.name == "_load_issues":
            if event.state == WorkerState.SUCCESS:
                self.issues = event.worker.result
                self.populate_table()
            elif event.state == WorkerState.ERROR:
                self.notify("Failed to load issues", severity="error")
                self.app.pop_screen()

    def populate_table(self) -> None:
        """Populate the data table with issues."""
        table = self.query_one(DataTable)
        loading = self.query_one("#loading", LoadingIndicator)

        loading.display = False
        table.display = True

        for issue in self.issues:
            status = "Complete" if issue.is_complete else "Incomplete"
            table.add_row(
                str(issue.number),
                issue.date_str,
                issue.title,
                status,
            )

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Handle issue selection.

        Args:
            event: Row selection event
        """
        row_index = event.cursor_row
        if row_index is not None and row_index < len(self.issues):
            selected_issue = self.issues[row_index]
            # Switch to progress screen to generate EPUB
            self.app.push_screen("progress", (self.zine, selected_issue))

    def action_back(self) -> None:
        """Go back to zine list."""
        self.app.pop_screen()

    def action_quit(self) -> None:
        """Quit the application."""
        self.app.exit()
