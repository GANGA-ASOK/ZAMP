"""
User MongoDB document model.

Stores credentials and roles for authenticated vendors and administrators
in the ``users`` collection of the database.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class UserModel:
    """
    MongoDB document model for users.

    Stored in the ``users`` collection.
    Email is unique-indexed at the database level.
    Password hash is stored using Argon2id.
    """
    email: str
    password_hash: str
    name: str
    role: str = "vendor"        # UserRole: "vendor" | "admin"
    status: str = "active"      # UserStatus: "active" | "inactive" | "suspended"
    created_at: datetime = field(default_factory=_utcnow)
    updated_at: datetime = field(default_factory=_utcnow)
    user_id: str = ""           # Populated from MongoDB _id

    def to_dict(self) -> dict[str, Any]:
        return {
            "email": self.email.lower().strip(),
            "password_hash": self.password_hash,
            "name": self.name.strip(),
            "role": self.role,
            "status": self.status,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_mongo(cls, doc: dict[str, Any]) -> UserModel:
        """Construct a UserModel from a MongoDB document dict."""
        return cls(
            user_id=str(doc.get("_id", "")),
            email=doc.get("email", ""),
            password_hash=doc.get("password_hash", ""),
            name=doc.get("name", ""),
            role=doc.get("role", "vendor"),
            status=doc.get("status", "active"),
            created_at=doc.get("created_at") or _utcnow(),
            updated_at=doc.get("updated_at") or _utcnow(),
        )

