-- silver.fct_order_line : cleansed order-line fact with RI enforcement (Iceberg)
CREATE ICEBERG TABLE IF NOT EXISTS {db}.SILVER.FCT_ORDER_LINE (
  order_id STRING NOT NULL, line_number INT NOT NULL, customer_id STRING NOT NULL,
  product_id STRING NOT NULL, order_date DATE, order_ts TIMESTAMP_NTZ(6),
  quantity INT, unit_price DECIMAL(12,2), line_amount DECIMAL(14,2), order_status STRING,
  _ingest_sha256 STRING, _silver_ts TIMESTAMP_NTZ(6)
) CATALOG='SNOWFLAKE' EXTERNAL_VOLUME='{vol}' BASE_LOCATION='iceberg/silver/fct_order_line';

CREATE OR REPLACE TEMPORARY TABLE {db}.SILVER._STG_ORDER_LINE AS
SELECT o.order_id, o.line_number, o.customer_id, o.product_id,
       CAST(o.order_ts AS DATE) AS order_date, o.order_ts, o.quantity, o.unit_price,
       o.quantity * o.unit_price AS line_amount, UPPER(TRIM(o.order_status)) AS order_status,
       o._ingest_sha256,
       c.customer_id IS NOT NULL AS has_customer, p.product_id IS NOT NULL AS has_product
FROM {db}.BRONZE.ORDERS o
LEFT JOIN {db}.SILVER.DIM_CUSTOMER c ON c.customer_id = o.customer_id
LEFT JOIN {db}.SILVER.DIM_PRODUCT  p ON p.product_id  = o.product_id
QUALIFY ROW_NUMBER() OVER (PARTITION BY o.order_id, o.line_number ORDER BY o._ingest_ts DESC) = 1;

-- quarantine referential-integrity failures instead of silently dropping them
INSERT INTO {db}.OPS.QUARANTINE_ORDER_LINE (order_id, line_number, customer_id, product_id, reason, _ingest_sha256)
SELECT order_id, line_number, customer_id, product_id,
       CASE WHEN NOT has_customer THEN 'UNKNOWN_CUSTOMER' ELSE 'UNKNOWN_PRODUCT' END, _ingest_sha256
FROM {db}.SILVER._STG_ORDER_LINE WHERE NOT has_customer OR NOT has_product;

MERGE INTO {db}.SILVER.FCT_ORDER_LINE t
USING (SELECT * FROM {db}.SILVER._STG_ORDER_LINE WHERE has_customer AND has_product) s
  ON t.order_id = s.order_id AND t.line_number = s.line_number
WHEN MATCHED AND t._ingest_sha256 <> s._ingest_sha256 THEN UPDATE SET
  customer_id = s.customer_id, product_id = s.product_id, order_date = s.order_date,
  order_ts = s.order_ts, quantity = s.quantity, unit_price = s.unit_price,
  line_amount = s.line_amount, order_status = s.order_status,
  _ingest_sha256 = s._ingest_sha256, _silver_ts = CURRENT_TIMESTAMP()
WHEN NOT MATCHED THEN INSERT (order_id, line_number, customer_id, product_id, order_date, order_ts,
  quantity, unit_price, line_amount, order_status, _ingest_sha256, _silver_ts)
VALUES (s.order_id, s.line_number, s.customer_id, s.product_id, s.order_date, s.order_ts,
  s.quantity, s.unit_price, s.line_amount, s.order_status, s._ingest_sha256, CURRENT_TIMESTAMP());
