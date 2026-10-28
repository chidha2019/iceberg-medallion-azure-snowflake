"""CLI entry point: `lakehouse <command>`."""
from __future__ import annotations

import json
from pathlib import Path

import typer

from lakehouse import orchestrator
from lakehouse.config import Settings, load_dataset_specs
from lakehouse.lineage import registry
from lakehouse.logging import configure_logging
from lakehouse.snowflake.connection import SnowflakeRunner
from lakehouse.snowflake.iceberg import bronze_iceberg_ddl

app = typer.Typer(help="On-prem CSV -> Azure Blob -> Snowflake Iceberg medallion pipeline")


@app.callback()
def _init(log_level: str = "INFO") -> None:
    configure_logging(log_level)


@app.command()
def setup() -> None:
    """Create database/schemas/stage and bronze Iceberg tables (external volume needs ACCOUNTADMIN)."""
    s = Settings()
    r = SnowflakeRunner(s)
    r.execute_file("00_setup/02_database.sql", db=s.snowflake_database)
    r.execute_file("00_setup/03_landing_stage.sql", db=s.snowflake_database,
                   tenant_id=s.azure_tenant_id, storage_account=s.azure_storage_account,
                   container=s.azure_storage_container)
    for spec in load_dataset_specs(s.lakehouse_config):
        r.execute(bronze_iceberg_ddl(spec, s.snowflake_database, s.snowflake_external_volume))
    typer.echo("setup complete")


@app.command()
def ingest(dataset: list[str] = typer.Option(None), all: bool = False) -> None:
    """Bronze: scan on-prem CSVs, upload to Azure Blob, COPY INTO Iceberg bronze."""
    s = Settings()
    out = orchestrator.run_bronze(s, SnowflakeRunner(s), None if all else dataset)
    typer.echo(json.dumps(out, indent=2))


@app.command("run-layer")
def run_layer(layer: str = typer.Argument(..., help="bronze | silver | gold")) -> None:
    s = Settings()
    out = orchestrator.run_layer(layer, s, SnowflakeRunner(s))
    typer.echo(json.dumps(out, indent=2, default=str))


@app.command("export-manifest")
def export_manifest(out: Path = Path("docs/asset-manifest.json")) -> None:
    """Dump the declared asset graph for the knowledge-graph crawler."""
    import lakehouse.orchestrator  # noqa: F401  ensure all assets registered
    manifest = {
        "assets": [a.to_dict() for a in registry.all()],
        "edges": [{"from": u, "to": d, "type": "FEEDS"} for u, d in registry.edges()],
    }
    out.write_text(json.dumps(manifest, indent=2))
    typer.echo(f"wrote {out} ({len(manifest['assets'])} assets, {len(manifest['edges'])} edges)")


@app.command("show-ddl")
def show_ddl() -> None:
    """Print generated bronze Iceberg DDL (no connection needed)."""
    s = Settings()
    for spec in load_dataset_specs(s.lakehouse_config):
        typer.echo(bronze_iceberg_ddl(spec, s.snowflake_database, s.snowflake_external_volume))
        typer.echo()


if __name__ == "__main__":
    app()
