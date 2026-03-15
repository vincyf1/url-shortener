import asyncio
from pathlib import Path

from app.main import URLShortenerApp
from app.screens.create_url import CreateURLModal


def test_n_shortcut_opens_create_modal(tmp_path: Path):
    async def scenario() -> None:
        db_path = tmp_path / "urls.db"
        app = URLShortenerApp(db_path=db_path)
        app.db.set_setting("server_enabled", "0")

        async with app.run_test() as pilot:
            await pilot.pause(0.3)
            await pilot.press("n")
            await pilot.pause(0.2)
            assert isinstance(app.screen, CreateURLModal)

    asyncio.run(scenario())
