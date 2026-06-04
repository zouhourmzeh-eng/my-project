from fastapi import APIRouter, Depends, File, Form, UploadFile

from app.api.deps import get_current_user
from app.models import User
from app.schemas.schemas import UploadUrlOut
from app.services.storage import generate_presigned_upload, upload_bytes

router = APIRouter(prefix="/uploads", tags=["uploads"])


@router.post("/presign", response_model=UploadUrlOut)
async def presign(filename: str, content_type: str = "application/octet-stream", _: User = Depends(get_current_user)):
    """Get a pre-signed URL so the browser can PUT the file directly to S3/R2."""
    return generate_presigned_upload(filename, content_type)


@router.post("/direct")
async def direct_upload(file: UploadFile = File(...), _: User = Depends(get_current_user)):
    """Server-side passthrough upload — useful when CORS to the bucket is not configured."""
    data = await file.read()
    url = await upload_bytes(file.filename or "file", data, file.content_type or "application/octet-stream")
    return {"file_url": url, "file_name": file.filename}
