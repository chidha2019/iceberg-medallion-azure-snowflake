from lakehouse.lineage import asset
from lakehouse.silver.base import run_sql_asset


@asset(
    name="silver.dim_customer", layer="silver", output="LAKEHOUSE.SILVER.DIM_CUSTOMER",
    inputs=("bronze.customers",), grain="one row per customer_id (latest version)",
    keys=("customer_id",), sql_file="20_silver/dim_customer.sql",
    transformations=(
        "dedupe on customer_id keeping max(updated_at)",
        "lower+trim email", "upper country ISO2", "proper-case names",
        "null email -> is_contactable=false",
    ),
    description="Conformed customer dimension (SCD type 1).",
)
def dim_customer(runner, settings):
    return run_sql_asset(dim_customer.__asset__, runner, settings)
