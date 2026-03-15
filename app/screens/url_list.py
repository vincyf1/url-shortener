"""Main URL list screen — the primary view of the application."""

from datetime import datetime
from typing import Optional

from textual import work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.events import Key
from textual.screen import Screen
from textual.widgets import DataTable, Footer, Header, Input, Static

from ..database import Database


class URLListScreen(Screen):
    """Main screen showing all shortened URLs in a table."""

    BINDINGS = [
        Binding("n", "new_url", "New URL", priority=True),
        Binding("d", "delete_url", "Delete"),
        Binding("enter", "view_detail", "Details"),
        Binding("slash", "search", "Search"),
        Binding("escape", "clear_search", "Clear Search"),
        Binding("s", "open_settings", "Settings"),
        Binding("h", "open_help", "Help"),
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
        height: 1fr;
        content-align: center middle;
        text-align: center;
        color: $text-muted;
        display: none;
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
        yield Static("No URLs yet. Press 'n' to create one.", id="empty-message")
        yield Static("", id="server-status")
        yield Footer()

    def on_mount(self) -> None:
        """Set up the data table and load URLs."""
        table = self.query_one("#url-table", DataTable)
        table.cursor_type = "row"
        table.add_columns("Code", "Original URL", "Created", "Clicks")
        # Keep focus on the screen so printable shortcuts like `n` are reliable.
        self.set_focus(None)
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
        empty = self.query_one("#empty-message", Static)
        table.clear()

        if not urls:
            table.styles.display = "none"
            empty.styles.display = "block"
            return

        empty.styles.display = "none"
        table.styles.display = "block"

        for url in urls:
            original = url["original_url"]
            if len(original) > 60:
                original = original[:57] + "..."

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
            status.update(f"● Server running on port {port}  |  Press h for help")
        else:
            status.update("○ Server stopped  |  Press h for help")

    def action_new_url(self) -> None:
        from .create_url import CreateURLModal

        self.app.push_screen(CreateURLModal(self.db), callback=self._on_url_created)

    def _on_url_created(self, result: Optional[dict]) -> None:
        if result:
            self.load_urls()
            self.notify(f"Created: /{result['short_code']}", title="URL Created")

    def action_delete_url(self) -> None:
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
        if confirmed:
            self._do_delete(short_code)

    @work(thread=True)
    def _do_delete(self, short_code: str) -> None:
        success = self.db.delete_url(short_code)
        if success:
            self.app.call_from_thread(self.load_urls)
            self.app.call_from_thread(self.notify, f"Deleted: /{short_code}", title="URL Deleted")
        else:
            self.app.call_from_thread(self.notify, "Failed to delete URL.", severity="error")

    def action_view_detail(self) -> None:
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
        url_data = self.db.get_url_by_code(short_code)
        if url_data:
            from .url_detail import URLDetailModal

            self.app.call_from_thread(
                self.app.push_screen,
                URLDetailModal(self.db, url_data),
                self._on_detail_closed,
            )
        else:
            self.app.call_from_thread(self.notify, "URL not found.", severity="error")

    def _on_detail_closed(self, result: Optional[str]) -> None:
        self.load_urls()

    def on_key(self, event: Key) -> None:
        """Fallback key handler for printable shortcuts when table focus swallows bindings."""
        if event.key == "n" and not isinstance(self.app.focused, Input):
            self.action_new_url()
            event.stop()

    def action_search(self) -> None:
        search_bar = self.query_one("#search-bar")
        search_bar.add_class("visible")
        self.query_one("#search-input", Input).focus()

    def action_clear_search(self) -> None:
        search_bar = self.query_one("#search-bar")
        search_bar.remove_class("visible")
        search_input = self.query_one("#search-input", Input)
        search_input.value = ""
        self._search_query = None
        self.load_urls()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "search-input":
            query = event.value.strip()
            self._search_query = query if query else None
            self.load_urls()

    def action_open_settings(self) -> None:
        from .settings import SettingsModal

        self.app.push_screen(SettingsModal(self.db), callback=self._on_settings_closed)

    def _on_settings_closed(self, result: Optional[dict]) -> None:
        if result:
            self.app.apply_settings(result)

    def action_open_help(self) -> None:
        self.app.action_open_help()

    def action_refresh(self) -> None:
        self.load_urls()
        self.notify("Refreshed", timeout=1)

    def action_quit_app(self) -> None:
        self.app.exit()
