"""EPUB generation completion screen."""

import subprocess
import sys
from pathlib import Path

from textual.app import ComposeResult
from textual.containers import Container, Horizontal
from textual.screen import Screen
from textual.widgets import Header, Footer, Button, Label
from textual.binding import Binding


class CompleteScreen(Screen):
    """Screen showing successful EPUB generation with action options."""

    BINDINGS = [
        Binding("escape", "back", "Back to List"),
        Binding("q", "quit", "Quit"),
    ]

    CSS = """
    CompleteScreen {
        align: center middle;
    }

    #complete-container {
        width: 70;
        height: auto;
        border: solid $success;
        padding: 2;
    }

    #title {
        text-align: center;
        text-style: bold;
        padding: 1;
        color: $success;
    }

    #message {
        text-align: center;
        padding: 1 2;
        color: $text;
    }

    #file-path {
        text-align: center;
        padding: 1 2;
        color: $accent;
        text-style: italic;
    }

    Horizontal {
        align: center middle;
        height: auto;
        padding: 2;
    }

    Button {
        margin: 0 1;
        min-width: 18;
    }
    """

    def __init__(self, epub_path: str):
        """Initialize complete screen.

        Args:
            epub_path: Path to the generated EPUB file
        """
        super().__init__()
        self.epub_path = Path(epub_path)

    def compose(self) -> ComposeResult:
        """Compose the screen layout."""
        yield Header()
        with Container(id="complete-container"):
            yield Label("EPUB Generation Complete!", id="title")
            yield Label(
                "Your EPUB file has been successfully created.",
                id="message"
            )
            yield Label(f"File: {self.epub_path.name}", id="file-path")
            with Horizontal():
                yield Button("Go Back to List", id="back-btn", variant="primary")
                yield Button("Open EPUB", id="open-epub-btn", variant="success")
                yield Button("Open Folder", id="open-folder-btn", variant="default")
        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses.

        Args:
            event: Button press event
        """
        button_id = event.button.id

        if button_id == "back-btn":
            self.action_back()
        elif button_id == "open-epub-btn":
            self.open_epub()
        elif button_id == "open-folder-btn":
            self.open_folder()

    def open_epub(self) -> None:
        """Open the EPUB file with the system default application."""
        try:
            if sys.platform == "win32":
                subprocess.run(["start", "", str(self.epub_path)], shell=True, check=True)
            elif sys.platform == "darwin":
                subprocess.run(["open", str(self.epub_path)], check=True)
            else:  # Linux and other Unix-like systems
                subprocess.run(["xdg-open", str(self.epub_path)], check=True)

            self.notify("Opening EPUB file...", severity="information")
        except Exception as e:
            self.notify(f"Failed to open EPUB: {e}", severity="error")

    def open_folder(self) -> None:
        """Open the folder containing the EPUB file."""
        folder_path = self.epub_path.parent

        try:
            if sys.platform == "win32":
                subprocess.run(["explorer", str(folder_path)], check=True)
            elif sys.platform == "darwin":
                subprocess.run(["open", str(folder_path)], check=True)
            else:  # Linux and other Unix-like systems
                subprocess.run(["xdg-open", str(folder_path)], check=True)

            self.notify("Opening folder...", severity="information")
        except Exception as e:
            self.notify(f"Failed to open folder: {e}", severity="error")

    def action_back(self) -> None:
        """Go back to the zine list (pop all screens)."""
        # Pop back to the main zine list screen
        # We need to pop: complete -> progress -> issue_list
        self.app.pop_screen()  # Pop complete
        self.app.pop_screen()  # Pop progress
        self.app.pop_screen()  # Pop issue_list

    def action_quit(self) -> None:
        """Quit the application."""
        self.app.exit()
