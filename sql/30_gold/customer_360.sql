-- gold.customer_360 : one row per customer with lifetime metrics (full rebuild, Iceberg)
CREATE OR REPLACE ICEBERG TABLE {db}.GOLD.CUSTOMER_360
  CATALOG='SNOWFLAKE' EXTERNAL_VOLUME='{vol}' BASE_LOCATION='iceberg/gold/customer_360'
AS
WITH completed AS (
  SELECT * FROM {db}.SILVER.FCT_ORDER_LINE WHERE order_status = 'COMPLETED'
)
SELECT c.customer_id, c.first_name, c.last_name, c.email, c.country, c.signup_date,
       COUNT(DISTINCT f.order_id)              AS order_count,
       COALESCE(SUM(f.line_amount), 0)         AS lifetime_value,
       MIN(f.order_date)                       AS first_order_date,
       MAX(f.order_date)                       AS last_order_date,
       DATEDIFF('day', MAX(f.order_date), CURRENT_DATE()) AS days_since_last_order,
       CASE WHEN COALESCE(SUM(f.line_amount),0) >= 250 THEN 'HIGH'
            WHEN COALESCE(SUM(f.line_amount),0) >= 50  THEN 'MEDIUM'
            WHEN COALESCE(SUM(f.line_amount),0) >  0   THEN 'LOW'
            ELSE 'NO_PURCHASE' END              AS customer_segment,
       CURRENT_TIMESTAMP()                     AS _gold_ts
FROM {db}.SILVER.DIM_CUSTOMER c
LEFT JOIN completed f ON f.customer_id = c.customer_id
GROUP BY ALL;
