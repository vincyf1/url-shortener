"""Create new URL modal screen."""

from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label, Static
from textual.containers import Vertical, Horizontal
from textual import work

from ..database import Database
from ..shortener import create_short_url, InvalidURLError, CodeExistsError, CodeGenerationError
from ..clipboard import copy_to_clipboard


class CreateURLModal(ModalScreen[dict | None]):
    """Modal dialog for creating a new short URL."""

    BINDINGS = [
        Binding("escape", "cancel", "Cancel", show=True),
    ]

    DEFAULT_CSS = """
    CreateURLModal {
        align: center middle;
    }

    #create-dialog {
        width: 70;
        height: auto;
        max-height: 24;
        border: thick $accent;
        background: $surface;
        padding: 1 2;
    }

    #create-dialog Label {
        margin-top: 1;
    }

    #create-dialog Input {
        margin-bottom: 1;
    }

    #result-area {
        height: auto;
        margin-top: 1;
        padding: 1;
        background: $boost;
        display: none;
    }

    #button-row {
        height: 3;
        margin-top: 1;
        align: center middle;
    }

    #button-row Button {
        margin: 0 1;
    }
    """

    def __init__(self, db: Database):
        super().__init__()
        self.db = db
        self.base_url = db.get_setting("base_url", "http://localhost:8080")
        self._created_record: dict | None = None

    def compose(self) -> ComposeResult:
        with Vertical(id="create-dialog"):
            yield Label("Create Short URL", id="dialog-title")
            yield Label("Long URL:")
            yield Input(placeholder="https://example.com/very/long/url", id="url-input")
            yield Label("Custom short code (optional):")
            yield Input(placeholder="Leave blank for auto-generated", id="code-input")
            yield Static("", id="result-area")
            with Horizontal(id="button-row"):
                yield Button("Create", variant="primary", id="btn-create")
                yield Button("Cancel", variant="default", id="btn-cancel")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-create":
            self._do_create()
        elif event.button.id == "btn-cancel":
            self.dismiss(None)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "url-input":
            self.query_one("#code-input", Input).focus()
        elif event.input.id == "code-input":
            self._do_create()

    @work(thread=True)
    def _do_create(self) -> None:
        url = self.app.call_from_thread(lambda: self.query_one("#url-input", Input).value.strip())
        custom_code = self.app.call_from_thread(lambda: self.query_one("#code-input", Input).value.strip())

        try:
            record = create_short_url(
                self.db,
                original_url=url,
                custom_code=custom_code if custom_code else None,
            )
        except (InvalidURLError, CodeExistsError, CodeGenerationError) as exc:
            self.app.call_from_thread(self.notify, str(exc), severity="error")
            return

        short_url = f"{self.base_url}/{record['short_code']}"
        self._created_record = record

        def _show_result():
            result = self.query_one("#result-area", Static)
            result.update(f"✓ Created: {short_url}")
            result.styles.display = "block"
            # Try clipboard
            ok, msg = copy_to_clipboard(short_url)
            if ok:
                self.notify("Short URL copied to clipboard!", severity="information")
            else:
                self.notify(msg, severity="warning")
            self.dismiss(record)

        self.app.call_from_thread(_show_result)

    def action_cancel(self) -> None:
        self.dismiss(None)
