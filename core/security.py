from core.settings import settings
from datetime import datetime, timedelta, timezone
from passlib.context import CryptContext
from typing import List, Dict, Any
from fastapi import Request, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from starlette.middleware.base import BaseHTTPMiddleware
import jwt
import logging

logger = logging.getLogger(__name__)

pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(plain: str) -> str:
    if len(plain) > 72:
        plain = plain[:72]  # truncate safely for bcrypt
    return pwd_ctx.hash(plain[:72])

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_ctx.verify(plain, hashed)

def create_access_token(sub: str, extra: dict | None = None) -> str:
    payload = {"sub": sub, "exp": datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)}
    if extra: payload.update(extra)
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALG)

def decode_token(token: str) -> dict:
    return jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALG])


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to all responses"""
    
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        
        # Add security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        
        return response


def sanitize_input(data: Any) -> Any:
    """Sanitize input data to prevent injection attacks"""
    if isinstance(data, str):
        # Remove potentially dangerous characters
        dangerous_chars = ['<', '>', '"', "'", '&', '\x00']
        for char in dangerous_chars:
            data = data.replace(char, '')
        return data.strip()
    elif isinstance(data, dict):
        return {k: sanitize_input(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [sanitize_input(item) for item in data]
    return data


def mask_sensitive_data(data: Dict[str, Any], sensitive_fields: List[str] = None) -> Dict[str, Any]:
    """Mask sensitive data in logs or responses"""
    if sensitive_fields is None:
        sensitive_fields = [
            'password', 'token', 'secret', 'key', 'credential',
            'authorization', 'auth', 'jwt', 'session'
        ]
    
    masked_data = data.copy()
    
    for key, value in masked_data.items():
        key_lower = key.lower()
        if any(sensitive_field in key_lower for sensitive_field in sensitive_fields):
            if isinstance(value, str) and len(value) > 4:
                masked_data[key] = value[:2] + '*' * (len(value) - 4) + value[-2:]
            else:
                masked_data[key] = '***'
        elif isinstance(value, dict):
            masked_data[key] = mask_sensitive_data(value, sensitive_fields)
    
    return masked_data