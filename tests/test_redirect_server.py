import socket
from pathlib import Path
from urllib.request import build_opener, HTTPRedirectHandler, Request
from urllib.error import HTTPError

from app.database import Database
from app.shortener import create_short_url
from app.server import RedirectServer


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def test_redirect_behavior(tmp_path: Path):
    db_path = tmp_path / "urls.db"
    db = Database(db_path=db_path)
    create_short_url(db, "https://example.com/target", custom_code="go")

    port = _free_port()
    server = RedirectServer(port=port, db_path=db_path)
    server.start()
    try:
        opener = build_opener(NoRedirect)

        # Existing code => 301 with Location header
        req = Request(f"http://127.0.0.1:{port}/go")
        try:
            opener.open(req)
            raise AssertionError("Expected 301 response")
        except HTTPError as e:
            assert e.code == 301
            assert e.headers["Location"] == "https://example.com/target"

        # Missing code => 404
        req_missing = Request(f"http://127.0.0.1:{port}/missing")
        try:
            opener.open(req_missing)
            raise AssertionError("Expected 404 response")
        except HTTPError as e:
            assert e.code == 404

        # Click count incremented
        updated = db.get_url_by_code("go")
        assert updated is not None
        assert updated["click_count"] == 1
    finally:
        server.stop()
        db.close()
