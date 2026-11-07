"""
Authentication API routes for VendorFlow.

Endpoints:
    POST /api/auth/register — Public vendor registration
    POST /api/auth/login    — Email & password authentication
    POST /api/auth/refresh  — JWT token refresh & rotation
    POST /api/auth/logout   — Clear authentication cookies
    GET  /api/auth/me       — Retrieve current authenticated user profile
"""

from __future__ import annotations

import logging
from typing import Annotated

import jwt
from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response, status

from src.dependencies.auth import (
    AuthServiceDep,
    CurrentUserDep,
    get_auth_service,
    get_current_user,
)
from src.models.enums import UserRole
from src.schemas.auth import (
    RefreshTokenRequest,
    TokenResponse,
    UserLoginRequest,
    UserRegisterRequest,
    UserResponse,
)
from src.services.auth_service import (
    AccountInactiveError,
    DuplicateEmailError,
    InvalidCredentialsError,
)
from src.utils.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication"])

# Cookie settings for local development and production
COOKIE_SECURE = False  # Set to True when HTTPS is enabled
COOKIE_SAMESITE = "lax"


def _set_auth_cookies(
    response: Response,
    access_token: str,
    refresh_token: str,
) -> None:
    """Set secure HttpOnly cookies for access and refresh tokens."""
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=COOKIE_SECURE,
        samesite=COOKIE_SAMESITE,
        max_age=3600,  # 1 hour
        path="/",
    )
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=COOKIE_SECURE,
        samesite=COOKIE_SAMESITE,
        max_age=7 * 24 * 3600,  # 7 days
        path="/",
    )


def _clear_auth_cookies(response: Response) -> None:
    """Clear authentication cookies."""
    response.delete_cookie(key="access_token", path="/")
    response.delete_cookie(key="refresh_token", path="/")


@router.post(
    "/register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new vendor account",
)
async def register_vendor(
    payload: UserRegisterRequest,
    response: Response,
    service: AuthServiceDep,
) -> TokenResponse:
    """
    Register a new vendor account.
    Automatically assigns the 'vendor' role and creates an associated onboarding profile.
    """
    try:
        user = await service.register_user(
            name=payload.name,
            email=payload.email,
            password=payload.password,
            role=UserRole.VENDOR.value,
        )
    except DuplicateEmailError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        )

    access_token = create_access_token(user.user_id, user.email, user.role)
    refresh_token = create_refresh_token(user.user_id, user.email, user.role)

    _set_auth_cookies(response, access_token, refresh_token)

    vendor_id = service.get_vendor_id_for_user(user.user_id)

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=3600,
        user=UserResponse(
            id=user.user_id,
            name=user.name,
            email=user.email,
            role=user.role,
            status=user.status,
            created_at=user.created_at,
        ),
        vendor_id=vendor_id,
    )


@router.post(
    "/login",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Authenticate vendor or administrator",
)
async def login(
    payload: UserLoginRequest,
    response: Response,
    service: AuthServiceDep,
) -> TokenResponse:
    """
    Authenticate with email and password.
    Returns access token, user info, and sets HttpOnly cookies.
    """
    try:
        user = await service.authenticate_user(
            email=payload.email,
            password=payload.password,
        )
    except InvalidCredentialsError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
            headers={"WWW-Authenticate": "Bearer"},
        )
    except AccountInactiveError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        )

    access_token = create_access_token(user.user_id, user.email, user.role)
    refresh_token = create_refresh_token(user.user_id, user.email, user.role)

    _set_auth_cookies(response, access_token, refresh_token)

    vendor_id = None
    if user.role == UserRole.VENDOR.value:
        vendor_id = service.get_or_create_vendor_profile(
            user.user_id,
            contact_name=user.name,
            email=user.email,
        )

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=3600,
        user=UserResponse(
            id=user.user_id,
            name=user.name,
            email=user.email,
            role=user.role,
            status=user.status,
            created_at=user.created_at,
        ),
        vendor_id=vendor_id,
    )


@router.post(
    "/refresh",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Refresh access token",
)
async def refresh_token(
    request: Request,
    response: Response,
    service: AuthServiceDep,
    payload: RefreshTokenRequest | None = None,
) -> TokenResponse:
    """
    Rotate tokens using a valid refresh token from request body or HttpOnly cookie.
    """
    token: str | None = None
    if payload and payload.refresh_token:
        token = payload.refresh_token
    elif "refresh_token" in request.cookies:
        token = request.cookies.get("refresh_token")

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token required.",
        )

    try:
        decoded = decode_token(token, expected_type="refresh")
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token expired. Please log in again.",
        )
    except jwt.PyJWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid refresh token: {exc}",
        )

    user_id = decoded.get("sub")
    user = service.get_user_by_id(user_id) if user_id else None

    if not user or user.status != "active":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account no longer active.",
        )

    new_access_token = create_access_token(user.user_id, user.email, user.role)
    new_refresh_token = create_refresh_token(user.user_id, user.email, user.role)

    _set_auth_cookies(response, new_access_token, new_refresh_token)

    vendor_id = service.get_vendor_id_for_user(user.user_id) if user.role == UserRole.VENDOR.value else None

    return TokenResponse(
        access_token=new_access_token,
        token_type="bearer",
        expires_in=3600,
        user=UserResponse(
            id=user.user_id,
            name=user.name,
            email=user.email,
            role=user.role,
            status=user.status,
            created_at=user.created_at,
        ),
        vendor_id=vendor_id,
    )


@router.post(
    "/logout",
    status_code=status.HTTP_200_OK,
    summary="Log out and clear session cookies",
)
async def logout(response: Response) -> dict[str, str]:
    """Clear authentication cookies."""
    _clear_auth_cookies(response)
    return {"message": "Successfully logged out."}


@router.get(
    "/me",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="Get current user details",
)
async def get_me(
    current_user: CurrentUserDep,
) -> UserResponse:
    """Return the profile of the currently authenticated user."""
    return UserResponse(
        id=current_user.user_id,
        name=current_user.name,
        email=current_user.email,
        role=current_user.role,
        status=current_user.status,
        created_at=current_user.created_at,
    )

