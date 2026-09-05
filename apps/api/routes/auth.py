"""Authentication and Session Management for Iran Market Radar."""
import secrets
import hashlib
from datetime import datetime, timedelta, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Header, Response, Cookie, Request, status
from pydantic import BaseModel
from jose import jwt, JWTError
import redis
from redis.exceptions import RedisError

from packages.shared.config import settings
from packages.shared.logger import logger

router = APIRouter(prefix="/auth", tags=["Authentication"])

# JWT Configuration
ALGORITHM = "HS256"
TOKEN_ISSUER = "iran-market-radar"
TOKEN_AUDIENCE = "iran-market-radar-admin"
_LOGIN_WINDOW_SECONDS = 300
_LOGIN_ATTEMPTS_PER_WINDOW = 5
_login_rate_store = redis.Redis.from_url(settings.redis_url, decode_responses=True)


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    success: bool
    message: str
    username: str
    expires_in_minutes: int


class UserProfileResponse(BaseModel):
    authenticated: bool
    username: Optional[str] = None
    role: Optional[str] = None
    session_valid_until: Optional[str] = None


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Generates a signed JWT access token."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=settings.session_ttl_minutes))
    to_encode.update({
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "iss": TOKEN_ISSUER,
        "aud": TOKEN_AUDIENCE,
        "jti": secrets.token_urlsafe(18),
    })
    return jwt.encode(to_encode, settings.session_secret, algorithm=ALGORITHM)


def verify_token(token: str) -> Optional[dict]:
    """Decodes and validates a JWT access token."""
    try:
        payload = jwt.decode(
            token,
            settings.session_secret,
            algorithms=[ALGORITHM],
            issuer=TOKEN_ISSUER,
            audience=TOKEN_AUDIENCE,
        )
        if payload.get("role") != "admin" or not payload.get("sub"):
            return None
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
            detail="نشست مالک سامانه موجود نیست؛ لطفاً دوباره وارد شوید.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = verify_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="نشست مالک سامانه منقضی شده است؛ لطفاً دوباره وارد شوید.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return payload


def _login_rate_key(username: str) -> str:
    """Use a non-reversible account key so usernames never enter Redis or logs."""
    normalized = username.strip().casefold().encode("utf-8")
    digest = hashlib.sha256(normalized).hexdigest()
    return f"security:login-attempts:{digest}"


def _enforce_login_rate_limit(username: str) -> str:
    """Reserve one shared login attempt across every API worker.

    The limiter is account-scoped instead of proxy-IP-scoped: requests forwarded
    by the Next.js container therefore cannot lock unrelated account names, and
    adding API replicas does not reset the attempt budget. Redis outages fail
    closed because accepting unlimited administrator guesses is unsafe.
    """
    key = _login_rate_key(username)
    try:
        with _login_rate_store.pipeline(transaction=True) as pipe:
            pipe.incr(key)
            pipe.expire(key, _LOGIN_WINDOW_SECONDS)
            count, _ = pipe.execute()
    except RedisError as exc:
        logger.error("Administrator login rate limiter is unavailable.")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="سامانه کنترل امنیت ورود موقتاً در دسترس نیست؛ کمی بعد دوباره تلاش کنید.",
        ) from exc
    if int(count) > _LOGIN_ATTEMPTS_PER_WINDOW:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="تعداد تلاش‌های ورود بیش از حد مجاز است؛ پنج دقیقه دیگر تلاش کنید.",
        )
    return key


def _clear_login_rate_limit(key: str) -> None:
    try:
        _login_rate_store.delete(key)
    except RedisError:
        # Authentication already succeeded; do not turn a successful password
        # verification into an outage merely because cleanup was unavailable.
        logger.warning("Could not clear the successful login attempt counter.")


@router.post("/login", response_model=LoginResponse)
def login(req: LoginRequest, response: Response, request: Request):
    """
    Verifies username and password, issuing an HttpOnly session for the configured TTL.
    """
    # Constant-time comparison for security
    rate_key = _enforce_login_rate_limit(req.username)
    user_match = secrets.compare_digest(req.username.strip(), settings.radar_admin_user)
    pass_match = secrets.compare_digest(req.password, settings.radar_admin_password)

    if not (user_match and pass_match):
        logger.warning("Failed administrator login attempt.")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="نام کاربری یا رمز عبور اشتباه است.",
        )

    token = create_access_token(
        data={"sub": req.username, "role": "admin"},
        expires_delta=timedelta(minutes=settings.session_ttl_minutes),
    )

    # Set secure persistent HTTP-only cookie
    response.set_cookie(
        key="radar_session",
        value=token,
        max_age=settings.session_ttl_minutes * 60,
        expires=datetime.now(timezone.utc) + timedelta(minutes=settings.session_ttl_minutes),
        httponly=True,
        secure=settings.cookie_secure,
        samesite="strict",
        path="/",
    )

    _clear_login_rate_limit(rate_key)
    logger.info("Authenticated system-owner session created.")

    return LoginResponse(
        success=True,
        message="ورود موفقیت‌آمیز بود و نشست امن برقرار شد.",
        username=req.username,
        expires_in_minutes=settings.session_ttl_minutes,
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
    response.delete_cookie("radar_session", path="/", secure=settings.cookie_secure, samesite="strict")
    return {"success": True, "message": "از سامانه خارج شدید."}
