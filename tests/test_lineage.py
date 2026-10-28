import lakehouse.orchestrator
from lakehouse.lineage import registry


def test_all_layers_registered():
    names = {a.name for a in registry.all()}
    assert {"bronze.orders", "silver.fct_order_line", "gold.daily_sales"} <= names


def test_gold_depends_only_on_silver():
    for a in registry.by_layer("gold"):
        assert all(i.startswith("silver.") for i in a.inputs), a.name


def test_topological_order_puts_dims_before_fact():
    order = [a.name for a in registry.topological(["silver.fct_order_line"])]
    assert order.index("silver.dim_customer") < order.index("silver.fct_order_line")


def test_every_sql_asset_has_existing_file():
    for a in registry.all():
        if a.sql_file:
            assert (registry.get(a.name).fn is not None)
            assert (lakehouse.orchestrator.Path(__file__).parents[1] / "sql" / a.sql_file).exists()
