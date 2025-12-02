from core.settings import settings
from datetime import datetime, timedelta, timezone
from passlib.context import CryptContext
from typing import List, Dict, Any, Optional
from fastapi import Request, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from starlette.middleware.base import BaseHTTPMiddleware
from jwt.exceptions import JWTError
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


# ========== REFRESH TOKEN FUNCTIONS ==========

def create_refresh_token(user_id: int) -> str:
    """Create a refresh token with 7-day expiration"""
    expires = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    payload = {
        "sub": str(user_id),
        "type": "refresh",
        "exp": expires,
        "iat": datetime.now(timezone.utc)
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALG)


def decode_refresh_token(token: str) -> dict:
    """Decode and validate refresh token"""
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALG])

        # Verify token type
        if payload.get("type") != "refresh":
            raise HTTPException(status_code=401, detail="Invalid token type")

        return payload
    except JWTError as e:
        logger.warning(f"Refresh token validation failed: {e}")
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")


async def revoke_token(token: str, request: Request) -> None:
    """Add token to Redis blacklist until expiration"""
    try:
        redis = request.app.state.redis
        decoded = decode_token(token)
        exp = decoded.get("exp")

        # Calculate TTL (time until expiration)
        ttl = exp - int(datetime.now(timezone.utc).timestamp())

        if ttl > 0:
            # Store in Redis with automatic expiration
            await redis.set(f"token:blacklist:{token}", "1", ex=ttl)
            logger.info(f"Token revoked: expires in {ttl}s")
    except Exception as e:
        logger.error(f"Failed to revoke token: {e}")
        # Don't raise - allow logout to proceed even if Redis fails


async def is_token_revoked(token: str, request: Request) -> bool:
    """Check if token is in blacklist"""
    try:
        redis = request.app.state.redis
        result = await redis.exists(f"token:blacklist:{token}")
        return result > 0
    except Exception as e:
        logger.warning(f"Redis check failed, assuming token valid: {e}")
        return False  # Fail open - allow access if Redis is down


# ========== AUTHENTICATION LOGGING ==========

def log_auth_event(
    event_type: str,
    user_id: Optional[int],
    email: Optional[str],
    success: bool,
    reason: Optional[str] = None,
    ip: Optional[str] = None,
    metadata: Optional[dict] = None
):
    """
    Log authentication events with masked sensitive data

    Args:
        event_type: Type of event (LOGIN, REGISTER, PASSWORD_RESET, etc.)
        user_id: User ID if known
        email: User email (will be masked)
        success: Whether operation succeeded
        reason: Failure reason or additional context
        ip: Client IP address
        metadata: Additional event-specific data
    """
    # Mask email for privacy (show first 2 chars + domain)
    if email and isinstance(email, str) and '@' in email:
        parts = email.split('@')
        if len(parts[0]) > 2:
            masked_email = parts[0][:2] + '***@' + parts[1]
        else:
            masked_email = '***@' + parts[1]
    else:
        masked_email = "N/A"

    log_data = {
        "event": event_type,
        "user_id": user_id or "N/A",
        "email": masked_email,
        "success": success,
        "reason": reason or "N/A",
        "ip": ip or "N/A"
    }

    if metadata:
        log_data.update(metadata)

    # Log as structured data for easy parsing
    logger.info(f"AUTH_EVENT: {' | '.join(f'{k}={v}' for k, v in log_data.items())}")


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