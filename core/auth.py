# core/auth.py
from fastapi import Request, HTTPException

def get_app_user_id(req: Request) -> str:
    user_id = req.headers.get("x-user-id")
    if not user_id:
        raise HTTPException(status_code=400, detail="Missing user id")
    return user_id