"""SQLite database layer for URL shortener.

Uses WAL mode for concurrent access between TUI and redirect server.
All click_count updates use atomic SQL increments.
"""

import sqlite3
import os
from pathlib import Path
from datetime import datetime
from typing import Optional


# Default DB location: XDG-compliant
DEFAULT_DB_DIR = Path(os.environ.get(
    "URL_SHORTENER_DATA_DIR",
    os.path.expanduser("~/.local/share/url-shortener"),
))
DEFAULT_DB_PATH = DEFAULT_DB_DIR / "urls.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS urls (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    short_code  TEXT    UNIQUE NOT NULL,
    original_url TEXT   NOT NULL,
    created_at  TEXT    NOT NULL DEFAULT (datetime('now')),
    click_count INTEGER NOT NULL DEFAULT 0,
    title       TEXT    DEFAULT NULL,
    active      INTEGER NOT NULL DEFAULT 1
);

CREATE INDEX IF NOT EXISTS idx_short_code ON urls(short_code);
CREATE INDEX IF NOT EXISTS idx_created_at ON urls(created_at);

CREATE TABLE IF NOT EXISTS settings (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""

# Default settings
DEFAULT_SETTINGS = {
    "server_port": "8080",
    "base_url": "http://localhost:8080",
    "server_enabled": "1",
}


class Database:
    """SQLite database interface for the URL shortener.

    Thread-safe: each method creates its own connection or uses
    the instance connection. For cross-thread use, instantiate
    a separate Database per thread.
    """

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or DEFAULT_DB_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn: Optional[sqlite3.Connection] = None
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        """Get or create the database connection."""
        if self._conn is None:
            self._conn = sqlite3.connect(
                str(self.db_path),
                check_same_thread=False,
            )
            self._conn.row_factory = sqlite3.Row
            self._conn.execute("PRAGMA journal_mode=WAL")
            self._conn.execute("PRAGMA foreign_keys=ON")
        return self._conn

    def _init_db(self) -> None:
        """Initialize the database schema and default settings."""
        conn = self._get_conn()
        conn.executescript(SCHEMA)
        # Insert default settings if not present
        for key, value in DEFAULT_SETTINGS.items():
            conn.execute(
                "INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)",
                (key, value),
            )
        conn.commit()

    def close(self) -> None:
        """Close the database connection."""
        if self._conn:
            self._conn.close()
            self._conn = None

    # --- URL operations ---

    def add_url(
        self,
        short_code: str,
        original_url: str,
        title: Optional[str] = None,
    ) -> dict:
        """Add a new shortened URL. Returns the created row as a dict."""
        conn = self._get_conn()
        cursor = conn.execute(
            """INSERT INTO urls (short_code, original_url, title)
               VALUES (?, ?, ?)""",
            (short_code, original_url, title),
        )
        conn.commit()
        row = conn.execute(
            "SELECT * FROM urls WHERE id = ?", (cursor.lastrowid,)
        ).fetchone()
        return dict(row)

    def get_url_by_code(self, short_code: str) -> Optional[dict]:
        """Look up a URL by its short code."""
        conn = self._get_conn()
        row = conn.execute(
            "SELECT * FROM urls WHERE short_code = ? AND active = 1",
            (short_code,),
        ).fetchone()
        return dict(row) if row else None

    def get_all_urls(self, include_inactive: bool = False) -> list[dict]:
        """Get all URLs, ordered by creation date descending."""
        conn = self._get_conn()
        if include_inactive:
            query = "SELECT * FROM urls ORDER BY created_at DESC"
            rows = conn.execute(query).fetchall()
        else:
            query = "SELECT * FROM urls WHERE active = 1 ORDER BY created_at DESC"
            rows = conn.execute(query).fetchall()
        return [dict(r) for r in rows]

    def search_urls(self, query: str) -> list[dict]:
        """Search URLs by short code or original URL."""
        conn = self._get_conn()
        pattern = f"%{query}%"
        rows = conn.execute(
            """SELECT * FROM urls
               WHERE active = 1
                 AND (short_code LIKE ? OR original_url LIKE ? OR title LIKE ?)
               ORDER BY created_at DESC""",
            (pattern, pattern, pattern),
        ).fetchall()
        return [dict(r) for r in rows]

    def increment_click_count(self, short_code: str) -> None:
        """Atomically increment the click count for a URL."""
        conn = self._get_conn()
        conn.execute(
            "UPDATE urls SET click_count = click_count + 1 WHERE short_code = ?",
            (short_code,),
        )
        conn.commit()

    def delete_url(self, short_code: str) -> bool:
        """Soft-delete a URL by setting active = 0."""
        conn = self._get_conn()
        cursor = conn.execute(
            "UPDATE urls SET active = 0 WHERE short_code = ? AND active = 1",
            (short_code,),
        )
        conn.commit()
        return cursor.rowcount > 0

    def hard_delete_url(self, short_code: str) -> bool:
        """Permanently delete a URL."""
        conn = self._get_conn()
        cursor = conn.execute(
            "DELETE FROM urls WHERE short_code = ?",
            (short_code,),
        )
        conn.commit()
        return cursor.rowcount > 0

    def update_url(
        self,
        short_code: str,
        original_url: Optional[str] = None,
        title: Optional[str] = None,
    ) -> Optional[dict]:
        """Update a URL's original_url and/or title."""
        conn = self._get_conn()
        updates = []
        params: list = []
        if original_url is not None:
            updates.append("original_url = ?")
            params.append(original_url)
        if title is not None:
            updates.append("title = ?")
            params.append(title)
        if not updates:
            return self.get_url_by_code(short_code)
        params.append(short_code)
        conn.execute(
            f"UPDATE urls SET {', '.join(updates)} WHERE short_code = ?",
            params,
        )
        conn.commit()
        return self.get_url_by_code(short_code)

    def code_exists(self, short_code: str) -> bool:
        """Check if a short code already exists (including inactive)."""
        conn = self._get_conn()
        row = conn.execute(
            "SELECT 1 FROM urls WHERE short_code = ?",
            (short_code,),
        ).fetchone()
        return row is not None

    def get_url_count(self) -> int:
        """Get the total number of active URLs."""
        conn = self._get_conn()
        row = conn.execute(
            "SELECT COUNT(*) as cnt FROM urls WHERE active = 1"
        ).fetchone()
        return row["cnt"]

    # --- Settings operations ---

    def get_setting(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """Get a setting value by key."""
        conn = self._get_conn()
        row = conn.execute(
            "SELECT value FROM settings WHERE key = ?", (key,)
        ).fetchone()
        if row:
            return row["value"]
        return default

    def set_setting(self, key: str, value: str) -> None:
        """Set a setting value (insert or update)."""
        conn = self._get_conn()
        conn.execute(
            "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
            (key, value),
        )
        conn.commit()

    def get_all_settings(self) -> dict[str, str]:
        """Get all settings as a dictionary."""
        conn = self._get_conn()
        rows = conn.execute("SELECT key, value FROM settings").fetchall()
        return {r["key"]: r["value"] for r in rows}
