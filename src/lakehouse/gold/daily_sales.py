from lakehouse.lineage import asset
from lakehouse.silver.base import run_sql_asset


@asset(
    name="gold.daily_sales", layer="gold", output="LAKEHOUSE.GOLD.DAILY_SALES",
    inputs=("silver.fct_order_line", "silver.dim_product", "silver.dim_customer"),
    grain="one row per order_date + category + country",
    keys=("order_date", "category", "country"), sql_file="30_gold/daily_sales.sql",
    transformations=("inner join fact to product and customer dims",
                     "filter order_status = COMPLETED",
                     "aggregate: gross_revenue, units_sold, order_count, distinct_customers"),
    description="Daily sales rollup by product category and customer country.",
)
def daily_sales(runner, settings):
    return run_sql_asset(daily_sales.__asset__, runner, settings)
