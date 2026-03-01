from pathlib import Path

from app.database import Database
from app.shortener import create_short_url


def test_create_list_detail_edit_delete_search_and_settings(tmp_path: Path):
    db = Database(db_path=tmp_path / "urls.db")

    # create
    created = create_short_url(db, "https://example.com/a", custom_code="abc123", title="Example")
    assert created["short_code"] == "abc123"

    # list
    rows = db.get_all_urls()
    assert len(rows) == 1
    assert rows[0]["short_code"] == "abc123"

    # detail
    detail = db.get_url_by_code("abc123")
    assert detail is not None
    assert detail["original_url"] == "https://example.com/a"

    # edit
    updated = db.update_url("abc123", original_url="https://example.org/updated", title="Updated")
    assert updated is not None
    assert updated["original_url"] == "https://example.org/updated"
    assert updated["title"] == "Updated"

    # search
    search_rows = db.search_urls("updated")
    assert len(search_rows) == 1
    assert search_rows[0]["short_code"] == "abc123"

    # settings flow
    db.set_setting("server_port", "9090")
    db.set_setting("base_url", "http://localhost:9090")
    db.set_setting("server_enabled", "0")
    settings = db.get_all_settings()
    assert settings["server_port"] == "9090"
    assert settings["base_url"] == "http://localhost:9090"
    assert settings["server_enabled"] == "0"

    # delete
    deleted = db.delete_url("abc123")
    assert deleted is True
    assert db.get_url_by_code("abc123") is None
    assert db.get_url_count() == 0

    db.close()
