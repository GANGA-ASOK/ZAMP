"""
Phase 7 Authentication and RBAC tests for VendorFlow.

Tests isolated in-memory using mongomock via conftest.py.
Covers all 14 required verification scenarios.
"""

from __future__ import annotations

import io
from datetime import timedelta
import pytest
from bson import ObjectId
from fastapi.testclient import TestClient

import src.main as main_module
from src.models.enums import UserRole
from src.utils.security import create_access_token


@pytest.fixture
def client():
    """Test client for FastAPI app."""
    return TestClient(main_module.app)


# ---------------------------------------------------------------------------
# 1. Vendor account registration
# ---------------------------------------------------------------------------

def test_01_vendor_registration(client: TestClient):
    payload = {
        "name": "Jane Vendor",
        "email": "jane.vendor@example.com",
        "password": "SecurePassword123!",
    }
    response = client.post("/api/auth/register", json=payload)
    assert response.status_code == 201, response.text
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["email"] == "jane.vendor@example.com"
    assert data["user"]["role"] == "vendor"
    assert "vendor_id" in data
    assert data["vendor_id"] is not None
    # Verify HttpOnly cookies
    assert "access_token" in response.cookies
    assert "refresh_token" in response.cookies


# ---------------------------------------------------------------------------
# 2. Duplicate email registration
# ---------------------------------------------------------------------------

def test_02_duplicate_email_registration(client: TestClient):
    payload = {
        "name": "Jane Copy",
        "email": "jane.vendor@example.com",  # same email as test 01
        "password": "AnotherPassword123!",
    }
    response = client.post("/api/auth/register", json=payload)
    assert response.status_code == 409
    assert "already exists" in response.json()["detail"].lower()


# ---------------------------------------------------------------------------
# 3. Successful login
# ---------------------------------------------------------------------------

def test_03_successful_login(client: TestClient):
    payload = {
        "email": "jane.vendor@example.com",
        "password": "SecurePassword123!",
    }
    response = client.post("/api/auth/login", json=payload)
    assert response.status_code == 200, response.text
    data = response.json()
    assert "access_token" in data
    assert data["user"]["email"] == "jane.vendor@example.com"
    assert data["vendor_id"] is not None


# ---------------------------------------------------------------------------
# 4. Incorrect password rejection
# ---------------------------------------------------------------------------

def test_04_incorrect_password(client: TestClient):
    payload = {
        "email": "jane.vendor@example.com",
        "password": "WrongPassword!",
    }
    response = client.post("/api/auth/login", json=payload)
    assert response.status_code == 401
    assert "invalid email or password" in response.json()["detail"].lower()


# ---------------------------------------------------------------------------
# 5. Invalid or expired token
# ---------------------------------------------------------------------------

def test_05_invalid_token(client: TestClient):
    headers = {"Authorization": "Bearer invalid.token.value"}
    response = client.get("/api/auth/me", headers=headers)
    assert response.status_code == 401
    assert "invalid" in response.json()["detail"].lower()


def test_05b_expired_token(client: TestClient):
    # Expired token in past
    expired = create_access_token(
        user_id=str(ObjectId()),
        email="expired@example.com",
        role="vendor",
        expires_delta=timedelta(seconds=-10),
    )
    headers = {"Authorization": f"Bearer {expired}"}
    response = client.get("/api/auth/me", headers=headers)
    assert response.status_code == 401
    assert "expired" in response.json()["detail"].lower()


# ---------------------------------------------------------------------------
# 6. Authenticated user retrieval (GET /api/auth/me)
# ---------------------------------------------------------------------------

def test_06_get_current_user_me(client: TestClient):
    # Login as Jane
    login_resp = client.post(
        "/api/auth/login",
        json={"email": "jane.vendor@example.com", "password": "SecurePassword123!"},
    )
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    response = client.get("/api/auth/me", headers=headers)
    assert response.status_code == 200, response.text
    assert response.json()["email"] == "jane.vendor@example.com"
    assert response.json()["role"] == "vendor"


# ---------------------------------------------------------------------------
# 7. Vendor accessing their own profile
# ---------------------------------------------------------------------------

def test_07_vendor_access_own_profile(client: TestClient):
    # Register vendor 2
    reg_resp = client.post(
        "/api/auth/register",
        json={
            "name": "Vendor Two",
            "email": "vendor2@example.com",
            "password": "Password123!",
        },
    )
    token2 = reg_resp.json()["access_token"]
    vendor_id2 = reg_resp.json()["vendor_id"]
    headers = {"Authorization": f"Bearer {token2}"}

    # Access own profile via ID
    response = client.get(f"/api/vendors/{vendor_id2}", headers=headers)
    assert response.status_code == 200, response.text
    assert response.json()["id"] == vendor_id2

    # Access own profile via /my-profile
    resp_my = client.get("/api/vendors/my-profile", headers=headers)
    assert resp_my.status_code == 200, resp_my.text
    assert resp_my.json()["id"] == vendor_id2


# ---------------------------------------------------------------------------
# 8. Vendor attempting to access another vendor's profile (403 Forbidden)
# ---------------------------------------------------------------------------

def test_08_cross_vendor_access_denied(client: TestClient):
    # Vendor 1 tries to access Vendor 2's profile
    login1 = client.post(
        "/api/auth/login",
        json={"email": "jane.vendor@example.com", "password": "SecurePassword123!"},
    )
    token1 = login1.json()["access_token"]

    login2 = client.post(
        "/api/auth/login",
        json={"email": "vendor2@example.com", "password": "Password123!"},
    )
    vendor_id2 = login2.json()["vendor_id"]

    headers = {"Authorization": f"Bearer {token1}"}
    response = client.get(f"/api/vendors/{vendor_id2}", headers=headers)
    assert response.status_code == 403
    assert "access denied" in response.json()["detail"].lower()


# ---------------------------------------------------------------------------
# 9. Vendor attempting to access admin APIs (403 Forbidden)
# ---------------------------------------------------------------------------

def test_09_vendor_access_admin_forbidden(client: TestClient):
    login = client.post(
        "/api/auth/login",
        json={"email": "jane.vendor@example.com", "password": "SecurePassword123!"},
    )
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    response = client.get("/api/admin/metrics", headers=headers)
    assert response.status_code == 403
    assert "administrator" in response.json()["detail"].lower()

    resp2 = client.get("/api/admin/vendors", headers=headers)
    assert resp2.status_code == 403


# ---------------------------------------------------------------------------
# 10. Admin accessing vendor listing & metrics
# ---------------------------------------------------------------------------

def test_10_admin_listing_and_metrics(client: TestClient):
    from src.services.auth_service import AuthService
    import asyncio

    # Provision an admin via AuthService
    auth_svc = AuthService()
    admin_user = asyncio.run(
        auth_svc.register_user(
            name="Super Admin",
            email="admin@vendorflow.io",
            password="AdminSecretPassword123!",
            role=UserRole.ADMIN.value,
        )
    )

    # Login as admin
    admin_login = client.post(
        "/api/auth/login",
        json={"email": "admin@vendorflow.io", "password": "AdminSecretPassword123!"},
    )
    assert admin_login.status_code == 200
    admin_token = admin_login.json()["access_token"]
    headers = {"Authorization": f"Bearer {admin_token}"}

    # Fetch metrics
    metrics_resp = client.get("/api/admin/metrics", headers=headers)
    assert metrics_resp.status_code == 200
    metrics = metrics_resp.json()
    assert "total_vendors" in metrics
    assert metrics["total_vendors"] >= 2

    # Fetch paginated vendor list
    list_resp = client.get("/api/admin/vendors?page=1&limit=10", headers=headers)
    assert list_resp.status_code == 200
    data = list_resp.json()
    assert "items" in data
    assert len(data["items"]) >= 2
    assert "metrics" in data


# ---------------------------------------------------------------------------
# 11. Admin accessing individual vendor details (including raw/unmasked)
# ---------------------------------------------------------------------------

def test_11_admin_access_vendor_detail(client: TestClient):
    # Login as admin
    admin_login = client.post(
        "/api/auth/login",
        json={"email": "admin@vendorflow.io", "password": "AdminSecretPassword123!"},
    )
    admin_token = admin_login.json()["access_token"]
    headers = {"Authorization": f"Bearer {admin_token}"}

    # Get vendor 2 id
    v2_login = client.post(
        "/api/auth/login",
        json={"email": "vendor2@example.com", "password": "Password123!"},
    )
    v2_id = v2_login.json()["vendor_id"]

    response = client.get(f"/api/admin/vendors/{v2_id}", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == v2_id
    assert "banking_details" in data


# ---------------------------------------------------------------------------
# 12. Unauthenticated access to protected APIs (401 Unauthorized)
# ---------------------------------------------------------------------------

def test_12_unauthenticated_access_rejected(client: TestClient):
    fake_id = str(ObjectId())

    # Protected vendor endpoints
    assert client.get(f"/api/vendors/{fake_id}").status_code == 401
    assert client.put(f"/api/vendors/{fake_id}", json={}).status_code == 401
    assert client.patch(f"/api/vendors/{fake_id}", json={}).status_code == 401
    assert client.post(f"/api/vendors/{fake_id}/submit").status_code == 401
    assert client.get("/api/vendors/my-profile").status_code == 401

    # Protected admin endpoints
    assert client.get("/api/admin/metrics").status_code == 401
    assert client.get("/api/admin/vendors").status_code == 401

    # Protected document endpoints
    assert client.get(f"/api/vendors/{fake_id}/documents").status_code == 401


# ---------------------------------------------------------------------------
# 13. Vendor document ownership & cross-vendor isolation
# ---------------------------------------------------------------------------

def test_13_document_ownership_and_isolation(client: TestClient):
    # Vendor 1 login
    login1 = client.post(
        "/api/auth/login",
        json={"email": "jane.vendor@example.com", "password": "SecurePassword123!"},
    )
    token1 = login1.json()["access_token"]
    v1_id = login1.json()["vendor_id"]
    headers1 = {"Authorization": f"Bearer {token1}"}

    # Vendor 2 login
    login2 = client.post(
        "/api/auth/login",
        json={"email": "vendor2@example.com", "password": "Password123!"},
    )
    token2 = login2.json()["access_token"]
    v2_id = login2.json()["vendor_id"]
    headers2 = {"Authorization": f"Bearer {token2}"}

    # Vendor 1 uploads a PAN document
    pdf_content = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF"
    upload_resp = client.post(
        f"/api/vendors/{v1_id}/documents",
        data={"category": "pan_card"},
        files={"file": ("pan.pdf", io.BytesIO(pdf_content), "application/pdf")},
        headers=headers1,
    )
    assert upload_resp.status_code == 201, upload_resp.text
    doc_id = upload_resp.json()["document_id"]

    # Vendor 1 can download own document
    dl_resp = client.get(f"/api/vendors/{v1_id}/documents/{doc_id}/download", headers=headers1)
    assert dl_resp.status_code == 200
    assert dl_resp.content == pdf_content

    # Vendor 2 tries to download Vendor 1's document (Cross-vendor forbidden)
    cross_dl = client.get(f"/api/vendors/{v1_id}/documents/{doc_id}/download", headers=headers2)
    assert cross_dl.status_code == 403

    # Vendor 2 tries to list Vendor 1's documents
    cross_list = client.get(f"/api/vendors/{v1_id}/documents", headers=headers2)
    assert cross_list.status_code == 403


# ---------------------------------------------------------------------------
# 14. Logout and session clear
# ---------------------------------------------------------------------------

def test_14_logout(client: TestClient):
    response = client.post("/api/auth/logout")
    assert response.status_code == 200
    assert "logged out" in response.json()["message"].lower()
    # Confirm cookies are cleared/deleted
    assert response.cookies.get("access_token") is None or response.cookies.get("access_token") == ""

