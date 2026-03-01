"""URL detail modal and delete confirmation dialog."""

from typing import Optional

from textual import work
from textual.app import ComposeResult
from textual.containers import Vertical, Horizontal
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label, Static

from ..database import Database


class DeleteConfirmModal(ModalScreen[bool]):
    """Confirmation dialog for deleting a URL."""

    CSS = """
    DeleteConfirmModal {
        align: center middle;
    }
    #confirm-dialog {
        width: 50;
        height: auto;
        border: thick $error;
        background: $surface;
        padding: 1 2;
    }
    #confirm-title {
        text-align: center;
        text-style: bold;
        width: 100%;
        margin-bottom: 1;
    }
    #confirm-message {
        text-align: center;
        width: 100%;
        margin-bottom: 1;
    }
    #confirm-buttons {
        height: 3;
        align: center middle;
    }
    #confirm-buttons Button {
        margin: 0 1;
    }
    """

    BINDINGS = [
        ("escape", "cancel", "Cancel"),
    ]

    def __init__(self, short_code: str, **kwargs):
        super().__init__(**kwargs)
        self.short_code = short_code

    def compose(self) -> ComposeResult:
        with Vertical(id="confirm-dialog"):
            yield Label("⚠ Delete URL?", id="confirm-title")
            yield Label(
                f"Are you sure you want to delete /{self.short_code}?",
                id="confirm-message",
            )
            with Horizontal(id="confirm-buttons"):
                yield Button("Delete", variant="error", id="confirm-yes")
                yield Button("Cancel", variant="default", id="confirm-no")

    def on_mount(self) -> None:
        self.query_one("#confirm-no", Button).focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "confirm-yes":
            self.dismiss(True)
        else:
            self.dismiss(False)

    def action_cancel(self) -> None:
        self.dismiss(False)


class URLDetailModal(ModalScreen[Optional[str]]):
    """Modal showing full details of a URL, with edit and delete options."""

    CSS = """
    URLDetailModal {
        align: center middle;
    }
    #detail-dialog {
        width: 75;
        height: auto;
        max-height: 30;
        border: thick $accent;
        background: $surface;
        padding: 1 2;
    }
    #detail-title {
        text-align: center;
        text-style: bold;
        width: 100%;
        margin-bottom: 1;
    }
    .detail-row {
        height: auto;
        margin-bottom: 0;
    }
    .detail-key {
        color: $text-muted;
        width: 16;
    }
    .detail-value {
        width: 1fr;
    }
    #edit-section {
        display: none;
        margin-top: 1;
        border-top: solid $accent;
        padding-top: 1;
    }
    #edit-section.visible {
        display: block;
    }
    .edit-label {
        margin-top: 1;
        color: $text-muted;
    }
    #detail-error {
        color: $error;
        margin-top: 1;
        display: none;
    }
    #detail-error.visible {
        display: block;
    }
    #detail-buttons {
        margin-top: 1;
        height: 3;
        align: center middle;
    }
    #detail-buttons Button {
        margin: 0 1;
    }
    """

    BINDINGS = [
        ("escape", "close", "Close"),
    ]

    def __init__(self, db: Database, url_data: dict, **kwargs):
        super().__init__(**kwargs)
        self.db = db
        self.url_data = url_data

    def compose(self) -> ComposeResult:
        base_url = self.db.get_setting("base_url", "http://localhost:8080")
        short_url = f"{base_url}/{self.url_data['short_code']}"

        with Vertical(id="detail-dialog"):
            yield Label("📋 URL Details", id="detail-title")

            with Horizontal(classes="detail-row"):
                yield Label("Short Code:", classes="detail-key")
                yield Label(f"/{self.url_data['short_code']}", classes="detail-value")

            with Horizontal(classes="detail-row"):
                yield Label("Short URL:", classes="detail-key")
                yield Label(short_url, classes="detail-value", id="short-url-display")

            with Horizontal(classes="detail-row"):
                yield Label("Original URL:", classes="detail-key")
                yield Label(
                    self.url_data["original_url"],
                    classes="detail-value",
                    id="original-url-display",
                )

            with Horizontal(classes="detail-row"):
                yield Label("Title:", classes="detail-key")
                yield Label(
                    self.url_data.get("title") or "—",
                    classes="detail-value",
                )

            with Horizontal(classes="detail-row"):
                yield Label("Created:", classes="detail-key")
                yield Label(
                    self.url_data.get("created_at", "Unknown"),
                    classes="detail-value",
                )

            with Horizontal(classes="detail-row"):
                yield Label("Clicks:", classes="detail-key")
                yield Label(
                    str(self.url_data.get("click_count", 0)),
                    classes="detail-value",
                )

            # Edit section (hidden by default)
            with Vertical(id="edit-section"):
                yield Label("Edit URL:", classes="edit-label")
                yield Input(
                    value=self.url_data["original_url"],
                    id="edit-url-input",
                )
                yield Label("Edit Title:", classes="edit-label")
                yield Input(
                    value=self.url_data.get("title") or "",
                    id="edit-title-input",
                )

            yield Label("", id="detail-error")

            with Horizontal(id="detail-buttons"):
                yield Button("Copy URL", variant="primary", id="copy-btn")
                yield Button("Edit", variant="warning", id="edit-btn")
                yield Button("Delete", variant="error", id="delete-btn")
                yield Button("Close", variant="default", id="close-btn")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "copy-btn":
            self._copy_short_url()
        elif event.button.id == "edit-btn":
            self._toggle_edit()
        elif event.button.id == "delete-btn":
            self._delete_url()
        elif event.button.id == "close-btn":
            self.dismiss(None)

    def _copy_short_url(self) -> None:
        """Copy the short URL to clipboard."""
        base_url = self.db.get_setting("base_url", "http://localhost:8080")
        short_url = f"{base_url}/{self.url_data['short_code']}"
        try:
            import pyperclip
            pyperclip.copy(short_url)
            self.notify(f"Copied: {short_url}", title="Copied!")
        except Exception:
            self.notify(
                f"Copy manually: {short_url}",
                title="Clipboard unavailable",
                severity="warning",
            )

    def _toggle_edit(self) -> None:
        """Toggle the edit section visibility."""
        edit_section = self.query_one("#edit-section")
        edit_btn = self.query_one("#edit-btn", Button)

        if edit_section.has_class("visible"):
            # Save changes
            self._save_edit()
        else:
            edit_section.add_class("visible")
            edit_btn.label = "Save"
            self.query_one("#edit-url-input", Input).focus()

    @work(thread=True)
    def _save_edit(self) -> None:
        """Save edits in a worker thread."""
        new_url = self.app.call_from_thread(
            lambda: self.query_one("#edit-url-input", Input).value.strip()
        )
        new_title = self.app.call_from_thread(
            lambda: self.query_one("#edit-title-input", Input).value.strip()
        )

        # Validate URL
        from ..shortener import validate_url, InvalidURLError
        try:
            new_url = validate_url(new_url)
        except InvalidURLError as e:
            self.app.call_from_thread(self._show_error, str(e))
            return

        result = self.db.update_url(
            self.url_data["short_code"],
            original_url=new_url,
            title=new_title or None,
        )

        if result:
            self.url_data = result
            self.app.call_from_thread(self._update_display_after_edit, result)
        else:
            self.app.call_from_thread(self._show_error, "Failed to save changes.")

    def _update_display_after_edit(self, result: dict) -> None:
        """Update UI after successful edit."""
        self.query_one("#original-url-display", Label).update(result["original_url"])
        edit_section = self.query_one("#edit-section")
        edit_section.remove_class("visible")
        edit_btn = self.query_one("#edit-btn", Button)
        edit_btn.label = "Edit"
        self._hide_error()
        self.notify("URL updated!", title="Saved")

    def _delete_url(self) -> None:
        """Delete the URL after confirmation."""
        self.app.push_screen(
            DeleteConfirmModal(self.url_data["short_code"]),
            callback=self._on_delete_confirmed,
        )

    def _on_delete_confirmed(self, confirmed: bool) -> None:
        if confirmed:
            self._do_delete()

    @work(thread=True)
    def _do_delete(self) -> None:
        """Perform deletion in a worker thread."""
        success = self.db.delete_url(self.url_data["short_code"])
        if success:
            self.app.call_from_thread(self.dismiss, "deleted")
            self.app.call_from_thread(
                self.notify,
                f"Deleted: /{self.url_data['short_code']}",
                title="Deleted",
            )
        else:
            self.app.call_from_thread(self._show_error, "Failed to delete.")

    def _show_error(self, message: str) -> None:
        label = self.query_one("#detail-error", Label)
        label.update(f"⚠ {message}")
        label.add_class("visible")

    def _hide_error(self) -> None:
        label = self.query_one("#detail-error", Label)
        label.remove_class("visible")

    def action_close(self) -> None:
        self.dismiss(None)
