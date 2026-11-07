"""
Pydantic schemas for Phase 9: Workflow, Clarifications, History, Comments, and Notifications.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Status & Approval / Rejection Payloads
# ---------------------------------------------------------------------------

class StatusUpdatePayload(BaseModel):
    """Payload for updating an application's lifecycle status."""
    status: str = Field(..., description="Target status (e.g., 'under_review', 'approved', 'rejected')")
    notes: str | None = Field(default=None, description="Optional transition note or rationale")


class ApprovePayload(BaseModel):
    """Payload for approving a vendor application."""
    comment: str | None = Field(default=None, description="Optional approval remark or note")


class RejectPayload(BaseModel):
    """Payload for rejecting a vendor application."""
    rejection_reason: str = Field(..., min_length=3, description="Mandatory detailed rejection reason")


# ---------------------------------------------------------------------------
# Clarification Schemas
# ---------------------------------------------------------------------------

class ClarificationCreatePayload(BaseModel):
    """Admin payload to request clarification from a vendor."""
    clarification_message: str = Field(..., min_length=5, description="Clear explanation of required correction")
    related_document_id: str | None = Field(default=None, description="Document ID requiring correction if applicable")
    related_document_name: str | None = Field(default=None, description="Document name or category")
    related_field: str | None = Field(default=None, description="Specific field name requiring clarification if applicable")
    admin_notes: str | None = Field(default=None, description="Optional internal comment")


class ClarificationRespondPayload(BaseModel):
    """Vendor response to a clarification request."""
    vendor_response: str = Field(..., min_length=2, description="Vendor explanation or note on corrections made")
    replaced_document_id: str | None = Field(default=None, description="ID of newly uploaded replacement document if applicable")
    updated_fields: dict[str, Any] | None = Field(default=None, description="Dictionary of corrected field values")


class ClarificationItemResponse(BaseModel):
    """Detailed clarification request view."""
    id: str
    application_id: str
    vendor_id: str
    clarification_message: str
    related_document_id: str | None = None
    related_document_name: str | None = None
    related_field: str | None = None
    admin_notes: str | None = None
    vendor_response: str | None = None
    replaced_document_id: str | None = None
    status: str
    created_at: datetime
    resolved_at: datetime | None = None


# ---------------------------------------------------------------------------
# Resubmission Payload
# ---------------------------------------------------------------------------

class VendorResubmitPayload(BaseModel):
    """Payload for vendor resubmitting application after corrections."""
    resubmission_notes: str | None = Field(default=None, description="Summary notes of changes made")


# ---------------------------------------------------------------------------
# Notification Schemas
# ---------------------------------------------------------------------------

class NotificationResponse(BaseModel):
    """Individual notification representation."""
    id: str
    recipient_type: str
    title: str
    message: str
    notification_type: str
    vendor_id: str | None = None
    application_id: str | None = None
    is_read: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime


class NotificationListResponse(BaseModel):
    """Notification feed with unread count."""
    items: list[NotificationResponse]
    unread_count: int
    total_count: int


# ---------------------------------------------------------------------------
# Admin Comment Schemas
# ---------------------------------------------------------------------------

class AdminCommentCreatePayload(BaseModel):
    """Payload for creating an internal admin review note."""
    comment: str = Field(..., min_length=2, description="Internal review note text")
    visibility_type: str = Field(default="internal", description="Visibility level")


class AdminCommentResponse(BaseModel):
    """Internal admin comment record."""
    id: str
    application_id: str
    vendor_id: str
    comment: str
    visibility_type: str
    author_name: str
    created_at: datetime


# ---------------------------------------------------------------------------
# Activity History Timeline Schemas
# ---------------------------------------------------------------------------

class ActivityEventResponse(BaseModel):
    """Single chronological milestone event in application lifecycle."""
    id: str
    application_id: str
    vendor_id: str
    event_type: str
    description: str
    actor_type: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime


# ---------------------------------------------------------------------------
# Application Management Table Listing
# ---------------------------------------------------------------------------

class ApplicationListItem(BaseModel):
    """Application row for admin management table."""
    id: str
    vendor_id: str
    reference_number: str
    company_name: str
    vendor_name: str
    email: str
    status: str
    submission_date: datetime | None = None
    last_updated_date: datetime | None = None
    document_count: int = 0
    ai_verification_status: str = "pending"  # pending | completed | flagged | needs_manual_review
    pending_clarifications_count: int = 0
    ai_decision: dict[str, Any] | None = None  # latest AI Decision Engine outcome summary


class ApplicationPaginationResponse(BaseModel):
    """Paginated application management results."""
    items: list[ApplicationListItem]
    total: int
    page: int
    limit: int
    pages: int
    status_counts: dict[str, int]

