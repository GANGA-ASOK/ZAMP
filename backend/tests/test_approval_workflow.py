"""
Phase 9: Comprehensive Approval Workflow and Vendor Communication Tests.

Covers all 16 required verification points:
 1. Admin can retrieve all applications.
 2. Admin can filter applications by status.
 3. Admin can retrieve a specific application.
 4. Admin can approve an application.
 5. Admin cannot approve an invalid application state.
 6. Admin cannot reject without a reason.
 7. Admin can request clarification.
 8. Vendor can retrieve clarification requests.
 9. Vendor can respond to clarification.
10. Vendor can resubmit corrected information.
11. Resubmitted applications return to Under Review.
12. Application history is persisted.
13. Notifications are created correctly.
14. Notifications can be marked as read.
15. Vendor isolation (one vendor cannot retrieve another vendor's notifications/clarifications).
16. Existing document upload and verification continue working.
"""

from __future__ import annotations

import io
import mongomock
import pytest
from bson import ObjectId

from src.models.enums import (
    ActivityEventType,
    ActorType,
    ClarificationStatus,
    NotificationRecipientType,
    NotificationType,
    VendorStatus,
)
from src.services.document_service import DocumentService
from src.services.vendor_service import VendorService
from src.services.workflow_service import (
    InvalidStatusTransitionError,
    WorkflowService,
)


@pytest.fixture
def mock_db():
    client = mongomock.MongoClient()
    return client["zamp_test"]


@pytest.fixture
def workflow_svc(mock_db):
    return WorkflowService(db=mock_db)


@pytest.fixture
def vendor_svc(mock_db):
    return VendorService(db=mock_db)


@pytest.fixture
def doc_svc(mock_db):
    # Patch doc_svc to use mock_db
    svc = DocumentService()
    svc._db = mock_db
    return svc


def _create_sample_vendor(mock_db, status=VendorStatus.SUBMITTED.value, legal_name="Acme Corp"):
    doc = {
        "reference_number": f"VND-2026-{ObjectId()}",
        "status": status,
        "company_info": {
            "legal_company_name": legal_name,
            "business_entity_type": "Private Limited Company",
        },
        "contact_info": {
            "primary": {
                "first_name": "John",
                "last_name": "Doe",
                "email": "john@acme.com",
            }
        },
        "tax_details": {
            "pan_number": "ABCDE1234F",
            "gstin": "29ABCDE1234F1Z5",
        },
        "banking_details": {
            "account_number": "1234567890",
            "ifsc_code": "HDFC0001234",
        },
        "documents": [],
    }
    res = mock_db["vendors"].insert_one(doc)
    return str(res.inserted_id)


# ---------------------------------------------------------------------------
# Test Cases
# ---------------------------------------------------------------------------

def test_01_admin_can_retrieve_all_applications(mock_db, workflow_svc):
    """1. Admin can retrieve all applications."""
    _create_sample_vendor(mock_db, VendorStatus.SUBMITTED.value, "Company A")
    _create_sample_vendor(mock_db, VendorStatus.UNDER_REVIEW.value, "Company B")

    result = workflow_svc.list_applications()
    assert result["total"] == 2
    assert len(result["items"]) == 2
    assert result["status_counts"]["all"] == 2


def test_02_admin_can_filter_applications_by_status(mock_db, workflow_svc):
    """2. Admin can filter applications by status."""
    id1 = _create_sample_vendor(mock_db, VendorStatus.SUBMITTED.value, "Sub Corp")
    id2 = _create_sample_vendor(mock_db, VendorStatus.APPROVED.value, "App Corp")
    id3 = _create_sample_vendor(mock_db, VendorStatus.CLARIFICATION_REQUIRED.value, "Clar Corp")

    sub_res = workflow_svc.list_applications(status="submitted")
    assert sub_res["total"] == 1
    assert sub_res["items"][0]["company_name"] == "Sub Corp"

    app_res = workflow_svc.list_applications(status="approved")
    assert app_res["total"] == 1
    assert app_res["items"][0]["company_name"] == "App Corp"


def test_03_admin_can_retrieve_specific_application(mock_db, workflow_svc):
    """3. Admin can retrieve a specific application and search by company name."""
    vid = _create_sample_vendor(mock_db, VendorStatus.UNDER_REVIEW.value, "Specific Vendor Ltd")

    search_res = workflow_svc.list_applications(search="Specific Vendor")
    assert search_res["total"] == 1
    assert search_res["items"][0]["id"] == vid


def test_04_admin_can_approve_application(mock_db, workflow_svc):
    """4. Admin can approve an application."""
    vid = _create_sample_vendor(mock_db, VendorStatus.UNDER_REVIEW.value, "Approvable Corp")

    res = workflow_svc.approve_application(vid, comment="All documents look consistent.", actor_name="Compliance Admin")
    assert res["status"] == VendorStatus.APPROVED.value
    assert res["approved_at"] is not None

    # Check MongoDB record
    updated = mock_db["vendors"].find_one({"_id": ObjectId(vid)})
    assert updated["status"] == VendorStatus.APPROVED.value
    assert updated["review_notes"] == "All documents look consistent."


def test_05_admin_cannot_approve_invalid_application_state(mock_db, workflow_svc):
    """5. Admin cannot approve an invalid application state (e.g. Draft)."""
    vid = _create_sample_vendor(mock_db, VendorStatus.DRAFT.value, "Draft Corp")

    with pytest.raises(InvalidStatusTransitionError):
        workflow_svc.approve_application(vid)

    # Status must remain draft
    doc = mock_db["vendors"].find_one({"_id": ObjectId(vid)})
    assert doc["status"] == VendorStatus.DRAFT.value


def test_06_admin_cannot_reject_without_reason(mock_db, workflow_svc):
    """6. Admin cannot reject without a reason."""
    vid = _create_sample_vendor(mock_db, VendorStatus.UNDER_REVIEW.value, "Reject Corp")

    with pytest.raises(ValueError):
        workflow_svc.reject_application(vid, rejection_reason="")

    with pytest.raises(ValueError):
        workflow_svc.reject_application(vid, rejection_reason="   ")

    # Reject with valid reason succeeds
    res = workflow_svc.reject_application(vid, rejection_reason="PAN card format invalid and mismatched company.")
    assert res["status"] == VendorStatus.REJECTED.value
    assert res["rejection_reason"] == "PAN card format invalid and mismatched company."


def test_07_admin_can_request_clarification(mock_db, workflow_svc):
    """7. Admin can request clarification."""
    vid = _create_sample_vendor(mock_db, VendorStatus.UNDER_REVIEW.value, "Clarify Corp")

    clarif = workflow_svc.request_clarification(
        application_id=vid,
        clarification_message="GST certificate trade name does not match legal name.",
        related_document_name="GST Certificate",
        related_field="company_info.legal_name",
        admin_notes="Re-verify once updated",
    )
    assert clarif["id"] is not None
    assert clarif["status"] == ClarificationStatus.PENDING.value

    # Application status should be updated to clarification_required
    doc = mock_db["vendors"].find_one({"_id": ObjectId(vid)})
    assert doc["status"] == VendorStatus.CLARIFICATION_REQUIRED.value


def test_08_vendor_can_retrieve_clarification_requests(mock_db, workflow_svc):
    """8. Vendor can retrieve clarification requests."""
    vid = _create_sample_vendor(mock_db, VendorStatus.UNDER_REVIEW.value, "Clarify Corp")
    workflow_svc.request_clarification(vid, "Please upload clear bank proof.")

    clarifs = workflow_svc.get_clarifications(vid)
    assert len(clarifs) == 1
    assert clarifs[0]["clarification_message"] == "Please upload clear bank proof."
    assert clarifs[0]["status"] == ClarificationStatus.PENDING.value


def test_09_vendor_can_respond_to_clarification(mock_db, workflow_svc):
    """9. Vendor can respond to clarification."""
    vid = _create_sample_vendor(mock_db, VendorStatus.UNDER_REVIEW.value, "Clarify Corp")
    req = workflow_svc.request_clarification(vid, "Bank account number unclear.")

    res = workflow_svc.respond_to_clarification(
        vendor_id=vid,
        clarification_id=req["id"],
        vendor_response="Uploaded high resolution bank statement.",
        replaced_document_id="new_doc_123",
    )
    assert res["status"] == ClarificationStatus.RESOLVED.value
    assert res["vendor_response"] == "Uploaded high resolution bank statement."
    assert res["replaced_document_id"] == "new_doc_123"


def test_10_vendor_can_resubmit_corrected_information(mock_db, workflow_svc):
    """10. Vendor can resubmit corrected information."""
    vid = _create_sample_vendor(mock_db, VendorStatus.UNDER_REVIEW.value, "Clarify Corp")
    req = workflow_svc.request_clarification(vid, "Update details.")
    workflow_svc.respond_to_clarification(vid, req["id"], "Fixed everything.")

    res = workflow_svc.resubmit_application(vid, resubmission_notes="All documents corrected.")
    assert res["status"] == VendorStatus.RESUBMITTED.value

    doc = mock_db["vendors"].find_one({"_id": ObjectId(vid)})
    assert doc["status"] == VendorStatus.RESUBMITTED.value


def test_11_resubmitted_applications_return_to_under_review(mock_db, workflow_svc):
    """11. Resubmitted applications return to Under Review."""
    vid = _create_sample_vendor(mock_db, VendorStatus.RESUBMITTED.value, "Resubmitted Corp")

    res = workflow_svc.update_application_status(vid, VendorStatus.UNDER_REVIEW.value, notes="Starting re-audit.")
    assert res["status"] == VendorStatus.UNDER_REVIEW.value

    doc = mock_db["vendors"].find_one({"_id": ObjectId(vid)})
    assert doc["status"] == VendorStatus.UNDER_REVIEW.value


def test_12_application_history_is_persisted(mock_db, workflow_svc):
    """12. Application history is persisted."""
    vid = _create_sample_vendor(mock_db, VendorStatus.SUBMITTED.value, "History Corp")

    workflow_svc.log_activity(vid, vid, ActivityEventType.SUBMITTED.value, "Vendor submitted application", ActorType.VENDOR.value)
    workflow_svc.log_activity(vid, vid, ActivityEventType.UNDER_REVIEW.value, "Moved to Under Review", ActorType.ADMIN.value)
    workflow_svc.log_activity(vid, vid, ActivityEventType.APPROVED.value, "Approved by admin", ActorType.ADMIN.value)

    history = workflow_svc.get_activity_timeline(vid)
    assert len(history) == 3
    assert history[0]["event_type"] == ActivityEventType.SUBMITTED.value
    assert history[1]["event_type"] == ActivityEventType.UNDER_REVIEW.value
    assert history[2]["event_type"] == ActivityEventType.APPROVED.value


def test_13_notifications_are_created_correctly(mock_db, workflow_svc):
    """13. Notifications are created correctly."""
    vid = _create_sample_vendor(mock_db, VendorStatus.UNDER_REVIEW.value, "Notify Corp")

    # Approve generates vendor notification
    workflow_svc.approve_application(vid, "Approved!")

    notifs = workflow_svc.get_notifications(NotificationRecipientType.VENDOR.value, vendor_id=vid)
    assert notifs["total_count"] >= 1
    assert notifs["unread_count"] >= 1
    assert "approved" in notifs["items"][0]["title"].lower()


def test_14_notifications_can_be_marked_as_read(mock_db, workflow_svc):
    """14. Notifications can be marked as read."""
    vid = _create_sample_vendor(mock_db, VendorStatus.UNDER_REVIEW.value, "Read Corp")
    notif = workflow_svc.create_notification(
        recipient_type=NotificationRecipientType.VENDOR.value,
        title="Test Alert",
        message="Please check your status.",
        vendor_id=vid,
    )

    unread_before = workflow_svc.get_notifications(NotificationRecipientType.VENDOR.value, vendor_id=vid)["unread_count"]
    assert unread_before == 1

    success = workflow_svc.mark_notification_read(notif["id"])
    assert success is True

    unread_after = workflow_svc.get_notifications(NotificationRecipientType.VENDOR.value, vendor_id=vid)["unread_count"]
    assert unread_after == 0


def test_15_vendor_isolation(mock_db, workflow_svc):
    """15. One vendor cannot retrieve another vendor's notifications or clarification requests through vendor endpoints."""
    vid1 = _create_sample_vendor(mock_db, VendorStatus.UNDER_REVIEW.value, "Vendor 1")
    vid2 = _create_sample_vendor(mock_db, VendorStatus.UNDER_REVIEW.value, "Vendor 2")

    # Notification for Vendor 1
    workflow_svc.create_notification(
        recipient_type=NotificationRecipientType.VENDOR.value,
        title="For Vendor 1",
        message="Secret data 1",
        vendor_id=vid1,
    )

    # Clarification for Vendor 1
    req1 = workflow_svc.request_clarification(vid1, "Clarification for Vendor 1")

    # Vendor 2 querying notifications
    v2_notifs = workflow_svc.get_notifications(NotificationRecipientType.VENDOR.value, vendor_id=vid2)
    assert v2_notifs["total_count"] == 0

    # Vendor 2 cannot respond to Vendor 1's clarification
    with pytest.raises(Exception):
        workflow_svc.respond_to_clarification(
            vendor_id=vid2,
            clarification_id=req1["id"],
            vendor_response="Unauthorized response",
        )


def test_16_existing_document_upload_and_verification_continue_working(mock_db, doc_svc):
    """16. Existing document upload and verification APIs continue working."""
    vid = _create_sample_vendor(mock_db, VendorStatus.DRAFT.value, "Doc Corp")

    # Upload PDF
    pdf_bytes = b"%PDF-1.4 Minimal test pdf content \n%%EOF"
    upload_res = doc_svc.upload_document(
        vendor_id=vid,
        file_bytes=pdf_bytes,
        filename="pan_proof.pdf",
        category="pan_card",
    )

    assert upload_res["document_id"] is not None
    assert upload_res["verification_status"] == "uploaded"

    # Replace document
    replacement_pdf = b"%PDF-1.4 Corrected pan proof content \n%%EOF"
    replace_res = doc_svc.replace_document(
        vendor_id=vid,
        document_id=upload_res["document_id"],
        file_bytes=replacement_pdf,
        filename="pan_proof_v2.pdf",
    )
    assert replace_res["document_id"] is not None
    assert replace_res["document_id"] != upload_res["document_id"]

