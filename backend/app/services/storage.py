import re
import unicodedata
import os
import uuid
import asyncio
import logging
from typing import Optional
from pathlib import Path
from supabase import create_client, Client

from app.core.config import settings

logger = logging.getLogger(__name__)
STORAGE_PATH = Path("storage")
_supabase_client = None


def sanitize_filename(name: str) -> str:
    """Normalize and sanitize the filename to contain only safe ASCII characters."""
    # Normalize unicode to separate accents from base characters
    name = unicodedata.normalize("NFKD", name)
    # Strip accents
    name = name.encode("ascii", "ignore").decode("ascii")
    # Replace non-alphanumeric (except dot, dash, underscore) with underscore
    name = re.sub(r"[^a-zA-Z0-9._-]", "_", name)
    # Remove double underscores
    name = re.sub(r"__+", "_", name)
    # Strip leading/trailing underscores or dots
    name = name.strip("_.")
    return name or "file"


def _client() -> Optional[Client]:
    global _supabase_client
    if _supabase_client is not None:
        return _supabase_client
    
    # Check if settings are valid
    if not settings.SUPABASE_URL or not settings.SUPABASE_KEY:
        return None
    if "your-project-id" in settings.SUPABASE_URL or "your-supabase-key" in settings.SUPABASE_KEY:
        return None
        
    try:
        # Clean URL to get the base Supabase project URL
        supabase_url = settings.SUPABASE_URL.strip()
        if "/rest/v1" in supabase_url:
            supabase_url = supabase_url.split("/rest/v1")[0]
        supabase_url = supabase_url.rstrip("/")

        _supabase_client = create_client(supabase_url, settings.SUPABASE_KEY)
        return _supabase_client
    except Exception as e:
        logger.error(f"Failed to initialize Supabase client: {e}")
        return None


def ensure_local_file(file_key: str) -> Optional[str]:
    """Ensure the file exists locally, fetching it from Supabase if needed."""
    local_path = STORAGE_PATH / file_key
    if local_path.is_file():
        return str(local_path)

    client = _client()
    if client:
        try:
            local_path.parent.mkdir(parents=True, exist_ok=True)
            # Download file from private Supabase bucket
            data = client.storage.from_(settings.SUPABASE_BUCKET).download(file_key)
            with open(local_path, "wb") as f:
                f.write(data)
            return str(local_path)
        except Exception as e:
            logger.error(f"Failed to fetch file '{file_key}' from Supabase: {e}")
    return None


def generate_presigned_upload(filename: str, content_type: str = "application/octet-stream") -> dict:
    """Return a signed URL for direct browser uploads or a stub url if not configured."""
    safe_filename = sanitize_filename(filename)
    file_key = f"{uuid.uuid4().hex}/{safe_filename}"
    client = _client()
    if not client:
        # Dev fallback
        return {
            "upload_url": "",
            "file_url": f"/api/storage/{file_key}",
            "file_key": file_key,
        }
    try:
        # Generate signed upload URL from Supabase
        res = client.storage.from_(settings.SUPABASE_BUCKET).create_signed_upload_url(file_key)
        upload_url = res.get("signed_url", "")
        file_url = f"/api/storage/{file_key}"
        return {"upload_url": upload_url, "file_url": file_url, "file_key": file_key}
    except Exception as e:
        logger.error(f"Failed to create signed upload URL: {e}")
        return {
            "upload_url": "",
            "file_url": f"/api/storage/{file_key}",
            "file_key": file_key,
        }


async def upload_bytes(filename: str, data: bytes, content_type: str = "application/octet-stream") -> Optional[str]:
    """Uploads file bytes to Supabase Storage or fallback to local disk."""
    safe_filename = sanitize_filename(filename)
    file_key = f"{uuid.uuid4().hex}/{safe_filename}"
    client = _client()
    if client:
        try:
            # Run the synchronous Supabase call in a thread pool to avoid blocking FastAPI
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(
                None,
                lambda: client.storage.from_(settings.SUPABASE_BUCKET).upload(
                    path=file_key,
                    file=data,
                    file_options={"content-type": content_type}
                )
            )
            # Pre-cache the file locally so it's instantly available for gap analysis/AI
            local_path = STORAGE_PATH / file_key
            local_path.parent.mkdir(parents=True, exist_ok=True)
            with open(local_path, "wb") as f:
                f.write(data)
                
            return f"/api/storage/{file_key}"
        except Exception as e:
            logger.error(f"Supabase upload failed: {e}")
            # Fallback to local
            pass
            
    # Save locally for dev
    full_path = STORAGE_PATH / file_key
    full_path.parent.mkdir(parents=True, exist_ok=True)
    with open(full_path, "wb") as f:
        f.write(data)
    return f"/api/storage/{file_key}"
