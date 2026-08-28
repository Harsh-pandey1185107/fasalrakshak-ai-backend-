from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.user import User


# ============================================================================
# JWT CONFIGURATION
# ============================================================================

SECRET_KEY = "fasalrakshak-change-this-secret-key-before-deployment"
ALGORITHM = "HS256"


# ============================================================================
# BEARER TOKEN
# ============================================================================

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/v1/auth/login"
)


# ============================================================================
# GET CURRENT USER
# ============================================================================

def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated.",
        headers={
            "WWW-Authenticate": "Bearer"
        },
    )

    try:

        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM],
        )

        username = payload.get("sub")

        if not username:
            raise credentials_exception

    except JWTError:

        raise credentials_exception

    user = (
        db.query(User)
        .filter(
            User.username == username
        )
        .first()
    )

    if not user:

        raise credentials_exception

    return user


# ============================================================================
# FARMER ONLY
# ============================================================================

def get_current_farmer(
    current_user: User = Depends(get_current_user),
) -> User:

    if current_user.role != "farmer":

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Farmer access required.",
        )

    return current_user


# ============================================================================
# OFFICER ONLY
# ============================================================================

def get_current_officer(
    current_user: User = Depends(get_current_user),
) -> User:

    if current_user.role != "officer":

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Officer access required.",
        )

    return current_user
