"""Snowflake connection + a thin SQL runner with file support and retries."""
from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

import snowflake.connector
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_fixed

from lakehouse.config import Settings
from lakehouse.logging import get_logger

log = get_logger(__name__)
TRANSIENT = (snowflake.connector.errors.OperationalError,)


class SnowflakeRunner:
    def __init__(self, settings: Settings) -> None:
        self._s = settings
        self.sql_root = Path(__file__).resolve().parents[3] / "sql"

    @contextmanager
    def connect(self) -> Iterator[snowflake.connector.SnowflakeConnection]:
        conn = snowflake.connector.connect(
            account=self._s.snowflake_account,
            user=self._s.snowflake_user,
            password=self._s.snowflake_password,
            role=self._s.snowflake_role,
            warehouse=self._s.snowflake_warehouse,
            database=self._s.snowflake_database,
            session_parameters={"QUERY_TAG": f"lakehouse:{self._s.lakehouse_env}"},
        )
        try:
            yield conn
        finally:
            conn.close()

    @retry(retry=retry_if_exception_type(TRANSIENT), stop=stop_after_attempt(3), wait=wait_fixed(10))
    def execute(self, sql: str, params: dict[str, Any] | None = None) -> list[tuple]:
        with self.connect() as conn, conn.cursor() as cur:
            log.debug("sql_execute", preview=sql.strip()[:120])
            cur.execute(sql, params or {})
            return cur.fetchall() if cur.description else []

    def execute_file(self, relative: str, **fmt: Any) -> None:
        """Run every `;`-terminated statement in sql/<relative>, with {placeholders}."""
        text = (self.sql_root / relative).read_text().format(**fmt)
        with self.connect() as conn, conn.cursor() as cur:
            for stmt in (s.strip() for s in text.split(";")):
                if stmt and not stmt.startswith("--"):
                    cur.execute(stmt)
        log.info("sql_file_executed", file=relative)

    def scalar(self, sql: str) -> Any:
        rows = self.execute(sql)
        return rows[0][0] if rows else None
