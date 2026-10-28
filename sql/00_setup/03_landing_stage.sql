-- External stage pointing at the Azure landing zone written by BlobUploader.
CREATE STORAGE INTEGRATION IF NOT EXISTS AZURE_LANDING_INT
  TYPE = EXTERNAL_STAGE STORAGE_PROVIDER = 'AZURE' ENABLED = TRUE
  AZURE_TENANT_ID = '{tenant_id}'
  STORAGE_ALLOWED_LOCATIONS = ('azure://{storage_account}.blob.core.windows.net/{container}/landing/');

CREATE STAGE IF NOT EXISTS {db}.BRONZE.LANDING_STAGE
  STORAGE_INTEGRATION = AZURE_LANDING_INT
  URL = 'azure://{storage_account}.blob.core.windows.net/{container}/landing/'
  FILE_FORMAT = (TYPE = CSV SKIP_HEADER = 1);

-- Quarantine for silver referential-integrity rejects
CREATE TABLE IF NOT EXISTS {db}.OPS.QUARANTINE_ORDER_LINE (
  order_id STRING, line_number INT, customer_id STRING, product_id STRING,
  reason STRING, _ingest_sha256 STRING, quarantined_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);
