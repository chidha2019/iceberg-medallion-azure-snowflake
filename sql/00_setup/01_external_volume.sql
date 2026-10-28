-- One-time: Azure external volume for Snowflake-managed Iceberg tables.
-- Run as ACCOUNTADMIN. After creation, grant the Snowflake service principal
-- "Storage Blob Data Contributor" on the container (DESCRIBE EXTERNAL VOLUME shows the app).
CREATE EXTERNAL VOLUME IF NOT EXISTS {vol}
  STORAGE_LOCATIONS = ((
    NAME = 'azure-lakehouse'
    STORAGE_PROVIDER = 'AZURE'
    STORAGE_BASE_URL = 'azure://{storage_account}.blob.core.windows.net/{container}/'
    AZURE_TENANT_ID = '{tenant_id}'
  ))
  ALLOW_WRITES = TRUE;
