"""
Pydantic v2 schemas for the VendorFlow API.

Schema architecture
-------------------
Request schemas  → used to validate inbound data (POST / PATCH bodies)
Response schemas → used to serialise outbound data (GET / POST responses)

Naming convention
-----------------
  <Entity>Create  — full create payload (all required fields must be present)
  <Entity>Update  — partial update payload (all fields Optional for PATCH)
  <Entity>Response — shape returned to the caller

Sensitive field handling
------------------------
* ``account_number`` is never returned in a standard VendorResponse; only a
  masked variant is included (see BankingDetailsResponse).
* ``pan_number`` is similarly masked in responses.
* These fields are stored internally using the full value (see models/vendor.py)
  but are NEVER echoed back in their entirety over the API.

Security TODOs before production
---------------------------------
1. Implement application-level encryption on ``account_number`` and
   ``pan_number`` before persist (AES-256-GCM recommended).
2. Add MongoDB Queryable Encryption or CSFLE for the ``tax_details`` and
   ``banking_details`` sub-documents.
3. Restrict the ``/vendors/{id}`` endpoint so that only admins can retrieve
   the full (unmasked) sensitive data.
4. Add rate-limiting to prevent enumeration of vendor reference numbers.
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any

from bson import ObjectId
from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    field_validator,
    model_validator,
)

from src.models.enums import (
    AccountType,
    BusinessEntityType,
    DocumentCategory,
    DocumentVerificationStatus,
    GSTStatus,
    VendorStatus,
)

# ---------------------------------------------------------------------------
# Regex patterns (mirror frontend validation.ts)
# ---------------------------------------------------------------------------

_PAN_RE = re.compile(r"^[A-Z]{5}[0-9]{4}[A-Z]{1}$")
_GSTIN_RE = re.compile(r"^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$")
_IFSC_RE = re.compile(r"^[A-Z]{4}0[A-Z0-9]{6}$")
_TAN_RE = re.compile(r"^[A-Z]{4}[0-9]{5}[A-Z]{1}$")
_PINCODE_RE = re.compile(r"^[1-9][0-9]{5}$")
_PHONE_RE = re.compile(r"^[+]?[(]?[0-9]{1,4}[)]?[-\s./0-9]{8,14}$")


# ---------------------------------------------------------------------------
# PyObjectId — JSON-serialisable MongoDB ObjectId wrapper
# ---------------------------------------------------------------------------

class PyObjectId(str):
    """
    A string subclass that validates MongoDB ObjectIds.

    Pydantic v2 usage:  id: PyObjectId = Field(default_factory=...)
    """

    @classmethod
    def __get_validators__(cls):  # pydantic v1 compatibility shim
        yield cls.validate

    @classmethod
    def validate(cls, v: Any) -> "PyObjectId":
        if isinstance(v, ObjectId):
            return cls(str(v))
        if isinstance(v, str) and ObjectId.is_valid(v):
            return cls(v)
        raise ValueError(f"Invalid ObjectId: {v!r}")

    @classmethod
    def __get_pydantic_core_schema__(cls, source_type: Any, handler: Any):
        from pydantic_core import core_schema

        return core_schema.no_info_plain_validator_function(
            cls.validate,
            serialization=core_schema.to_string_ser_schema(),
        )


# ---------------------------------------------------------------------------
# Shared base config
# ---------------------------------------------------------------------------

class _VendorBase(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
        str_strip_whitespace=True,
        use_enum_values=True,
    )


# ===========================================================================
# ADDRESS
# ===========================================================================

class AddressCreate(_VendorBase):
    street: str = Field(..., min_length=1, max_length=500,
                        description="Street address, building, suite, or flat number")
    city: str = Field(..., min_length=1, max_length=100)
    state: str = Field(..., min_length=1, max_length=100)
    pincode: str = Field(..., min_length=1, max_length=10)
    country: str = Field(default="India", max_length=100)

    @field_validator("pincode")
    @classmethod
    def validate_pincode(cls, v: str, info: Any) -> str:
        # Only enforce Indian PIN format when country is India
        # (country may not be present in validator context — guard defensively)
        if _PINCODE_RE.match(v) or len(v) >= 4:
            return v
        raise ValueError("Please enter a valid PIN / postal code")


class AddressUpdate(_VendorBase):
    street: str | None = Field(default=None, max_length=500)
    city: str | None = Field(default=None, max_length=100)
    state: str | None = Field(default=None, max_length=100)
    pincode: str | None = Field(default=None, max_length=10)
    country: str | None = Field(default=None, max_length=100)


class AddressResponse(_VendorBase):
    street: str = ""
    city: str = ""
    state: str = ""
    pincode: str = ""
    country: str = "India"


# ===========================================================================
# COMPANY INFORMATION  (Step 1)
# ===========================================================================

class CompanyInfoCreate(_VendorBase):
    legal_company_name: str = Field(..., min_length=1, max_length=300,
                                    description="Full legal name of the registered entity")
    trade_name: str = Field(default="", max_length=300,
                            description="Brand or trade name (optional)")
    business_entity_type: BusinessEntityType = Field(
        ..., description="Legal structure of the business entity"
    )
    country: str = Field(..., min_length=1, max_length=100)
    registration_number: str = Field(default="", max_length=50,
                                     description="CIN / LLPIN (required for corporate entities)")
    incorporation_date: str = Field(default="", max_length=10,
                                    description="ISO date YYYY-MM-DD")
    industry: str = Field(..., min_length=1, max_length=100)
    website: str = Field(default="", max_length=500)
    registered_address: AddressCreate
    is_operational_same_as_registered: bool = True
    operational_address: AddressCreate | None = None

    @model_validator(mode="after")
    def validate_corporate_fields(self) -> "CompanyInfoCreate":
        corporate_types = {
            BusinessEntityType.PRIVATE_LIMITED.value,
            BusinessEntityType.PUBLIC_LIMITED.value,
            BusinessEntityType.LLP.value,
            BusinessEntityType.OPC.value,
        }
        if self.business_entity_type in corporate_types:
            if not self.registration_number:
                raise ValueError(
                    "registration_number is required for corporate entity types"
                )
            if not self.incorporation_date:
                raise ValueError(
                    "incorporation_date is required for corporate entity types"
                )
        return self

    @model_validator(mode="after")
    def validate_operational_address(self) -> "CompanyInfoCreate":
        if not self.is_operational_same_as_registered and not self.operational_address:
            raise ValueError(
                "operational_address is required when "
                "is_operational_same_as_registered is False"
            )
        return self


class CompanyInfoUpdate(_VendorBase):
    legal_company_name: str | None = Field(default=None, max_length=300)
    trade_name: str | None = Field(default=None, max_length=300)
    business_entity_type: BusinessEntityType | None = None
    country: str | None = Field(default=None, max_length=100)
    registration_number: str | None = Field(default=None, max_length=50)
    incorporation_date: str | None = Field(default=None, max_length=10)
    industry: str | None = Field(default=None, max_length=100)
    website: str | None = Field(default=None, max_length=500)
    registered_address: AddressUpdate | None = None
    is_operational_same_as_registered: bool | None = None
    operational_address: AddressUpdate | None = None


class CompanyInfoResponse(_VendorBase):
    legal_company_name: str = ""
    trade_name: str = ""
    business_entity_type: str = ""
    country: str = ""
    registration_number: str = ""
    incorporation_date: str = ""
    industry: str = ""
    website: str = ""
    registered_address: AddressResponse | None = None
    is_operational_same_as_registered: bool = True
    operational_address: AddressResponse | None = None


# ===========================================================================
# CONTACT INFORMATION  (Step 2)
# ===========================================================================

class ContactPersonCreate(_VendorBase):
    first_name: str = Field(default="", max_length=100)
    last_name: str = Field(default="", max_length=100)
    full_name: str = Field(default="", max_length=200,
                           description="Used for signatory (single combined field)")
    designation: str = Field(default="", max_length=200)
    email: EmailStr | None = None
    phone: str = Field(default="", max_length=20)
    department: str = Field(default="", max_length=100)

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        if v and not _PHONE_RE.match(v):
            raise ValueError("Please enter a valid phone number")
        return v


class ContactPersonUpdate(_VendorBase):
    first_name: str | None = Field(default=None, max_length=100)
    last_name: str | None = Field(default=None, max_length=100)
    full_name: str | None = Field(default=None, max_length=200)
    designation: str | None = Field(default=None, max_length=200)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=20)
    department: str | None = Field(default=None, max_length=100)


class ContactPersonResponse(_VendorBase):
    first_name: str = ""
    last_name: str = ""
    full_name: str = ""
    designation: str = ""
    email: str | None = None
    phone: str = ""
    department: str = ""


class ContactInfoCreate(_VendorBase):
    primary: ContactPersonCreate
    secondary: ContactPersonCreate | None = None
    signatory: ContactPersonCreate
    confirm_authorized: bool

    @field_validator("confirm_authorized")
    @classmethod
    def must_be_authorized(cls, v: bool) -> bool:
        if not v:
            raise ValueError(
                "confirm_authorized must be True — vendor must confirm "
                "they are authorised to submit this application"
            )
        return v

    @model_validator(mode="after")
    def primary_must_have_name_and_email(self) -> "ContactInfoCreate":
        p = self.primary
        if not p.first_name:
            raise ValueError("primary.first_name is required")
        if not p.last_name:
            raise ValueError("primary.last_name is required")
        if not p.email:
            raise ValueError("primary.email is required")
        if not p.designation:
            raise ValueError("primary.designation is required")
        if not p.phone:
            raise ValueError("primary.phone is required")
        if not p.department:
            raise ValueError("primary.department is required")
        return self

    @model_validator(mode="after")
    def signatory_must_have_name_and_email(self) -> "ContactInfoCreate":
        s = self.signatory
        if not s.full_name:
            raise ValueError("signatory.full_name is required")
        if not s.designation:
            raise ValueError("signatory.designation is required")
        if not s.email:
            raise ValueError("signatory.email is required")
        return self


class ContactInfoUpdate(_VendorBase):
    primary: ContactPersonUpdate | None = None
    secondary: ContactPersonUpdate | None = None
    signatory: ContactPersonUpdate | None = None
    confirm_authorized: bool | None = None


class ContactInfoResponse(_VendorBase):
    primary: ContactPersonResponse = Field(default_factory=ContactPersonResponse)
    secondary: ContactPersonResponse | None = None
    signatory: ContactPersonResponse = Field(default_factory=ContactPersonResponse)
    confirm_authorized: bool = False


# ===========================================================================
# TAX DETAILS  (Step 3 — tax portion)
# ===========================================================================

class TaxDetailsCreate(_VendorBase):
    pan_number: str = Field(..., min_length=10, max_length=10,
                            description="Permanent Account Number (10 chars, e.g. ABCDE1234F)")
    gst_status: GSTStatus
    gstin: str = Field(default="", max_length=15,
                       description="GSTIN (15 chars) — required when gst_status is Registered")
    gst_state: str = Field(default="", max_length=100,
                           description="State of GST registration")
    tan_number: str = Field(default="", max_length=10,
                            description="Tax Deduction Account Number (10 chars, optional)")

    @field_validator("pan_number")
    @classmethod
    def validate_pan(cls, v: str) -> str:
        v = v.upper()
        if not _PAN_RE.match(v):
            raise ValueError(
                "Invalid PAN format. Must be 10 characters (e.g. ABCDE1234F)"
            )
        return v

    @field_validator("tan_number")
    @classmethod
    def validate_tan(cls, v: str) -> str:
        if not v:
            return v
        v = v.upper()
        if not _TAN_RE.match(v):
            raise ValueError(
                "Invalid TAN format. Must be 10 characters (e.g. ABCD12345E)"
            )
        return v

    @model_validator(mode="after")
    def validate_gst_fields(self) -> "TaxDetailsCreate":
        if self.gst_status == GSTStatus.REGISTERED.value:
            gstin = self.gstin.upper() if self.gstin else ""
            if not gstin:
                raise ValueError("gstin is required when gst_status is Registered")
            if not _GSTIN_RE.match(gstin):
                raise ValueError(
                    "Invalid GSTIN format. Must be 15 characters (e.g. 29ABCDE1234F1Z5)"
                )
            # Cross-check: GSTIN chars 3–12 must equal PAN
            embedded_pan = gstin[2:12]
            if embedded_pan != self.pan_number:
                raise ValueError(
                    f"GSTIN inconsistency: embedded PAN ({embedded_pan}) "
                    f"does not match PAN ({self.pan_number})"
                )
            if not self.gst_state:
                raise ValueError("gst_state is required when gst_status is Registered")
        return self


class TaxDetailsUpdate(_VendorBase):
    pan_number: str | None = Field(default=None, max_length=10)
    gst_status: GSTStatus | None = None
    gstin: str | None = Field(default=None, max_length=15)
    gst_state: str | None = Field(default=None, max_length=100)
    tan_number: str | None = Field(default=None, max_length=10)


class TaxDetailsResponse(_VendorBase):
    """
    ⚠️  Sensitive response — PAN is MASKED (shows only last 4 chars).
    Full PAN is never returned over the public API.
    """
    pan_number_masked: str = ""   # e.g. "******1234F"
    gst_status: str = ""
    gstin: str = ""               # GSTIN itself is returned (needed for display)
    gst_state: str = ""
    tan_number: str = ""


# ===========================================================================
# BANKING DETAILS  (Step 3 — banking portion)
# ===========================================================================

class BankingDetailsCreate(_VendorBase):
    account_holder_name: str = Field(..., min_length=1, max_length=300)
    bank_name: str = Field(..., min_length=1, max_length=200)
    account_number: str = Field(..., min_length=8, max_length=20,
                                description="Bank account number (8–20 digits)")
    confirm_account_number: str = Field(..., min_length=8, max_length=20,
                                        description="Must match account_number; never persisted")
    ifsc_code: str = Field(..., min_length=11, max_length=11,
                           description="IFSC code (11 chars, e.g. HDFC0001234)")
    account_type: AccountType
    bank_branch: str = Field(default="", max_length=200)
    confirm_bank_ownership: bool

    @field_validator("ifsc_code")
    @classmethod
    def validate_ifsc(cls, v: str) -> str:
        v = v.upper()
        if not _IFSC_RE.match(v):
            raise ValueError(
                "Invalid IFSC format. Must be 11 characters (e.g. HDFC0001234)"
            )
        return v

    @field_validator("confirm_bank_ownership")
    @classmethod
    def must_confirm_ownership(cls, v: bool) -> bool:
        if not v:
            raise ValueError(
                "confirm_bank_ownership must be True"
            )
        return v

    @model_validator(mode="after")
    def accounts_must_match(self) -> "BankingDetailsCreate":
        if self.account_number != self.confirm_account_number:
            raise ValueError("account_number and confirm_account_number do not match")
        return self


class BankingDetailsUpdate(_VendorBase):
    account_holder_name: str | None = Field(default=None, max_length=300)
    bank_name: str | None = Field(default=None, max_length=200)
    account_number: str | None = Field(default=None, max_length=20)
    confirm_account_number: str | None = Field(default=None, max_length=20)
    ifsc_code: str | None = Field(default=None, max_length=11)
    account_type: AccountType | None = None
    bank_branch: str | None = Field(default=None, max_length=200)
    confirm_bank_ownership: bool | None = None


class BankingDetailsResponse(_VendorBase):
    """
    ⚠️  Sensitive response — account number is MASKED (shows last 4 digits only).
    confirm_account_number is NEVER returned.
    """
    account_holder_name: str = ""
    bank_name: str = ""
    account_number_masked: str = ""    # e.g. "****1234"
    ifsc_code: str = ""
    account_type: str = ""
    bank_branch: str = ""


# ===========================================================================
# DOCUMENT METADATA  (Step 4)
# ===========================================================================

class DocumentMetaCreate(_VendorBase):
    document_id: str = Field(..., min_length=1, max_length=200,
                             description="UUID or storage object key")
    category: DocumentCategory
    file_name: str = Field(..., min_length=1, max_length=500)
    file_size: int = Field(..., ge=1, description="File size in bytes")
    file_type: str = Field(..., min_length=1, max_length=100,
                           description="MIME type, e.g. application/pdf")
    storage_path: str = Field(default="", max_length=1000,
                              description="Cloud storage URI (populated post-upload)")


class DocumentMetaUpdate(_VendorBase):
    verification_status: DocumentVerificationStatus | None = None
    storage_path: str | None = Field(default=None, max_length=1000)
    rejection_reason: str | None = Field(default=None, max_length=1000)
    verified_at: str | None = None


class DocumentMetaResponse(_VendorBase):
    document_id: str
    category: str
    file_name: str
    file_size: int
    file_type: str
    verification_status: str = "pending"
    uploaded_at: str = ""
    verified_at: str = ""
    rejection_reason: str = ""


# ===========================================================================
# DECLARATIONS  (Step 4)
# ===========================================================================

class DeclarationsCreate(_VendorBase):
    confirm_accurate: bool
    authorize_verification: bool
    agree_terms: bool

    @field_validator("confirm_accurate", "authorize_verification", "agree_terms")
    @classmethod
    def all_must_be_true(cls, v: bool, info: Any) -> bool:
        if not v:
            raise ValueError(f"{info.field_name} must be accepted before submission")
        return v


class DeclarationsUpdate(_VendorBase):
    confirm_accurate: bool | None = None
    authorize_verification: bool | None = None
    agree_terms: bool | None = None


class DeclarationsResponse(_VendorBase):
    confirm_accurate: bool = False
    authorize_verification: bool = False
    agree_terms: bool = False


# ===========================================================================
# VENDOR CREATE  (full submission — all 4 steps)
# ===========================================================================

class VendorCreate(_VendorBase):
    """
    Full vendor registration payload.

    This is the schema used when a vendor clicks "Submit" on the final step.
    All four step sub-schemas must be fully populated.
    """
    company_info: CompanyInfoCreate
    contact_info: ContactInfoCreate
    tax_details: TaxDetailsCreate
    banking_details: BankingDetailsCreate
    documents: list[DocumentMetaCreate] = Field(default_factory=list)
    declarations: DeclarationsCreate


# ===========================================================================
# VENDOR DRAFT CREATE (supports partial/step-by-step saves)
# ===========================================================================

class VendorDraftCreate(_VendorBase):
    """
    Draft vendor registration payload.

    Supports initiating onboarding with whatever fields the vendor has filled so far.
    """
    company_info: CompanyInfoUpdate | None = None
    contact_info: ContactInfoUpdate | None = None
    tax_details: TaxDetailsUpdate | None = None
    banking_details: BankingDetailsUpdate | None = None
    documents: list[DocumentMetaCreate] = Field(default_factory=list)
    declarations: DeclarationsUpdate | None = None


# ===========================================================================
# VENDOR UPDATE  (partial — PATCH)
# ===========================================================================

class VendorUpdate(_VendorBase):
    """
    Partial vendor update payload.

    All fields are optional so a PATCH can update only the changed sub-section.
    """
    company_info: CompanyInfoUpdate | None = None
    contact_info: ContactInfoUpdate | None = None
    tax_details: TaxDetailsUpdate | None = None
    banking_details: BankingDetailsUpdate | None = None
    documents: list[DocumentMetaCreate] | None = None
    declarations: DeclarationsUpdate | None = None
    status: VendorStatus | None = None


# ===========================================================================
# VENDOR RESPONSE  (returned to callers)
# ===========================================================================

def mask_pan(pan: str) -> str:
    """Masks all but the last 4 characters of a PAN (e.g. ABCDE1234F -> ******234F)."""
    if not pan:
        return ""
    if len(pan) <= 4:
        return "****"
    return "*" * (len(pan) - 4) + pan[-4:]


def mask_account_number(account_number: str) -> str:
    """Masks all but the last 4 digits of a bank account number."""
    if not account_number:
        return ""
    if len(account_number) <= 4:
        return "****"
    return "*" * (len(account_number) - 4) + account_number[-4:]


class VendorResponse(_VendorBase):
    """
    Vendor API response object.

    Security properties
    -------------------
    * ``tax_details`` uses TaxDetailsResponse (PAN masked).
    * ``banking_details`` uses BankingDetailsResponse (account number masked).
    * ``id`` is the string form of the MongoDB ``_id``.
    """
    id: str = Field(..., description="MongoDB document _id as a hex string")
    reference_number: str
    status: str
    company_info: CompanyInfoResponse
    contact_info: ContactInfoResponse
    tax_details: TaxDetailsResponse
    banking_details: BankingDetailsResponse
    documents: list[DocumentMetaResponse]
    declarations: DeclarationsResponse
    created_at: datetime
    updated_at: datetime
    submitted_at: datetime | None = None
    reviewed_at: datetime | None = None

    @classmethod
    def from_mongo(cls, doc: dict[str, Any]) -> "VendorResponse":
        """
        Construct a VendorResponse from a MongoDB document dictionary,
        ensuring sensitive values (PAN, bank account number) are masked
        and unpersisted verification fields are omitted.
        """
        doc_id = str(doc.get("_id", doc.get("id", "")))
        tax = doc.get("tax_details", {})
        bank = doc.get("banking_details", {})

        tax_resp = {
            "pan_number_masked": mask_pan(tax.get("pan_number", "")),
            "gst_status": tax.get("gst_status", ""),
            "gstin": tax.get("gstin", ""),
            "gst_state": tax.get("gst_state", ""),
            "tan_number": tax.get("tan_number", ""),
        }

        bank_resp = {
            "account_holder_name": bank.get("account_holder_name", ""),
            "bank_name": bank.get("bank_name", ""),
            "account_number_masked": mask_account_number(bank.get("account_number", "")),
            "ifsc_code": bank.get("ifsc_code", ""),
            "account_type": bank.get("account_type", ""),
            "bank_branch": bank.get("bank_branch", ""),
        }

        return cls(
            id=doc_id,
            reference_number=doc.get("reference_number", ""),
            status=doc.get("status", VendorStatus.DRAFT.value),
            company_info=doc.get("company_info", {}),
            contact_info=doc.get("contact_info", {}),
            tax_details=TaxDetailsResponse(**tax_resp),
            banking_details=BankingDetailsResponse(**bank_resp),
            documents=doc.get("documents", []),
            declarations=doc.get("declarations", {}),
            created_at=doc.get("created_at") or datetime.now(),
            updated_at=doc.get("updated_at") or datetime.now(),
            submitted_at=doc.get("submitted_at"),
            reviewed_at=doc.get("reviewed_at"),
        )


# ===========================================================================
# VENDOR SUMMARY  (list view — minimal data)
# ===========================================================================

class VendorSummaryResponse(_VendorBase):
    """
    Lightweight vendor entry for list/search endpoints.

    Does NOT include any sensitive sub-documents.
    """
    id: str
    reference_number: str
    status: str
    legal_company_name: str
    primary_contact_email: str
    created_at: datetime
    updated_at: datetime
    submitted_at: datetime | None = None


# ===========================================================================
# VENDOR STATUS & SUBMISSION RESPONSES
# ===========================================================================

class VendorStatusResponse(_VendorBase):
    """
    Onboarding status response returned by GET /api/vendors/{id}/status.
    """
    vendor_id: str
    reference_number: str
    status: str
    submitted_at: datetime | None = None
    updated_at: datetime


class VendorSubmissionResponse(_VendorBase):
    """
    Submission confirmation response returned by POST /api/vendors/{id}/submit.
    """
    message: str = "Vendor registration submitted successfully."
    vendor_id: str
    reference_number: str
    status: str
    submitted_at: datetime


