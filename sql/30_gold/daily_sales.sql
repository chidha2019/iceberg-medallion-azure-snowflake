-- gold.daily_sales : daily revenue by category x country (full rebuild, Iceberg)
CREATE OR REPLACE ICEBERG TABLE {db}.GOLD.DAILY_SALES
  CATALOG='SNOWFLAKE' EXTERNAL_VOLUME='{vol}' BASE_LOCATION='iceberg/gold/daily_sales'
AS
SELECT f.order_date, p.category, c.country,
       SUM(f.line_amount)            AS gross_revenue,
       SUM(f.quantity)               AS units_sold,
       COUNT(DISTINCT f.order_id)    AS order_count,
       COUNT(DISTINCT f.customer_id) AS distinct_customers,
       CURRENT_TIMESTAMP()           AS _gold_ts
FROM {db}.SILVER.FCT_ORDER_LINE f
JOIN {db}.SILVER.DIM_PRODUCT  p ON p.product_id  = f.product_id
JOIN {db}.SILVER.DIM_CUSTOMER c ON c.customer_id = f.customer_id
WHERE f.order_status = 'COMPLETED'
GROUP BY ALL;
