from pathlib import Path

from app.main import URLShortenerApp


def test_imports_and_app_startup_smoke(tmp_path: Path):
    app = URLShortenerApp(db_path=tmp_path / "urls.db")

    # Ensure server doesn't try to bind during test runner startup checks.
    app.db.set_setting("server_enabled", "0")

    # Validate key screens/modules import and class wiring.
    from app.screens.url_list import URLListScreen  # noqa: F401
    from app.screens.create_url import CreateURLModal  # noqa: F401
    from app.screens.url_detail import URLDetailModal  # noqa: F401
    from app.screens.settings import SettingsModal  # noqa: F401

    # Sanity checks on app fields and DB readiness.
    assert app.db.get_all_settings()["server_port"]
    assert app._server is None
    app.db.close()
