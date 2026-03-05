import asyncio
from pathlib import Path

import pytest
from textual.widgets import Label

from app.main import URLShortenerApp
from app.database import Database
from app.screens.help import HelpModal
from app.shortener import (
    CodeExistsError,
    InvalidURLError,
    create_short_url,
    validate_base_url,
    validate_custom_code,
    validate_url,
)


def test_validate_url_rejects_dangerous_and_missing_scheme():
    with pytest.raises(InvalidURLError):
        validate_url("javascript:alert(1)")

    with pytest.raises(InvalidURLError):
        validate_url("example.com/no-scheme")


def test_validate_custom_code_rules():
    assert validate_custom_code("ok-code_123") == "ok-code_123"

    with pytest.raises(ValueError):
        validate_custom_code("bad code with spaces")


def test_validate_base_url_rules():
    assert validate_base_url("https://short.example.com/") == "https://short.example.com"

    with pytest.raises(InvalidURLError):
        validate_base_url("ftp://short.example.com")

    with pytest.raises(InvalidURLError):
        validate_base_url("https://short.example.com/?x=1")


def test_create_short_url_rejects_duplicate_custom_code(tmp_path: Path):
    db = Database(db_path=tmp_path / "urls.db")
    create_short_url(db, "https://example.com/one", custom_code="dup")

    with pytest.raises(CodeExistsError):
        create_short_url(db, "https://example.com/two", custom_code="dup")

    db.close()


def test_app_help_modal_accessible_from_main_screen(tmp_path: Path):
    async def scenario():
        app = URLShortenerApp(db_path=tmp_path / "urls.db")
        app.db.set_setting("server_enabled", "0")

        async with app.run_test() as pilot:
            await pilot.pause(0.2)
            app.action_open_help()
            await pilot.pause(0.1)
            assert isinstance(app.screen, HelpModal)
            title = app.query_one("#help-title", Label)
            assert "Help" in str(title.renderable)
            await pilot.press("escape")
            await pilot.pause(0.1)

    asyncio.run(scenario())
