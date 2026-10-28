"""Post-load data quality checks derived from the asset's declared contract."""
from __future__ import annotations

from lakehouse.lineage import Asset
from lakehouse.logging import get_logger

log = get_logger(__name__)


class QualityError(RuntimeError):
    pass


def uniqueness_sql(a: Asset) -> str:
    keys = ", ".join(a.keys)
    return f"SELECT COUNT(*) FROM (SELECT {keys} FROM {a.output} GROUP BY {keys} HAVING COUNT(*) > 1)"


def not_null_sql(a: Asset) -> str:
    cond = " OR ".join(f"{k} IS NULL" for k in a.keys)
    return f"SELECT COUNT(*) FROM {a.output} WHERE {cond}"


def run_checks(a: Asset, runner) -> dict:
    """error-level: key uniqueness, key not-null, non-empty. Raises on failure."""
    results = {
        "duplicate_keys": runner.scalar(uniqueness_sql(a)),
        "null_keys": runner.scalar(not_null_sql(a)),
        "row_count": runner.scalar(f"SELECT COUNT(*) FROM {a.output}"),
    }
    failures = [k for k, v in results.items() if (v or 0) > 0 and k != "row_count"]
    if results["row_count"] == 0:
        failures.append("empty_table")
    if failures:
        log.error("quality_failed", asset=a.name, failures=failures, results=results)
        raise QualityError(f"{a.name}: {failures}")
    return results
