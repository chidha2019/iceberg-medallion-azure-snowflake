"""Silver execution model: each asset = one idempotent SQL file (MERGE or CREATE OR REPLACE)."""
from __future__ import annotations

from lakehouse.config import Settings
from lakehouse.lineage import Asset
from lakehouse.logging import get_logger
from lakehouse.quality.checks import run_checks
from lakehouse.snowflake.connection import SnowflakeRunner

log = get_logger(__name__)


def run_sql_asset(a: Asset, runner: SnowflakeRunner, settings: Settings) -> dict:
    assert a.sql_file, f"{a.name} has no sql_file"
    runner.execute_file(a.sql_file, db=settings.snowflake_database,
                        vol=settings.snowflake_external_volume)
    rows = runner.scalar(f"SELECT COUNT(*) FROM {a.output}")
    checks = run_checks(a, runner)
    log.info("asset_complete", asset=a.name, rows=rows, checks=checks)
    return {"asset": a.name, "rows": rows, "checks": checks}
