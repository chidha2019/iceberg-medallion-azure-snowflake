from lakehouse.lineage import asset
from lakehouse.silver.base import run_sql_asset


@asset(
    name="gold.customer_360", layer="gold", output="LAKEHOUSE.GOLD.CUSTOMER_360",
    inputs=("silver.dim_customer", "silver.fct_order_line"),
    grain="one row per customer_id", keys=("customer_id",),
    sql_file="30_gold/customer_360.sql",
    transformations=("left join customers to completed order lines",
                     "aggregate: order_count, lifetime_value, first/last order date",
                     "derive customer_segment by lifetime_value tiers"),
    description="Customer 360 aggregate for CRM and marketing analytics.",
)
def customer_360(runner, settings):
    return run_sql_asset(customer_360.__asset__, runner, settings)
