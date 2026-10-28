from lakehouse.snowflake.iceberg import bronze_copy_sql, bronze_iceberg_ddl


def test_ddl_is_managed_iceberg(specs):
    ddl = bronze_iceberg_ddl(specs["customers"], "LAKEHOUSE", "VOL")
    assert "CREATE ICEBERG TABLE" in ddl and "CATALOG = 'SNOWFLAKE'" in ddl
    assert "EXTERNAL_VOLUME = 'VOL'" in ddl and "customer_id STRING NOT NULL" in ddl
    assert "_ingest_sha256" in ddl


def test_copy_stamps_audit_columns(specs):
    sql = bronze_copy_sql(specs["orders"], "LAKEHOUSE", "BRONZE.LANDING_STAGE",
                          "orders/x.csv", "abc", "batch1")
    assert "METADATA$FILENAME" in sql and "'abc'" in sql and "'batch1'" in sql
    assert "$2::INT" in sql
