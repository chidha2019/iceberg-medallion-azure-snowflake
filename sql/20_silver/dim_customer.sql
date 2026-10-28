-- silver.dim_customer : SCD1 conformed customer dimension (Iceberg)
CREATE ICEBERG TABLE IF NOT EXISTS {db}.SILVER.DIM_CUSTOMER (
  customer_id STRING NOT NULL, first_name STRING, last_name STRING, email STRING,
  country STRING, signup_date DATE, is_contactable BOOLEAN,
  source_updated_at TIMESTAMP_NTZ(6), _silver_ts TIMESTAMP_NTZ(6)
) CATALOG='SNOWFLAKE' EXTERNAL_VOLUME='{vol}' BASE_LOCATION='iceberg/silver/dim_customer';

MERGE INTO {db}.SILVER.DIM_CUSTOMER t
USING (
  SELECT customer_id,
         INITCAP(TRIM(first_name))               AS first_name,
         INITCAP(TRIM(last_name))                AS last_name,
         NULLIF(LOWER(TRIM(email)), '')          AS email,
         UPPER(TRIM(country))                    AS country,
         signup_date,
         NULLIF(LOWER(TRIM(email)), '') IS NOT NULL AS is_contactable,
         updated_at                              AS source_updated_at,
         CURRENT_TIMESTAMP()                     AS _silver_ts
  FROM {db}.BRONZE.CUSTOMERS
  QUALIFY ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY updated_at DESC, _ingest_ts DESC) = 1
) s ON t.customer_id = s.customer_id
WHEN MATCHED AND s.source_updated_at > t.source_updated_at THEN UPDATE SET
  first_name = s.first_name, last_name = s.last_name, email = s.email, country = s.country,
  signup_date = s.signup_date, is_contactable = s.is_contactable,
  source_updated_at = s.source_updated_at, _silver_ts = s._silver_ts
WHEN NOT MATCHED THEN INSERT VALUES (
  s.customer_id, s.first_name, s.last_name, s.email, s.country, s.signup_date,
  s.is_contactable, s.source_updated_at, s._silver_ts);
