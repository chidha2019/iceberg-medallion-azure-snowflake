"""Snowflake-managed Iceberg table DDL generation from dataset contracts."""
from __future__ import annotations

from lakehouse.config import DatasetSpec

TYPE_MAP = {  # contract type -> Snowflake Iceberg-compatible type
    "STRING": "STRING",
    "INTEGER": "INT",
    "BOOLEAN": "BOOLEAN",
    "DATE": "DATE",
    "TIMESTAMP": "TIMESTAMP_NTZ(6)",
}

AUDIT_COLUMNS = [
    ("_ingest_file", "STRING"),
    ("_ingest_sha256", "STRING"),
    ("_ingest_ts", "TIMESTAMP_NTZ(6)"),
    ("_batch_id", "STRING"),
]


def map_type(t: str) -> str:
    return TYPE_MAP.get(t.upper(), t.upper())  # DECIMAL(p,s) passes through


def bronze_iceberg_ddl(spec: DatasetSpec, database: str, external_volume: str) -> str:
    cols = ",\n  ".join(
        f"{c.name} {map_type(c.type)}" + ("" if c.nullable else " NOT NULL") for c in spec.columns
    )
    audit = ",\n  ".join(f"{n} {t}" for n, t in AUDIT_COLUMNS)
    return f"""
CREATE ICEBERG TABLE IF NOT EXISTS {database}.{spec.bronze_table} (
  {cols},
  {audit}
)
  CATALOG = 'SNOWFLAKE'
  EXTERNAL_VOLUME = '{external_volume}'
  BASE_LOCATION = 'iceberg/bronze/{spec.name}'
  COMMENT = '{spec.description} Source: {spec.source_system}.';
""".strip()


def bronze_copy_sql(spec: DatasetSpec, database: str, stage: str, blob_name: str,
                    sha256: str, batch_id: str) -> str:
    """COPY INTO bronze from the external stage, stamping audit columns."""
    select_cols = ", ".join(f"${i + 1}::{map_type(c.type)}" for i, c in enumerate(spec.columns))
    target_cols = ", ".join(c.name for c in spec.columns)
    audit_cols = ", ".join(n for n, _ in AUDIT_COLUMNS)
    return f"""
COPY INTO {database}.{spec.bronze_table} ({target_cols}, {audit_cols})
FROM (
  SELECT {select_cols},
         METADATA$FILENAME, '{sha256}', CURRENT_TIMESTAMP(), '{batch_id}'
  FROM @{database}.{stage}/{blob_name}
)
FILE_FORMAT = (TYPE = CSV FIELD_DELIMITER = '{spec.delimiter}' SKIP_HEADER = 1
               FIELD_OPTIONALLY_ENCLOSED_BY = '"' NULL_IF = ('', 'NULL') TRIM_SPACE = TRUE)
ON_ERROR = 'ABORT_STATEMENT'
FORCE = FALSE;
""".strip()
