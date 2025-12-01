"""
Rate limiting module with Redis-based distributed rate limiting and in-memory fallback.
Supports tier-aware limits (free vs pro users) and both burst and daily quotas.
"""
import logging
import time
from datetime import datetime, timezone
from typing import Optional, Callable
from fastapi import Request, HTTPException, status, Depends
from utils.cache import InMemoryCache

logger = logging.getLogger(__name__)


# Rate limit policies by route group and tier
RATE_LIMIT_POLICIES = {
    # AI Chat Endpoints (text-based chat)
    "chat": {
        "free": [
            {"limit": 10, "window": 60, "type": "burst"},     # 10/min
            {"limit": 50, "window": 86400, "type": "daily"}   # 50/day
        ],
        "pro": [
            {"limit": 30, "window": 60, "type": "burst"},     # 30/min
            {"limit": 200, "window": 86400, "type": "daily"}  # 200/day
        ]
    },
    # AI Image Generation (DALL-E - higher cost)
    "chat-image": {
        "free": [
            {"limit": 2, "window": 60, "type": "burst"},      # 2/min
            {"limit": 10, "window": 86400, "type": "daily"}   # 10/day
        ],
        "pro": [
            {"limit": 5, "window": 60, "type": "burst"},      # 5/min
            {"limit": 50, "window": 86400, "type": "daily"}   # 50/day
        ]
    },
    # Pantry CRUD operations (authenticated)
    "pantry-write": {
        "default": [
            {"limit": 60, "window": 60, "type": "burst"}      # 60/min
        ]
    },
    "pantry-read": {
        "default": [
            {"limit": 120, "window": 60, "type": "burst"}     # 120/min
        ]
    },
    # Notifications
    "notifications": {
        "default": [
            {"limit": 20, "window": 60, "type": "burst"}      # 20/min
        ]
    },
    # Auth endpoints (IP-based, no user)
    "auth-login": {
        "default": [
            {"limit": 10, "window": 60, "type": "burst"},     # 10/min
            {"limit": 50, "window": 86400, "type": "daily"}   # 50/day
        ]
    },
    "auth-register": {
        "default": [
            {"limit": 5, "window": 60, "type": "burst"},      # 5/min
            {"limit": 20, "window": 86400, "type": "daily"}   # 20/day
        ]
    },
    "auth-password-reset": {
        "default": [
            {"limit": 3, "window": 60, "type": "burst"},      # 3/min
            {"limit": 10, "window": 86400, "type": "daily"}   # 10/day
        ]
    },
    # Global IP fallback (for unauthenticated requests)
    "global-ip": {
        "default": [
            {"limit": 200, "window": 60, "type": "burst"}     # 200/min
        ]
    }
}


def build_rate_limit_key(
    route_group: str,
    identifier: str,
    window: int,
    policy_type: str = "burst"
) -> str:
    """
    Build Redis/cache key for rate limiting.

    Args:
        route_group: The route group (e.g., "chat", "pantry-write")
        identifier: User ID or IP address
        window: Time window in seconds
        policy_type: "burst" or "daily"

    Returns:
        Redis key string

    Examples:
        rl:user:123:chat:60
        rl:user:123:chat:day:20251201
        rl:ip:192.168.1.1:auth-login:60
    """
    if policy_type == "daily":
        # Use UTC date for daily quotas (resets at midnight UTC)
        date_str = datetime.now(timezone.utc).strftime("%Y%m%d")
        return f"rl:{identifier}:{route_group}:day:{date_str}"
    else:
        # Burst limits use window in seconds
        return f"rl:{identifier}:{route_group}:{window}"


async def check_rate_limit_redis(
    redis,
    key: str,
    limit: int,
    window: int
) -> tuple[bool, int]:
    """
    Check rate limit using Redis INCR + EXPIRE pattern.

    Args:
        redis: Redis client
        key: Rate limit key
        limit: Maximum requests allowed
        window: Time window in seconds

    Returns:
        (allowed: bool, ttl_seconds: int)
    """
    try:
        # Increment counter
        current = await redis.incr(key)

        # Set expiration on first increment
        if current == 1:
            await redis.expire(key, window)

        # Get TTL for retry-after header
        ttl = await redis.ttl(key)
        if ttl == -1:  # Key exists but has no expiration
            await redis.expire(key, window)
            ttl = window

        allowed = current <= limit
        return allowed, max(ttl, 0)

    except Exception as e:
        logger.error(f"Redis rate limit check error: {e}")
        # On Redis error, allow the request (fail open)
        return True, 0


async def check_rate_limit_memory(
    cache: InMemoryCache,
    key: str,
    limit: int,
    window: int
) -> tuple[bool, int]:
    """
    Check rate limit using in-memory cache as fallback.

    Args:
        cache: InMemoryCache instance
        key: Rate limit key
        limit: Maximum requests allowed
        window: Time window in seconds

    Returns:
        (allowed: bool, ttl_seconds: int)
    """
    try:
        # Get current count
        data = await cache.get(key)

        if data is None:
            # First request, set count to 1
            await cache.set(key, {"count": 1, "expires_at": time.time() + window}, ttl=window)
            return True, window

        current_count = data.get("count", 0)
        expires_at = data.get("expires_at", time.time() + window)

        # Increment count
        new_count = current_count + 1
        await cache.set(key, {"count": new_count, "expires_at": expires_at}, ttl=window)

        # Calculate TTL
        ttl = int(expires_at - time.time())

        allowed = new_count <= limit
        return allowed, max(ttl, 0)

    except Exception as e:
        logger.error(f"In-memory rate limit check error: {e}")
        # On error, allow the request (fail open)
        return True, 0


async def check_rate_limit(
    redis,
    fallback_cache: InMemoryCache,
    key: str,
    limit: int,
    window: int
) -> tuple[bool, int]:
    """
    Check if request exceeds rate limit.
    Uses Redis if available, falls back to in-memory cache.

    Args:
        redis: Redis client (can be None)
        fallback_cache: InMemoryCache instance for fallback
        key: Rate limit key
        limit: Maximum requests allowed
        window: Time window in seconds

    Returns:
        (allowed: bool, ttl_seconds: int)
    """
    if redis is not None:
        return await check_rate_limit_redis(redis, key, limit, window)
    else:
        return await check_rate_limit_memory(fallback_cache, key, limit, window)


def get_policies_for(route_group: str, tier: str = "free") -> list[dict]:
    """
    Get rate limit policies for a route group and user tier.

    Args:
        route_group: The route group (e.g., "chat", "pantry-write")
        tier: User tier ("free", "pro", or "default")

    Returns:
        List of policy dictionaries
    """
    policies = RATE_LIMIT_POLICIES.get(route_group, {})

    # Try to get tier-specific policies
    tier_policies = policies.get(tier)
    if tier_policies:
        return tier_policies

    # Fall back to "default" policies
    default_policies = policies.get("default")
    if default_policies:
        return default_policies

    # If tier is not "free", try falling back to "free" tier
    if tier != "free":
        free_policies = policies.get("free")
        if free_policies:
            logger.warning(f"No policies for tier '{tier}' in route '{route_group}', using 'free' tier")
            return free_policies

    # No policies found
    logger.error(f"No rate limit policies found for route '{route_group}' and tier '{tier}'")
    return []


def rate_limiter(route_group: str, require_auth: bool = True) -> Callable:
    """
    Dependency factory for rate limiting.

    Args:
        route_group: The route group to apply limits for
        require_auth: If True, requires authentication and uses user-based limits.
                     If False, uses IP-based limits (for auth endpoints)

    Usage:
        @router.post("/chat", dependencies=[Depends(rate_limiter("chat"))])
        async def chat_endpoint(...): ...

        @router.post("/login", dependencies=[Depends(rate_limiter("auth-login", require_auth=False))])
        async def login(...): ...

    Returns:
        FastAPI dependency function
    """
    async def rate_limit_dependency(request: Request):
        # Get Redis and fallback cache from app state
        redis = getattr(request.app.state, "redis", None)
        fallback_cache = getattr(request.app.state, "rate_limit_cache", None)

        if fallback_cache is None:
            # No rate limiting configured
            logger.warning("Rate limiting not configured, allowing request")
            return

        # Determine user or IP identifier
        if require_auth:
            # Get user from request state (set by get_current_user dependency)
            user = getattr(request.state, "user", None)
            if user is None:
                # Try to get from FastAPI dependency injection
                # This happens when rate_limiter runs before get_current_user
                # In this case, we'll use IP-based limiting as fallback
                logger.warning(f"No user found for authenticated endpoint {route_group}, using IP fallback")
                identifier = f"ip:{request.client.host}"
                tier = "default"
            else:
                identifier = f"user:{user.id}"
                tier = getattr(user, "tier", "free")
        else:
            # IP-based limiting for unauthenticated endpoints
            identifier = f"ip:{request.client.host}"
            tier = "default"

        # Get policies for this route and tier
        policies = get_policies_for(route_group, tier)

        if not policies:
            logger.warning(f"No policies found for {route_group}, allowing request")
            return

        # Check all policies (both burst and daily if configured)
        for policy in policies:
            limit = policy["limit"]
            window = policy["window"]
            policy_type = policy.get("type", "burst")

            # Build key
            key = build_rate_limit_key(route_group, identifier, window, policy_type)

            # Check limit
            allowed, ttl = await check_rate_limit(redis, fallback_cache, key, limit, window)

            if not allowed:
                # Rate limit exceeded
                logger.warning(
                    f"Rate limit exceeded: {route_group} for {identifier} "
                    f"(tier: {tier}, limit: {limit}/{window}s, type: {policy_type})"
                )

                # Raise 429 with detailed error
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail={
                        "error": "Rate limit exceeded",
                        "route_group": route_group,
                        "tier": tier,
                        "limit": limit,
                        "window": window,
                        "policy_type": policy_type,
                        "retry_after": ttl
                    },
                    headers={"Retry-After": str(ttl)}
                )

        # All policies passed
        logger.debug(f"Rate limit check passed for {route_group} ({identifier}, tier: {tier})")

    return rate_limit_dependency


# Special dependency that requires authentication and injects user into request state
# This allows rate_limiter to access the user before get_current_user runs
def rate_limiter_with_user(route_group: str) -> Callable:
    """
    Rate limiter that requires authentication and properly injects user.
    Use this for authenticated endpoints to ensure user-based rate limiting.

    Usage:
        from core.deps import get_current_user

        @router.post("/chat")
        async def chat(
            request: Request,
            current_user: User = Depends(get_current_user),
            _rate_limit = Depends(rate_limiter_with_user("chat"))
        ): ...
    """
    from core.deps import get_current_user

    async def dependency(
        request: Request,
        current_user = Depends(get_current_user)
    ):
        # Inject user into request state for rate_limiter to access
        request.state.user = current_user

        # Run rate limiting
        await rate_limiter(route_group, require_auth=True)(request)

    return dependency
