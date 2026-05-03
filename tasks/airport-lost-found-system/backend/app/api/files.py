from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, File, UploadFile

from app.core.config import get_settings
from app.core.rate_limit import rate_limit
from app.schemas import FileUploadResponse
from app.services.azure_blob_service import azure_blob_service
from app.services.malware_scan_service import malware_scan_service


router = APIRouter(prefix="/files", tags=["files"])


@router.post("/upload", response_model=FileUploadResponse, dependencies=[Depends(rate_limit("files_upload", get_settings().rate_limit_upload_per_minute, 60))])
async def upload_file(file: UploadFile = File(...), folder: str = "uploads") -> dict:
    scan = await malware_scan_service.scan_upload(file)
    if not scan.get("clean"):
        from fastapi import HTTPException, status

        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="File failed malware scanning")
    result = await azure_blob_service.upload_file(file, folder=folder)
    result["malware_scan_status"] = str(scan.get("provider", "unknown"))
    result["retention_expires_at"] = datetime.now(UTC) + timedelta(days=get_settings().proof_document_retention_days)
    return result


@router.get("/{file_id:path}")
async def get_file(file_id: str) -> dict[str, str]:
    return {"file_id": file_id, "url": await azure_blob_service.generate_secure_url(file_id)}
