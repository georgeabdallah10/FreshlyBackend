from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from core.db import get_db
from core.security import decode_token
from models.user import User
from models.membership import FamilyMembership

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    try:
        payload = decode_token(token); uid = int(payload.get("sub"))
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    user = db.query(User).get(uid)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user

def require_family_role(min_role: str):
    rank = {"member": 1, "admin": 2, "owner": 3}
    def _guard(family_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
        m = db.query(FamilyMembership).filter_by(family_id=family_id, user_id=current_user.id).first()
        if not m or rank[m.role] < rank[min_role]:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return current_user
    return _guard