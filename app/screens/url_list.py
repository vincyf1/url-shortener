"""Main URL list screen — the primary view of the application."""

from datetime import datetime
from typing import Optional

from textual import work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import (
    DataTable,
    Footer,
    Header,
    Input,
    Label,
    Static,
)

from ..database import Database


class URLListScreen(Screen):
    """Main screen showing all shortened URLs in a table."""

    BINDINGS = [
        Binding("n", "new_url", "New URL"),
        Binding("d", "delete_url", "Delete"),
        Binding("enter", "view_detail", "Details"),
        Binding("slash", "search", "Search"),
        Binding("escape", "clear_search", "Clear Search"),
        Binding("s", "open_settings", "Settings"),
        Binding("r", "refresh", "Refresh"),
        Binding("q", "quit_app", "Quit"),
    ]

    CSS = """
    #server-status {
        dock: bottom;
        height: 1;
        padding: 0 1;
        background: $surface;
        color: $text-muted;
    }
    #search-bar {
        dock: top;
        height: 3;
        padding: 0 1;
        display: none;
    }
    #search-bar.visible {
        display: block;
    }
    #search-input {
        width: 100%;
    }
    #url-table {
        height: 1fr;
    }
    #empty-message {
        width: 100%;
        height: 100%;
        content-align: center middle;
        text-align: center;
        color: $text-muted;
    }
    """

    def __init__(self, db: Database, **kwargs):
        super().__init__(**kwargs)
        self.db = db
        self._search_query: Optional[str] = None

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Vertical(id="search-bar"):
            yield Input(placeholder="Search URLs... (Esc to clear)", id="search-input")
        yield DataTable(id="url-table")
        yield Static("", id="server-status")
        yield Footer()

    def on_mount(self) -> None:
        """Set up the data table and load URLs."""
        table = self.query_one("#url-table", DataTable)
        table.cursor_type = "row"
        table.add_columns("Code", "Original URL", "Created", "Clicks")
        self.load_urls()

    @work(thread=True)
    def load_urls(self) -> None:
        """Load URLs from database in a worker thread."""
        if self._search_query:
            urls = self.db.search_urls(self._search_query)
        else:
            urls = self.db.get_all_urls()
        self.app.call_from_thread(self._populate_table, urls)

    def _populate_table(self, urls: list[dict]) -> None:
        """Populate the data table with URL records (must run on main thread)."""
        table = self.query_one("#url-table", DataTable)
        table.clear()

        if not urls:
            # Show empty message
            try:
                empty = self.query_one("#empty-message", Static)
            except Exception:
                empty = None
            if empty is None:
                pass  # Table will just be empty
        else:
            pass

        for url in urls:
            # Truncate long URLs for display
            original = url["original_url"]
            if len(original) > 60:
                original = original[:57] + "..."

            # Format date
            try:
                dt = datetime.fromisoformat(url["created_at"])
                date_str = dt.strftime("%Y-%m-%d %H:%M")
            except (ValueError, TypeError):
                date_str = url["created_at"] or "Unknown"

            table.add_row(
                url["short_code"],
                original,
                date_str,
                str(url["click_count"]),
                key=url["short_code"],
            )

    def update_server_status(self, running: bool, port: int) -> None:
        """Update the server status bar."""
        status = self.query_one("#server-status", Static)
        if running:
            status.update(f"● Server running on port {port}")
        else:
            status.update("○ Server stopped")

    # --- Actions ---

    def action_new_url(self) -> None:
        """Open the create URL dialog."""
        from .create_url import CreateURLModal
        self.app.push_screen(CreateURLModal(self.db), callback=self._on_url_created)

    def _on_url_created(self, result: Optional[dict]) -> None:
        """Called when the create URL modal is dismissed."""
        if result:
            self.load_urls()
            self.notify(f"Created: /{result['short_code']}", title="URL Created")

    def action_delete_url(self) -> None:
        """Delete the selected URL (with confirmation)."""
        table = self.query_one("#url-table", DataTable)
        if table.row_count == 0:
            self.notify("No URLs to delete.", severity="warning")
            return

        try:
            row_key, _ = table.coordinate_to_cell_key(table.cursor_coordinate)
        except Exception:
            self.notify("Select a URL first.", severity="warning")
            return

        short_code = str(row_key)
        from .url_detail import DeleteConfirmModal
        self.app.push_screen(
            DeleteConfirmModal(short_code),
            callback=lambda confirmed: self._on_delete_confirmed(confirmed, short_code),
        )

    def _on_delete_confirmed(self, confirmed: bool, short_code: str) -> None:
        """Handle delete confirmation result."""
        if confirmed:
            self._do_delete(short_code)

    @work(thread=True)
    def _do_delete(self, short_code: str) -> None:
        """Perform the deletion in a worker thread."""
        success = self.db.delete_url(short_code)
        if success:
            self.app.call_from_thread(self.load_urls)
            self.app.call_from_thread(
                self.notify, f"Deleted: /{short_code}", title="URL Deleted"
            )
        else:
            self.app.call_from_thread(
                self.notify, "Failed to delete URL.", severity="error"
            )

    def action_view_detail(self) -> None:
        """View details of the selected URL."""
        table = self.query_one("#url-table", DataTable)
        if table.row_count == 0:
            return

        try:
            row_key, _ = table.coordinate_to_cell_key(table.cursor_coordinate)
        except Exception:
            return

        short_code = str(row_key)
        self._open_detail(short_code)

    @work(thread=True)
    def _open_detail(self, short_code: str) -> None:
        """Load URL details and open the detail modal."""
        url_data = self.db.get_url_by_code(short_code)
        if url_data:
            from .url_detail import URLDetailModal
            self.app.call_from_thread(
                self.app.push_screen,
                URLDetailModal(self.db, url_data),
                self._on_detail_closed,
            )
        else:
            self.app.call_from_thread(
                self.notify, "URL not found.", severity="error"
            )

    def _on_detail_closed(self, result: Optional[str]) -> None:
        """Called when the detail modal is closed."""
        # Refresh in case of edits
        self.load_urls()

    def action_search(self) -> None:
        """Show the search bar."""
        search_bar = self.query_one("#search-bar")
        search_bar.add_class("visible")
        search_input = self.query_one("#search-input", Input)
        search_input.focus()

    def action_clear_search(self) -> None:
        """Clear and hide the search bar."""
        search_bar = self.query_one("#search-bar")
        search_bar.remove_class("visible")
        search_input = self.query_one("#search-input", Input)
        search_input.value = ""
        self._search_query = None
        self.load_urls()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle search input submission."""
        if event.input.id == "search-input":
            query = event.value.strip()
            self._search_query = query if query else None
            self.load_urls()

    def action_open_settings(self) -> None:
        """Open the settings screen."""
        from .settings import SettingsModal
        self.app.push_screen(SettingsModal(self.db), callback=self._on_settings_closed)

    def _on_settings_closed(self, result: Optional[dict]) -> None:
        """Called when settings modal is closed."""
        if result:
            # Settings changed — the app will handle restarting the server
            self.app.apply_settings(result)

    def action_refresh(self) -> None:
        """Refresh the URL list."""
        self.load_urls()
        self.notify("Refreshed", timeout=1)

    def action_quit_app(self) -> None:
        """Quit the application."""
        self.app.exit()
