"""Confirmation dialog."""

from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import ModalScreen
from textual.widgets import Button, Label
from textual.containers import Vertical, Horizontal


class ConfirmDialog(ModalScreen[bool]):
    """Simple yes/no confirmation dialog."""

    BINDINGS = [
        Binding("escape", "cancel", "Cancel"),
        Binding("y", "confirm", "Yes"),
        Binding("n", "cancel", "No"),
    ]

    DEFAULT_CSS = """
    ConfirmDialog {
        align: center middle;
    }

    #confirm-dialog {
        width: 50;
        height: auto;
        border: thick $error;
        background: $surface;
        padding: 1 2;
    }

    #confirm-message {
        margin: 1 0;
        text-align: center;
    }

    #confirm-button-row {
        height: 3;
        margin-top: 1;
        align: center middle;
    }

    #confirm-button-row Button {
        margin: 0 1;
    }
    """

    def __init__(self, message: str):
        super().__init__()
        self._message = message

    def compose(self) -> ComposeResult:
        with Vertical(id="confirm-dialog"):
            yield Label(self._message, id="confirm-message")
            with Horizontal(id="confirm-button-row"):
                yield Button("Yes (y)", variant="error", id="btn-yes")
                yield Button("No (n)", variant="default", id="btn-no")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-yes":
            self.dismiss(True)
        else:
            self.dismiss(False)

    def action_confirm(self) -> None:
        self.dismiss(True)

    def action_cancel(self) -> None:
        self.dismiss(False)
