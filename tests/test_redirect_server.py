import socket
from pathlib import Path
from urllib.request import build_opener, HTTPRedirectHandler, Request, urlopen
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
            assert e.headers["X-Content-Type-Options"] == "nosniff"
            assert e.headers["Referrer-Policy"] == "no-referrer"

        # Missing code => 404
        req_missing = Request(f"http://127.0.0.1:{port}/missing")
        try:
            opener.open(req_missing)
            raise AssertionError("Expected 404 response")
        except HTTPError as e:
            assert e.code == 404
            assert e.headers["X-Frame-Options"] == "DENY"

        # Click count incremented
        updated = db.get_url_by_code("go")
        assert updated is not None
        assert updated["click_count"] == 1
    finally:
        server.stop()
        db.close()


def test_healthz_endpoint(tmp_path: Path):
    db_path = tmp_path / "urls.db"
    db = Database(db_path=db_path)

    port = _free_port()
    server = RedirectServer(port=port, db_path=db_path)
    server.start()
    try:
        response = urlopen(f"http://127.0.0.1:{port}/healthz")
        body = response.read().decode("utf-8")
        assert response.status == 200
        assert body == "ok"
        assert response.headers["Cache-Control"] == "no-store"
    finally:
        server.stop()
        db.close()


def test_healthz_returns_503_when_db_unreachable(tmp_path: Path, monkeypatch):
    db_path = tmp_path / "urls.db"

    class BrokenDatabase:
        def __init__(self, *args, **kwargs):
            raise RuntimeError("db unavailable")

    monkeypatch.setattr("app.server.Database", BrokenDatabase)

    port = _free_port()
    server = RedirectServer(port=port, db_path=db_path)
    server.start()
    try:
        try:
            urlopen(f"http://127.0.0.1:{port}/healthz")
            raise AssertionError("Expected 503 response")
        except HTTPError as e:
            assert e.code == 503
            assert e.read().decode("utf-8") == "db_unhealthy"
    finally:
        server.stop()
