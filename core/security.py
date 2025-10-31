from core.settings import settings
from datetime import datetime, timedelta, timezone
from passlib.context import CryptContext
from typing import List, Dict, Any
from fastapi import Request, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from starlette.middleware.base import BaseHTTPMiddleware
import jwt
import logging
import time
from collections import defaultdict, deque

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

class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limiting middleware with different limits for different endpoints"""
    
    def __init__(self, app, default_requests: int = 100, window_seconds: int = 60):
        super().__init__(app)
        self.default_requests = default_requests
        self.window_seconds = window_seconds
        # Store request timestamps for each IP
        self.requests: Dict[str, deque] = defaultdict(lambda: deque())
        
        # Different limits for different endpoint types
        self.endpoint_limits = {
            '/api/v1/auth/': 10,      # Strict for auth endpoints
            '/api/v1/chat/legacy': 20, # Moderate for AI endpoints
            '/api/v1/chat': 50,        # Higher for authenticated chat
        }

    async def dispatch(self, request: Request, call_next):
        # Get client IP
        client_ip = request.client.host
        current_time = time.time()
        
        # Determine rate limit for this endpoint
        rate_limit = self._get_rate_limit_for_path(request.url.path)
        
        # Clean old requests outside the window
        while (self.requests[client_ip] and 
               current_time - self.requests[client_ip][0] > self.window_seconds):
            self.requests[client_ip].popleft()
        
        # Check if rate limit exceeded
        if len(self.requests[client_ip]) >= rate_limit:
            logger.warning(f"Rate limit exceeded for IP {client_ip} on {request.url.path}")
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded. Max {rate_limit} requests per {self.window_seconds} seconds"
            )
        
        # Add current request
        self.requests[client_ip].append(current_time)
        
        response = await call_next(request)
        return response

    def _get_rate_limit_for_path(self, path: str) -> int:
        """Get rate limit based on endpoint path"""
        for endpoint_prefix, limit in self.endpoint_limits.items():
            if path.startswith(endpoint_prefix):
                return limit
        return self.default_requests


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