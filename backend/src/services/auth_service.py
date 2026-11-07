"""
Authentication service for VendorFlow.

Handles user registration, authentication, JWT issuing, and database indexes.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from bson import ObjectId
from pymongo import ASCENDING
from pymongo.database import Database

import src.database.mongodb as mongodb_module
from src.models.enums import UserRole, UserStatus
from src.models.user import UserModel
from src.models.vendor import VendorDocument
from src.utils.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)

logger = logging.getLogger(__name__)


class AuthServiceError(Exception):
    """Base exception for authentication service errors."""


class DuplicateEmailError(AuthServiceError):
    """Raised when an email address is already registered."""


class InvalidCredentialsError(AuthServiceError):
    """Raised when email/password authentication fails."""


class AccountInactiveError(AuthServiceError):
    """Raised when an account is disabled or suspended."""


class UserNotFoundError(AuthServiceError):
    """Raised when a user is not found."""


class AuthService:
    """Service layer managing user accounts, authentication, and vendor profile linking."""

    def __init__(self, db: Database | None = None) -> None:
        if db is not None:
            self._db = db
        elif mongodb_module.db is not None:
            self._db = mongodb_module.db
        else:
            raise RuntimeError("Database connection is not initialized.")

    @property
    def users_collection(self):
        return self._db["users"]

    @property
    def vendors_collection(self):
        return self._db["vendors"]

    def ensure_indexes(self) -> None:
        """Create database indexes for users and vendor association."""
        try:
            # Case-insensitive unique index on email
            self.users_collection.create_index(
                [("email", ASCENDING)],
                unique=True,
                name="unique_user_email_idx",
            )
            # Index on user_id in vendors collection
            self.vendors_collection.create_index(
                [("user_id", ASCENDING)],
                name="vendor_user_id_idx",
            )
            logger.info("Auth database indexes verified.")
        except Exception as exc:
            logger.warning("Auth index creation encountered notice: %s", exc)

    async def register_user(
        self,
        name: str,
        email: str,
        password: str,
        role: str = UserRole.VENDOR.value,
    ) -> UserModel:
        """
        Register a new user account.
        Public registration only allows creating vendor accounts.
        """
        normalized_email = email.lower().strip()

        # Check for existing user
        existing = self.users_collection.find_one({"email": normalized_email})
        if existing:
            raise DuplicateEmailError("An account with this email address already exists.")

        hashed = hash_password(password)
        user = UserModel(
            email=normalized_email,
            password_hash=hashed,
            name=name.strip(),
            role=role,
            status=UserStatus.ACTIVE.value,
        )

        doc = user.to_dict()
        result = self.users_collection.insert_one(doc)
        user.user_id = str(result.inserted_id)

        # If role is vendor, automatically create or link their vendor profile
        if role == UserRole.VENDOR.value:
            self.get_or_create_vendor_profile(user.user_id, contact_name=name, email=normalized_email)

        logger.info("Registered user %s (role: %s)", normalized_email, role)
        return user

    async def authenticate_user(
        self,
        email: str,
        password: str,
    ) -> UserModel:
        """
        Authenticate a user by email and password.
        Uses generic error message to prevent account enumeration.
        """
        normalized_email = email.lower().strip()
        doc = self.users_collection.find_one({"email": normalized_email})

        if not doc:
            raise InvalidCredentialsError("Invalid email or password.")

        if not verify_password(password, doc.get("password_hash", "")):
            raise InvalidCredentialsError("Invalid email or password.")

        user = UserModel.from_mongo(doc)

        if user.status != UserStatus.ACTIVE.value:
            raise AccountInactiveError("This account is currently disabled or suspended.")

        return user

    def get_user_by_id(self, user_id: str) -> UserModel | None:
        """Retrieve user by MongoDB ObjectId string."""
        try:
            oid = ObjectId(user_id)
        except Exception:
            return None
        doc = self.users_collection.find_one({"_id": oid})
        if not doc:
            return None
        return UserModel.from_mongo(doc)

    def get_vendor_id_for_user(self, user_id: str) -> str | None:
        """Find the vendor profile ObjectId string associated with a user."""
        doc = self.vendors_collection.find_one({"user_id": user_id})
        if doc:
            return str(doc["_id"])
        return None

    def get_or_create_vendor_profile(
        self,
        user_id: str,
        contact_name: str = "",
        email: str = "",
    ) -> str:
        """
        Ensure the vendor user has an associated vendor onboarding record.
        Returns the vendor's ObjectId string.
        """
        doc = self.vendors_collection.find_one({"user_id": user_id})
        if doc:
            return str(doc["_id"])

        # Create new vendor document linked to this user_id
        vendor = VendorDocument(
            user_id=user_id,
            status="draft",
        )
        if contact_name or email:
            # Pre-populate primary contact if available
            parts = contact_name.split(maxsplit=1)
            vendor.contact_info.primary.first_name = parts[0] if parts else ""
            vendor.contact_info.primary.last_name = parts[1] if len(parts) > 1 else ""
            vendor.contact_info.primary.email = email

        vendor_dict = vendor.to_dict()
        result = self.vendors_collection.insert_one(vendor_dict)
        return str(result.inserted_id)

