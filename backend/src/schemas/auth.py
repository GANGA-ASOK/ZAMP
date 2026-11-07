"""
Authentication Pydantic schemas.
"""

from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserRegisterRequest(BaseModel):
    """Payload for vendor account registration."""
    name: str = Field(..., min_length=2, max_length=100, description="Full name or representative name")
    email: EmailStr = Field(..., description="Unique email address")
    password: str = Field(..., min_length=8, max_length=128, description="Account password (at least 8 chars)")

    model_config = ConfigDict(str_strip_whitespace=True)


class UserLoginRequest(BaseModel):
    """Payload for user login."""
    email: EmailStr = Field(..., description="Account email address")
    password: str = Field(..., min_length=1, max_length=128, description="Account password")

    model_config = ConfigDict(str_strip_whitespace=True)


class RefreshTokenRequest(BaseModel):
    """Payload for refreshing an access token."""
    refresh_token: str | None = Field(default=None, description="JWT refresh token (can also be provided via cookie)")


class UserResponse(BaseModel):
    """User profile response (safe: no password hashes or internal secrets)."""
    id: str = Field(..., description="User unique identifier (hex string)")
    name: str = Field(...)
    email: str = Field(...)
    role: str = Field(..., description="Role: 'vendor' or 'admin'")
    status: str = Field(..., description="Account status: 'active', etc.")
    created_at: datetime = Field(...)

    model_config = ConfigDict(from_attributes=True)


class TokenResponse(BaseModel):
    """Token response on successful login or registration."""
    access_token: str
    token_type: str = "bearer"
    expires_in: int = Field(..., description="Access token expiry in seconds")
    user: UserResponse
    vendor_id: str | None = Field(default=None, description="Associated vendor profile ID if role is vendor")

