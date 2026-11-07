"""
MongoDB document models for Phase 9: Workflow, Clarifications, History, Comments, and Notifications.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class ApplicationHistoryModel:
    """Records an immutable milestone or transition event in the application lifecycle."""
    application_id: str
    vendor_id: str
    event_type: str
    description: str
    actor_type: str = "system"
    metadata: dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=_utcnow)

    def to_dict(self) -> dict[str, Any]:
        return {
            "application_id": self.application_id,
            "vendor_id": self.vendor_id,
            "event_type": self.event_type,
            "description": self.description,
            "actor_type": self.actor_type,
            "metadata": self.metadata,
            "timestamp": self.timestamp,
        }


@dataclass
class ClarificationRequestModel:
    """Represents a clarification or correction request made by an admin to a vendor."""
    application_id: str
    vendor_id: str
    clarification_message: str
    related_document_id: str | None = None
    related_document_name: str | None = None
    related_field: str | None = None
    admin_notes: str | None = None
    vendor_response: str | None = None
    replaced_document_id: str | None = None
    status: str = "pending"  # pending | resolved
    created_at: datetime = field(default_factory=_utcnow)
    resolved_at: datetime | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "application_id": self.application_id,
            "vendor_id": self.vendor_id,
            "clarification_message": self.clarification_message,
            "related_document_id": self.related_document_id,
            "related_document_name": self.related_document_name,
            "related_field": self.related_field,
            "admin_notes": self.admin_notes,
            "vendor_response": self.vendor_response,
            "replaced_document_id": self.replaced_document_id,
            "status": self.status,
            "created_at": self.created_at,
            "resolved_at": self.resolved_at,
        }


@dataclass
class NotificationModel:
    """In-app notification for vendors or administrators."""
    recipient_type: str  # 'admin' or 'vendor'
    title: str
    message: str
    notification_type: str = "info"  # info, status_change, clarification, approval, rejection, resubmission
    vendor_id: str | None = None
    application_id: str | None = None
    is_read: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=_utcnow)

    def to_dict(self) -> dict[str, Any]:
        return {
            "recipient_type": self.recipient_type,
            "title": self.title,
            "message": self.message,
            "notification_type": self.notification_type,
            "vendor_id": self.vendor_id,
            "application_id": self.application_id,
            "is_read": self.is_read,
            "metadata": self.metadata,
            "created_at": self.created_at,
        }


@dataclass
class AdminCommentModel:
    """Internal administrator review comment kept separate from vendor-facing clarification messages."""
    application_id: str
    vendor_id: str
    comment: str
    visibility_type: str = "internal"
    author_name: str = "Admin"
    created_at: datetime = field(default_factory=_utcnow)

    def to_dict(self) -> dict[str, Any]:
        return {
            "application_id": self.application_id,
            "vendor_id": self.vendor_id,
            "comment": self.comment,
            "visibility_type": self.visibility_type,
            "author_name": self.author_name,
            "created_at": self.created_at,
        }

