# How this repo is designed to be crawled

This repo is structured so a two-pass codebase crawler can extract clean, typed facts
and distinguish **declared behaviour** from **implementation evidence** from **test coverage**.

## Pass 1 — structure discovery

| Signal | Where | What it yields |
|---|---|---|
| Entry points | `pyproject.toml [project.scripts]`, `src/lakehouse/cli.py`, `dags/` | `Capability` nodes: setup, ingest, run-layer, export-manifest |
| Data contracts | `config/datasets.yaml` | `Dataset`, `Column`, `SourceSystem` nodes; PK / CDC edges |
| Orchestration | `config/pipeline.yaml` | layer membership, schedule, retry policy |
| Layers | `src/lakehouse/{bronze,silver,gold}` + `sql/{10,20,30}_*` | `Layer` nodes |
| Asset manifest | `docs/asset-manifest.json` (from `lakehouse export-manifest`) | `Asset` nodes + `FEEDS` edges — the declared lineage graph |

## Pass 2 — implementation & evidence

| Fact type | Evidence source | Example extraction |
|---|---|---|
| Declared transformation | `@asset(transformations=...)` | "dedupe on customer_id keeping max(updated_at)" |
| Implemented transformation | matching `sql_file` | `QUALIFY ROW_NUMBER() OVER (PARTITION BY customer_id ...)` |
| Declared grain/keys | `@asset(grain=..., keys=...)` | one row per order_id + line_number |
| Enforced keys | `quality/checks.py` | uniqueness + not-null SQL generated from `keys` |
| Operational behaviour | `tenacity` retries, `ON_ERROR`, `FORCE=FALSE`, `_processed/` archive | idempotency & failure semantics |
| Test coverage | `tests/test_*.py` | which contracts/DDL/lineage facts are asserted |
| Gaps | declared transformation with no matching SQL construct, or asset with no test | flagged as `GAP` |

### Suggested node/edge model (Neo4j)

```
(:SourceSystem)-[:PROVIDES]->(:Dataset)-[:LANDS_IN]->(:Asset {layer:'bronze'})
(:Asset)-[:FEEDS]->(:Asset)
(:Asset)-[:IMPLEMENTED_BY]->(:SqlFile|:PyFunction)
(:Asset)-[:DECLARES]->(:Transformation)
(:SqlFile)-[:EVIDENCES]->(:Transformation)          -- found in implementation
(:Test)-[:COVERS]->(:Asset|:Transformation|:Contract)
(:Asset)-[:CHECKED_BY]->(:QualityCheck)
```

### Why this helps agents build new pipelines

When a Data Engineer agent is asked to build a new silver asset, it retrieves:
1. the **pattern**: `@asset` decorator → `run_sql_asset` → `MERGE` with `QUALIFY ROW_NUMBER` dedupe,
2. the **conventions**: Iceberg DDL options, `_silver_ts` audit column, quarantine instead of drop,
3. the **contract shape** it must emit: name, layer, output, inputs, grain, keys, sql_file,
4. the **tests** it must satisfy: lineage layering rule, SQL placeholders render, keys unique.
