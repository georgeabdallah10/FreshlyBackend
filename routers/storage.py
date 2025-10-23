# routers/storage.py
import os
from PIL import Image
from fastapi import APIRouter, File, UploadFile, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from core.supaBase_client import get_supabase_admin
from core.auth import get_app_user_id   # uses x-user-id header
from io import BytesIO

# Helper to normalize get_public_url return shape
def _public_url_from(res) -> str:
    # Handles both storage3 return shapes:
    # - dict-like {"data": {"publicUrl": "..."}}
    # - plain string "https://.../object"
    if isinstance(res, str):
        return res
    if isinstance(res, dict):
        data = res.get("data") or {}
        return data.get("publicUrl") or res.get("publicUrl") or res.get("url") or ""
    return ""


router = APIRouter(prefix="/storage", tags=["storage"])
BUCKET = os.getenv("AVATARS_BUCKET", "users")
MAX_BYTES = 5 * 1024 * 1024  # 5MB

def detect_image_type(data: bytes) -> str | None:
    try:
        with Image.open(BytesIO(data)) as img:
            fmt = img.format.lower()
            if fmt in {"jpeg", "png"}:
                return fmt
    except Exception:
        return None
    return None

@router.post("/avatar/proxy")
async def upload_avatar_proxy(
    user_id: str = Depends(get_app_user_id),  # <- comes from x-user-id
    file: UploadFile = File(...)
):
    raw = await file.read()
    if len(raw) > MAX_BYTES:
        raise HTTPException(status_code=413, detail="Image too large")

    sniff = detect_image_type(raw) # 'jpeg' | 'png' | None
    if sniff not in {"jpeg", "png"}:
        raise HTTPException(status_code=400, detail="Invalid image type")

    ext = "jpg" if sniff == "jpeg" else sniff
    path = f"{user_id}/profile.{ext}"        # canonical path

    sb = get_supabase_admin()
    res = sb.storage.from_(BUCKET).upload(path, raw, {
        "content_type": f"image/{'jpeg' if ext=='jpg' else ext}",
        "cache_control": "3600",
        "upsert": "true"
    })
    if isinstance(res, dict) and res.get("error"):
        raise HTTPException(status_code=400, detail=res["error"]["message"])

    public_res = sb.storage.from_(BUCKET).get_public_url(path)
    public = _public_url_from(public_res)
    if not public:
        raise HTTPException(status_code=500, detail="Failed to derive public URL")
    return JSONResponse({"bucket": BUCKET, "path": path, "publicUrl": public}, status_code=201)

@router.post("/avatar/signed_url")
async def create_avatar_signed_upload(
    user_id: str = Depends(get_app_user_id),  # <- from x-user-id
):
    path = f"{user_id}/profile.jpg"           # enforce JPEG from client
    sb = get_supabase_admin()

    signed = sb.storage.from_(BUCKET).create_signed_upload_url(path)
    if isinstance(signed, dict) and signed.get("error"):
        raise HTTPException(status_code=400, detail=signed["error"]["message"])

    public_res = sb.storage.from_(BUCKET).get_public_url(path)
    public = _public_url_from(public_res)
    return {
        "bucket": BUCKET,
        "path": path,
        "signedUrl": signed["data"]["signedUrl"],
        "token": signed["data"].get("token"),
        "publicUrl": public
    }