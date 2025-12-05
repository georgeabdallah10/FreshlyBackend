"""
HTTP cache headers utility for response caching.
Provides ETag and Cache-Control headers for GET endpoints.
"""
import hashlib
import json
from typing import Any, Callable, Optional
from functools import wraps
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder


def generate_etag(content: Any) -> str:
    """
    Generate an ETag hash from response content.

    Args:
        content: Response content (will be JSON serialized)

    Returns:
        MD5 hash as ETag
    """
    if isinstance(content, (dict, list)):
        content_str = json.dumps(content, sort_keys=True, default=str)
    else:
        content_str = str(content)

    return hashlib.md5(content_str.encode()).hexdigest()


def cache_control(
    max_age: int = 300,  # 5 minutes default
    private: bool = True,
    must_revalidate: bool = True
):
    """
    Decorator to add Cache-Control and ETag headers to GET endpoints.

    Args:
        max_age: Cache duration in seconds (default: 300 = 5 minutes)
        private: If True, cache is private (user-specific), otherwise public
        must_revalidate: If True, requires revalidation after expiry

    Usage:
        @router.get("/items")
        @cache_control(max_age=600, private=True)
        async def get_items():
            return {"items": [...]}
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Get request from kwargs
            request: Optional[Request] = kwargs.get('request')

            # Execute the endpoint function
            result = await func(*args, **kwargs)

            # Generate ETag from response content
            if isinstance(result, dict) or isinstance(result, list):
                etag = generate_etag(result)
            else:
                # If result is already a Response, extract content
                etag = generate_etag(getattr(result, 'body', result))

            # Check If-None-Match header (client's cached ETag)
            if request:
                client_etag = request.headers.get('If-None-Match')
                if client_etag == etag:
                    # Client has up-to-date cached version
                    return Response(status_code=304, headers={
                        'ETag': etag,
                        'Cache-Control': f"{'private' if private else 'public'}, max-age={max_age}{', must-revalidate' if must_revalidate else ''}"
                    })

            # Build Cache-Control header
            cache_directive = f"{'private' if private else 'public'}, max-age={max_age}"
            if must_revalidate:
                cache_directive += ", must-revalidate"

            # Return response with cache headers
            if isinstance(result, Response):
                result.headers['ETag'] = etag
                result.headers['Cache-Control'] = cache_directive
                return result
            else:
                encoded = jsonable_encoder(result)
                return JSONResponse(
                    content=encoded,
                    headers={
                        'ETag': etag,
                        'Cache-Control': cache_directive
                    }
                )

        return wrapper
    return decorator


def no_cache():
    """
    Decorator to explicitly disable caching for sensitive endpoints.

    Usage:
        @router.get("/user/profile")
        @no_cache()
        async def get_profile():
            return {"sensitive": "data"}
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            result = await func(*args, **kwargs)

            if isinstance(result, Response):
                result.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
                result.headers['Pragma'] = 'no-cache'
                return result
            else:
                encoded = jsonable_encoder(result)
                return JSONResponse(
                    content=encoded,
                    headers={
                        'Cache-Control': 'no-store, no-cache, must-revalidate, max-age=0',
                        'Pragma': 'no-cache'
                    }
                )

        return wrapper
    return decorator
