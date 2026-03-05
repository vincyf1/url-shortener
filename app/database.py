"""Storage facade and backend selection for URL shortener."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from app.adapters.mysql_repository import MySQLRepository
from app.adapters.postgres_repository import PostgreSQLRepository
from app.adapters.sqlite_repository import DEFAULT_DB_PATH, SQLiteRepository
from app.repository import URLRepository


@dataclass(frozen=True)
class StorageConfig:
    backend: str
    db_path: Optional[Path] = None
    dsn: Optional[str] = None


def resolve_storage_config(
    db_path: Optional[Path] = None,
    backend: Optional[str] = None,
    dsn: Optional[str] = None,
) -> StorageConfig:
    backend_name = (backend or os.environ.get("DB_BACKEND", "sqlite")).strip().lower()

    if backend_name == "sqlite":
        return StorageConfig(backend="sqlite", db_path=db_path or DEFAULT_DB_PATH)

    if backend_name == "postgres":
        resolved_dsn = dsn or os.environ.get("POSTGRES_DSN") or os.environ.get("DATABASE_URL")
        if not resolved_dsn:
            raise ValueError("DB_BACKEND=postgres requires POSTGRES_DSN or DATABASE_URL")
        return StorageConfig(backend="postgres", dsn=resolved_dsn)

    if backend_name == "mysql":
        resolved_dsn = dsn or os.environ.get("MYSQL_DSN") or os.environ.get("DATABASE_URL")
        if not resolved_dsn:
            raise ValueError("DB_BACKEND=mysql requires MYSQL_DSN or DATABASE_URL")
        return StorageConfig(backend="mysql", dsn=resolved_dsn)

    raise ValueError(f"Unsupported DB_BACKEND: {backend_name}")


def create_repository(config: StorageConfig) -> URLRepository:
    if config.backend == "sqlite":
        return SQLiteRepository(db_path=config.db_path)
    if config.backend == "postgres":
        return PostgreSQLRepository(dsn=config.dsn or "")
    if config.backend == "mysql":
        return MySQLRepository(dsn=config.dsn or "")
    raise ValueError(f"Unsupported backend: {config.backend}")


class Database:
    """Backwards-compatible facade over pluggable storage repository."""

    def __init__(
        self,
        db_path: Optional[Path] = None,
        backend: Optional[str] = None,
        dsn: Optional[str] = None,
    ):
        self.config = resolve_storage_config(db_path=db_path, backend=backend, dsn=dsn)
        self.backend = self.config.backend
        self.db_path = self.config.db_path
        self.dsn = self.config.dsn
        self._repo = create_repository(self.config)

    def close(self) -> None:
        return self._repo.close()

    def add_url(self, short_code: str, original_url: str, title: Optional[str] = None) -> dict:
        return self._repo.add_url(short_code=short_code, original_url=original_url, title=title)

    def get_url_by_code(self, short_code: str) -> Optional[dict]:
        return self._repo.get_url_by_code(short_code)

    def get_all_urls(self, include_inactive: bool = False) -> list[dict]:
        return self._repo.get_all_urls(include_inactive=include_inactive)

    def search_urls(self, query: str) -> list[dict]:
        return self._repo.search_urls(query)

    def increment_click_count(self, short_code: str) -> None:
        return self._repo.increment_click_count(short_code)

    def delete_url(self, short_code: str) -> bool:
        return self._repo.delete_url(short_code)

    def hard_delete_url(self, short_code: str) -> bool:
        return self._repo.hard_delete_url(short_code)

    def update_url(self, short_code: str, original_url: Optional[str] = None, title: Optional[str] = None) -> Optional[dict]:
        return self._repo.update_url(short_code=short_code, original_url=original_url, title=title)

    def code_exists(self, short_code: str) -> bool:
        return self._repo.code_exists(short_code)

    def get_url_count(self) -> int:
        return self._repo.get_url_count()

    def get_setting(self, key: str, default: Optional[str] = None) -> Optional[str]:
        return self._repo.get_setting(key=key, default=default)

    def set_setting(self, key: str, value: str) -> None:
        return self._repo.set_setting(key=key, value=value)

    def get_all_settings(self) -> dict[str, str]:
        return self._repo.get_all_settings()
