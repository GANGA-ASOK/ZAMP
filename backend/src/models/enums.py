"""
Enumerations shared across VendorFlow models and schemas.

These are the canonical source-of-truth for all string-typed enumerated fields
stored in MongoDB and exchanged over the API.
"""

from enum import Enum


# ---------------------------------------------------------------------------
# Vendor onboarding lifecycle
# ---------------------------------------------------------------------------

class VendorStatus(str, Enum):
    """
    Tracks the lifecycle of a vendor's onboarding application.

    Transitions (happy path):
        draft → submitted → under_review → approved

    Unhappy paths:
        any      → rejected
        any      → clarification_required → submitted (re-submission)
    """

    DRAFT = "draft"
    """Vendor has started the form but not yet submitted it."""

    SUBMITTED = "submitted"
    """Vendor has completed and submitted the form; awaiting admin review."""

    UNDER_REVIEW = "under_review"
    """An admin is actively reviewing the application."""

    CLARIFICATION_REQUIRED = "clarification_required"
    """Admin has requested additional information or document corrections."""

    RESUBMITTED = "resubmitted"
    """Vendor has submitted the requested corrections."""

    APPROVED = "approved"
    """The vendor has been verified and approved."""

    REJECTED = "rejected"
    """The application has been permanently rejected."""


# ---------------------------------------------------------------------------
# Document categories
# ---------------------------------------------------------------------------

class DocumentCategory(str, Enum):
    """
    Canonical document types that a vendor may upload.

    Maps 1-to-1 with the ``DocumentKey`` type in the frontend
    ``src/types/vendor.ts``.
    """

    CERTIFICATE_OF_INCORPORATION = "certificate_of_incorporation"
    """Certificate of Incorporation (CoI) — required for corporate entities."""

    PAN_CARD = "pan_card"
    """PAN Card or PAN Certificate — mandatory for all vendors."""

    GST_CERTIFICATE = "gst_certificate"
    """GST Registration Certificate — required when vendor is GST-registered."""

    BANK_PROOF = "bank_proof"
    """Cancelled cheque, bank statement, or letter — mandatory for all vendors."""

    TAN_CERTIFICATE = "tan_certificate"
    """TAN Certificate — optional; required only when TAN is provided."""

    MSME_CERTIFICATE = "msme_certificate"
    """MSME / Udyam Registration Certificate — optional."""

    OTHER = "other"
    """Any additional supporting documents uploaded by the vendor."""


# ---------------------------------------------------------------------------
# Document-level verification status
# ---------------------------------------------------------------------------

class DocumentVerificationStatus(str, Enum):
    """
    Tracks the verification state of an individual uploaded document.

    Transitions:
        pending → uploaded → verified
                          → rejected (re-upload required)
    """

    PENDING = "pending"
    """Document slot exists but no file has been uploaded yet."""

    UPLOADED = "uploaded"
    """File has been uploaded and is awaiting admin or AI review."""

    VERIFIED = "verified"
    """Document has been reviewed and accepted."""

    REJECTED = "rejected"
    """Document was reviewed and found to be invalid or insufficient."""


# ---------------------------------------------------------------------------
# Reference data enums (mirrors frontend validation.ts constants)
# ---------------------------------------------------------------------------

class BusinessEntityType(str, Enum):
    PRIVATE_LIMITED = "Private Limited Company"
    PUBLIC_LIMITED = "Public Limited Company"
    LLP = "Limited Liability Partnership (LLP)"
    PARTNERSHIP = "Partnership"
    SOLE_PROPRIETORSHIP = "Sole Proprietorship"
    OPC = "One Person Company (OPC)"
    OTHER = "Other"


class GSTStatus(str, Enum):
    REGISTERED = "Registered"
    NOT_REGISTERED = "Not Registered"
    EXEMPT = "Exempt"


class AccountType(str, Enum):
    CURRENT = "Current Account"
    SAVINGS = "Savings Account"
    OTHER = "Other"


# ---------------------------------------------------------------------------
# User authentication & RBAC roles
# ---------------------------------------------------------------------------

class UserRole(str, Enum):
    VENDOR = "vendor"
    ADMIN = "admin"


class UserStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"


# ---------------------------------------------------------------------------
# Phase 9: Approval Workflow, Clarifications, Notifications & Activity
# ---------------------------------------------------------------------------

class ClarificationStatus(str, Enum):
    PENDING = "pending"
    RESOLVED = "resolved"


class ActorType(str, Enum):
    VENDOR = "vendor"
    ADMIN = "admin"
    SYSTEM = "system"


class NotificationRecipientType(str, Enum):
    VENDOR = "vendor"
    ADMIN = "admin"


class NotificationType(str, Enum):
    INFO = "info"
    STATUS_CHANGE = "status_change"
    CLARIFICATION = "clarification"
    APPROVAL = "approval"
    REJECTION = "rejection"
    RESUBMISSION = "resubmission"


class ActivityEventType(str, Enum):
    CREATED = "created"
    SUBMITTED = "submitted"
    UNDER_REVIEW = "under_review"
    CLARIFICATION_REQUESTED = "clarification_requested"
    CLARIFICATION_RESPONDED = "clarification_responded"
    RESUBMITTED = "resubmitted"
    APPROVED = "approved"
    REJECTED = "rejected"
    DOCUMENT_UPLOADED = "document_uploaded"
    DOCUMENT_REPLACED = "document_replaced"
    COMMENT_ADDED = "comment_added"
    AI_VERIFICATION = "ai_verification"



