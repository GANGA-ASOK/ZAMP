"""
FastAPI authentication and role-based access control (RBAC) dependencies.
"""

from __future__ import annotations

import logging
from typing import Annotated

import jwt
from bson import ObjectId
from fastapi import Cookie, Depends, Header, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from src.models.enums import UserRole, UserStatus
from src.models.user import UserModel
from src.services.auth_service import AuthService
from src.utils.security import decode_token

logger = logging.getLogger(__name__)

# HTTPBearer security scheme (auto_error=False so we can fall back to cookies)
bearer_scheme = HTTPBearer(auto_error=False)


def get_auth_service() -> AuthService:
    """Dependency returning an AuthService instance."""
    return AuthService()


AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]


async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    auth_service: AuthService = Depends(get_auth_service),
) -> UserModel:
    """
    Extract, decode, and validate JWT access token from:
    1. HTTP Authorization Bearer header
    2. HttpOnly 'access_token' cookie

    Returns the authenticated UserModel or raises HTTP 401.
    """
    token: str | None = None

    if credentials and credentials.credentials:
        token = credentials.credentials
    elif "access_token" in request.cookies:
        token = request.cookies.get("access_token")

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Please log in.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        payload = decode_token(token, expected_type="access")
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired. Please log in again.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.PyJWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid authentication token: {exc}",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Malformed token claims.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = auth_service.get_user_by_id(user_id)
    if not user or user.status != UserStatus.ACTIVE.value:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account not found or deactivated.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


CurrentUserDep = Annotated[UserModel, Depends(get_current_user)]


async def get_current_user_optional(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    auth_service: AuthService = Depends(get_auth_service),
) -> UserModel | None:
    """
    Optional authentication: returns UserModel if valid token provided, else None.
    Does not raise 401 if unauthenticated.
    """
    token: str | None = None
    if credentials and credentials.credentials:
        token = credentials.credentials
    elif "access_token" in request.cookies:
        token = request.cookies.get("access_token")

    if not token:
        return None

    try:
        payload = decode_token(token, expected_type="access")
        user_id = payload.get("sub")
        if not user_id:
            return None
        user = auth_service.get_user_by_id(user_id)
        if user and user.status == UserStatus.ACTIVE.value:
            return user
    except Exception:
        return None
    return None


async def require_vendor(
    current_user: UserModel = Depends(get_current_user),
) -> UserModel:
    """Enforces that the authenticated user possesses the 'vendor' role."""
    if current_user.role != UserRole.VENDOR.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Vendor access required. Administrators cannot perform vendor onboarding actions.",
        )
    return current_user


VendorUserDep = Annotated[UserModel, Depends(require_vendor)]


async def require_admin(
    current_user: UserModel | None = Depends(get_current_user_optional),
) -> UserModel:
    """Enforces admin role when authenticated, but allows prototype access when unauthenticated."""
    if current_user and current_user.role != UserRole.ADMIN.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access forbidden: Administrator privilege required.",
        )
    return current_user or UserModel(
        email="prototype.admin@vendorflow.io",
        password_hash="",
        name="Prototype Admin",
        role=UserRole.ADMIN.value,
        user_id="prototype_admin",
    )


AdminUserDep = Annotated[UserModel, Depends(require_admin)]


async def verify_vendor_ownership(
    vendor_id: str,
    current_user: UserModel | None = Depends(get_current_user_optional),
    auth_service: AuthService = Depends(get_auth_service),
) -> UserModel | None:
    """
    Checks if current_user is authorized to access the given vendor_id:
    - Admins can access all vendors.
    - If unauthenticated, access is permitted for this prototype.
    - If authenticated as vendor, enforces ownership.
    """
    if current_user is None or current_user.role == UserRole.ADMIN.value:
        return current_user

    # Vendor check
    try:
        oid = ObjectId(vendor_id)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid vendor identifier: '{vendor_id}'.",
        )

    doc = auth_service.vendors_collection.find_one({"_id": oid})
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Vendor with id '{vendor_id}' was not found.",
        )

    vendor_user_id = doc.get("user_id")
    if vendor_user_id and vendor_user_id != current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: You do not have permission to view or modify this vendor profile.",
        )

    if not vendor_user_id:
        auth_service.vendors_collection.update_one(
            {"_id": oid},
            {"$set": {"user_id": current_user.user_id}},
        )

    return current_user

