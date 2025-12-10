# services/oauth_signup.py
import logging
import secrets
from typing import Tuple

import httpx
from fastapi import HTTPException, status
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from core.security import create_access_token, hash_password, log_auth_event
from core.settings import settings
from crud.auth import get_user_by_email
from crud.user_preferences import create_user_preference
from models.oauth_account import OAuthAccount
from models.user import User

logger = logging.getLogger(__name__)


class OAuthSignupService:
    """Handle Supabase-backed OAuth signup."""

    _SUPPORTED_PROVIDERS = {"google", "apple"}
    _SUPABASE_USER_ENDPOINT = "/auth/v1/user"

    @classmethod
    async def register(
        cls,
        db: Session,
        supabase_jwt: str,
    ) -> Tuple[User, str, str]:
        """
        Verify token with Supabase, create a new local user, and persist a linked OAuth account.

        Returns (user, provider, username).
        """
        identity = await cls._fetch_supabase_identity(supabase_jwt)
        email = identity.get("email")
        if not email:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="OAuth profile missing email")

        metadata = identity.get("user_metadata") or {}
        username = (metadata.get("name") or "").strip()
        if not username and "@" in email:
            username = email.split("@", 1)[0]
        if not username:
            username = "freshly-user"

        provider = (identity.get("app_metadata") or {}).get("provider")
        provider = (provider or "").lower()
        if provider not in cls._SUPPORTED_PROVIDERS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Unsupported OAuth provider",
            )

        supabase_user_id = identity.get("id")
        if not supabase_user_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid Supabase response")

        # Check if email already exists and handle account linking protection
        existing_user = get_user_by_email(db, email)
        if existing_user:
            # Check if they have an OAuth account with a different provider
            existing_oauth = db.query(OAuthAccount).filter(
                OAuthAccount.user_id == existing_user.id
            ).first()

            if existing_oauth and existing_oauth.provider != provider:
                # Different provider - suggest using existing provider
                log_auth_event(
                    "OAUTH_SIGNUP_BLOCKED_PROVIDER_MISMATCH",
                    user_id=existing_user.id,
                    email=email,
                    success=False,
                    reason=f"Email registered with {existing_oauth.provider}",
                    metadata={"attempted_provider": provider, "existing_provider": existing_oauth.provider}
                )
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Email already registered with {existing_oauth.provider}. Please login with {existing_oauth.provider} instead."
                )
            else:
                # Same provider or email/password user
                log_auth_event(
                    "OAUTH_SIGNUP_BLOCKED_EMAIL_EXISTS",
                    user_id=existing_user.id,
                    email=email,
                    success=False,
                    reason="Email already registered"
                )
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Email already registered. Please login instead."
                )

        if db.query(OAuthAccount).filter(OAuthAccount.supabase_user_id == supabase_user_id).first():
            logger.info("[AuthService] OAuth signup blocked - Supabase user already linked: %s", supabase_user_id)
            log_auth_event(
                "OAUTH_SIGNUP_BLOCKED_SUPABASE_ID_EXISTS",
                user_id=None,
                email=email,
                success=False,
                reason="Supabase user ID already linked"
            )
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="User already exists")

        password_placeholder = hash_password(secrets.token_urlsafe(32))
        user = User(
            email=email,
            name=username,
            hashed_password=password_placeholder,
            is_verified=True,
        )

        oauth_account = OAuthAccount(
            user_id=user.id if user.id else None,
            email=email,
            username=username,
            provider=provider,
            supabase_user_id=supabase_user_id,
        )

        try:
            db.add(user)
            db.flush()  # Ensure user ID for FK
            oauth_account.user_id = user.id
            db.add(oauth_account)

            # Create default UserPreference for OAuth users (same as regular signup)
            create_user_preference(
                db,
                user_id=user.id,
                allergen_ingredient_ids=[],
                diet_codes=[],
                disliked_ingredient_ids=[],
                goal="balanced",
                calorie_target=2000
            )

            db.commit()
            db.refresh(user)
        except IntegrityError as exc:
            db.rollback()
            logger.error("[AuthService] Failed to create OAuth user %s: %s", email, exc)
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="User already exists")
        except Exception as exc:
            db.rollback()
            logger.error("[AuthService] Unexpected error creating OAuth user %s: %s", email, exc)
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Could not create user")

        logger.info("[AuthService] New %s user created: %s", provider.title(), email)
        return user, provider, username

    @staticmethod
    def issue_access_token(user: User) -> str:
        """Create a JWT using the shared helper."""
        return create_access_token(sub=str(user.id), extra={"email": user.email})

    @classmethod
    async def authenticate(
        cls,
        db: Session,
        supabase_jwt: str,
    ) -> Tuple[User, str, str]:
        """Validate a Supabase token and return the linked user."""
        identity = await cls._fetch_supabase_identity(supabase_jwt)
        email = identity.get("email")
        if not email:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")

        provider = (identity.get("app_metadata") or {}).get("provider")
        provider = (provider or "").lower()
        if provider not in cls._SUPPORTED_PROVIDERS:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported OAuth provider")

        supabase_user_id = identity.get("id")
        if not supabase_user_id:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")

        oauth_account = (
            db.query(OAuthAccount)
            .filter(
                or_(
                    OAuthAccount.email == email,
                    OAuthAccount.supabase_user_id == supabase_user_id,
                )
            )
            .first()
        )

        if not oauth_account:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not registered. Please sign up first.",
            )

        if oauth_account.provider != provider:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Authentication provider mismatch.",
            )

        user = db.query(User).get(oauth_account.user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not registered. Please sign up first.",
            )

        username = oauth_account.username or (user.name or email.split("@", 1)[0])
        logger.info("[AuthService] %s user logged in: %s", provider.title(), email)
        return user, provider, username

    @classmethod
    async def _fetch_supabase_identity(cls, supabase_jwt: str) -> dict:
        """
        Validate Supabase token and extract identity.
        Uses JWKS (RS256) validation with HS256/HTTP fallback.
        """
        if not supabase_jwt:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")

        # Primary: JWKS validation (local, no network call to Supabase user endpoint)
        try:
            from core.supabase_jwt import SupabaseJWTValidator

            claims = await SupabaseJWTValidator.validate_token(supabase_jwt)

            # Transform claims to expected format
            identity = {
                "id": claims.get("sub"),
                "email": claims.get("email"),
                "user_metadata": claims.get("user_metadata", {}),
                "app_metadata": claims.get("app_metadata", {}),
            }

            log_auth_event(
                "OAUTH_TOKEN_VALIDATION_SUCCESS",
                user_id=None,
                email=claims.get("email"),
                success=True,
                metadata={"method": "jwks"}
            )

            return identity

        except HTTPException:
            # Re-raise 401 errors (expired/invalid token)
            raise

        except Exception as exc:
            logger.warning(f"[AuthService] JWKS validation failed, falling back to HTTP: {exc}")
            # Fall back to HTTP validation if JWKS fails
            return await cls._fetch_supabase_identity_http(supabase_jwt)

    @classmethod
    async def _fetch_supabase_identity_http(cls, supabase_jwt: str) -> dict:
        """
        Fallback: HTTP call to Supabase /auth/v1/user endpoint.
        Used when JWKS validation fails (e.g., SUPABASE_URL misconfigured).
        """
        base_url = (settings.SUPABASE_URL or "").rstrip("/")
        if not base_url:
            logger.error("[AuthService] SUPABASE_URL not configured")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Supabase not configured")

        headers = {
            "Authorization": f"Bearer {supabase_jwt}",
            "Accept": "application/json",
        }
        if settings.SUPABASE_SERVICE_ROLE:
            headers["apikey"] = settings.SUPABASE_SERVICE_ROLE

        url = f"{base_url}{cls._SUPABASE_USER_ENDPOINT}"
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(url, headers=headers)
        except httpx.RequestError as exc:
            logger.error("[AuthService] Supabase request error: %s", exc)
            log_auth_event(
                "OAUTH_TOKEN_VALIDATION_FAILED",
                user_id=None,
                email=None,
                success=False,
                reason="network_error",
                metadata={"error": str(exc)}
            )
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Supabase unavailable")

        if resp.status_code == status.HTTP_401_UNAUTHORIZED:
            log_auth_event(
                "OAUTH_TOKEN_VALIDATION_FAILED",
                user_id=None,
                email=None,
                success=False,
                reason="invalid_token"
            )
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")

        if resp.status_code >= 400:
            logger.error(
                "[AuthService] Supabase verification failed (%s): %s",
                resp.status_code,
                resp.text,
            )
            log_auth_event(
                "OAUTH_TOKEN_VALIDATION_FAILED",
                user_id=None,
                email=None,
                success=False,
                reason="supabase_error",
                metadata={"status_code": resp.status_code}
            )
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Unable to verify token")

        identity = resp.json()
        log_auth_event(
            "OAUTH_TOKEN_VALIDATION_SUCCESS",
            user_id=None,
            email=identity.get("email"),
            success=True,
            metadata={"method": "http"}
        )

        return identity
