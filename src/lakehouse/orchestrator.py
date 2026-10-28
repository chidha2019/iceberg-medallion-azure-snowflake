"""Layer-level runner: resolves assets from config/pipeline.yaml and runs them in lineage order."""
from __future__ import annotations

from pathlib import Path

import yaml

import lakehouse.bronze.load
import lakehouse.gold
import lakehouse.silver  # noqa: F401
from lakehouse.bronze.load import BronzeLoader
from lakehouse.config import Settings, load_dataset_specs
from lakehouse.ingestion.blob_uploader import BlobUploader
from lakehouse.lineage import registry
from lakehouse.logging import get_logger
from lakehouse.snowflake.connection import SnowflakeRunner

log = get_logger(__name__)


def load_pipeline_config(path: Path = Path("config/pipeline.yaml")) -> dict:
    return yaml.safe_load(path.read_text())


def run_bronze(settings: Settings, runner: SnowflakeRunner, only: list[str] | None = None) -> list[dict]:
    loader = BronzeLoader(settings, runner, BlobUploader(settings))
    specs = {s.name: s for s in load_dataset_specs(settings.lakehouse_config)}
    results = []
    for a in registry.by_layer("bronze"):
        ds = a.name.split(".", 1)[1]
        if only and ds not in only:
            continue
        results.append(a.fn(loader, specs[ds]))  # type: ignore[misc]
    return results


def run_layer(layer: str, settings: Settings, runner: SnowflakeRunner) -> list[dict]:
    if layer == "bronze":
        return run_bronze(settings, runner)
    names = load_pipeline_config()["layers"][layer]["assets"]
    results = []
    for a in registry.topological(names):
        if a.layer != layer:
            continue  # upstream layers are assumed already materialised
        log.info("asset_start", asset=a.name, inputs=a.inputs)
        results.append(a.fn(runner, settings))  # type: ignore[misc]
    return results
