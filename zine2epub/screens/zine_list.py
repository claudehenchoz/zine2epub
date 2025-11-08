"""Zine selection screen."""

from textual.app import ComposeResult
from textual.containers import Container
from textual.screen import Screen
from textual.widgets import Header, Footer, ListView, ListItem, Label
from textual.binding import Binding

from zine2epub.models import Zine


class ZineListScreen(Screen):
    """Screen for selecting a zine."""

    BINDINGS = [
        Binding("q", "quit", "Quit", priority=True),
        Binding("escape", "quit", "Quit"),
    ]

    CSS = """
    ZineListScreen {
        align: center middle;
    }

    #zine-container {
        width: 60;
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

    ListView {
        height: auto;
        max-height: 20;
    }

    ListItem {
        padding: 1 2;
    }

    ListItem:hover {
        background: $accent 20%;
    }
    """

    def __init__(self, zines: list[Zine]):
        """Initialize zine list screen.

        Args:
            zines: List of available zines
        """
        super().__init__()
        self.zines = zines

    def compose(self) -> ComposeResult:
        """Compose the screen layout."""
        yield Header()
        with Container(id="zine-container"):
            yield Label("Select a Zine", id="title")
            yield ListView(
                *[ListItem(Label(zine.display_name)) for zine in self.zines],
                id="zine-list"
            )
        yield Footer()

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        """Handle zine selection.

        Args:
            event: Selection event
        """
        selected_index = event.list_view.index
        if selected_index is not None:
            selected_zine = self.zines[selected_index]
            # Switch to issue list screen
            self.app.push_screen("issue_list", selected_zine)

    def action_quit(self) -> None:
        """Quit the application."""
        self.app.exit()
