import os
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault("AZURE_STORAGE_ACCOUNT", "test")
os.environ.setdefault("SNOWFLAKE_ACCOUNT", "test")
os.environ.setdefault("SNOWFLAKE_USER", "test")
os.environ.setdefault("SNOWFLAKE_PASSWORD", "test")


@pytest.fixture
def specs():
    from lakehouse.config import load_dataset_specs
    return {s.name: s for s in load_dataset_specs(ROOT / "config" / "datasets.yaml")}


class FakeRunner:
    """Records SQL instead of executing it."""
    def __init__(self):
        self.executed: list[str] = []
        self.files: list[str] = []
        self.sql_root = ROOT / "sql"

    def execute(self, sql, params=None):
        self.executed.append(sql)
        return []

    def execute_file(self, relative, **fmt):
        (self.sql_root / relative).read_text().format(**fmt)  # validates placeholders
        self.files.append(relative)

    def scalar(self, sql):
        return 0 if "HAVING" in sql or "IS NULL" in sql else 5


@pytest.fixture
def fake_runner():
    return FakeRunner()
