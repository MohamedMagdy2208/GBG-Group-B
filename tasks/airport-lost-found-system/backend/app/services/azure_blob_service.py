import logging
from pathlib import Path
from urllib.parse import urlparse
from uuid import uuid4

from fastapi import HTTPException, UploadFile, status

from app.core.config import get_settings


logger = logging.getLogger(__name__)

ALLOWED_CONTENT_TYPES = {
    "image/jpeg",
    "image/png",
    "image/webp",
    "application/pdf",
}

SIGNATURES = {
    "image/jpeg": [b"\xff\xd8\xff"],
    "image/png": [b"\x89PNG\r\n\x1a\n"],
    "image/webp": [b"RIFF"],
    "application/pdf": [b"%PDF"],
}

CONTENT_TYPE_ALIASES = {
    "image/jpg": "image/jpeg",
    "image/pjpeg": "image/jpeg",
    "image/x-png": "image/png",
}


def _normalize_content_type(value: str | None) -> str | None:
    if not value:
        return None
    canonical = value.split(";", 1)[0].strip().lower()
    return CONTENT_TYPE_ALIASES.get(canonical, canonical)


class AzureBlobService:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.settings.local_upload_dir.mkdir(parents=True, exist_ok=True)

    def _blob_service_client(self):
        from azure.storage.blob import BlobServiceClient

        if self.settings.azure_storage_connection_string:
            return BlobServiceClient.from_connection_string(self.settings.azure_storage_connection_string)
        from azure.identity import DefaultAzureCredential

        account_url = f"https://{self.settings.azure_storage_account_name}.blob.core.windows.net"
        return BlobServiceClient(account_url=account_url, credential=DefaultAzureCredential())

    async def validate_file(self, file: UploadFile, content: bytes) -> str:
        """Validate the upload. Returns the canonical content-type."""
        content_type = _normalize_content_type(file.content_type)
        if content_type not in ALLOWED_CONTENT_TYPES:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported file type")
        if not any(content.startswith(signature) for signature in SIGNATURES.get(content_type, [])):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="File content does not match declared type")
        max_bytes = self.settings.max_upload_mb * 1024 * 1024
        if len(content) > max_bytes:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="File is too large")
        if len(content) < 32:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="File is too small")
        return content_type

    async def upload_file(self, file: UploadFile, folder: str = "uploads") -> dict[str, str | int]:
        content = await file.read()
        canonical_type = await self.validate_file(file, content)
        suffix = Path(file.filename or "upload").suffix.lower()
        file_id = f"{folder}/{uuid4().hex}{suffix}"
        if self.settings.use_azure_services and (self.settings.azure_storage_connection_string or self.settings.azure_storage_account_name):
            from azure.storage.blob import ContentSettings

            client = self._blob_service_client()
            container = client.get_container_client(self.settings.azure_storage_container_name)
            container.upload_blob(
                name=file_id,
                data=content,
                overwrite=True,
                content_settings=ContentSettings(content_type=canonical_type),
            )
            url = container.get_blob_client(file_id).url
        else:
            local_path = self.settings.local_upload_dir / file_id
            local_path.parent.mkdir(parents=True, exist_ok=True)
            local_path.write_bytes(content)
            url = f"/uploads/{file_id}"
        logger.info("file uploaded", extra={"event": "blob_upload", "size_bytes": len(content)})
        return {"file_id": file_id, "url": url, "content_type": canonical_type, "size_bytes": len(content)}

    async def generate_secure_url(self, file_id: str, minutes: int = 15) -> str:
        if self.settings.use_azure_services and (self.settings.azure_storage_connection_string or self.settings.azure_storage_account_name):
            from datetime import UTC, datetime, timedelta

            from azure.storage.blob import BlobSasPermissions, generate_blob_sas

            client = self._blob_service_client()
            account_name = self.settings.azure_storage_account_name or client.account_name
            expiry = datetime.now(UTC) + timedelta(minutes=minutes)
            if not self.settings.azure_storage_connection_string:
                delegation_key = client.get_user_delegation_key(datetime.now(UTC), expiry)
                sas = generate_blob_sas(
                    account_name=account_name,
                    container_name=self.settings.azure_storage_container_name,
                    blob_name=file_id,
                    user_delegation_key=delegation_key,
                    permission=BlobSasPermissions(read=True),
                    expiry=expiry,
                )
                return f"{client.get_container_client(self.settings.azure_storage_container_name).get_blob_client(file_id).url}?{sas}"
            sas = generate_blob_sas(
                account_name=account_name,
                container_name=self.settings.azure_storage_container_name,
                blob_name=file_id,
                account_key=client.credential.account_key,
                permission=BlobSasPermissions(read=True),
                expiry=expiry,
            )
            return f"{client.get_container_client(self.settings.azure_storage_container_name).get_blob_client(file_id).url}?{sas}"
        return f"/uploads/{file_id}"

    async def generate_secure_url_from_blob_url(self, blob_url: str, minutes: int = 15) -> str:
        if "?" in blob_url or not self.settings.use_azure_services:
            return blob_url
        parsed = urlparse(blob_url)
        parts = parsed.path.strip("/").split("/", 1)
        if len(parts) != 2:
            return blob_url
        container, blob_name = parts
        if container != self.settings.azure_storage_container_name:
            return blob_url
        return await self.generate_secure_url(blob_name, minutes=minutes)

    def secure_url_from_blob_url_sync(self, blob_url: str | None, minutes: int = 60) -> str | None:
        """Synchronously sign a blob URL with a SAS token so the browser can fetch it.

        Returns the URL unchanged when:
          - input is None or empty
          - we are in local mode (URL is already a relative /uploads/... path)
          - URL already has a query string (already signed)
          - URL points at a different container than ours
        """
        if not blob_url:
            return blob_url
        if "?" in blob_url:
            return blob_url
        if not self.settings.use_azure_services:
            return blob_url
        if not (self.settings.azure_storage_connection_string or self.settings.azure_storage_account_name):
            return blob_url
        parsed = urlparse(blob_url)
        parts = parsed.path.strip("/").split("/", 1)
        if len(parts) != 2:
            return blob_url
        container, blob_name = parts
        if container != self.settings.azure_storage_container_name:
            return blob_url
        try:
            from datetime import UTC, datetime, timedelta

            from azure.storage.blob import BlobSasPermissions, generate_blob_sas

            client = self._blob_service_client()
            account_name = self.settings.azure_storage_account_name or client.account_name
            expiry = datetime.now(UTC) + timedelta(minutes=minutes)
            if self.settings.azure_storage_connection_string:
                sas = generate_blob_sas(
                    account_name=account_name,
                    container_name=self.settings.azure_storage_container_name,
                    blob_name=blob_name,
                    account_key=client.credential.account_key,
                    permission=BlobSasPermissions(read=True),
                    expiry=expiry,
                )
            else:
                delegation_key = client.get_user_delegation_key(datetime.now(UTC), expiry)
                sas = generate_blob_sas(
                    account_name=account_name,
                    container_name=self.settings.azure_storage_container_name,
                    blob_name=blob_name,
                    user_delegation_key=delegation_key,
                    permission=BlobSasPermissions(read=True),
                    expiry=expiry,
                )
            return f"{blob_url}?{sas}"
        except Exception:
            logger.exception("could not generate SAS URL", extra={"event": "sas_generate_failed"})
            return blob_url

    async def delete_file(self, file_id: str) -> None:
        if self.settings.use_azure_services and (self.settings.azure_storage_connection_string or self.settings.azure_storage_account_name):
            client = self._blob_service_client()
            client.get_container_client(self.settings.azure_storage_container_name).delete_blob(file_id)
            return
        local_path = self.settings.local_upload_dir / file_id
        if local_path.exists():
            local_path.unlink()


azure_blob_service = AzureBlobService()
