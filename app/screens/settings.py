"""Settings modal dialog for configuring the URL shortener."""

from typing import Optional

from textual.app import ComposeResult
from textual.containers import Vertical, Horizontal
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label, Switch

from ..database import Database
from ..shortener import InvalidURLError, validate_base_url


class SettingsModal(ModalScreen[Optional[dict]]):
    """Modal dialog for application settings."""

    CSS = """
    SettingsModal {
        align: center middle;
    }
    #settings-dialog {
        width: 65;
        height: auto;
        max-height: 22;
        border: thick $accent;
        background: $surface;
        padding: 1 2;
    }
    #settings-title {
        text-align: center;
        text-style: bold;
        width: 100%;
        margin-bottom: 1;
    }
    .settings-label {
        margin-top: 1;
        color: $text-muted;
    }
    .settings-hint {
        color: $text-disabled;
        margin-bottom: 0;
    }
    #server-toggle-row {
        height: 3;
        margin-top: 1;
    }
    #server-toggle-row Label {
        padding: 1 1;
    }
    #settings-error {
        color: $error;
        margin-top: 1;
        display: none;
    }
    #settings-error.visible {
        display: block;
    }
    #settings-buttons {
        margin-top: 1;
        height: 3;
        align: center middle;
    }
    #settings-buttons Button {
        margin: 0 1;
    }
    """

    BINDINGS = [
        ("escape", "cancel", "Cancel"),
    ]

    def __init__(self, db: Database, **kwargs):
        super().__init__(**kwargs)
        self.db = db

    def compose(self) -> ComposeResult:
        settings = self.db.get_all_settings()
        port = settings.get("server_port", "8080")
        base_url = settings.get("base_url", "http://localhost:8080")
        server_enabled = settings.get("server_enabled", "1") == "1"

        with Vertical(id="settings-dialog"):
            yield Label("⚙ Settings", id="settings-title")

            yield Label("Server Port:", classes="settings-label")
            yield Input(value=port, id="port-input", type="integer")
            yield Label(
                "Port for the redirect server (requires restart)",
                classes="settings-hint",
            )

            yield Label("Base URL:", classes="settings-label")
            yield Input(value=base_url, id="base-url-input")
            yield Label(
                "URL prefix for generated short links",
                classes="settings-hint",
            )

            with Horizontal(id="server-toggle-row"):
                yield Label("Server enabled:")
                yield Switch(value=server_enabled, id="server-toggle")

            yield Label("", id="settings-error")

            with Horizontal(id="settings-buttons"):
                yield Button("Save", variant="primary", id="save-btn")
                yield Button("Cancel", variant="default", id="cancel-btn")

    def on_mount(self) -> None:
        self.query_one("#port-input", Input).focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "save-btn":
            self._save_settings()
        elif event.button.id == "cancel-btn":
            self.dismiss(None)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        self._save_settings()

    def _save_settings(self) -> None:
        """Validate and save settings."""
        port_str = self.query_one("#port-input", Input).value.strip()
        base_url = self.query_one("#base-url-input", Input).value.strip()
        server_enabled = self.query_one("#server-toggle", Switch).value

        # Validate port
        try:
            port = int(port_str)
            if not (1 <= port <= 65535):
                raise ValueError()
        except (ValueError, TypeError):
            self._show_error("Port must be a number between 1 and 65535.")
            return

        # Validate base URL
        try:
            base_url = validate_base_url(base_url)
        except InvalidURLError as exc:
            self._show_error(str(exc))
            return

        # Save to database
        self.db.set_setting("server_port", str(port))
        self.db.set_setting("base_url", base_url)
        self.db.set_setting("server_enabled", "1" if server_enabled else "0")

        result = {
            "server_port": port,
            "base_url": base_url,
            "server_enabled": server_enabled,
        }
        self.dismiss(result)

    def _show_error(self, message: str) -> None:
        label = self.query_one("#settings-error", Label)
        label.update(f"⚠ {message}")
        label.add_class("visible")

    def action_cancel(self) -> None:
        self.dismiss(None)
