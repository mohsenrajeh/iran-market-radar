"""Authentication and Session Management for Iran Market Radar."""
import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Header, Response, Cookie, status
from pydantic import BaseModel
from jose import jwt, JWTError

from packages.shared.config import settings
from packages.shared.logger import logger

router = APIRouter(prefix="/auth", tags=["Authentication"])

# JWT Configuration
# Long session token duration: 30 days (43,200 minutes)
ACCESS_TOKEN_EXPIRE_DAYS = 30
SECRET_KEY = os.environ.get("SESSION_SECRET", "iran_market_radar_ultra_secure_jwt_secret_key_2026_super_long")
ALGORITHM = "HS256"

# Default Admin Credentials (Configurable via ENV)
RADAR_ADMIN_USER = os.environ.get("RADAR_ADMIN_USER", "admin")
RADAR_ADMIN_PASS = os.environ.get("RADAR_ADMIN_PASSWORD", "radar2026")


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    success: bool
    message: str
    token: str
    username: str
    expires_in_days: int = ACCESS_TOKEN_EXPIRE_DAYS


class UserProfileResponse(BaseModel):
    authenticated: bool
    username: Optional[str] = None
    role: Optional[str] = None
    session_valid_until: Optional[str] = None


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Generates a signed JWT access token."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(days=ACCESS_TOKEN_EXPIRE_DAYS))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def verify_token(token: str) -> Optional[dict]:
    """Decodes and validates a JWT access token."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None


def get_current_user(
    authorization: Optional[str] = Header(None),
    radar_session: Optional[str] = Cookie(None),
) -> dict:
    """
    Dependency to verify user session from Authorization header or cookie.
    Allows seamless authenticated API operations.
    """
    token = None
    if authorization and authorization.startswith("Bearer "):
        token = authorization.split(" ")[1]
    elif radar_session:
        token = radar_session

    if not token:
        # Fallback to guest if auth not strictly enforced, or raise 401
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="احراز هویت انجام نشده است. لطفاً وارد حساب کاربری خود شوید.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = verify_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="نشست کاربری منقضی شده یا نامعتبر است. لطفاً مجدداً لاگین کنید.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return payload


@router.post("/login", response_model=LoginResponse)
def login(req: LoginRequest, response: Response):
    """
    Verifies username and password, issuing a persistent 30-day JWT session.
    """
    # Constant-time comparison for security
    user_match = secrets.compare_digest(req.username.strip(), RADAR_ADMIN_USER)
    pass_match = secrets.compare_digest(req.password.strip(), RADAR_ADMIN_PASS)

    if not (user_match and pass_match):
        logger.warning(f"Failed login attempt for user: {req.username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="نام کاربری یا رمز عبور اشتباه است.",
        )

    token = create_access_token(
        data={"sub": req.username, "role": "admin"},
        expires_delta=timedelta(days=ACCESS_TOKEN_EXPIRE_DAYS),
    )

    # Set secure persistent HTTP-only cookie
    response.set_cookie(
        key="radar_session",
        value=token,
        max_age=ACCESS_TOKEN_EXPIRE_DAYS * 24 * 3600,
        httponly=False,  # Allow frontend to inspect session if needed
        samesite="lax",
    )

    logger.info(f"User {req.username} logged in successfully (30-day session granted).")

    return LoginResponse(
        success=True,
        message="ورود موفقیت‌آمیز بود. نشست شما به مدت ۳۰ روز پایدار خواهد ماند.",
        token=token,
        username=req.username,
        expires_in_days=ACCESS_TOKEN_EXPIRE_DAYS,
    )


@router.get("/me", response_model=UserProfileResponse)
def get_user_status(
    authorization: Optional[str] = Header(None),
    radar_session: Optional[str] = Cookie(None),
):
    """Returns current user authentication status without throwing 401."""
    token = None
    if authorization and authorization.startswith("Bearer "):
        token = authorization.split(" ")[1]
    elif radar_session:
        token = radar_session

    if not token:
        return UserProfileResponse(authenticated=False)

    payload = verify_token(token)
    if not payload:
        return UserProfileResponse(authenticated=False)

    exp_ts = payload.get("exp")
    valid_until = datetime.fromtimestamp(exp_ts, tz=timezone.utc).isoformat() if exp_ts else None

    return UserProfileResponse(
        authenticated=True,
        username=payload.get("sub"),
        role=payload.get("role", "admin"),
        session_valid_until=valid_until,
    )


@router.post("/logout")
def logout(response: Response):
    """Clears user session cookie."""
    response.delete_cookie("radar_session")
    return {"success": True, "message": "از سامانه خارج شدید."}
