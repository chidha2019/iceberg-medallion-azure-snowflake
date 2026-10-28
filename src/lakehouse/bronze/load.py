"""Bronze layer: on-prem CSV -> Azure Blob landing -> Snowflake Iceberg bronze table.

Bronze is append-only and schema-aligned to the contract; no business logic.
Each file is loaded exactly once (checksum-keyed blob name + Snowflake COPY
load history + local archive).
"""
from __future__ import annotations

import uuid
from datetime import UTC, datetime

from lakehouse.config import DatasetSpec, Settings
from lakehouse.ingestion import scanner
from lakehouse.ingestion.blob_uploader import BlobUploader
from lakehouse.ingestion.validator import validate_csv
from lakehouse.lineage import asset
from lakehouse.logging import get_logger
from lakehouse.snowflake.connection import SnowflakeRunner
from lakehouse.snowflake.iceberg import bronze_copy_sql, bronze_iceberg_ddl

log = get_logger(__name__)
LANDING_STAGE = "BRONZE.LANDING_STAGE"


class BronzeLoader:
    def __init__(self, settings: Settings, runner: SnowflakeRunner, uploader: BlobUploader) -> None:
        self.settings, self.runner, self.uploader = settings, runner, uploader

    def ensure_table(self, spec: DatasetSpec) -> None:
        self.runner.execute(
            bronze_iceberg_ddl(spec, self.settings.snowflake_database,
                               self.settings.snowflake_external_volume)
        )

    def load_dataset(self, spec: DatasetSpec) -> dict:
        batch_id = f"{spec.name}-{datetime.now(UTC):%Y%m%dT%H%M%S}-{uuid.uuid4().hex[:6]}"
        files = scanner.scan(self.settings.lakehouse_source_root, spec)
        loaded, rejected = 0, []
        self.ensure_table(spec)
        if spec.load_mode == "full_refresh":
            self.runner.execute(f"TRUNCATE TABLE {self.settings.snowflake_database}.{spec.bronze_table}")
        for f in files:
            v = validate_csv(f.path, spec)
            if not v.ok:
                log.error("file_rejected", file=str(f.path), errors=v.errors[:5])
                rejected.append(f.path.name)
                continue
            blob = self.uploader.upload(f, spec)
            self.runner.execute(
                bronze_copy_sql(spec, self.settings.snowflake_database, LANDING_STAGE,
                                blob, f.sha256, batch_id)
            )
            if spec.archive_after_upload:
                scanner.archive(f)
            loaded += v.row_count
            log.info("file_loaded", file=f.path.name, rows=v.row_count, batch_id=batch_id)
        return {"dataset": spec.name, "batch_id": batch_id, "files": len(files),
                "rows": loaded, "rejected": rejected}


# Declared assets — one per contract. Inputs are external systems.
@asset(name="bronze.customers", layer="bronze", output="LAKEHOUSE.BRONZE.CUSTOMERS",
       inputs=("source:CRM_ONPREM.customers",), grain="one row per CSV record (append-only)",
       keys=("customer_id", "_ingest_sha256"), transformations=("type cast", "audit columns"),
       description="Raw customer extracts landed from on-prem CRM.")
def bronze_customers(loader: BronzeLoader, spec: DatasetSpec) -> dict:
    return loader.load_dataset(spec)


@asset(name="bronze.products", layer="bronze", output="LAKEHOUSE.BRONZE.PRODUCTS",
       inputs=("source:ERP_ONPREM.products",), grain="one row per CSV record (append-only)",
       keys=("product_id", "_ingest_sha256"), transformations=("type cast", "audit columns"),
       description="Raw product catalog extracts landed from on-prem ERP.")
def bronze_products(loader: BronzeLoader, spec: DatasetSpec) -> dict:
    return loader.load_dataset(spec)


@asset(name="bronze.orders", layer="bronze", output="LAKEHOUSE.BRONZE.ORDERS",
       inputs=("source:OMS_ONPREM.orders",), grain="one row per CSV record (append-only)",
       keys=("order_id", "line_number", "_ingest_sha256"),
       transformations=("type cast", "audit columns"),
       description="Raw order line extracts landed from on-prem OMS.")
def bronze_orders(loader: BronzeLoader, spec: DatasetSpec) -> dict:
    return loader.load_dataset(spec)
