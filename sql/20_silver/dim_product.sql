-- silver.dim_product : conformed product dimension (Iceberg)
CREATE ICEBERG TABLE IF NOT EXISTS {db}.SILVER.DIM_PRODUCT (
  product_id STRING NOT NULL, sku STRING, product_name STRING, category STRING,
  unit_price DECIMAL(12,2), active BOOLEAN,
  source_updated_at TIMESTAMP_NTZ(6), _silver_ts TIMESTAMP_NTZ(6)
) CATALOG='SNOWFLAKE' EXTERNAL_VOLUME='{vol}' BASE_LOCATION='iceberg/silver/dim_product';

MERGE INTO {db}.SILVER.DIM_PRODUCT t
USING (
  SELECT product_id, UPPER(TRIM(sku)) AS sku, TRIM(product_name) AS product_name,
         INITCAP(TRIM(category)) AS category, unit_price, active,
         updated_at AS source_updated_at, CURRENT_TIMESTAMP() AS _silver_ts
  FROM {db}.BRONZE.PRODUCTS
  WHERE unit_price > 0
  QUALIFY ROW_NUMBER() OVER (PARTITION BY product_id ORDER BY updated_at DESC, _ingest_ts DESC) = 1
) s ON t.product_id = s.product_id
WHEN MATCHED AND s.source_updated_at > t.source_updated_at THEN UPDATE SET
  sku = s.sku, product_name = s.product_name, category = s.category, unit_price = s.unit_price,
  active = s.active, source_updated_at = s.source_updated_at, _silver_ts = s._silver_ts
WHEN NOT MATCHED THEN INSERT VALUES (
  s.product_id, s.sku, s.product_name, s.category, s.unit_price, s.active,
  s.source_updated_at, s._silver_ts);
