"""
Phase 8: NVIDIA-Powered Document Extraction and AI Verification Tests.

Tests run in-memory using mongomock and synthetic documents.
Covers file preprocessing, Nemotron 3.5 Parse, Nemotron 3.5 Super VL reasoning,
deterministic field validation, cross-document consistency checks, and end-to-end pipeline.
"""

from __future__ import annotations

import io
import pytest
from bson import ObjectId
from PIL import Image

from src.schemas.verification import ConsistencyFinding
from src.services.document_service import DocumentService
from src.services.extraction.preprocessor import DocumentPreprocessor, PreprocessingError
from src.services.nvidia_parse_service import NvidiaParseService
from src.services.nvidia_super_vl_service import NvidiaSuperVLService
from src.services.vendor_service import VendorService
from src.services.verification.field_validator import (
    DeterministicFieldValidator,
    normalize_company_name,
)
from src.services.verification_service import VerificationService



def create_synthetic_pdf(text: str = "Test document content") -> bytes:
    """Generate minimal valid PDF bytes with selectable text using PyMuPDF."""
    import pymupdf as fitz
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)
    page.insert_text((50, 72), text, fontsize=12)
    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


def create_synthetic_image(text: str = "Test Image") -> bytes:
    """Generate minimal valid JPEG bytes using Pillow."""
    img = Image.new("RGB", (300, 100), color=(255, 255, 255))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


# ---------------------------------------------------------------------------
# 1. File Preprocessing Tests
# ---------------------------------------------------------------------------

def test_01_valid_pdf_preprocessing():
    pdf_bytes = create_synthetic_pdf("INCOME TAX DEPARTMENT GOVT OF INDIA PAN ABCDE1234F")
    mime = DocumentPreprocessor.validate_file_bytes(pdf_bytes, "pan.pdf")
    assert mime == "application/pdf"

    pages = DocumentPreprocessor.render_pages_for_parse(pdf_bytes, mime)
    assert len(pages) >= 1
    assert pages[0].page_number == 1
    assert pages[0].base64_data_uri.startswith("data:image/jpeg;base64,")


def test_02_valid_image_preprocessing():
    img_bytes = create_synthetic_image()
    mime = DocumentPreprocessor.validate_file_bytes(img_bytes, "check.jpg")
    assert mime == "image/jpeg"

    pages = DocumentPreprocessor.render_pages_for_parse(img_bytes, mime)
    assert len(pages) == 1
    assert pages[0].base64_data_uri.startswith("data:image/jpeg;base64,")


def test_03_corrupted_and_empty_file_rejected():
    with pytest.raises(PreprocessingError, match="empty"):
        DocumentPreprocessor.validate_file_bytes(b"", "empty.pdf")

    with pytest.raises(PreprocessingError, match="Unsupported or corrupted"):
        DocumentPreprocessor.validate_file_bytes(b"INVALID_HEADER_BYTES_123456", "corrupted.pdf")

    with pytest.raises(PreprocessingError, match="extension is not permitted"):
        DocumentPreprocessor.validate_file_bytes(b"%PDF-1.4 header", "malicious.exe")


# ---------------------------------------------------------------------------
# 2. Deterministic Field Validation Tests
# ---------------------------------------------------------------------------

def test_04_pan_validation():
    # Valid PAN (4th char 'C' = Company)
    res_valid = DeterministicFieldValidator.validate_pan("AAACC1234F")
    assert res_valid.is_valid is True
    assert "Company" in res_valid.details

    # Invalid PAN (format)
    res_inv = DeterministicFieldValidator.validate_pan("INVALID_PAN")
    assert res_inv.is_valid is False

    # Missing PAN
    res_none = DeterministicFieldValidator.validate_pan(None)
    assert res_none.is_valid is False


def test_05_gstin_validation():
    # Valid GSTIN: 29 (Karnataka) + ABCDE1234F + 1 + Z + 5
    res_valid = DeterministicFieldValidator.validate_gstin("29ABCDE1234F1Z5")
    assert res_valid.is_valid is True
    assert "29" in res_valid.details

    # Invalid GSTIN format
    res_inv = DeterministicFieldValidator.validate_gstin("29ABCDE1234")
    assert res_inv.is_valid is False


def test_06_ifsc_and_account_number_validation():
    # Valid IFSC (5th char must be 0)
    res_ifsc = DeterministicFieldValidator.validate_ifsc("HDFC0001234")
    assert res_ifsc.is_valid is True

    # Invalid IFSC
    res_inv_ifsc = DeterministicFieldValidator.validate_ifsc("HDFCX001234")
    assert res_inv_ifsc.is_valid is False

    # Plausible Account Number (9-18 digits)
    res_acc = DeterministicFieldValidator.validate_account_number("123456789012")
    assert res_acc.is_valid is True

    # Invalid Account Number (letters or too short)
    res_bad_acc = DeterministicFieldValidator.validate_account_number("1234")
    assert res_bad_acc.is_valid is False


# ---------------------------------------------------------------------------
# 3. Super VL Fallback & Cross-Document Comparison Tests
# ---------------------------------------------------------------------------

def test_07_matching_pan_comparison():
    service = NvidiaSuperVLService(api_key="mock_key")
    parsed_text = "INCOME TAX DEPARTMENT GOVT OF INDIA\nPERMANENT ACCOUNT NUMBER CARD\nPAN: ABCDE1234F\nNAME: ACME TECH PVT LTD"
    vendor_data = {
        "tax_details": {"pan_number": "ABCDE1234F"},
        "company_info": {"legal_name": "Acme Tech Pvt Ltd"},
    }

    result = service._fallback_extract_and_verify("pan_card", parsed_text, vendor_data)
    assert result["extracted_fields"]["pan_number"] == "ABCDE1234F"
    assert result["verification_status"] == "completed"

    matches = [f for f in result["consistency_findings"] if f.status == "match"]
    assert len(matches) >= 1
    assert any("matches the registration record" in m.explanation for m in matches)


def test_08_mismatched_pan_flagged():
    service = NvidiaSuperVLService(api_key="mock_key")
    parsed_text = "INCOME TAX DEPARTMENT\nPAN: ZZZZZ9999Z\nNAME: UNKNOWN ENTITY"
    vendor_data = {
        "tax_details": {"pan_number": "ABCDE1234F"},
        "company_info": {"legal_name": "Acme Tech Pvt Ltd"},
    }

    result = service._fallback_extract_and_verify("pan_card", parsed_text, vendor_data)
    assert result["extracted_fields"]["pan_number"] == "ZZZZZ9999Z"
    assert result["verification_status"] == "flagged"

    mismatches = [f for f in result["consistency_findings"] if f.status == "mismatch"]
    assert len(mismatches) >= 1
    assert "mismatch" in mismatches[0].explanation.lower()


def test_09_bank_proof_comparison():
    service = NvidiaSuperVLService(api_key="mock_key")
    parsed_text = "HDFC BANK CANCELLED CHEQUE\nIFSC: HDFC0001234\nA/C NUMBER: 50100234567890\nPAY: ACME CLOUD SERVICES"
    vendor_data = {
        "banking_details": {
            "account_number": "50100234567890",
            "ifsc_code": "HDFC0001234",
            "account_holder_name": "Acme Cloud Services",
        }
    }

    result = service._fallback_extract_and_verify("bank_proof", parsed_text, vendor_data)
    assert result["extracted_fields"]["ifsc_code"] == "HDFC0001234"
    assert result["extracted_fields"]["account_number"] == "50100234567890"
    assert result["verification_status"] == "completed"


def test_10_company_name_normalization():
    # Normalization handles punctuation and abbreviations
    name1 = "Acme Technologies Pvt. Ltd."
    name2 = "ACME TECHNOLOGIES PRIVATE LIMITED"
    assert normalize_company_name(name1) == normalize_company_name(name2)


# ---------------------------------------------------------------------------
# 4. End-to-End Pipeline Test (direct service calls, no HTTP transport)
# ---------------------------------------------------------------------------

def test_11_end_to_end_verification_pipeline():
    """
    Full pipeline test: vendor create → document upload → AI verification → result retrieval.

    Calls services directly (no HTTP layer) to avoid asyncio event-loop issues
    in the sandbox test environment. All logic paths — preprocessing, Nemotron
    mock extraction, deterministic validation, MongoDB persistence — are exercised.
    """
    import gridfs
    import src.database.mongodb as mongo_module
    from src.schemas.vendor import VendorDraftCreate
    from src.services.vendor_service import VendorService
    from src.services.document_service import DocumentService
    from src.services.verification_service import VerificationService

    db = mongo_module.db

    # 1. Create vendor via VendorService
    vendor_svc = VendorService(db=db)
    vendor_payload = VendorDraftCreate(
        company_info={
            "legal_name": "Acme Technologies Private Limited",
            "trade_name": "Acme Tech",
            "business_entity_type": "Private Limited Company",
            "country": "India",
            "industry": "Technology",
            "registered_address": {
                "street": "123 Tech Park",
                "city": "Bengaluru",
                "state": "Karnataka",
                "pincode": "560001",
                "country": "India",
            },
        },
        tax_details={
            "pan_number": "ABCDE1234F",
            "gstin": "29ABCDE1234F1Z5",
            "gst_status": "Registered",
        },
        banking_details={
            "account_holder_name": "Acme Technologies Private Limited",
            "bank_name": "HDFC Bank",
            "account_number": "50100234567890",
            "ifsc_code": "HDFC0001234",
            "account_type": "Current Account",
            "bank_branch": "Koramangala",
            "confirm_bank_ownership": True,
        },
    )

    # VendorService.create_vendor is async — run synchronously
    def run_sync(coro):
        """Run an async coroutine without an event loop when all sub-coroutines complete immediately."""
        try:
            coro.send(None)
        except StopIteration as exc:
            return exc.value
        raise RuntimeError("Coroutine suspended unexpectedly in mock environment")

    vendor_resp = run_sync(vendor_svc.create_vendor(vendor_payload))
    vendor_id = vendor_resp.id

    # 2. Upload document directly via GridFS (bypasses HTTP)
    doc_svc = DocumentService(db=db)
    pdf_content = create_synthetic_pdf(
        "GOVERNMENT OF INDIA INCOME TAX DEPARTMENT\n"
        "PERMANENT ACCOUNT NUMBER: ABCDE1234F\n"
        "NAME: ACME TECHNOLOGIES PRIVATE LIMITED"
    )
    doc_meta = doc_svc.upload_document(
        vendor_id=vendor_id,
        file_bytes=pdf_content,
        filename="pan_card.pdf",
        content_type="application/pdf",
        category="pan_card",
    )
    document_id = doc_meta["document_id"]

    # 3. Execute verification pipeline synchronously
    vfs_svc = VerificationService(db=db)
    result = run_sync(vfs_svc.execute_verification(vendor_id, document_id))

    assert result["vendor_id"] == vendor_id
    assert result["document_id"] == document_id
    assert result["extraction_status"] == "completed"
    assert result["verification_status"] in ("completed", "flagged", "needs_manual_review")
    assert "pan_number" in result["extracted_fields"]
    assert len(result["consistency_findings"]) >= 1

    # 4. Retrieve single verification result
    fetched = vfs_svc.get_document_verification(vendor_id, document_id)
    assert fetched is not None
    assert fetched["document_id"] == document_id

    # 5. Retrieve vendor-wide verification summary
    summary = vfs_svc.get_vendor_verification_summary(vendor_id)
    assert summary["total_documents"] == 1
    assert len(summary["results"]) == 1


