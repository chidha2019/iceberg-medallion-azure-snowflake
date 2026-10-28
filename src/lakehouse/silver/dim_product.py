from lakehouse.lineage import asset
from lakehouse.silver.base import run_sql_asset


@asset(
    name="silver.dim_product", layer="silver", output="LAKEHOUSE.SILVER.DIM_PRODUCT",
    inputs=("bronze.products",), grain="one row per product_id (latest version)",
    keys=("product_id",), sql_file="20_silver/dim_product.sql",
    transformations=("dedupe on product_id keeping max(updated_at)",
                     "standardise category", "unit_price must be > 0"),
    description="Conformed product dimension.",
)
def dim_product(runner, settings):
    return run_sql_asset(dim_product.__asset__, runner, settings)
