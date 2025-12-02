from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from jwt.exceptions import JWTError
from core.db import get_db
from core.security import decode_token, is_token_revoked
from models.user import User
from models.membership import FamilyMembership
import logging

logger = logging.getLogger(__name__)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

async def get_current_user(
    request: Request,
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> User:
    """Validate access token and return current user"""
    try:
        # Check if token is revoked
        if await is_token_revoked(token, request):
            logger.warning(f"AUTH_EVENT: TOKEN_VALIDATION_FAILED | reason=Token revoked | ip={request.client.host if request.client else 'N/A'}")
            raise HTTPException(status_code=401, detail="Token has been revoked")

        payload = decode_token(token)
        user_id = int(payload.get("sub"))

        user = db.get(User, user_id)
        if not user:
            raise HTTPException(status_code=401, detail="User not found")

        return user

    except JWTError as e:
        logger.warning(f"AUTH_EVENT: TOKEN_VALIDATION_FAILED | reason={str(e)} | ip={request.client.host if request.client else 'N/A'}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"AUTH_EVENT: TOKEN_VALIDATION_ERROR | reason={str(e)} | ip={request.client.host if request.client else 'N/A'}")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

def require_family_role(min_role: str):
    rank = {"member": 1, "admin": 2, "owner": 3}
    def _guard(family_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
        m = db.query(FamilyMembership).filter_by(family_id=family_id, user_id=current_user.id).first()
        if not m or rank[m.role] < rank[min_role]:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return current_user
    return _guard