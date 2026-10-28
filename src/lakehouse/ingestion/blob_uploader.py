"""Upload on-prem files to Azure Blob (ADLS Gen2) landing zone with retries."""
from __future__ import annotations

from azure.core.exceptions import ResourceExistsError
from azure.identity import ClientSecretCredential, DefaultAzureCredential
from azure.storage.blob import BlobServiceClient, ContentSettings
from tenacity import retry, stop_after_attempt, wait_exponential

from lakehouse.config import DatasetSpec, Settings
from lakehouse.ingestion.scanner import SourceFile
from lakehouse.logging import get_logger

log = get_logger(__name__)


class BlobUploader:
    def __init__(self, settings: Settings) -> None:
        cred = (
            ClientSecretCredential(
                settings.azure_tenant_id, settings.azure_client_id, settings.azure_client_secret
            )
            if settings.azure_client_secret
            else DefaultAzureCredential()
        )
        self._client = BlobServiceClient(settings.blob_account_url, credential=cred)
        self._container = settings.azure_storage_container

    @retry(stop=stop_after_attempt(4), wait=wait_exponential(min=2, max=30), reraise=True)
    def upload(self, f: SourceFile, spec: DatasetSpec) -> str:
        """Idempotent: same checksum -> same blob name -> skip if it already exists."""
        name = f"{spec.blob_prefix}/{f.blob_name}"
        blob = self._client.get_blob_client(self._container, name)
        try:
            with f.path.open("rb") as data:
                blob.upload_blob(
                    data,
                    overwrite=False,
                    content_settings=ContentSettings(content_type="text/csv"),
                    metadata={"sha256": f.sha256, "dataset": f.dataset, "source": str(f.path)},
                )
            log.info("blob_uploaded", blob=name, bytes=f.size_bytes)
        except ResourceExistsError:
            log.info("blob_exists_skip", blob=name)
        return name
