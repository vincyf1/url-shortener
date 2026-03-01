import asyncio
import socket
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import HTTPRedirectHandler, Request, build_opener

from app.main import URLShortenerApp
from app.screens.url_detail import URLDetailModal
from textual.widgets import DataTable, Input, Switch


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


async def _wait_until(predicate, timeout: float = 2.0, step: float = 0.05):
    elapsed = 0.0
    while elapsed < timeout:
        try:
            if predicate():
                return
        except Exception:
            pass
        await asyncio.sleep(step)
        elapsed += step
    raise AssertionError("Timed out waiting for condition")


def test_full_tui_e2e(tmp_path: Path):
    async def scenario():
        db_path = tmp_path / "urls.db"
        app = URLShortenerApp(db_path=db_path)

        # Keep startup deterministic until we explicitly test server settings.
        app.db.set_setting("server_enabled", "0")
        test_port = _free_port()
        app.db.set_setting("server_port", str(test_port))
        app.db.set_setting("base_url", f"http://127.0.0.1:{test_port}")

        async with app.run_test() as pilot:
            await pilot.pause(0.2)

            # --- Create URL (new screen/modal) ---
            app.screen.action_new_url()
            await pilot.pause(0.1)

            create_screen = app.screen
            create_screen.query_one("#url-input", Input).value = "https://example.com/alpha"
            create_screen.query_one("#code-input", Input).value = "alpha1"
            await pilot.click("#btn-create")

            await _wait_until(lambda: isinstance(app.screen.query_one("#url-table", DataTable), DataTable))
            table = app.screen.query_one("#url-table", DataTable)
            assert table.row_count == 1

            # --- Search and clear search ---
            app.screen.action_search()
            await pilot.pause(0.1)
            search_input = app.screen.query_one("#search-input", Input)
            search_input.value = "no-match"
            await pilot.press("enter")
            await pilot.pause(0.2)
            assert app.screen.query_one("#url-table", DataTable).row_count == 0

            app.screen.action_clear_search()
            await pilot.pause(0.2)
            assert app.screen.query_one("#url-table", DataTable).row_count == 1

            # --- Details and edit ---
            detail_record = app.db.get_url_by_code("alpha1")
            assert detail_record is not None
            app.push_screen(URLDetailModal(app.db, detail_record))
            await _wait_until(lambda: app.query_one("#edit-btn") is not None)
            detail_screen = app.screen
            detail_screen._toggle_edit()
            await pilot.pause(0.05)
            detail_screen.query_one("#edit-url-input", Input).value = "https://example.org/edited"
            detail_screen.query_one("#edit-title-input", Input).value = "Edited Title"
            detail_screen._toggle_edit()  # Save
            await pilot.pause(0.2)
            assert "example.org/edited" in str(detail_screen.query_one("#original-url-display").renderable)
            detail_screen.dismiss(None)
            await pilot.pause(0.1)

            # --- Settings and redirect server ---
            app.screen.action_open_settings()
            await _wait_until(lambda: app.query_one("#port-input") is not None)
            settings = app.screen
            settings.query_one("#port-input", Input).value = str(test_port)
            settings.query_one("#base-url-input", Input).value = f"http://127.0.0.1:{test_port}"
            settings.query_one("#server-toggle", Switch).value = True
            settings._save_settings()
            await pilot.pause(0.3)

            assert app._server is not None
            assert app._server.is_running

            opener = build_opener(NoRedirect)
            try:
                opener.open(Request(f"http://127.0.0.1:{test_port}/alpha1"))
                raise AssertionError("Expected redirect HTTPError 301")
            except HTTPError as e:
                assert e.code == 301
                assert e.headers["Location"] == "https://example.org/edited"

            # --- Delete URL via list screen logic (confirmation callback path) ---
            app.screen._on_delete_confirmed(True, "alpha1")
            await _wait_until(lambda: app.screen.query_one("#url-table", DataTable).row_count == 0)
            assert app.screen.query_one("#url-table", DataTable).row_count == 0

            # --- Disable server in settings ---
            app.screen.action_open_settings()
            await _wait_until(lambda: app.query_one("#port-input") is not None)
            settings = app.screen
            settings.query_one("#server-toggle", Switch).value = False
            settings._save_settings()
            await pilot.pause(0.2)
            assert app._server is None or not app._server.is_running

            await pilot.press("q")

    asyncio.run(scenario())
