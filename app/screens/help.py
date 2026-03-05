"""Universal help modal for URL Shortener TUI."""

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical, Horizontal
from textual.screen import ModalScreen
from textual.widgets import Button, Label, Static


class HelpModal(ModalScreen[None]):
    """A single help surface reachable from anywhere in the app."""

    BINDINGS = [
        Binding("escape", "close", "Close"),
        Binding("h", "close", "Close"),
    ]

    CSS = """
    HelpModal {
        align: center middle;
    }

    #help-dialog {
        width: 90;
        height: auto;
        max-height: 35;
        border: thick $accent;
        background: $surface;
        padding: 1 2;
    }

    #help-title {
        text-style: bold;
        width: 100%;
        content-align: center middle;
        margin-bottom: 1;
    }

    .help-section-title {
        text-style: bold;
        color: $accent;
        margin-top: 1;
    }

    .help-line {
        color: $text;
    }

    #help-footer {
        margin-top: 1;
        color: $text-muted;
    }

    #help-buttons {
        margin-top: 1;
        align: center middle;
        height: 3;
    }
    """

    def compose(self) -> ComposeResult:
        with Vertical(id="help-dialog"):
            yield Label("❓ URL Shortener — Help", id="help-title")

            yield Static("Core Operations", classes="help-section-title")
            yield Static("• n: Create URL", classes="help-line")
            yield Static("• Enter: View URL details", classes="help-line")
            yield Static("• d: Delete selected URL", classes="help-line")
            yield Static("• /: Search URLs", classes="help-line")
            yield Static("• Esc: Clear search / close modal", classes="help-line")
            yield Static("• r: Refresh list", classes="help-line")

            yield Static("URL Detail", classes="help-section-title")
            yield Static("• Copy short URL", classes="help-line")
            yield Static("• Edit original URL + title", classes="help-line")
            yield Static("• Delete URL", classes="help-line")

            yield Static("Settings + Server Control", classes="help-section-title")
            yield Static("• s: Open settings", classes="help-line")
            yield Static("• Configure server port and base URL", classes="help-line")
            yield Static("• Toggle redirect server on/off", classes="help-line")
            yield Static("• Saving applies settings and restarts server when needed", classes="help-line")

            yield Static("Navigation", classes="help-section-title")
            yield Static("• h: Open/close help from any screen", classes="help-line")
            yield Static("• q or Ctrl+Q: Quit app", classes="help-line")

            yield Static("Tip: A Nerd Mono font is recommended for best alignment, but optional.", id="help-footer")

            with Horizontal(id="help-buttons"):
                yield Button("Close", variant="primary", id="close-help")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "close-help":
            self.dismiss(None)

    def action_close(self) -> None:
        self.dismiss(None)
