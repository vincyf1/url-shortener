from pathlib import Path

import pytest

from app.database import Database, resolve_storage_config


def test_sqlite_is_default_backend(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("DB_BACKEND", raising=False)
    db = Database(db_path=tmp_path / "urls.db")
    assert db.backend == "sqlite"
    db.close()


def test_invalid_backend_is_rejected(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("DB_BACKEND", "nope")
    with pytest.raises(ValueError):
        resolve_storage_config()


def test_postgres_requires_dsn(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("DB_BACKEND", "postgres")
    monkeypatch.delenv("POSTGRES_DSN", raising=False)
    monkeypatch.delenv("DATABASE_URL", raising=False)
    with pytest.raises(ValueError):
        resolve_storage_config()


def test_mysql_requires_dsn(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("DB_BACKEND", "mysql")
    monkeypatch.delenv("MYSQL_DSN", raising=False)
    monkeypatch.delenv("DATABASE_URL", raising=False)
    with pytest.raises(ValueError):
        resolve_storage_config()
