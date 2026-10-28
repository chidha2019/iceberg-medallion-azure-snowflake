import lakehouse.orchestrator  # noqa: F401
from lakehouse.config import Settings
from lakehouse.lineage import registry


def test_silver_and_gold_sql_render_and_run(fake_runner):
    s = Settings()
    for layer in ("silver", "gold"):
        for a in registry.by_layer(layer):
            out = a.fn(fake_runner, s)
            assert out["rows"] == 5 and out["checks"]["duplicate_keys"] == 0
    assert "20_silver/fct_order_line.sql" in fake_runner.files
    assert "30_gold/customer_360.sql" in fake_runner.files
