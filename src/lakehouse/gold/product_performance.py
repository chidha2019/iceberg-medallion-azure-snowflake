from lakehouse.lineage import asset
from lakehouse.silver.base import run_sql_asset


@asset(
    name="gold.product_performance", layer="gold", output="LAKEHOUSE.GOLD.PRODUCT_PERFORMANCE",
    inputs=("silver.dim_product", "silver.fct_order_line"),
    grain="one row per product_id", keys=("product_id",),
    sql_file="30_gold/product_performance.sql",
    transformations=("left join products to order lines",
                     "aggregate: units_sold, revenue, cancel_rate",
                     "window: revenue_rank over category"),
    description="Product performance with category ranking.",
)
def product_performance(runner, settings):
    return run_sql_asset(product_performance.__asset__, runner, settings)
