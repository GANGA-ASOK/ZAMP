"""
Unit tests for VendorFlow Pydantic v2 schemas and data models.

Required test suite coverage:
 1. Valid vendor data (full creation payload)
 2. Missing required fields
 3. Invalid email address
 4. Invalid onboarding status
 5. Valid partial update
 6. Invalid ObjectId handling
 7. Valid document metadata
 8. Invalid document metadata
 9. Response serialization (JSON serializability and format)
10. Sensitive information not appearing in normal response representations
"""

from datetime import datetime, timezone
from bson import ObjectId
import pytest
from pydantic import ValidationError

from src.models.enums import (
    AccountType,
    BusinessEntityType,
    DocumentCategory,
    DocumentVerificationStatus,
    GSTStatus,
    VendorStatus,
)
from src.models.vendor import (
    AddressModel,
    BankingDetailsModel,
    CompanyInfoModel,
    ContactInfoModel,
    ContactPersonModel,
    DeclarationsModel,
    DocumentMetaModel,
    TaxDetailsModel,
    VendorDocument,
)
from src.schemas.vendor import (
    AddressCreate,
    BankingDetailsCreate,
    BankingDetailsResponse,
    CompanyInfoCreate,
    ContactInfoCreate,
    ContactPersonCreate,
    DeclarationsCreate,
    DocumentMetaCreate,
    DocumentMetaResponse,
    PyObjectId,
    TaxDetailsCreate,
    TaxDetailsResponse,
    VendorCreate,
    VendorResponse,
    VendorSummaryResponse,
    VendorUpdate,
    mask_account_number,
    mask_pan,
)


# ---------------------------------------------------------------------------
# Fixtures / Helper Data
# ---------------------------------------------------------------------------

@pytest.fixture
def valid_company_info():
    return {
        "legal_company_name": "Acme Technologies Private Limited",
        "trade_name": "Acme Cloud",
        "business_entity_type": BusinessEntityType.PRIVATE_LIMITED.value,
        "country": "India",
        "registration_number": "U72200KA2020PTC123456",
        "incorporation_date": "2020-05-15",
        "industry": "Information Technology",
        "website": "https://acmecloud.example.com",
        "registered_address": {
            "street": "123 Tech Park, Residency Road",
            "city": "Bengaluru",
            "state": "Karnataka",
            "pincode": "560001",
            "country": "India",
        },
        "is_operational_same_as_registered": True,
        "operational_address": None,
    }


@pytest.fixture
def valid_contact_info():
    return {
        "primary": {
            "first_name": "Rajesh",
            "last_name": "Sharma",
            "designation": "Director of Operations",
            "email": "rajesh.sharma@acme.example.com",
            "phone": "+919876543210",
            "department": "Operations",
        },
        "secondary": {
            "first_name": "Priya",
            "last_name": "Patel",
            "designation": "Procurement Lead",
            "email": "priya.patel@acme.example.com",
            "phone": "+919876543211",
            "department": "Finance",
        },
        "signatory": {
            "full_name": "Rajesh Sharma",
            "designation": "Managing Director",
            "email": "signatory@acme.example.com",
            "phone": "+919876543210",
        },
        "confirm_authorized": True,
    }


@pytest.fixture
def valid_tax_details():
    return {
        "pan_number": "ABCDE1234F",
        "gst_status": GSTStatus.REGISTERED.value,
        "gstin": "29ABCDE1234F1Z5",
        "gst_state": "Karnataka",
        "tan_number": "BLRA12345B",
    }


@pytest.fixture
def valid_banking_details():
    return {
        "account_holder_name": "Acme Technologies Pvt Ltd",
        "bank_name": "HDFC Bank",
        "account_number": "50100432198765",
        "confirm_account_number": "50100432198765",
        "ifsc_code": "HDFC0001234",
        "account_type": AccountType.CURRENT.value,
        "bank_branch": "Koramangala, Bengaluru",
        "confirm_bank_ownership": True,
    }


@pytest.fixture
def valid_documents():
    return [
        {
            "document_id": "doc-coi-001",
            "category": DocumentCategory.CERTIFICATE_OF_INCORPORATION.value,
            "file_name": "certificate_of_incorporation.pdf",
            "file_size": 1048576,
            "file_type": "application/pdf",
            "storage_path": "gs://vendorflow-docs/doc-coi-001.pdf",
        },
        {
            "document_id": "doc-pan-002",
            "category": DocumentCategory.PAN_CARD.value,
            "file_name": "pan_card.pdf",
            "file_size": 524288,
            "file_type": "application/pdf",
            "storage_path": "gs://vendorflow-docs/doc-pan-002.pdf",
        },
    ]


@pytest.fixture
def valid_declarations():
    return {
        "confirm_accurate": True,
        "authorize_verification": True,
        "agree_terms": True,
    }


@pytest.fixture
def complete_vendor_payload(
    valid_company_info,
    valid_contact_info,
    valid_tax_details,
    valid_banking_details,
    valid_documents,
    valid_declarations,
):
    return {
        "company_info": valid_company_info,
        "contact_info": valid_contact_info,
        "tax_details": valid_tax_details,
        "banking_details": valid_banking_details,
        "documents": valid_documents,
        "declarations": valid_declarations,
    }


# ---------------------------------------------------------------------------
# Test 1: Valid Vendor Data
# ---------------------------------------------------------------------------

def test_01_valid_vendor_data(complete_vendor_payload):
    """Scenario 1: Full valid vendor registration payload passes validation."""
    vendor = VendorCreate(**complete_vendor_payload)
    assert vendor.company_info.legal_company_name == "Acme Technologies Private Limited"
    assert vendor.company_info.business_entity_type == BusinessEntityType.PRIVATE_LIMITED.value
    assert vendor.contact_info.primary.email == "rajesh.sharma@acme.example.com"
    assert vendor.tax_details.pan_number == "ABCDE1234F"
    assert vendor.tax_details.gstin == "29ABCDE1234F1Z5"
    assert vendor.banking_details.account_number == "50100432198765"
    assert len(vendor.documents) == 2
    assert vendor.declarations.agree_terms is True


# ---------------------------------------------------------------------------
# Test 2: Missing Required Fields
# ---------------------------------------------------------------------------

def test_02_missing_required_fields(complete_vendor_payload):
    """Scenario 2: Missing mandatory fields trigger ValidationError."""
    # Missing legal company name
    payload = complete_vendor_payload.copy()
    payload["company_info"] = complete_vendor_payload["company_info"].copy()
    del payload["company_info"]["legal_company_name"]
    with pytest.raises(ValidationError) as exc_info:
        VendorCreate(**payload)
    assert "legal_company_name" in str(exc_info.value)

    # Missing primary email
    payload = complete_vendor_payload.copy()
    payload["contact_info"] = complete_vendor_payload["contact_info"].copy()
    payload["contact_info"]["primary"] = complete_vendor_payload["contact_info"]["primary"].copy()
    payload["contact_info"]["primary"]["email"] = None
    with pytest.raises(ValidationError) as exc_info:
        VendorCreate(**payload)
    assert "primary.email" in str(exc_info.value) or "email" in str(exc_info.value)

    # Corporate entity without registration number
    payload = complete_vendor_payload.copy()
    payload["company_info"] = complete_vendor_payload["company_info"].copy()
    payload["company_info"]["registration_number"] = ""
    with pytest.raises(ValidationError) as exc_info:
        VendorCreate(**payload)
    assert "registration_number is required" in str(exc_info.value)


# ---------------------------------------------------------------------------
# Test 3: Invalid Email
# ---------------------------------------------------------------------------

def test_03_invalid_email(valid_contact_info):
    """Scenario 3: Invalid email addresses fail validation."""
    invalid_emails = [
        "notanemail",
        "missingatsign.com",
        "@nodomain.com",
        "spaces in@email.com",
    ]
    for bad_email in invalid_emails:
        data = valid_contact_info.copy()
        data["primary"] = valid_contact_info["primary"].copy()
        data["primary"]["email"] = bad_email
        with pytest.raises(ValidationError) as exc_info:
            ContactInfoCreate(**data)
        assert "value is not a valid email address" in str(exc_info.value)


# ---------------------------------------------------------------------------
# Test 4: Invalid Onboarding Status
# ---------------------------------------------------------------------------

def test_04_invalid_onboarding_status():
    """Scenario 4: Invalid status value rejected by enum validation."""
    with pytest.raises(ValidationError) as exc_info:
        VendorUpdate(status="unknown_status")
    assert "status" in str(exc_info.value)

    # Valid statuses must pass
    valid_statuses = [s.value for s in VendorStatus]
    for status in valid_statuses:
        update = VendorUpdate(status=status)
        assert update.status == status


# ---------------------------------------------------------------------------
# Test 5: Valid Partial Update
# ---------------------------------------------------------------------------

def test_05_valid_partial_update():
    """Scenario 5: VendorUpdate allows updating individual sections or fields."""
    # Update only company trade name
    patch1 = VendorUpdate(
        company_info={"trade_name": "Acme Global Solutions"}
    )
    assert patch1.company_info.trade_name == "Acme Global Solutions"
    assert patch1.company_info.legal_company_name is None
    assert patch1.contact_info is None
    assert patch1.banking_details is None

    # Update only onboarding status
    patch2 = VendorUpdate(status=VendorStatus.UNDER_REVIEW.value)
    assert patch2.status == VendorStatus.UNDER_REVIEW.value
    assert patch2.company_info is None


# ---------------------------------------------------------------------------
# Test 6: PyObjectId Validation
# ---------------------------------------------------------------------------

def test_06_pyobjectid_handling():
    """Scenario 6: Valid and invalid MongoDB ObjectIds are handled properly."""
    # Valid string representation of ObjectId
    valid_id_str = "507f1f77bcf86cd799439011"
    parsed_id = PyObjectId.validate(valid_id_str)
    assert parsed_id == valid_id_str

    # Valid BSON ObjectId instance
    oid = ObjectId()
    parsed_oid = PyObjectId.validate(oid)
    assert parsed_oid == str(oid)

    # Invalid ObjectId
    with pytest.raises(ValueError) as exc_info:
        PyObjectId.validate("not-a-valid-hex-object-id")
    assert "Invalid ObjectId" in str(exc_info.value)


# ---------------------------------------------------------------------------
# Test 7: Valid Document Metadata
# ---------------------------------------------------------------------------

def test_07_valid_document_metadata():
    """Scenario 7: Valid document metadata passes validation."""
    doc = DocumentMetaCreate(
        document_id="doc-xyz-123",
        category=DocumentCategory.PAN_CARD.value,
        file_name="vendor_pan_scan.pdf",
        file_size=204800,
        file_type="application/pdf",
        storage_path="gs://bucket/vendor_pan_scan.pdf",
    )
    assert doc.document_id == "doc-xyz-123"
    assert doc.category == DocumentCategory.PAN_CARD.value
    assert doc.file_size == 204800


# ---------------------------------------------------------------------------
# Test 8: Invalid Document Metadata
# ---------------------------------------------------------------------------

def test_08_invalid_document_metadata():
    """Scenario 8: Missing or malformed document fields are rejected."""
    # Invalid category
    with pytest.raises(ValidationError) as exc_info:
        DocumentMetaCreate(
            document_id="doc-123",
            category="unsupported_category",
            file_name="doc.pdf",
            file_size=1024,
            file_type="application/pdf",
        )
    assert "category" in str(exc_info.value)

    # Non-positive file size
    with pytest.raises(ValidationError) as exc_info:
        DocumentMetaCreate(
            document_id="doc-123",
            category=DocumentCategory.OTHER.value,
            file_name="doc.pdf",
            file_size=0,
            file_type="application/pdf",
        )
    assert "file_size" in str(exc_info.value)

    # Empty document ID
    with pytest.raises(ValidationError) as exc_info:
        DocumentMetaCreate(
            document_id="",
            category=DocumentCategory.OTHER.value,
            file_name="doc.pdf",
            file_size=1024,
            file_type="application/pdf",
        )
    assert "document_id" in str(exc_info.value)


# ---------------------------------------------------------------------------
# Test 9: Response Serialization
# ---------------------------------------------------------------------------

def test_09_response_serialization(complete_vendor_payload):
    """Scenario 9: VendorResponse can be constructed from a DB dict and serializes cleanly."""
    raw_doc = {
        "_id": ObjectId("507f1f77bcf86cd799439011"),
        "reference_number": "VND-2026-00042",
        "status": VendorStatus.SUBMITTED.value,
        "company_info": complete_vendor_payload["company_info"],
        "contact_info": complete_vendor_payload["contact_info"],
        "tax_details": complete_vendor_payload["tax_details"],
        "banking_details": complete_vendor_payload["banking_details"],
        "documents": complete_vendor_payload["documents"],
        "declarations": complete_vendor_payload["declarations"],
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
        "submitted_at": datetime.now(timezone.utc),
        "reviewed_at": None,
    }

    # Transform to VendorResponse
    response = VendorResponse.from_mongo(raw_doc)
    assert response.id == "507f1f77bcf86cd799439011"
    assert response.reference_number == "VND-2026-00042"
    assert response.status == VendorStatus.SUBMITTED.value

    # Verify JSON serialization succeeds without raising TypeError
    json_output = response.model_dump_json()
    assert isinstance(json_output, str)
    assert "Acme Technologies Private Limited" in json_output
    assert "507f1f77bcf86cd799439011" in json_output

    # Verify VendorSummaryResponse serialization
    summary = VendorSummaryResponse(
        id=str(raw_doc["_id"]),
        reference_number=raw_doc["reference_number"],
        status=raw_doc["status"],
        legal_company_name=raw_doc["company_info"]["legal_company_name"],
        primary_contact_email=raw_doc["contact_info"]["primary"]["email"],
        created_at=raw_doc["created_at"],
        updated_at=raw_doc["updated_at"],
    )
    summary_json = summary.model_dump_json()
    assert "rajesh.sharma@acme.example.com" in summary_json


# ---------------------------------------------------------------------------
# Test 10: Sensitive Information Masking
# ---------------------------------------------------------------------------

def test_10_sensitive_information_masking(complete_vendor_payload):
    """Scenario 10: Sensitive fields (full PAN, full account number) are masked in responses."""
    raw_doc = {
        "_id": ObjectId("507f1f77bcf86cd799439011"),
        "reference_number": "VND-2026-00042",
        "status": VendorStatus.SUBMITTED.value,
        "company_info": complete_vendor_payload["company_info"],
        "contact_info": complete_vendor_payload["contact_info"],
        "tax_details": complete_vendor_payload["tax_details"],
        "banking_details": complete_vendor_payload["banking_details"],
        "documents": complete_vendor_payload["documents"],
        "declarations": complete_vendor_payload["declarations"],
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }

    response = VendorResponse.from_mongo(raw_doc)
    dumped_dict = response.model_dump()

    # 1. Full account number must NOT appear in response representation
    raw_account = complete_vendor_payload["banking_details"]["account_number"]
    assert "account_number" not in dumped_dict["banking_details"]
    assert "confirm_account_number" not in dumped_dict["banking_details"]
    assert dumped_dict["banking_details"]["account_number_masked"] == "**********8765"
    assert raw_account not in response.model_dump_json()

    # 2. Full PAN must NOT appear as pan_number in response representation
    raw_pan = complete_vendor_payload["tax_details"]["pan_number"]
    assert "pan_number" not in dumped_dict["tax_details"]
    assert dumped_dict["tax_details"]["pan_number_masked"] == "******234F"

    # 3. Masking helper sanity checks
    assert mask_pan("ABCDE1234F") == "******234F"
    assert mask_account_number("1234567890") == "******7890"


# ---------------------------------------------------------------------------
# Additional Business Validation Rule Tests
# ---------------------------------------------------------------------------

def test_gstin_embedded_pan_mismatch(valid_tax_details):
    """Embedded PAN inside GSTIN (chars 3..12) must match entered PAN."""
    data = valid_tax_details.copy()
    data["pan_number"] = "ABCDE1234F"
    # GSTIN with different embedded PAN 'XXXXX9999Y'
    data["gstin"] = "29XXXXX9999Y1Z5"
    with pytest.raises(ValidationError) as exc_info:
        TaxDetailsCreate(**data)
    assert "GSTIN inconsistency" in str(exc_info.value)


def test_banking_account_number_mismatch(valid_banking_details):
    """account_number and confirm_account_number must match."""
    data = valid_banking_details.copy()
    data["confirm_account_number"] = "999999999999"
    with pytest.raises(ValidationError) as exc_info:
        BankingDetailsCreate(**data)
    assert "do not match" in str(exc_info.value)


def test_vendor_document_model_to_dict():
    """Verify MongoDB document model converts to dict cleanly."""
    doc = VendorDocument(
        reference_number="VND-2026-99999",
        status=VendorStatus.DRAFT.value,
        company_info=CompanyInfoModel(legal_company_name="Test Enterprise"),
        tax_details=TaxDetailsModel(pan_number="ABCDE1234F"),
        banking_details=BankingDetailsModel(account_number="1234567890"),
    )
    doc_dict = doc.to_dict()
    assert doc_dict["reference_number"] == "VND-2026-99999"
    assert doc_dict["status"] == "draft"
    assert doc_dict["company_info"]["legal_company_name"] == "Test Enterprise"
    assert doc_dict["tax_details"]["pan_number"] == "ABCDE1234F"
