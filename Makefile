.PHONY: install lint test setup bronze silver gold run manifest

install:
	pip install -e ".[dev]"

lint:
	ruff check src tests && mypy src

test:
	pytest -q --cov=lakehouse

setup:        ## one-time Snowflake objects (external volume, schemas, bronze DDL)
	lakehouse setup

bronze:       ## scan on-prem CSVs -> Azure Blob -> Snowflake Iceberg bronze
	lakehouse ingest --all

silver:
	lakehouse run-layer silver

gold:
	lakehouse run-layer gold

run: bronze silver gold

manifest:     ## export asset registry for the knowledge-graph crawler
	lakehouse export-manifest --out docs/asset-manifest.json
