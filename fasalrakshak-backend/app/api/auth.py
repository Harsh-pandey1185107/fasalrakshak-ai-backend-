from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from jose import jwt
from passlib.context import CryptContext
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.user import User


router = APIRouter(
    prefix="/api/v1/auth",
    tags=["Authentication"],
)


# ============================================================================
# CONFIGURATION
# ============================================================================

SECRET_KEY = "fasalrakshak-change-this-secret-key-before-deployment"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24

pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
)


# ============================================================================
# REQUEST MODELS
# ============================================================================

class LoginRequest(BaseModel):
    username: str
    password: str


class RegisterFarmerRequest(BaseModel):
    full_name: str
    phone: str
    address: str


# ============================================================================
# PASSWORD HELPERS
# ============================================================================

def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(
    plain_password: str,
    password_hash: str,
) -> bool:
    return pwd_context.verify(
        plain_password,
        password_hash,
    )


# ============================================================================
# TOKEN
# ============================================================================

def create_access_token(
    username: str,
    role: str,
) -> str:

    expire = datetime.utcnow() + timedelta(
        minutes=ACCESS_TOKEN_EXPIRE_MINUTES
    )

    payload = {
        "sub": username,
        "role": role,
        "exp": expire,
    }

    return jwt.encode(
        payload,
        SECRET_KEY,
        algorithm=ALGORITHM,
    )


# ============================================================================
# FARMER REGISTRATION
# ============================================================================

@router.post("/register")
def register_farmer(
    request: RegisterFarmerRequest,
    db: Session = Depends(get_db),
):

    full_name = request.full_name.strip()
    phone = request.phone.strip()
    address = request.address.strip()

    # ------------------------------------------------------------------------
    # VALIDATION
    # ------------------------------------------------------------------------

    if not full_name:
        raise HTTPException(
            status_code=400,
            detail="Full name is required.",
        )

    if not phone:
        raise HTTPException(
            status_code=400,
            detail="Mobile number is required.",
        )

    if not phone.isdigit() or len(phone) != 10:
        raise HTTPException(
            status_code=400,
            detail="Enter a valid 10-digit mobile number.",
        )

    if not address:
        raise HTTPException(
            status_code=400,
            detail="Address is required.",
        )

    # ------------------------------------------------------------------------
    # PHONE NUMBER IS THE FARMER'S UNIQUE LOGIN ID
    # ------------------------------------------------------------------------

    username = f"farmer_{phone}"

    existing_user = (
        db.query(User)
        .filter(User.username == username)
        .first()
    )

    # ------------------------------------------------------------------------
    # EXISTING FARMER
    # ------------------------------------------------------------------------

    if existing_user:

        token = create_access_token(
            existing_user.username,
            existing_user.role,
        )

        return {
            "message": "Farmer already registered.",
            "access_token": token,
            "token_type": "bearer",
            "username": existing_user.username,
            "role": existing_user.role,
            "full_name": existing_user.full_name,
            "phone": existing_user.phone,
            "address": existing_user.address,
        }

    # ------------------------------------------------------------------------
    # CREATE NEW FARMER
    # ------------------------------------------------------------------------

    user = User(
        username=username,

        # Farmer does not use a password.
        # Authentication is based on the registered mobile number.
        password_hash="FARMER_PHONE_AUTH",

        role="farmer",

        full_name=full_name,
        phone=phone,
        address=address,
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    # ------------------------------------------------------------------------
    # CREATE LOGIN TOKEN
    # ------------------------------------------------------------------------

    token = create_access_token(
        user.username,
        user.role,
    )

    return {
        "message": "Farmer registered successfully.",
        "access_token": token,
        "token_type": "bearer",
        "username": user.username,
        "role": user.role,
        "full_name": user.full_name,
        "phone": user.phone,
        "address": user.address,
    }


# ============================================================================
# LOGIN
# ============================================================================

@router.post("/login")
def login(
    request: LoginRequest,
    db: Session = Depends(get_db),
):

    username = request.username.strip()

    user = (
        db.query(User)
        .filter(User.username == username)
        .first()
    )

    if not user:
        raise HTTPException(
            status_code=401,
            detail="Invalid username or password.",
        )

    # ------------------------------------------------------------------------
    # FARMER LOGIN
    # ------------------------------------------------------------------------

    if user.role == "farmer":

        raise HTTPException(
            status_code=400,
            detail="Farmers should use mobile number registration.",
        )

    # ------------------------------------------------------------------------
    # OFFICER LOGIN
    # ------------------------------------------------------------------------

    if not verify_password(
        request.password,
        user.password_hash,
    ):
        raise HTTPException(
            status_code=401,
            detail="Invalid username or password.",
        )

    token = create_access_token(
        user.username,
        user.role,
    )

    return {
        "message": "Login successful.",
        "access_token": token,
        "token_type": "bearer",
        "username": user.username,
        "role": user.role,
    }
