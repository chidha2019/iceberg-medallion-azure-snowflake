# lakehouse-demo

Production-style medallion pipeline: **on-prem CSV → Azure Blob landing → Snowflake-managed Iceberg tables** (Bronze) → cleansed **Silver** → aggregated **Gold**.

The codebase is deliberately *declarative-first*: every pipeline step is an `@asset` with explicit lineage, grain, keys and transformations, so the repo can be crawled into a knowledge graph and used as reference context by data-engineering agents that generate new silver/gold pipelines. See [`docs/knowledge-graph.md`](docs/knowledge-graph.md).

## Architecture

```mermaid
flowchart LR
    subgraph ONPREM["On-prem"]
        CRM[(CRM)] --> CSV1[customers_*.csv]
        ERP[(ERP)] --> CSV2[products_*.csv]
        OMS[(OMS)] --> CSV3[orders_*.csv]
    end

    subgraph ING["Ingestion (Python)"]
        SCAN[scanner<br/>sha256 ledger] --> VAL[validator<br/>contract check] --> UP[blob_uploader<br/>retry + idempotent]
    end

    subgraph AZ["Azure Blob / ADLS Gen2"]
        LAND[/landing/&lt;dataset&gt;/ingest_date=.../]
        ICE[/iceberg/bronze|silver|gold/ — Parquet + metadata/]
    end

    subgraph SF["Snowflake"]
        STG[External Stage] -->|COPY INTO| BRZ
        subgraph BRZ["BRONZE (Iceberg, append-only)"]
            B1[CUSTOMERS] 
            B2[PRODUCTS]
            B3[ORDERS]
        end
        subgraph SLV["SILVER (Iceberg, MERGE)"]
            S1[DIM_CUSTOMER]
            S2[DIM_PRODUCT]
            S3[FCT_ORDER_LINE]
            Q[(OPS.QUARANTINE)]
        end
        subgraph GLD["GOLD (Iceberg, rebuild)"]
            G1[CUSTOMER_360]
            G2[DAILY_SALES]
            G3[PRODUCT_PERFORMANCE]
        end
        EV[(External Volume)]
    end

    CSV1 & CSV2 & CSV3 --> SCAN
    UP --> LAND --> STG
    B1 --> S1
    B2 --> S2
    B3 & S1 & S2 --> S3
    S3 -.RI rejects.-> Q
    S1 & S3 --> G1
    S3 & S2 & S1 --> G2
    S2 & S3 --> G3
    EV <--> ICE
    BRZ & SLV & GLD -.managed by.-> EV

    subgraph ORCH["Orchestration & Lineage"]
        REG[lineage.registry<br/>@asset] --> DAG[Airflow DAG]
        REG --> MAN[asset-manifest.json] --> KG[(Knowledge Graph<br/>Neo4j + Postgres)]
    end
```

### Layer contracts

| Layer | Storage | Write mode | Keys / grain | Logic lives in |
|---|---|---|---|---|
| Bronze | Snowflake-managed Iceberg on Azure | `COPY INTO` append, `FORCE=FALSE` | source PK + `_ingest_sha256` | `src/lakehouse/bronze/load.py`, generated DDL |
| Silver | Iceberg | `MERGE` (SCD1 dims, upsert fact) | business keys | `sql/20_silver/*.sql` |
| Gold | Iceberg | `CREATE OR REPLACE ... AS` | aggregate grain | `sql/30_gold/*.sql` |

Audit columns: bronze `_ingest_file/_ingest_sha256/_ingest_ts/_batch_id`, silver `_silver_ts`, gold `_gold_ts`.

## Repository layout

```
config/
  datasets.yaml        # data contracts per on-prem feed (schema, PK, CDC, load mode)
  pipeline.yaml        # layer membership, schedule, retries
data/onprem/<ds>/      # simulated on-prem drop folders (sample CSVs included)
src/lakehouse/
  config.py            # pydantic Settings + DatasetSpec
  lineage/registry.py  # @asset decorator — declared lineage graph
  ingestion/           # scanner (checksum ledger), validator, blob_uploader
  snowflake/           # connection runner, Iceberg DDL / COPY generator
  bronze/load.py       # BronzeLoader + bronze.* assets
  silver/*.py          # silver.* assets -> sql/20_silver
  gold/*.py            # gold.* assets   -> sql/30_gold
  quality/checks.py    # key uniqueness / not-null / non-empty from declared keys
  orchestrator.py      # topological runner driven by registry + pipeline.yaml
  cli.py               # `lakehouse setup|ingest|run-layer|export-manifest|show-ddl`
sql/                   # 00_setup, 20_silver (MERGE), 30_gold (aggregations/joins)
dags/                  # Airflow DAG generated from the asset registry
tests/                 # contracts, validator, DDL, lineage, silver/gold rendering
docs/                  # knowledge-graph.md, asset-manifest.json
```

## Quick start

```bash
cp .env.example .env            # fill Azure + Snowflake credentials
make install
make test                       # 11 tests, no cloud needed

# one-time (ACCOUNTADMIN): sql/00_setup/01_external_volume.sql, then grant the
# Snowflake app "Storage Blob Data Contributor" on the container
make setup                      # db, schemas, stage, bronze Iceberg tables

make bronze                     # CSV -> Blob -> Iceberg bronze
make silver                     # MERGE into dims/fact, quarantine RI failures
make gold                       # rebuild aggregates
make manifest                   # docs/asset-manifest.json for the KG crawler
```

Demo-friendly dirty data is included: duplicate customer versions, mixed-case / padded emails, a null email, a cancelled order and an order for an unknown customer (`C999`) that lands in `OPS.QUARANTINE_ORDER_LINE`.

## Adding a new silver or gold asset

1. Write `sql/20_silver/<name>.sql` (idempotent: `CREATE ICEBERG TABLE IF NOT EXISTS` + `MERGE`, placeholders `{db}` `{vol}`).
2. Add `src/lakehouse/silver/<name>.py` with an `@asset(...)` declaring `inputs`, `grain`, `keys`, `transformations`, `sql_file`.
3. Import it in `silver/__init__.py` and list it in `config/pipeline.yaml`.
4. `make test` — lineage tests enforce layering (gold only reads silver) and that the SQL renders.

That four-step pattern, plus the manifest, is exactly what the knowledge graph captures so an agent can reproduce it.

## Operational notes

- **Idempotency**: blob name is checksum-keyed (`overwrite=False`), `COPY ... FORCE=FALSE` uses Snowflake load history, processed files move to `_processed/`.
- **Failure handling**: contract violations reject the file (pipeline continues, logged); transient Azure/Snowflake errors retry with backoff; quality failures raise and fail the task.
- **Observability**: structlog JSON logs; Snowflake `QUERY_TAG=lakehouse:<env>`; `_batch_id` on every bronze row.
- **Security**: service principal / `DefaultAzureCredential`, secrets via env only, least-privilege `LAKEHOUSE_ADMIN` role.
