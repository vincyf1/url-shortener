"""MySQL repository adapter."""

from __future__ import annotations

from typing import Optional
from urllib.parse import parse_qs, urlparse

from app.repository import DEFAULT_SETTINGS, URLRecord, URLRepository


SCHEMA_STATEMENTS = [
    """
    CREATE TABLE IF NOT EXISTS urls (
        id BIGINT AUTO_INCREMENT PRIMARY KEY,
        short_code VARCHAR(64) UNIQUE NOT NULL,
        original_url TEXT NOT NULL,
        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        click_count INT NOT NULL DEFAULT 0,
        title TEXT NULL,
        active TINYINT(1) NOT NULL DEFAULT 1,
        INDEX idx_short_code (short_code),
        INDEX idx_created_at (created_at)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS settings (
        `key` VARCHAR(191) PRIMARY KEY,
        value TEXT NOT NULL
    )
    """,
]


class MySQLRepository(URLRepository):
    def __init__(self, dsn: str):
        if not dsn:
            raise ValueError("MySQL DSN is required")
        self.dsn = dsn
        self._conn = None
        self._init_db()

    def _get_conn(self):
        if self._conn is None:
            try:
                import pymysql
            except ModuleNotFoundError as exc:
                raise RuntimeError("MySQL backend requires pymysql. Install with: uv sync --extra mysql") from exc
            parsed = urlparse(self.dsn)
            if parsed.scheme not in {"mysql", "mysql+pymysql"}:
                raise ValueError("MYSQL_DSN must use mysql:// or mysql+pymysql://")
            query = parse_qs(parsed.query)
            self._conn = pymysql.connect(
                host=parsed.hostname or "127.0.0.1",
                port=parsed.port or 3306,
                user=parsed.username,
                password=parsed.password,
                database=(parsed.path or "/").lstrip("/") or None,
                charset=query.get("charset", ["utf8mb4"])[0],
                autocommit=False,
                cursorclass=pymysql.cursors.Cursor,
            )
        return self._conn

    @staticmethod
    def _to_record(data: dict) -> URLRecord:
        return URLRecord(
            id=data["id"],
            short_code=data["short_code"],
            original_url=data["original_url"],
            created_at=str(data["created_at"]),
            click_count=data["click_count"],
            title=data.get("title"),
            active=int(data["active"]),
        )

    def _init_db(self) -> None:
        conn = self._get_conn()
        with conn.cursor() as cur:
            for stmt in SCHEMA_STATEMENTS:
                cur.execute(stmt)
            for key, value in DEFAULT_SETTINGS.items():
                cur.execute("INSERT IGNORE INTO settings (`key`, value) VALUES (%s, %s)", (key, value))
        conn.commit()

    def close(self) -> None:
        if self._conn:
            self._conn.close()
            self._conn = None

    def add_url(self, short_code: str, original_url: str, title: Optional[str] = None) -> dict:
        conn = self._get_conn()
        with conn.cursor() as cur:
            cur.execute("INSERT INTO urls (short_code, original_url, title) VALUES (%s, %s, %s)", (short_code, original_url, title))
            new_id = cur.lastrowid
            cur.execute("SELECT id, short_code, original_url, created_at, click_count, title, active FROM urls WHERE id = %s", (new_id,))
            row = cur.fetchone()
            cols = [d[0] for d in cur.description]
        conn.commit()
        return self._to_record(dict(zip(cols, row))).to_dict()

    def get_url_by_code(self, short_code: str) -> Optional[dict]:
        conn = self._get_conn()
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, short_code, original_url, created_at, click_count, title, active FROM urls WHERE short_code = %s AND active = 1",
                (short_code,),
            )
            row = cur.fetchone()
            if not row:
                return None
            cols = [d[0] for d in cur.description]
        return self._to_record(dict(zip(cols, row))).to_dict()

    def get_all_urls(self, include_inactive: bool = False) -> list[dict]:
        conn = self._get_conn()
        with conn.cursor() as cur:
            if include_inactive:
                cur.execute("SELECT id, short_code, original_url, created_at, click_count, title, active FROM urls ORDER BY created_at DESC")
            else:
                cur.execute("SELECT id, short_code, original_url, created_at, click_count, title, active FROM urls WHERE active = 1 ORDER BY created_at DESC")
            rows = cur.fetchall()
            cols = [d[0] for d in cur.description]
        return [self._to_record(dict(zip(cols, r))).to_dict() for r in rows]

    def search_urls(self, query: str) -> list[dict]:
        conn = self._get_conn()
        pattern = f"%{query}%"
        with conn.cursor() as cur:
            cur.execute(
                """SELECT id, short_code, original_url, created_at, click_count, title, active FROM urls
                   WHERE active = 1
                   AND (short_code LIKE %s OR original_url LIKE %s OR title LIKE %s)
                   ORDER BY created_at DESC""",
                (pattern, pattern, pattern),
            )
            rows = cur.fetchall()
            cols = [d[0] for d in cur.description]
        return [self._to_record(dict(zip(cols, r))).to_dict() for r in rows]

    def increment_click_count(self, short_code: str) -> None:
        conn = self._get_conn()
        with conn.cursor() as cur:
            cur.execute("UPDATE urls SET click_count = click_count + 1 WHERE short_code = %s", (short_code,))
        conn.commit()

    def delete_url(self, short_code: str) -> bool:
        conn = self._get_conn()
        with conn.cursor() as cur:
            cur.execute("UPDATE urls SET active = 0 WHERE short_code = %s AND active = 1", (short_code,))
            changed = cur.rowcount > 0
        conn.commit()
        return changed

    def hard_delete_url(self, short_code: str) -> bool:
        conn = self._get_conn()
        with conn.cursor() as cur:
            cur.execute("DELETE FROM urls WHERE short_code = %s", (short_code,))
            changed = cur.rowcount > 0
        conn.commit()
        return changed

    def update_url(self, short_code: str, original_url: Optional[str] = None, title: Optional[str] = None) -> Optional[dict]:
        updates = []
        params: list = []
        if original_url is not None:
            updates.append("original_url = %s")
            params.append(original_url)
        if title is not None:
            updates.append("title = %s")
            params.append(title)
        if not updates:
            return self.get_url_by_code(short_code)
        params.append(short_code)
        conn = self._get_conn()
        with conn.cursor() as cur:
            cur.execute(f"UPDATE urls SET {', '.join(updates)} WHERE short_code = %s", tuple(params))
        conn.commit()
        return self.get_url_by_code(short_code)

    def code_exists(self, short_code: str) -> bool:
        conn = self._get_conn()
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM urls WHERE short_code = %s", (short_code,))
            row = cur.fetchone()
        return row is not None

    def get_url_count(self) -> int:
        conn = self._get_conn()
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM urls WHERE active = 1")
            return int(cur.fetchone()[0])

    def get_setting(self, key: str, default: Optional[str] = None) -> Optional[str]:
        conn = self._get_conn()
        with conn.cursor() as cur:
            cur.execute("SELECT value FROM settings WHERE `key` = %s", (key,))
            row = cur.fetchone()
        return row[0] if row else default

    def set_setting(self, key: str, value: str) -> None:
        conn = self._get_conn()
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO settings (`key`, value) VALUES (%s, %s)
                   ON DUPLICATE KEY UPDATE value = VALUES(value)""",
                (key, value),
            )
        conn.commit()

    def get_all_settings(self) -> dict[str, str]:
        conn = self._get_conn()
        with conn.cursor() as cur:
            cur.execute("SELECT `key`, value FROM settings")
            rows = cur.fetchall()
        return {k: v for k, v in rows}
