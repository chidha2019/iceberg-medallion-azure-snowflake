-- gold.product_performance : per-product sales metrics with category ranking (Iceberg)
CREATE OR REPLACE ICEBERG TABLE {db}.GOLD.PRODUCT_PERFORMANCE
  CATALOG='SNOWFLAKE' EXTERNAL_VOLUME='{vol}' BASE_LOCATION='iceberg/gold/product_performance'
AS
WITH agg AS (
  SELECT p.product_id, p.sku, p.product_name, p.category, p.active,
         SUM(IFF(f.order_status='COMPLETED', f.quantity, 0))    AS units_sold,
         SUM(IFF(f.order_status='COMPLETED', f.line_amount, 0)) AS revenue,
         COUNT(f.order_id)                                       AS line_count,
         SUM(IFF(f.order_status='CANCELLED', 1, 0))              AS cancelled_lines
  FROM {db}.SILVER.DIM_PRODUCT p
  LEFT JOIN {db}.SILVER.FCT_ORDER_LINE f ON f.product_id = p.product_id
  GROUP BY ALL
)
SELECT *,
       IFF(line_count = 0, NULL, cancelled_lines / line_count) AS cancel_rate,
       RANK() OVER (PARTITION BY category ORDER BY revenue DESC) AS revenue_rank_in_category,
       CURRENT_TIMESTAMP() AS _gold_ts
FROM agg;
