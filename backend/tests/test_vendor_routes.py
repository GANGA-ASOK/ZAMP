"""
API integration and route tests for VendorFlow Vendor Registration APIs.

Uses an isolated, in-memory mongomock database to ensure no destructive operations
touch production data.

Covers all 10 required test scenarios:
 1. Creating a vendor draft.
 2. Retrieving an existing vendor.
 3. Retrieving a nonexistent vendor.
 4. Updating vendor details (PUT).
 5. Partially updating a nested section without losing other sections (PATCH).
 6. Updating with an invalid vendor ID.
 7. Submitting a complete vendor registration.
 8. Rejecting an incomplete registration.
 9. Checking vendor onboarding status.
10. Handling duplicate registrations (HTTP 409 Conflict).
"""

from datetime import datetime, timezone
import pytest
from fastapi.testclient import TestClient
import mongomock

from src.main import app
from src.models.enums import (
    AccountType,
    BusinessEntityType,
    DocumentCategory,
    GSTStatus,
    VendorStatus,
)
from src.routes.vendors import get_vendor_service
from src.services.vendor_service import VendorService


# ---------------------------------------------------------------------------
# Test Fixtures & Mock Database
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def isolated_service():
    """Provides a fresh in-memory database and test service for each test."""
    mock_client = mongomock.MongoClient()
    mock_db = mock_client["zamp_test"]
    service = VendorService(db=mock_db)

    # Override the dependency in FastAPI
    app.dependency_overrides[get_vendor_service] = lambda: service
    yield service
    app.dependency_overrides.clear()


@pytest.fixture
def client():
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture
def sample_company_info():
    return {
        "legal_company_name": "Apex Innovations Private Limited",
        "trade_name": "Apex Cloud",
        "business_entity_type": BusinessEntityType.PRIVATE_LIMITED.value,
        "country": "India",
        "registration_number": "U72200KA2021PTC654321",
        "incorporation_date": "2021-03-10",
        "industry": "Information Technology",
        "website": "https://apexcloud.example.com",
        "registered_address": {
            "street": "45 Brigade Road",
            "city": "Bengaluru",
            "state": "Karnataka",
            "pincode": "560025",
            "country": "India",
        },
        "is_operational_same_as_registered": True,
        "operational_address": None,
    }


@pytest.fixture
def sample_contact_info():
    return {
        "primary": {
            "first_name": "Ananya",
            "last_name": "Rao",
            "designation": "Vice President",
            "email": "ananya.rao@apex.example.com",
            "phone": "+919812345678",
            "department": "Management",
        },
        "signatory": {
            "full_name": "Ananya Rao",
            "designation": "Director",
            "email": "ananya.rao@apex.example.com",
            "phone": "+919812345678",
        },
        "confirm_authorized": True,
    }


@pytest.fixture
def sample_tax_details():
    return {
        "pan_number": "ABCDE5678G",
        "gst_status": GSTStatus.REGISTERED.value,
        "gstin": "29ABCDE5678G1Z2",
        "gst_state": "Karnataka",
        "tan_number": "BLRA56789C",
    }


@pytest.fixture
def sample_banking_details():
    return {
        "account_holder_name": "Apex Innovations Pvt Ltd",
        "bank_name": "ICICI Bank",
        "account_number": "10020030040050",
        "confirm_account_number": "10020030040050",
        "ifsc_code": "ICIC0000100",
        "account_type": AccountType.CURRENT.value,
        "bank_branch": "MG Road, Bengaluru",
        "confirm_bank_ownership": True,
    }


@pytest.fixture
def sample_documents():
    return [
        {
            "document_id": "doc-coi-100",
            "category": DocumentCategory.CERTIFICATE_OF_INCORPORATION.value,
            "file_name": "coi.pdf",
            "file_size": 512000,
            "file_type": "application/pdf",
        },
        {
            "document_id": "doc-pan-101",
            "category": DocumentCategory.PAN_CARD.value,
            "file_name": "pan.pdf",
            "file_size": 256000,
            "file_type": "application/pdf",
        },
    ]


@pytest.fixture
def sample_declarations():
    return {
        "confirm_accurate": True,
        "authorize_verification": True,
        "agree_terms": True,
    }


# ---------------------------------------------------------------------------
# Test 1: Creating a vendor draft
# ---------------------------------------------------------------------------

def test_01_create_vendor_draft(client, sample_company_info):
    """Scenario 1: POST /api/vendors/ initializes a draft with minimal or partial info."""
    draft_payload = {
        "company_info": {
            "legal_company_name": sample_company_info["legal_company_name"],
            "business_entity_type": sample_company_info["business_entity_type"],
            "country": sample_company_info["country"],
        }
    }
    response = client.post("/api/vendors/", json=draft_payload)
    assert response.status_code == 201

    data = response.json()
    assert "id" in data
    assert len(data["id"]) == 24
    assert data["reference_number"].startswith("VND-")
    assert data["status"] == VendorStatus.DRAFT.value
    assert data["company_info"]["legal_company_name"] == "Apex Innovations Private Limited"
    assert "created_at" in data
    assert "updated_at" in data


# ---------------------------------------------------------------------------
# Test 2: Retrieving an existing vendor
# ---------------------------------------------------------------------------

def test_02_retrieve_existing_vendor(client, sample_company_info):
    """Scenario 2: GET /api/vendors/{id} retrieves an existing vendor."""
    # Create first
    created = client.post("/api/vendors/", json={"company_info": sample_company_info}).json()
    vendor_id = created["id"]

    # Retrieve
    response = client.get(f"/api/vendors/{vendor_id}")
    assert response.status_code == 200

    data = response.json()
    assert data["id"] == vendor_id
    assert data["reference_number"] == created["reference_number"]
    assert data["company_info"]["legal_company_name"] == sample_company_info["legal_company_name"]


# ---------------------------------------------------------------------------
# Test 3: Retrieving a nonexistent vendor
# ---------------------------------------------------------------------------

def test_03_retrieve_nonexistent_vendor(client):
    """Scenario 3: GET /api/vendors/{id} returns 404 for nonexistent valid ObjectId."""
    nonexistent_id = "507f1f77bcf86cd799439011"
    response = client.get(f"/api/vendors/{nonexistent_id}")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


# ---------------------------------------------------------------------------
# Test 4: Updating vendor details (PUT)
# ---------------------------------------------------------------------------

def test_04_update_vendor_details(client, sample_company_info, sample_contact_info):
    """Scenario 4: PUT /api/vendors/{id} replaces onboarding info while preserving internal fields."""
    created = client.post("/api/vendors/", json={"company_info": sample_company_info}).json()
    vendor_id = created["id"]
    original_ref = created["reference_number"]

    # Update with additional contact info
    update_payload = {
        "company_info": {
            **sample_company_info,
            "trade_name": "Apex Global Innovations",
        },
        "contact_info": sample_contact_info,
    }

    response = client.put(f"/api/vendors/{vendor_id}", json=update_payload)
    assert response.status_code == 200

    data = response.json()
    assert data["reference_number"] == original_ref
    assert data["company_info"]["trade_name"] == "Apex Global Innovations"
    assert data["contact_info"]["primary"]["email"] == sample_contact_info["primary"]["email"]


# ---------------------------------------------------------------------------
# Test 5: Partially updating without losing sibling fields (PATCH)
# ---------------------------------------------------------------------------

def test_05_partial_update_nested_section_without_losing_other_sections(client, sample_company_info):
    """Scenario 5: PATCH /api/vendors/{id} updates only target fields without wiping siblings."""
    # Create with full company info
    created = client.post("/api/vendors/", json={"company_info": sample_company_info}).json()
    vendor_id = created["id"]

    # PATCH only the trade_name
    patch_payload = {
        "company_info": {
            "trade_name": "Apex SuperCloud"
        }
    }
    patch_resp = client.patch(f"/api/vendors/{vendor_id}", json=patch_payload)
    assert patch_resp.status_code == 200

    patched_data = patch_resp.json()
    # trade_name must be updated
    assert patched_data["company_info"]["trade_name"] == "Apex SuperCloud"
    # Sibling legal_company_name must NOT be wiped
    assert patched_data["company_info"]["legal_company_name"] == sample_company_info["legal_company_name"]
    # Sibling registered address must still be intact
    assert patched_data["company_info"]["registered_address"]["city"] == "Bengaluru"


# ---------------------------------------------------------------------------
# Test 6: Updating with an invalid vendor ID
# ---------------------------------------------------------------------------

def test_06_update_invalid_vendor_id(client):
    """Scenario 6: Endpoints return 400 Bad Request when vendor_id is not a valid ObjectId."""
    invalid_id = "invalid-not-an-object-id"

    # GET
    assert client.get(f"/api/vendors/{invalid_id}").status_code == 400
    # PUT
    assert client.put(f"/api/vendors/{invalid_id}", json={}).status_code == 400
    # PATCH
    assert client.patch(f"/api/vendors/{invalid_id}", json={}).status_code == 400
    # POST submit
    assert client.post(f"/api/vendors/{invalid_id}/submit").status_code == 400


# ---------------------------------------------------------------------------
# Test 7: Submitting a complete vendor registration
# ---------------------------------------------------------------------------

def test_07_submit_complete_vendor_registration(
    client,
    sample_company_info,
    sample_contact_info,
    sample_tax_details,
    sample_banking_details,
    sample_documents,
    sample_declarations,
):
    """Scenario 7: POST /api/vendors/{id}/submit successfully transitions complete vendor to 'submitted'."""
    complete_payload = {
        "company_info": sample_company_info,
        "contact_info": sample_contact_info,
        "tax_details": sample_tax_details,
        "banking_details": sample_banking_details,
        "documents": sample_documents,
        "declarations": sample_declarations,
    }

    # Create vendor with all sections filled
    created = client.post("/api/vendors/", json=complete_payload).json()
    vendor_id = created["id"]
    assert created["status"] == VendorStatus.DRAFT.value

    # Submit
    submit_resp = client.post(f"/api/vendors/{vendor_id}/submit")
    assert submit_resp.status_code == 200

    submit_data = submit_resp.json()
    assert submit_data["status"] == VendorStatus.SUBMITTED.value
    assert submit_data["vendor_id"] == vendor_id
    assert "submitted_at" in submit_data

    # Check status endpoint confirms submission
    status_resp = client.get(f"/api/vendors/{vendor_id}/status")
    assert status_resp.json()["status"] == VendorStatus.SUBMITTED.value


# ---------------------------------------------------------------------------
# Test 8: Rejecting an incomplete registration
# ---------------------------------------------------------------------------

def test_08_reject_incomplete_registration(client, sample_company_info):
    """Scenario 8: Submitting an incomplete draft returns 400 with missing field details."""
    # Create draft with only company info (missing contact, tax, banking, declarations)
    created = client.post(
        "/api/vendors/",
        json={"company_info": sample_company_info},
    ).json()
    vendor_id = created["id"]

    # Attempt submit
    response = client.post(f"/api/vendors/{vendor_id}/submit")
    assert response.status_code == 400

    err_detail = response.json()["detail"]
    assert "missing or invalid" in err_detail["message"].lower()
    assert len(err_detail["missing_fields"]) > 0

    # Ensure status remained draft
    status_check = client.get(f"/api/vendors/{vendor_id}/status").json()
    assert status_check["status"] == VendorStatus.DRAFT.value


# ---------------------------------------------------------------------------
# Test 9: Checking vendor onboarding status
# ---------------------------------------------------------------------------

def test_09_check_vendor_onboarding_status(client, sample_company_info):
    """Scenario 9: GET /api/vendors/{id}/status returns current onboarding status."""
    created = client.post(
        "/api/vendors/",
        json={"company_info": sample_company_info},
    ).json()
    vendor_id = created["id"]

    response = client.get(f"/api/vendors/{vendor_id}/status")
    assert response.status_code == 200

    status_data = response.json()
    assert status_data["vendor_id"] == vendor_id
    assert status_data["reference_number"] == created["reference_number"]
    assert status_data["status"] == VendorStatus.DRAFT.value
    assert status_data["submitted_at"] is None
    assert "updated_at" in status_data


# ---------------------------------------------------------------------------
# Test 10: Handling duplicate registrations (HTTP 409 Conflict)
# ---------------------------------------------------------------------------

def test_10_handle_duplicate_registrations(client, sample_company_info, sample_tax_details):
    """Scenario 10: Registering another vendor with the same PAN raises HTTP 409 Conflict."""
    first_payload = {
        "company_info": sample_company_info,
        "tax_details": sample_tax_details,
    }

    # Register first vendor
    resp1 = client.post("/api/vendors/", json=first_payload)
    assert resp1.status_code == 201

    # Attempt to register second vendor with the same PAN
    second_payload = {
        "company_info": {
            **sample_company_info,
            "legal_company_name": "Clone Technologies Ltd",
        },
        "tax_details": sample_tax_details,  # Same PAN
    }

    resp2 = client.post("/api/vendors/", json=second_payload)
    assert resp2.status_code == 409
    assert "already exists" in resp2.json()["detail"].lower()
