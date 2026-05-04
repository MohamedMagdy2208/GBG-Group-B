from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

from app.core.config import get_settings
from app.core.rate_limit import rate_limit
from app.core.rbac import get_current_user, get_optional_user
from app.models import User
from app.schemas import FileUploadResponse
from app.services.azure_blob_service import azure_blob_service
from app.services.malware_scan_service import malware_scan_service


router = APIRouter(prefix="/files", tags=["files"])

ALLOWED_FOLDERS = {"uploads", "proofs", "found-items"}


@router.post(
    "/upload",
    response_model=FileUploadResponse,
    dependencies=[Depends(rate_limit("files_upload", get_settings().rate_limit_upload_per_minute, 60))],
)
async def upload_file(
    file: UploadFile = File(...),
    folder: str = "uploads",
    current_user: User | None = Depends(get_optional_user),
) -> dict:
    if folder not in ALLOWED_FOLDERS:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported folder")
    # Anonymous passenger uploads are allowed only for the proof folder (chatbot intake).
    if current_user is None and folder != "proofs":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required for this folder")
    scan = await malware_scan_service.scan_upload(file)
    if not scan.get("clean"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="File failed malware scanning")
    result = await azure_blob_service.upload_file(file, folder=folder)
    result["malware_scan_status"] = str(scan.get("provider", "unknown"))
    result["retention_expires_at"] = datetime.now(UTC) + timedelta(days=get_settings().proof_document_retention_days)
    return result


@router.get("/{file_id:path}")
async def get_file(
    file_id: str,
    current_user: User = Depends(get_current_user),
) -> dict[str, str]:
    # The file id encodes the folder; staff can read anything, passengers can only read proofs they own
    # but ownership tracking isn't in scope here, so require auth at minimum.
    return {"file_id": file_id, "url": await azure_blob_service.generate_secure_url(file_id)}
