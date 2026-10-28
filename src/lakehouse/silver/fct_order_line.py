from lakehouse.lineage import asset
from lakehouse.silver.base import run_sql_asset


@asset(
    name="silver.fct_order_line", layer="silver", output="LAKEHOUSE.SILVER.FCT_ORDER_LINE",
    inputs=("bronze.orders", "silver.dim_customer", "silver.dim_product"),
    grain="one row per order_id + line_number", keys=("order_id", "line_number"),
    sql_file="20_silver/fct_order_line.sql",
    transformations=(
        "dedupe on (order_id, line_number) keeping latest _ingest_ts",
        "derive line_amount = quantity * unit_price", "order_date = date(order_ts)",
        "referential check: unknown customer/product -> quarantine table",
    ),
    description="Cleansed order-line fact with referential integrity enforced.",
)
def fct_order_line(runner, settings):
    return run_sql_asset(fct_order_line.__asset__, runner, settings)
