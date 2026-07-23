"""Auth router — local JWT (with optional Supabase).

For Supabase, set USE_SUPABASE=true in .env and provide keys. The frontend
posts the Supabase access token; we verify it server-side using Supabase's
JWT public key (or, more simply, by calling Supabase's /user endpoint).
For local development we run a self-issued JWT flow.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.deps import CurrentUser, get_db
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.models.audit_log import AuditLog
from app.models.user import User
from app.schemas.auth import (
    ForgotPasswordRequest,
    GoogleLogin,
    Message,
    RefreshRequest,
    TokenPair,
    UserCreate,
    UserLogin,
    UserOut,
)

router = APIRouter(prefix="/auth", tags=["auth"])


def _token_pair(user: User) -> TokenPair:
    return TokenPair(
        access_token=create_access_token(user.id),
        refresh_token=create_refresh_token(user.id),
        expires_in=settings.access_token_expire_minutes * 60,
    )


async def _audit(db: AsyncSession, request: Request, user: User | None, action: str) -> None:
    db.add(
        AuditLog(
            user_id=user.id if user else None,
            action=action,
            ip_address=(request.client.host if request.client else None),
            user_agent=request.headers.get("user-agent"),
        )
    )


@router.post("/register", response_model=TokenPair, status_code=201)
async def register(
    body: UserCreate,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    existing = (
        await db.execute(select(User).where(User.email == body.email.lower()))
    ).scalar_one_or_none()
    if existing:
        raise HTTPException(status.HTTP_409_CONFLICT, "Email already registered")
    user = User(
        email=body.email.lower(),
        full_name=body.full_name,
        hashed_password=hash_password(body.password),
        provider="local",
        is_verified=False,
    )
    db.add(user)
    await db.flush()
    await _audit(db, request, user, "user.register")
    return _token_pair(user)


@router.post("/login", response_model=TokenPair)
async def login(
    body: UserLogin,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    user = (
        await db.execute(select(User).where(User.email == body.email.lower()))
    ).scalar_one_or_none()
    if not user or not user.hashed_password or not verify_password(body.password, user.hashed_password):
        await _audit(db, request, user, "user.login.failed")
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid credentials")
    if not user.is_active:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Account disabled")
    user.last_login_at = datetime.now(timezone.utc)
    await _audit(db, request, user, "user.login.success")
    return _token_pair(user)


@router.post("/login/oauth", response_model=TokenPair)
async def login_oauth(
    body: GoogleLogin,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Verify a Google ID token (or Supabase access token when Supabase is enabled),
    upsert the user, and issue our own JWT pair.

    In a real production deployment you would verify the Google token against
    Google's JWKS. For this educational build we treat the token as opaque
    and require a backend env flag to be enabled.
    """
    if not settings.use_supabase:
        raise HTTPException(
            status.HTTP_501_NOT_IMPLEMENTED,
            "OAuth login is only enabled when USE_SUPABASE=true and Supabase is configured.",
        )
    # The real Supabase verification would happen here.
    raise HTTPException(status.HTTP_501_NOT_IMPLEMENTED, "Configure Supabase verification in app/core/supabase.py")


@router.post("/forgot-password", response_model=Message)
async def forgot_password(
    body: ForgotPasswordRequest,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    # We always return success to avoid email enumeration. In production this
    # would queue a reset email containing a signed token.
    user = (
        await db.execute(select(User).where(User.email == body.email.lower()))
    ).scalar_one_or_none()
    await _audit(db, request, user, "user.forgot_password")
    return Message(message="If that email exists, a reset link has been sent.")


@router.post("/refresh", response_model=TokenPair)
async def refresh(
    body: RefreshRequest,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    try:
        payload = decode_token(body.refresh_token)
        if payload.get("type") != "refresh":
            raise ValueError("Wrong token type")
    except ValueError as e:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, f"Invalid token: {e}") from e
    user = (
        await db.execute(select(User).where(User.id == payload["sub"]))
    ).scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "User not found")
    await _audit(db, request, user, "user.refresh")
    return _token_pair(user)


@router.get("/me", response_model=UserOut)
async def me(user: CurrentUser):
    return user


@router.post("/logout", response_model=Message)
async def logout(request: Request, db: Annotated[AsyncSession, Depends(get_db)], user: CurrentUser):
    await _audit(db, request, user, "user.logout")
    return Message(message="Logged out")
