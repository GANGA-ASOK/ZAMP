"""
Vendor MongoDB document model.

This module describes the shape of a vendor document as stored in the
``vendors`` collection of the ``zamp`` database.  It is intentionally kept
separate from the Pydantic request/response schemas (``src/schemas/``) so
that internal storage concerns never leak into the public API surface.

Security notes
--------------
* ``tax_details`` and ``banking_details`` are sub-documents that contain
  Personally Identifiable Information (PII) and financial data.
* Before production:
    - Apply MongoDB field-level encryption (Queryable Encryption or CSFLE)
    - Or implement application-level AES-256 encryption on ``account_number``
      and ``pan_number`` before inserting, decrypting only when needed.
    - Restrict read access to these sub-documents via MongoDB Role-Based
      Access Control (RBAC).
    - Audit all reads/writes to sensitive fields.
* ``confirm_account_number`` must NEVER be persisted to the database; it is
  only validated on the request side and then discarded.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


# ---------------------------------------------------------------------------
# Helper — UTC now
# ---------------------------------------------------------------------------

def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# Sub-document plain-dataclass models
# ---------------------------------------------------------------------------
# We use plain dataclasses (not Pydantic) for the MongoDB layer because
# PyMongo works with plain dicts.  The Pydantic schemas in src/schemas/ handle
# validation and serialisation at the API boundary.

@dataclass
class AddressModel:
    """Reusable address sub-document."""
    street: str = ""
    city: str = ""
    state: str = ""
    pincode: str = ""
    country: str = "India"

    def to_dict(self) -> dict[str, Any]:
        return {
            "street": self.street,
            "city": self.city,
            "state": self.state,
            "pincode": self.pincode,
            "country": self.country,
        }


@dataclass
class CompanyInfoModel:
    """Mirrors ``CompanyInformationData`` in frontend vendor.ts (Step 1)."""
    legal_company_name: str = ""
    trade_name: str = ""
    business_entity_type: str = ""
    country: str = ""
    registration_number: str = ""
    incorporation_date: str = ""          # ISO 8601 date string (YYYY-MM-DD)
    industry: str = ""
    website: str = ""
    registered_address: AddressModel = field(default_factory=AddressModel)
    # When True the operational address mirrors the registered address.
    is_operational_same_as_registered: bool = True
    operational_address: AddressModel = field(default_factory=AddressModel)

    def to_dict(self) -> dict[str, Any]:
        return {
            "legal_company_name": self.legal_company_name,
            "trade_name": self.trade_name,
            "business_entity_type": self.business_entity_type,
            "country": self.country,
            "registration_number": self.registration_number,
            "incorporation_date": self.incorporation_date,
            "industry": self.industry,
            "website": self.website,
            "registered_address": self.registered_address.to_dict(),
            "is_operational_same_as_registered": self.is_operational_same_as_registered,
            "operational_address": self.operational_address.to_dict(),
        }


@dataclass
class ContactPersonModel:
    """A single named contact (primary, secondary, or signatory)."""
    first_name: str = ""
    last_name: str = ""
    full_name: str = ""          # Used for signatory (single name field)
    designation: str = ""
    email: str = ""
    phone: str = ""
    department: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "first_name": self.first_name,
            "last_name": self.last_name,
            "full_name": self.full_name,
            "designation": self.designation,
            "email": self.email,
            "phone": self.phone,
            "department": self.department,
        }


@dataclass
class ContactInfoModel:
    """Mirrors ``ContactInformationData`` in frontend vendor.ts (Step 2)."""
    primary: ContactPersonModel = field(default_factory=ContactPersonModel)
    secondary: ContactPersonModel = field(default_factory=ContactPersonModel)
    signatory: ContactPersonModel = field(default_factory=ContactPersonModel)
    confirm_authorized: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "primary": self.primary.to_dict(),
            "secondary": self.secondary.to_dict(),
            "signatory": self.signatory.to_dict(),
            "confirm_authorized": self.confirm_authorized,
        }


@dataclass
class TaxDetailsModel:
    """
    Tax-related fields from Step 3.

    ⚠️  SENSITIVE — contains PAN, GSTIN, TAN.
    Before production: apply field-level encryption on ``pan_number``,
    ``gstin``, and ``tan_number``.
    """
    pan_number: str = ""           # e.g. ABCDE1234F
    gst_status: str = ""           # Registered | Not Registered | Exempt
    gstin: str = ""                # e.g. 29ABCDE1234F1Z5
    gst_state: str = ""
    tan_number: str = ""           # e.g. ABCD12345E (optional)

    def to_dict(self) -> dict[str, Any]:
        return {
            "pan_number": self.pan_number,
            "gst_status": self.gst_status,
            "gstin": self.gstin,
            "gst_state": self.gst_state,
            "tan_number": self.tan_number,
        }


@dataclass
class BankingDetailsModel:
    """
    Banking fields from Step 3.

    ⚠️  SENSITIVE — contains bank account number and IFSC code.
    Before production:
        - Encrypt ``account_number`` at rest (AES-256-GCM or MongoDB CSFLE).
        - Consider storing only a masked version for display and the full
          value in an encrypted field.
        - ``confirm_account_number`` is intentionally NOT stored.
    """
    account_holder_name: str = ""
    bank_name: str = ""
    account_number: str = ""       # ⚠️ encrypt before production
    ifsc_code: str = ""
    account_type: str = ""         # Current Account | Savings Account | Other
    bank_branch: str = ""
    confirm_bank_ownership: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "account_holder_name": self.account_holder_name,
            "bank_name": self.bank_name,
            "account_number": self.account_number,
            "ifsc_code": self.ifsc_code,
            "account_type": self.account_type,
            "bank_branch": self.bank_branch,
            "confirm_bank_ownership": self.confirm_bank_ownership,
        }


@dataclass
class DocumentMetaModel:
    """
    Metadata for a single uploaded document.

    The actual file bytes are NOT stored in MongoDB; they belong in object
    storage (e.g. Google Cloud Storage, AWS S3).  Only the reference is kept.
    """
    document_id: str = ""              # UUID or storage object key
    category: str = ""                 # DocumentCategory enum value
    file_name: str = ""
    file_size: int = 0                 # bytes
    file_type: str = ""                # MIME type, e.g. application/pdf
    storage_path: str = ""             # Cloud storage URI (populated post-upload)
    verification_status: str = "pending"  # DocumentVerificationStatus enum value
    uploaded_at: str = ""              # ISO 8601 datetime string
    verified_at: str = ""              # ISO 8601 datetime string (empty until verified)
    rejection_reason: str = ""         # Populated on rejection

    def to_dict(self) -> dict[str, Any]:
        return {
            "document_id": self.document_id,
            "category": self.category,
            "file_name": self.file_name,
            "file_size": self.file_size,
            "file_type": self.file_type,
            "storage_path": self.storage_path,
            "verification_status": self.verification_status,
            "uploaded_at": self.uploaded_at,
            "verified_at": self.verified_at,
            "rejection_reason": self.rejection_reason,
        }


@dataclass
class DeclarationsModel:
    """Legal declarations confirmed by the vendor at Step 4."""
    confirm_accurate: bool = False
    authorize_verification: bool = False
    agree_terms: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "confirm_accurate": self.confirm_accurate,
            "authorize_verification": self.authorize_verification,
            "agree_terms": self.agree_terms,
        }


# ---------------------------------------------------------------------------
# Top-level vendor document model
# ---------------------------------------------------------------------------

@dataclass
class VendorDocument:
    """
    Represents a vendor document as stored in the ``vendors`` MongoDB collection.

    Design decisions
    ----------------
    * ``tax_details`` and ``banking_details`` are intentionally separate
      sub-documents so RBAC field-level restrictions can be applied to them
      independently.
    * ``documents`` is a list (not a dict) so individual documents can carry
      their own verification state and additional metadata without key collisions.
    * ``status`` defaults to ``draft`` to support partial saves before final
      submission.
    * ``reference_number`` is the human-readable identifier shown to the vendor
      after submission (format: VND-YYYY-XXXXX).
    """

    # Onboarding workflow fields
    reference_number: str = ""         # e.g. VND-2026-00001
    status: str = "draft"              # VendorStatus enum value

    # Form data sub-documents (one per step)
    company_info: CompanyInfoModel = field(default_factory=CompanyInfoModel)
    contact_info: ContactInfoModel = field(default_factory=ContactInfoModel)
    tax_details: TaxDetailsModel = field(default_factory=TaxDetailsModel)
    banking_details: BankingDetailsModel = field(default_factory=BankingDetailsModel)
    documents: list[DocumentMetaModel] = field(default_factory=list)
    declarations: DeclarationsModel = field(default_factory=DeclarationsModel)

    # Review workflow metadata (populated by admin/AI in later phases)
    review_notes: str = ""
    rejection_reason: str = ""
    clarification_requests: list[str] = field(default_factory=list)

    # Timestamps
    created_at: datetime = field(default_factory=_utcnow)
    updated_at: datetime = field(default_factory=_utcnow)
    submitted_at: datetime | None = None
    reviewed_at: datetime | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serialise to a plain dict suitable for PyMongo insert/replace."""
        return {
            "reference_number": self.reference_number,
            "status": self.status,
            "company_info": self.company_info.to_dict(),
            "contact_info": self.contact_info.to_dict(),
            "tax_details": self.tax_details.to_dict(),
            "banking_details": self.banking_details.to_dict(),
            "documents": [d.to_dict() for d in self.documents],
            "declarations": self.declarations.to_dict(),
            "review_notes": self.review_notes,
            "rejection_reason": self.rejection_reason,
            "clarification_requests": self.clarification_requests,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "submitted_at": self.submitted_at,
            "reviewed_at": self.reviewed_at,
        }

