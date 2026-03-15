"""Threaded HTTP redirect server for URL shortener.

Runs as a daemon thread alongside the TUI.
Handles GET /<code> → 301 redirect to original URL.
"""

import logging
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Optional
from pathlib import Path

from .database import Database

logger = logging.getLogger(__name__)


class RedirectHandler(BaseHTTPRequestHandler):
    """HTTP request handler that redirects short codes to original URLs."""

    # Backend configuration set by RedirectServer
    db_path: Optional[Path] = None
    db_backend: Optional[str] = None
    db_dsn: Optional[str] = None

    def _send_security_headers(self) -> None:
        """Send baseline security headers for all responses."""
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("X-Frame-Options", "DENY")

    def do_GET(self) -> None:
        """Handle GET requests."""
        path = self.path.strip("/")

        if not path:
            # Root path — simple status page
            self._send_status_page()
            return

        # Strip query string if present
        if "?" in path:
            path = path.split("?", 1)[0]

        if path == "healthz":
            self._send_healthz()
            return

        # Look up the short code
        db = Database(db_path=self.db_path, backend=self.db_backend, dsn=self.db_dsn)
        try:
            url_record = db.get_url_by_code(path)
            if url_record:
                # Increment click count atomically
                db.increment_click_count(path)
                # Send 301 redirect
                self.send_response(301)
                self._send_security_headers()
                self.send_header("Location", url_record["original_url"])
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
            else:
                self._send_not_found(path)
        finally:
            db.close()

    def _send_status_page(self) -> None:
        """Send a simple HTML status page."""
        html = """<!DOCTYPE html>
<html>
<head><title>URL Shortener</title></head>
<body>
<h1>🔗 URL Shortener</h1>
<p>This server handles redirects for shortened URLs.</p>
<p>Manage your URLs via the TUI application.</p>
</body>
</html>"""
        self.send_response(200)
        self._send_security_headers()
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(html.encode())))
        self.end_headers()
        self.wfile.write(html.encode())

    def _send_healthz(self) -> None:
        """Send an application health response.

        Health is considered "ok" when the backing database is reachable.
        """
        status_code = 200
        body = b"ok"

        db = None
        try:
            db = Database(db_path=self.db_path, backend=self.db_backend, dsn=self.db_dsn)
            # Lightweight reachability probe.
            db.get_setting("base_url", "")
        except Exception:
            status_code = 503
            body = b"db_unhealthy"
        finally:
            if db is not None:
                db.close()

        self.send_response(status_code)
        self._send_security_headers()
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_not_found(self, code: str) -> None:
        """Send a 404 response."""
        html = f"""<!DOCTYPE html>
<html>
<head><title>Not Found</title></head>
<body>
<h1>404 — Not Found</h1>
<p>Short code <code>{code}</code> does not exist.</p>
</body>
</html>"""
        self.send_response(404)
        self._send_security_headers()
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(html.encode())))
        self.end_headers()
        self.wfile.write(html.encode())

    def log_message(self, format: str, *args) -> None:
        """Suppress default stderr logging; use logger instead."""
        logger.debug("HTTP: %s", format % args)


class RedirectServer:
    """Threaded HTTP redirect server.

    Runs as a daemon thread that dies when the main application exits.
    """

    def __init__(
        self,
        port: int = 8080,
        db_path: Optional[Path] = None,
        db_backend: Optional[str] = None,
        db_dsn: Optional[str] = None,
    ):
        self.port = port
        self.db_path = db_path
        self.db_backend = db_backend
        self.db_dsn = db_dsn
        self._server: Optional[ThreadingHTTPServer] = None
        self._thread: Optional[threading.Thread] = None
        self._running = False
        self._error: Optional[str] = None

    @property
    def is_running(self) -> bool:
        """Check if the server is currently running."""
        return self._running and self._thread is not None and self._thread.is_alive()

    @property
    def error(self) -> Optional[str]:
        """Get the last error message, if any."""
        return self._error

    def start(self) -> None:
        """Start the redirect server in a daemon thread.

        Raises:
            OSError: If the port is already in use or otherwise unavailable.
        """
        if self.is_running:
            return

        self._error = None

        # Set the DB path on the handler class
        RedirectHandler.db_path = self.db_path
        RedirectHandler.db_backend = self.db_backend
        RedirectHandler.db_dsn = self.db_dsn

        try:
            self._server = ThreadingHTTPServer(("0.0.0.0", self.port), RedirectHandler)
        except OSError as e:
            self._error = str(e)
            raise

        self._running = True
        self._thread = threading.Thread(
            target=self._serve,
            name="redirect-server",
            daemon=True,
        )
        self._thread.start()
        logger.info("Redirect server started on port %d", self.port)

    def _serve(self) -> None:
        """Server loop (runs in daemon thread)."""
        try:
            if self._server:
                self._server.serve_forever()
        except Exception as e:
            self._error = str(e)
            logger.error("Redirect server error: %s", e)
        finally:
            self._running = False

    def stop(self) -> None:
        """Stop the redirect server."""
        if self._server:
            self._server.shutdown()
            self._server.server_close()
            self._server = None
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
            self._thread = None
        logger.info("Redirect server stopped")

    def restart(self, port: Optional[int] = None) -> None:
        """Restart the server, optionally on a new port.

        Raises:
            OSError: If the new port is unavailable.
        """
        self.stop()
        if port is not None:
            self.port = port
        self.start()
