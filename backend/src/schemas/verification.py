"""
Pydantic schemas for Phase 8 AI-powered Document Extraction and Verification.

Covers category-specific extracted field schemas, field-level format validation,
cross-document consistency findings, and complete verification results.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------------------
# Category-Specific Extracted Fields Schemas
# ---------------------------------------------------------------------------

class GSTExtractedFields(BaseModel):
    """Fields extracted from a GST Registration Certificate."""
    gstin: str | None = Field(default=None, description="15-character Goods and Services Tax Identification Number")
    legal_name: str | None = Field(default=None, description="Legal business / company name")
    trade_name: str | None = Field(default=None, description="Trade name or brand name")
    registration_date: str | None = Field(default=None, description="Date of GST registration")
    principal_address: str | None = Field(default=None, description="Principal place of business address")
    status: str | None = Field(default=None, description="Taxpayer registration status (e.g. Active)")

    model_config = ConfigDict(extra="ignore")


class PANExtractedFields(BaseModel):
    """Fields extracted from a PAN Card or Certificate."""
    pan_number: str | None = Field(default=None, description="10-character Permanent Account Number")
    name: str | None = Field(default=None, description="Cardholder or entity name")
    date_of_birth_or_inc: str | None = Field(default=None, description="Date of birth or date of incorporation")

    model_config = ConfigDict(extra="ignore")


class IncorporationExtractedFields(BaseModel):
    """Fields extracted from a Certificate of Incorporation."""
    company_name: str | None = Field(default=None, description="Corporate legal name")
    cin: str | None = Field(default=None, description="Corporate Identification Number (CIN or LLPIN)")
    incorporation_date: str | None = Field(default=None, description="Date of incorporation")
    registered_address: str | None = Field(default=None, description="Registered office address")

    model_config = ConfigDict(extra="ignore")


class BankProofExtractedFields(BaseModel):
    """Fields extracted from a Cheque, Bank Statement, or Bank Letter."""
    account_holder_name: str | None = Field(default=None, description="Name of account holder")
    account_number: str | None = Field(default=None, description="Bank account number")
    ifsc_code: str | None = Field(default=None, description="11-character Indian Financial System Code")
    bank_name: str | None = Field(default=None, description="Name of the bank")
    branch: str | None = Field(default=None, description="Bank branch name")

    model_config = ConfigDict(extra="ignore")


class TANExtractedFields(BaseModel):
    """Fields extracted from a TAN Certificate."""
    tan_number: str | None = Field(default=None, description="10-character Tax Deduction and Collection Account Number")
    name: str | None = Field(default=None, description="Entity or deductor name")

    model_config = ConfigDict(extra="ignore")


class MSMEExtractedFields(BaseModel):
    """Fields extracted from an MSME / Udyam Certificate."""
    udyam_number: str | None = Field(default=None, description="Udyam Registration Number")
    enterprise_name: str | None = Field(default=None, description="Name of Enterprise")

    model_config = ConfigDict(extra="ignore")


# ---------------------------------------------------------------------------
# Page-Level Parsed Content (from Nemotron 3.5 Parse)
# ---------------------------------------------------------------------------

class ParsedPageResult(BaseModel):
    """Page-level text, tables and layout extracted by Nemotron 3.5 Parse."""
    page_number: int
    text: str
    tables: list[str] = Field(default_factory=list)
    status: str = "success"  # success, empty, failed


# ---------------------------------------------------------------------------
# Findings & Validation Results
# ---------------------------------------------------------------------------

class FieldValidationFinding(BaseModel):
    """Deterministic Python format check for a single field."""
    field_name: str
    value: str | None
    is_valid: bool
    rule: str
    details: str


class ConsistencyFinding(BaseModel):
    """Cross-document or Registration comparison finding."""
    field_name: str
    vendor_value: str | None = None
    extracted_value: str | None = None
    status: str = "match"  # match, mismatch, missing_in_document, manual_review
    explanation: str
    source_document_id: str | None = None
    page_number: int | None = None


# ---------------------------------------------------------------------------
# Full Verification Result Schema
# ---------------------------------------------------------------------------

class VerificationResultResponse(BaseModel):
    """Complete document extraction and verification result."""
    id: str = Field(..., description="Unique verification record ID")
    vendor_id: str
    document_id: str
    document_category: str
    file_name: str = ""
    extraction_status: str = "pending"  # pending, processing, completed, flagged, needs_manual_review, failed
    verification_status: str = "pending"  # pending, completed, flagged, needs_manual_review, failed
    parsed_pages: list[ParsedPageResult] = Field(default_factory=list)
    parsed_text: str = ""
    extracted_fields: dict[str, Any] = Field(default_factory=dict)
    field_validations: list[FieldValidationFinding] = Field(default_factory=list)
    consistency_findings: list[ConsistencyFinding] = Field(default_factory=list)
    summary_explanation: str = ""
    parse_model_id: str = "nvidia/nemotron-parse"
    super_vl_model_id: str = "nvidia/nemotron-3.5-super-vl-120b-a12b"
    processing_version: str = "1.0.0"
    processing_time_ms: int = 0
    error_details: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class VendorVerificationSummaryResponse(BaseModel):
    """Summary of all document verifications for a specific vendor."""
    vendor_id: str
    total_documents: int
    verified_documents: int
    flagged_documents: int
    pending_documents: int
    overall_status: str  # verified, flagged, needs_manual_review, pending
    results: list[VerificationResultResponse] = Field(default_factory=list)

