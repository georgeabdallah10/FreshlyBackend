# core/supabase_jwt.py
"""
Supabase JWT validation module using JWKS (RS256) with HS256 fallback.

This module validates Supabase-issued OAuth tokens locally without requiring
a network call to Supabase's /auth/v1/user endpoint. It uses the JWKS endpoint
to fetch and cache public keys for RS256 validation.
"""
import logging
from typing import Optional, Dict, Any
from datetime import datetime, timezone

import httpx
import jwt
from jwt import PyJWKClient, ExpiredSignatureError
from fastapi import HTTPException, status
from cachetools import TTLCache

from core.settings import settings

logger = logging.getLogger(__name__)


class SupabaseJWTValidator:
    """
    Validates Supabase-issued OAuth tokens using JWKS (RS256) with HS256 fallback.

    Primary validation method: RS256 using JWKS public keys
    Fallback: HS256 using SUPABASE_JWT_SECRET (if configured)
    """

    # Cache JWKS for 1 hour (3600 seconds)
    _jwks_cache: TTLCache = TTLCache(maxsize=10, ttl=3600)
    _jwk_client: Optional[PyJWKClient] = None

    @classmethod
    def _get_jwks_url(cls) -> str:
        """Construct the JWKS URL from SUPABASE_URL."""
        base_url = (settings.SUPABASE_URL or "").rstrip("/")
        if not base_url:
            raise ValueError("SUPABASE_URL not configured")
        return f"{base_url}/auth/v1/jwks"

    @classmethod
    async def _fetch_jwks(cls) -> Dict[str, Any]:
        """
        Fetch JWKS from Supabase and cache it.

        Returns:
            dict: JWKS response containing keys

        Raises:
            HTTPException: If JWKS fetch fails
        """
        cache_key = "supabase_jwks"

        # Check cache first
        cached = cls._jwks_cache.get(cache_key)
        if cached is not None:
            return cached

        jwks_url = cls._get_jwks_url()

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(jwks_url)

            if resp.status_code != 200:
                logger.error(f"SUPABASE_JWKS_FETCH_FAILED | status={resp.status_code} | url={jwks_url}")
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Unable to fetch Supabase JWKS"
                )

            jwks = resp.json()
            cls._jwks_cache[cache_key] = jwks
            logger.info(f"SUPABASE_JWKS_FETCH_SUCCESS | keys={len(jwks.get('keys', []))}")
            return jwks

        except httpx.RequestError as exc:
            logger.error(f"SUPABASE_JWKS_FETCH_FAILED | error={exc}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Supabase JWKS unavailable"
            )

    @classmethod
    def _get_jwk_client(cls) -> PyJWKClient:
        """Get or create the PyJWKClient for JWKS validation."""
        if cls._jwk_client is None:
            jwks_url = cls._get_jwks_url()
            cls._jwk_client = PyJWKClient(jwks_url, cache_keys=True, lifespan=3600)
        return cls._jwk_client

    @classmethod
    def _validate_with_jwks(cls, token: str) -> Dict[str, Any]:
        """
        Validate token using RS256 with JWKS public keys.

        Args:
            token: The JWT token to validate

        Returns:
            dict: Decoded token claims

        Raises:
            ExpiredSignatureError: If token is expired
            jwt.exceptions.PyJWKClientError: If JWKS fetch fails
            jwt.exceptions.DecodeError: If token is invalid
        """
        jwk_client = cls._get_jwk_client()
        signing_key = jwk_client.get_signing_key_from_jwt(token)

        # Decode and validate the token
        payload = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            options={
                "verify_aud": False,  # Supabase tokens may not have standard audience
                "verify_iss": False,  # Skip issuer verification for flexibility
            }
        )

        return payload

    @classmethod
    def _validate_with_secret(cls, token: str) -> Dict[str, Any]:
        """
        Validate token using HS256 with SUPABASE_JWT_SECRET.

        This is a fallback for environments where JWKS isn't available.

        Args:
            token: The JWT token to validate

        Returns:
            dict: Decoded token claims

        Raises:
            ExpiredSignatureError: If token is expired
            jwt.exceptions.DecodeError: If token is invalid
            ValueError: If SUPABASE_JWT_SECRET is not configured
        """
        secret = settings.SUPABASE_JWT_SECRET
        if not secret:
            raise ValueError("SUPABASE_JWT_SECRET not configured for HS256 fallback")

        payload = jwt.decode(
            token,
            secret,
            algorithms=["HS256"],
            options={
                "verify_aud": False,
                "verify_iss": False,
            }
        )

        return payload

    @classmethod
    async def validate_token(cls, token: str) -> Dict[str, Any]:
        """
        Validate a Supabase JWT token and return decoded claims.

        This method tries RS256 (JWKS) first, then falls back to HS256
        if SUPABASE_JWT_SECRET is configured.

        Args:
            token: The Supabase JWT token to validate

        Returns:
            dict: Decoded claims containing:
                - sub: Supabase user ID
                - email: User's email
                - app_metadata: Contains provider info
                - user_metadata: Contains name and other user info

        Raises:
            HTTPException(401): If token is expired or invalid
            HTTPException(503): If validation service unavailable
        """
        if not token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )

        # Try RS256 (JWKS) first
        try:
            payload = cls._validate_with_jwks(token)
            logger.debug(f"SUPABASE_TOKEN_VALID | method=jwks | sub={payload.get('sub')}")
            return payload

        except ExpiredSignatureError:
            logger.warning(f"SUPABASE_TOKEN_EXPIRED | method=jwks")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token expired",
                headers={"X-Token-Status": "expired"}
            )

        except Exception as jwks_error:
            logger.warning(f"SUPABASE_JWKS_VALIDATION_FAILED | error={jwks_error}")

            # Try HS256 fallback if secret is configured
            if settings.SUPABASE_JWT_SECRET:
                try:
                    payload = cls._validate_with_secret(token)
                    logger.debug(f"SUPABASE_TOKEN_VALID | method=hs256 | sub={payload.get('sub')}")
                    return payload

                except ExpiredSignatureError:
                    logger.warning(f"SUPABASE_TOKEN_EXPIRED | method=hs256")
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Token expired",
                        headers={"X-Token-Status": "expired"}
                    )

                except Exception as hs256_error:
                    logger.warning(f"SUPABASE_HS256_VALIDATION_FAILED | error={hs256_error}")
                    # Fall through to invalid token response

            # Both methods failed
            logger.warning(f"SUPABASE_TOKEN_INVALID | jwks_error={jwks_error}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )

    @classmethod
    def clear_cache(cls) -> None:
        """Clear the JWKS cache. Useful for testing."""
        cls._jwks_cache.clear()
        cls._jwk_client = None
