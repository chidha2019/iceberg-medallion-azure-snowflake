"""Typed configuration: environment settings + declarative dataset contracts."""
from __future__ import annotations

from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings sourced from environment / .env."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    azure_storage_account: str
    azure_storage_container: str = "lakehouse"
    azure_tenant_id: str | None = None
    azure_client_id: str | None = None
    azure_client_secret: str | None = None

    snowflake_account: str
    snowflake_user: str
    snowflake_password: str
    snowflake_role: str = "LAKEHOUSE_ADMIN"
    snowflake_warehouse: str = "LAKEHOUSE_WH"
    snowflake_database: str = "LAKEHOUSE"
    snowflake_external_volume: str = "AZURE_ICEBERG_VOL"

    lakehouse_source_root: Path = Path("./data/onprem")
    lakehouse_config: Path = Path("./config/datasets.yaml")
    lakehouse_env: Literal["dev", "test", "prod"] = "dev"

    @property
    def blob_account_url(self) -> str:
        return f"https://{self.azure_storage_account}.blob.core.windows.net"


class ColumnSpec(BaseModel):
    name: str
    type: str
    nullable: bool = True


class DatasetSpec(BaseModel):
    """Data contract for one on-prem CSV feed."""

    name: str
    source_system: str
    description: str = ""
    primary_key: list[str]
    cdc_column: str | None = None
    file_pattern: str = "*.csv"
    delimiter: str = ","
    encoding: str = "utf-8"
    header: bool = True
    blob_prefix: str = "landing"
    load_mode: Literal["append", "full_refresh"] = "append"
    archive_after_upload: bool = True
    schema_: list[ColumnSpec] = Field(alias="schema")

    model_config = {"populate_by_name": True}

    @property
    def columns(self) -> list[ColumnSpec]:
        return self.schema_

    @property
    def bronze_table(self) -> str:
        return f"BRONZE.{self.name.upper()}"


def load_dataset_specs(path: Path) -> list[DatasetSpec]:
    raw = yaml.safe_load(path.read_text())
    defaults: dict = raw.get("defaults", {})
    return [DatasetSpec(**{**defaults, **ds}) for ds in raw["datasets"]]
