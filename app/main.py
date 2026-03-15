"""URL Shortener TUI — Main Application.

Entry point for the Textual-based URL shortener.
Manages the TUI lifecycle, redirect server, and database.
"""

import logging
from typing import Optional

from textual.app import App, ComposeResult
from textual.binding import Binding

from .database import Database
from .server import RedirectServer
from .screens.url_list import URLListScreen

# Suppress noisy loggers
logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)


class URLShortenerApp(App):
    """Textual application for managing shortened URLs."""

    TITLE = "URL Shortener"
    SUB_TITLE = "Terminal URL Shortener & Redirect Server"

    CSS_PATH = "styles/app.tcss"

    SCREENS = {
        "url_list": URLListScreen,
    }

    BINDINGS = [
        Binding("n", "new_url", "New URL", priority=True),
        Binding("h", "open_help", "Help", priority=True),
        Binding("ctrl+q", "quit", "Quit", priority=True),
        Binding("ctrl+c", "quit", "Quit", show=False, priority=True),
    ]

    def __init__(self, db_path=None, db_backend=None, db_dsn=None, **kwargs):
        super().__init__(**kwargs)
        self.db = Database(db_path=db_path, backend=db_backend, dsn=db_dsn)
        self._server: Optional[RedirectServer] = None

    def on_mount(self) -> None:
        """Initialize the app: apply theme, push main screen, start server."""
        self._apply_theme_from_settings()

        list_screen = URLListScreen(self.db)
        self.push_screen(list_screen)

        # Start the redirect server after first render to avoid race with screen widgets.
        self.call_after_refresh(self._start_server_if_enabled)

    def _start_server_if_enabled(self) -> None:
        """Start the redirect server based on settings."""
        enabled = self.db.get_setting("server_enabled", "1") == "1"
        if not enabled:
            self._update_server_status()
            return

        port_str = self.db.get_setting("server_port", "8080")
        try:
            port = int(port_str)
        except ValueError:
            port = 8080

        self._server = RedirectServer(
            port=port,
            db_path=self.db.db_path,
            db_backend=self.db.backend,
            db_dsn=self.db.dsn,
        )
        try:
            self._server.start()
        except OSError as e:
            self.notify(
                f"Failed to start server on port {port}: {e}\n"
                "Change the port in Settings (s).",
                title="Server Error",
                severity="error",
                timeout=10,
            )
            self._server = None

        self._update_server_status()

    def _update_server_status(self) -> None:
        """Update server status on the current screen."""
        try:
            screen = self.screen
            if isinstance(screen, URLListScreen):
                running = self._server is not None and self._server.is_running
                port = self._server.port if self._server else 0
                screen.update_server_status(running, port)
        except Exception:
            logger.exception("Failed to update server status")

    def apply_settings(self, settings: dict) -> None:
        """Apply changed settings (called from settings modal)."""
        self._apply_theme_from_settings(settings)

        server_enabled = settings.get("server_enabled", True)
        new_port = settings.get("server_port", 8080)

        # Stop existing server
        if self._server:
            self._server.stop()
            self._server = None

        # Restart if enabled
        if server_enabled:
            self._server = RedirectServer(
                port=new_port,
                db_path=self.db.db_path,
                db_backend=self.db.backend,
                db_dsn=self.db.dsn,
            )
            try:
                self._server.start()
                self.notify(
                    f"Server restarted on port {new_port}",
                    title="Settings Applied",
                )
            except OSError as e:
                self.notify(
                    f"Failed to start server on port {new_port}: {e}",
                    title="Server Error",
                    severity="error",
                    timeout=10,
                )
                self._server = None
        else:
            self.notify("Server disabled", title="Settings Applied")

        self._update_server_status()

    def _apply_theme_from_settings(self, settings: Optional[dict] = None) -> None:
        """Apply persisted theme setting to the app."""
        if settings is None:
            dark = self.db.get_setting("theme_dark", "1") == "1"
        else:
            dark = bool(settings.get("theme_dark", True))

        self.dark = dark

    def action_new_url(self) -> None:
        """Open create URL modal from the active URL list screen."""
        screen = self.screen
        if isinstance(screen, URLListScreen):
            screen.action_new_url()

    def action_open_help(self) -> None:
        """Open universal help modal from any screen."""
        from .screens.help import HelpModal
        self.push_screen(HelpModal())

    def on_unmount(self) -> None:
        """Clean up on exit."""
        if self._server:
            self._server.stop()
        self.db.close()


def main():
    """Run the URL Shortener TUI application."""
    app = URLShortenerApp()
    app.run()


if __name__ == "__main__":
    main()
