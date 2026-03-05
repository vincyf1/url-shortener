"""PostgreSQL repository adapter."""

from __future__ import annotations

from typing import Optional

from app.repository import DEFAULT_SETTINGS, URLRecord, URLRepository


SCHEMA = """
CREATE TABLE IF NOT EXISTS urls (
    id BIGSERIAL PRIMARY KEY,
    short_code VARCHAR(64) UNIQUE NOT NULL,
    original_url TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    click_count INTEGER NOT NULL DEFAULT 0,
    title TEXT DEFAULT NULL,
    active BOOLEAN NOT NULL DEFAULT TRUE
);
CREATE INDEX IF NOT EXISTS idx_short_code ON urls(short_code);
CREATE INDEX IF NOT EXISTS idx_created_at ON urls(created_at);

CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""


class PostgreSQLRepository(URLRepository):
    def __init__(self, dsn: str):
        if not dsn:
            raise ValueError("PostgreSQL DSN is required")
        self.dsn = dsn
        self._conn = None
        self._init_db()

    def _get_conn(self):
        if self._conn is None:
            try:
                import psycopg
            except ModuleNotFoundError as exc:
                raise RuntimeError("PostgreSQL backend requires psycopg. Install with: uv sync --extra postgres") from exc
            self._conn = psycopg.connect(self.dsn)
            self._conn.autocommit = False
        return self._conn

    @staticmethod
    def _row_to_dict(row, columns) -> dict:
        return dict(zip(columns, row))

    @staticmethod
    def _to_record(data: dict) -> URLRecord:
        return URLRecord(
            id=data["id"],
            short_code=data["short_code"],
            original_url=data["original_url"],
            created_at=str(data["created_at"]),
            click_count=data["click_count"],
            title=data.get("title"),
            active=1 if data["active"] else 0,
        )

    def _init_db(self) -> None:
        conn = self._get_conn()
        with conn.cursor() as cur:
            cur.execute(SCHEMA)
            for key, value in DEFAULT_SETTINGS.items():
                cur.execute(
                    """INSERT INTO settings (key, value) VALUES (%s, %s)
                       ON CONFLICT (key) DO NOTHING""",
                    (key, value),
                )
        conn.commit()

    def close(self) -> None:
        if self._conn:
            self._conn.close()
            self._conn = None

    def add_url(self, short_code: str, original_url: str, title: Optional[str] = None) -> dict:
        conn = self._get_conn()
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO urls (short_code, original_url, title)
                   VALUES (%s, %s, %s)
                   RETURNING id, short_code, original_url, created_at, click_count, title, active""",
                (short_code, original_url, title),
            )
            row = cur.fetchone()
            cols = [d.name for d in cur.description]
        conn.commit()
        return self._to_record(self._row_to_dict(row, cols)).to_dict()

    def get_url_by_code(self, short_code: str) -> Optional[dict]:
        conn = self._get_conn()
        with conn.cursor() as cur:
            cur.execute(
                """SELECT id, short_code, original_url, created_at, click_count, title, active
                   FROM urls WHERE short_code = %s AND active = TRUE""",
                (short_code,),
            )
            row = cur.fetchone()
            if not row:
                return None
            cols = [d.name for d in cur.description]
        return self._to_record(self._row_to_dict(row, cols)).to_dict()

    def get_all_urls(self, include_inactive: bool = False) -> list[dict]:
        conn = self._get_conn()
        with conn.cursor() as cur:
            if include_inactive:
                cur.execute("SELECT id, short_code, original_url, created_at, click_count, title, active FROM urls ORDER BY created_at DESC")
            else:
                cur.execute("SELECT id, short_code, original_url, created_at, click_count, title, active FROM urls WHERE active = TRUE ORDER BY created_at DESC")
            rows = cur.fetchall()
            cols = [d.name for d in cur.description]
        return [self._to_record(self._row_to_dict(r, cols)).to_dict() for r in rows]

    def search_urls(self, query: str) -> list[dict]:
        conn = self._get_conn()
        pattern = f"%{query}%"
        with conn.cursor() as cur:
            cur.execute(
                """SELECT id, short_code, original_url, created_at, click_count, title, active FROM urls
                   WHERE active = TRUE
                   AND (short_code ILIKE %s OR original_url ILIKE %s OR title ILIKE %s)
                   ORDER BY created_at DESC""",
                (pattern, pattern, pattern),
            )
            rows = cur.fetchall()
            cols = [d.name for d in cur.description]
        return [self._to_record(self._row_to_dict(r, cols)).to_dict() for r in rows]

    def increment_click_count(self, short_code: str) -> None:
        conn = self._get_conn()
        with conn.cursor() as cur:
            cur.execute("UPDATE urls SET click_count = click_count + 1 WHERE short_code = %s", (short_code,))
        conn.commit()

    def delete_url(self, short_code: str) -> bool:
        conn = self._get_conn()
        with conn.cursor() as cur:
            cur.execute("UPDATE urls SET active = FALSE WHERE short_code = %s AND active = TRUE", (short_code,))
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
            cur.execute("SELECT COUNT(*) FROM urls WHERE active = TRUE")
            return int(cur.fetchone()[0])

    def get_setting(self, key: str, default: Optional[str] = None) -> Optional[str]:
        conn = self._get_conn()
        with conn.cursor() as cur:
            cur.execute("SELECT value FROM settings WHERE key = %s", (key,))
            row = cur.fetchone()
        return row[0] if row else default

    def set_setting(self, key: str, value: str) -> None:
        conn = self._get_conn()
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO settings (key, value) VALUES (%s, %s)
                   ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value""",
                (key, value),
            )
        conn.commit()

    def get_all_settings(self) -> dict[str, str]:
        conn = self._get_conn()
        with conn.cursor() as cur:
            cur.execute("SELECT key, value FROM settings")
            rows = cur.fetchall()
        return {k: v for k, v in rows}
