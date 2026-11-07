"""
Workflow, Approval, Clarification, Notification, and Activity History Service for Phase 9.
"""

from __future__ import annotations

import logging
import math
from datetime import datetime, timezone
from typing import Any

from bson import ObjectId
from pymongo import ASCENDING, DESCENDING
from pymongo.collection import Collection
from pymongo.database import Database

import src.database.mongodb as mongo_module
from src.models.enums import (
    ActivityEventType,
    ActorType,
    ClarificationStatus,
    NotificationRecipientType,
    NotificationType,
    VendorStatus,
)
from src.models.workflow import (
    AdminCommentModel,
    ApplicationHistoryModel,
    ClarificationRequestModel,
    NotificationModel,
)
from src.services.vendor_service import InvalidVendorIdError, VendorNotFoundError

logger = logging.getLogger(__name__)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _validate_object_id(id_str: str) -> ObjectId:
    if not isinstance(id_str, str) or not ObjectId.is_valid(id_str):
        raise InvalidVendorIdError(str(id_str))
    return ObjectId(id_str)


# ---------------------------------------------------------------------------
# Status Transition Rules
# ---------------------------------------------------------------------------

VALID_TRANSITIONS: dict[str, set[str]] = {
    VendorStatus.DRAFT.value: {
        VendorStatus.SUBMITTED.value,
    },
    VendorStatus.SUBMITTED.value: {
        VendorStatus.UNDER_REVIEW.value,
        VendorStatus.APPROVED.value,
        VendorStatus.REJECTED.value,
        VendorStatus.CLARIFICATION_REQUIRED.value,
    },
    VendorStatus.UNDER_REVIEW.value: {
        VendorStatus.APPROVED.value,
        VendorStatus.REJECTED.value,
        VendorStatus.CLARIFICATION_REQUIRED.value,
    },
    VendorStatus.CLARIFICATION_REQUIRED.value: {
        VendorStatus.RESUBMITTED.value,
    },
    VendorStatus.RESUBMITTED.value: {
        VendorStatus.UNDER_REVIEW.value,
        VendorStatus.APPROVED.value,
        VendorStatus.REJECTED.value,
        VendorStatus.CLARIFICATION_REQUIRED.value,
    },
    VendorStatus.APPROVED.value: set(),  # Terminal state
    VendorStatus.REJECTED.value: set(),  # Terminal state
}


class InvalidStatusTransitionError(Exception):
    """Raised when an illegal status change is attempted."""
    def __init__(self, current_status: str, target_status: str):
        super().__init__(
            f"Cannot transition application from '{current_status}' to '{target_status}'."
        )
        self.current_status = current_status
        self.target_status = target_status


class WorkflowService:
    """Service handling Phase 9 approval workflows, notifications, history, and clarifications."""

    def __init__(self, db: Database | None = None):
        self._db = db

    @property
    def db(self) -> Database:
        if self._db is not None:
            return self._db
        if mongo_module.db is not None:
            return mongo_module.db
        raise RuntimeError("Database not initialized. Please ensure connect_to_mongodb() has been called.")

    @property
    def vendors_col(self) -> Collection:
        return self.db["vendors"]

    @property
    def history_col(self) -> Collection:
        return self.db["application_history"]

    @property
    def clarifications_col(self) -> Collection:
        return self.db["clarification_requests"]

    @property
    def notifications_col(self) -> Collection:
        return self.db["notifications"]

    @property
    def comments_col(self) -> Collection:
        return self.db["admin_comments"]

    @property
    def verification_col(self) -> Collection:
        return self.db["verification_results"]

    def ensure_indexes(self) -> None:
        """Create indexes on workflow collections."""
        try:
            self.history_col.create_index([("application_id", ASCENDING), ("timestamp", ASCENDING)])
            self.history_col.create_index("vendor_id")
            self.clarifications_col.create_index([("application_id", ASCENDING), ("created_at", DESCENDING)])
            self.clarifications_col.create_index("vendor_id")
            self.clarifications_col.create_index("status")
            self.notifications_col.create_index([("recipient_type", ASCENDING), ("created_at", DESCENDING)])
            self.notifications_col.create_index([("vendor_id", ASCENDING), ("is_read", ASCENDING)])
            self.comments_col.create_index([("application_id", ASCENDING), ("created_at", ASCENDING)])
            logger.info("Workflow database indexes ensured.")
        except Exception as exc:
            logger.warning("Could not create workflow indexes: %s", exc)

    # -----------------------------------------------------------------------
    # Activity Timeline Logging
    # -----------------------------------------------------------------------

    def log_activity(
        self,
        application_id: str,
        vendor_id: str,
        event_type: str,
        description: str,
        actor_type: str = ActorType.SYSTEM.value,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Record an immutable event in the application history timeline."""
        now = _utcnow()
        doc = ApplicationHistoryModel(
            application_id=str(application_id),
            vendor_id=str(vendor_id),
            event_type=event_type,
            description=description,
            actor_type=actor_type,
            metadata=metadata or {},
            timestamp=now,
        ).to_dict()

        res = self.history_col.insert_one(doc)
        doc["id"] = str(res.inserted_id)
        if "_id" in doc:
            del doc["_id"]
        return doc

    def get_activity_timeline(self, application_id: str) -> list[dict[str, Any]]:
        """Retrieve chronological history for an application."""
        cursor = self.history_col.find(
            {"$or": [{"application_id": application_id}, {"vendor_id": application_id}]}
        ).sort("timestamp", ASCENDING)

        events: list[dict[str, Any]] = []
        for doc in cursor:
            doc["id"] = str(doc.pop("_id"))
            events.append(doc)
        return events

    # -----------------------------------------------------------------------
    # Notifications System
    # -----------------------------------------------------------------------

    def create_notification(
        self,
        recipient_type: str,
        title: str,
        message: str,
        notification_type: str = NotificationType.INFO.value,
        vendor_id: str | None = None,
        application_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Create an in-app notification for vendor or admin."""
        now = _utcnow()
        notif = NotificationModel(
            recipient_type=recipient_type,
            title=title,
            message=message,
            notification_type=notification_type,
            vendor_id=vendor_id,
            application_id=application_id,
            is_read=False,
            metadata=metadata or {},
            created_at=now,
        ).to_dict()

        res = self.notifications_col.insert_one(notif)
        notif["id"] = str(res.inserted_id)
        if "_id" in notif:
            del notif["_id"]
        return notif

    def get_notifications(
        self,
        recipient_type: str,
        vendor_id: str | None = None,
        limit: int = 50,
    ) -> dict[str, Any]:
        """Retrieve notifications and unread count."""
        query: dict[str, Any] = {"recipient_type": recipient_type}
        if recipient_type == NotificationRecipientType.VENDOR.value:
            if vendor_id:
                query["vendor_id"] = str(vendor_id)
        elif recipient_type == NotificationRecipientType.ADMIN.value:
            # Admins see global admin notifications
            pass

        total_count = self.notifications_col.count_documents(query)
        unread_count = self.notifications_col.count_documents({**query, "is_read": False})

        cursor = self.notifications_col.find(query).sort("created_at", DESCENDING).limit(limit)
        items: list[dict[str, Any]] = []
        for doc in cursor:
            doc["id"] = str(doc.pop("_id"))
            items.append(doc)

        return {
            "items": items,
            "unread_count": unread_count,
            "total_count": total_count,
        }

    def mark_notification_read(self, notification_id: str) -> bool:
        """Mark a single notification as read."""
        oid = _validate_object_id(notification_id)
        res = self.notifications_col.update_one({"_id": oid}, {"$set": {"is_read": True}})
        return res.modified_count > 0

    def mark_all_notifications_read(
        self,
        recipient_type: str,
        vendor_id: str | None = None,
    ) -> int:
        """Mark all notifications as read for a given recipient."""
        query: dict[str, Any] = {"recipient_type": recipient_type, "is_read": False}
        if recipient_type == NotificationRecipientType.VENDOR.value and vendor_id:
            query["vendor_id"] = str(vendor_id)

        res = self.notifications_col.update_many(query, {"$set": {"is_read": True}})
        return res.modified_count

    # -----------------------------------------------------------------------
    # Clarification Management
    # -----------------------------------------------------------------------

    def request_clarification(
        self,
        application_id: str,
        clarification_message: str,
        related_document_id: str | None = None,
        related_document_name: str | None = None,
        related_field: str | None = None,
        admin_notes: str | None = None,
    ) -> dict[str, Any]:
        """
        Admin creates a clarification request.
        Transitions application status to 'clarification_required'.
        Logs activity and creates vendor notification.
        """
        oid = _validate_object_id(application_id)
        vendor_doc = self.vendors_col.find_one({"_id": oid})
        if not vendor_doc:
            raise VendorNotFoundError(application_id)

        current_status = vendor_doc.get("status", VendorStatus.DRAFT.value)
        # Check transition validity
        if current_status not in (
            VendorStatus.SUBMITTED.value,
            VendorStatus.UNDER_REVIEW.value,
            VendorStatus.RESUBMITTED.value,
        ):
            raise InvalidStatusTransitionError(current_status, VendorStatus.CLARIFICATION_REQUIRED.value)

        now = _utcnow()
        req_doc = ClarificationRequestModel(
            application_id=str(oid),
            vendor_id=str(oid),
            clarification_message=clarification_message,
            related_document_id=related_document_id,
            related_document_name=related_document_name,
            related_field=related_field,
            admin_notes=admin_notes,
            status=ClarificationStatus.PENDING.value,
            created_at=now,
        ).to_dict()

        res = self.clarifications_col.insert_one(req_doc)
        clarification_id = str(res.inserted_id)
        req_doc["id"] = clarification_id
        if "_id" in req_doc:
            del req_doc["_id"]

        # Update vendor application status
        self.vendors_col.update_one(
            {"_id": oid},
            {
                "$set": {
                    "status": VendorStatus.CLARIFICATION_REQUIRED.value,
                    "updated_at": now,
                },
                "$push": {"clarification_requests": clarification_id},
            },
        )

        # Log activity history
        desc = f"Admin requested clarification: {clarification_message}"
        if related_document_name:
            desc += f" (Document: {related_document_name})"
        elif related_field:
            desc += f" (Field: {related_field})"

        self.log_activity(
            application_id=str(oid),
            vendor_id=str(oid),
            event_type=ActivityEventType.CLARIFICATION_REQUESTED.value,
            description=desc,
            actor_type=ActorType.ADMIN.value,
            metadata={
                "clarification_id": clarification_id,
                "related_document_id": related_document_id,
                "related_field": related_field,
            },
        )

        # Vendor Notification
        company_name = vendor_doc.get("company_info", {}).get("legal_company_name", "Vendor")
        self.create_notification(
            recipient_type=NotificationRecipientType.VENDOR.value,
            title="Clarification Required",
            message=f"An administrator has requested additional clarification or corrected documents: {clarification_message}",
            notification_type=NotificationType.CLARIFICATION.value,
            vendor_id=str(oid),
            application_id=str(oid),
            metadata={"clarification_id": clarification_id},
        )

        return req_doc

    def get_clarifications(self, application_id: str) -> list[dict[str, Any]]:
        """Retrieve all clarification requests for an application."""
        cursor = self.clarifications_col.find(
            {"$or": [{"application_id": application_id}, {"vendor_id": application_id}]}
        ).sort("created_at", DESCENDING)

        items: list[dict[str, Any]] = []
        for doc in cursor:
            doc["id"] = str(doc.pop("_id"))
            items.append(doc)
        return items

    def respond_to_clarification(
        self,
        vendor_id: str,
        clarification_id: str,
        vendor_response: str,
        replaced_document_id: str | None = None,
        updated_fields: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Vendor submits their answer to a specific clarification request."""
        c_oid = _validate_object_id(clarification_id)
        v_oid = _validate_object_id(vendor_id)

        req = self.clarifications_col.find_one({"_id": c_oid, "vendor_id": str(v_oid)})
        if not req:
            raise VendorNotFoundError(f"Clarification '{clarification_id}' not found for vendor '{vendor_id}'.")

        now = _utcnow()
        update_fields: dict[str, Any] = {
            "vendor_response": vendor_response,
            "status": ClarificationStatus.RESOLVED.value,
            "resolved_at": now,
        }
        if replaced_document_id:
            update_fields["replaced_document_id"] = replaced_document_id

        self.clarifications_col.update_one({"_id": c_oid}, {"$set": update_fields})

        # Log Activity
        self.log_activity(
            application_id=str(v_oid),
            vendor_id=str(v_oid),
            event_type=ActivityEventType.CLARIFICATION_RESPONDED.value,
            description=f"Vendor responded to clarification: {vendor_response}",
            actor_type=ActorType.VENDOR.value,
            metadata={
                "clarification_id": clarification_id,
                "replaced_document_id": replaced_document_id,
            },
        )

        # Notify Admin
        vendor_doc = self.vendors_col.find_one({"_id": v_oid}) or {}
        comp_name = vendor_doc.get("company_info", {}).get("legal_company_name", "Vendor")
        ref_num = vendor_doc.get("reference_number", "")

        self.create_notification(
            recipient_type=NotificationRecipientType.ADMIN.value,
            title="Clarification Response Received",
            message=f"{comp_name} ({ref_num}) responded to clarification request: {vendor_response}",
            notification_type=NotificationType.CLARIFICATION.value,
            vendor_id=str(v_oid),
            application_id=str(v_oid),
            metadata={"clarification_id": clarification_id},
        )

        updated_req = self.clarifications_col.find_one({"_id": c_oid})
        updated_req["id"] = str(updated_req.pop("_id"))
        return updated_req

    def resubmit_application(
        self,
        vendor_id: str,
        resubmission_notes: str | None = None,
    ) -> dict[str, Any]:
        """
        Vendor resubmits their corrected application.
        Transitions status from 'clarification_required' to 'resubmitted'.
        Logs activity and notifies admin.
        """
        oid = _validate_object_id(vendor_id)
        vendor_doc = self.vendors_col.find_one({"_id": oid})
        if not vendor_doc:
            raise VendorNotFoundError(vendor_id)

        curr_status = vendor_doc.get("status", VendorStatus.DRAFT.value)
        if curr_status != VendorStatus.CLARIFICATION_REQUIRED.value:
            raise InvalidStatusTransitionError(curr_status, VendorStatus.RESUBMITTED.value)

        now = _utcnow()
        self.vendors_col.update_one(
            {"_id": oid},
            {
                "$set": {
                    "status": VendorStatus.RESUBMITTED.value,
                    "resubmitted_at": now,
                    "updated_at": now,
                }
            },
        )

        # Log Activity
        desc = "Vendor resubmitted application with requested corrections."
        if resubmission_notes:
            desc += f" Notes: {resubmission_notes}"

        self.log_activity(
            application_id=str(oid),
            vendor_id=str(oid),
            event_type=ActivityEventType.RESUBMITTED.value,
            description=desc,
            actor_type=ActorType.VENDOR.value,
            metadata={"resubmission_notes": resubmission_notes},
        )

        # Admin Notification
        comp_name = vendor_doc.get("company_info", {}).get("legal_company_name", "Vendor")
        ref_num = vendor_doc.get("reference_number", "")

        self.create_notification(
            recipient_type=NotificationRecipientType.ADMIN.value,
            title="Application Resubmitted",
            message=f"{comp_name} ({ref_num}) has resubmitted their application with corrections and is ready for review.",
            notification_type=NotificationType.RESUBMISSION.value,
            vendor_id=str(oid),
            application_id=str(oid),
        )

        return {
            "message": "Application resubmitted successfully. It is now queued for administrator review.",
            "vendor_id": str(oid),
            "status": VendorStatus.RESUBMITTED.value,
            "resubmitted_at": now,
        }

    # -----------------------------------------------------------------------
    # Approval and Rejection
    # -----------------------------------------------------------------------

    def approve_application(
        self,
        application_id: str,
        comment: str | None = None,
        actor_name: str = "Admin",
    ) -> dict[str, Any]:
        """
        Admin approves a vendor onboarding application.
        Transitions status to 'approved'.
        Persists decision timestamp, notes, activity history, and vendor notification.
        """
        oid = _validate_object_id(application_id)
        vendor_doc = self.vendors_col.find_one({"_id": oid})
        if not vendor_doc:
            raise VendorNotFoundError(application_id)

        curr_status = vendor_doc.get("status", VendorStatus.DRAFT.value)
        # Verify valid transition
        if curr_status not in (
            VendorStatus.SUBMITTED.value,
            VendorStatus.UNDER_REVIEW.value,
            VendorStatus.RESUBMITTED.value,
        ):
            raise InvalidStatusTransitionError(curr_status, VendorStatus.APPROVED.value)

        now = _utcnow()
        update_doc: dict[str, Any] = {
            "status": VendorStatus.APPROVED.value,
            "approved_at": now,
            "reviewed_at": now,
            "updated_at": now,
        }
        if comment:
            update_doc["review_notes"] = comment

        self.vendors_col.update_one({"_id": oid}, {"$set": update_doc})

        # Activity History
        desc = "Application was officially approved by administrator."
        if comment:
            desc += f" Remark: {comment}"

        self.log_activity(
            application_id=str(oid),
            vendor_id=str(oid),
            event_type=ActivityEventType.APPROVED.value,
            description=desc,
            actor_type=ActorType.ADMIN.value,
            metadata={"comment": comment, "actor_name": actor_name},
        )

        # Vendor Notification
        ref_num = vendor_doc.get("reference_number", "")
        self.create_notification(
            recipient_type=NotificationRecipientType.VENDOR.value,
            title="Application Approved",
            message=f"Congratulations! Your vendor onboarding application ({ref_num}) has been reviewed and approved.",
            notification_type=NotificationType.APPROVAL.value,
            vendor_id=str(oid),
            application_id=str(oid),
            metadata={"comment": comment},
        )

        return {
            "message": "Vendor application approved successfully.",
            "application_id": str(oid),
            "status": VendorStatus.APPROVED.value,
            "approved_at": now,
        }

    def reject_application(
        self,
        application_id: str,
        rejection_reason: str,
        actor_name: str = "Admin",
    ) -> dict[str, Any]:
        """
        Admin rejects a vendor application.
        Requires non-empty rejection reason.
        Does not delete vendor record or files.
        """
        if not rejection_reason or not rejection_reason.strip():
            raise ValueError("Rejection reason is mandatory and cannot be empty.")

        oid = _validate_object_id(application_id)
        vendor_doc = self.vendors_col.find_one({"_id": oid})
        if not vendor_doc:
            raise VendorNotFoundError(application_id)

        curr_status = vendor_doc.get("status", VendorStatus.DRAFT.value)
        if curr_status not in (
            VendorStatus.SUBMITTED.value,
            VendorStatus.UNDER_REVIEW.value,
            VendorStatus.RESUBMITTED.value,
            VendorStatus.CLARIFICATION_REQUIRED.value,
        ):
            raise InvalidStatusTransitionError(curr_status, VendorStatus.REJECTED.value)

        now = _utcnow()
        self.vendors_col.update_one(
            {"_id": oid},
            {
                "$set": {
                    "status": VendorStatus.REJECTED.value,
                    "rejection_reason": rejection_reason.strip(),
                    "rejected_at": now,
                    "reviewed_at": now,
                    "updated_at": now,
                }
            },
        )

        # Activity History
        self.log_activity(
            application_id=str(oid),
            vendor_id=str(oid),
            event_type=ActivityEventType.REJECTED.value,
            description=f"Application was rejected by administrator. Reason: {rejection_reason.strip()}",
            actor_type=ActorType.ADMIN.value,
            metadata={"rejection_reason": rejection_reason.strip(), "actor_name": actor_name},
        )

        # Vendor Notification
        ref_num = vendor_doc.get("reference_number", "")
        self.create_notification(
            recipient_type=NotificationRecipientType.VENDOR.value,
            title="Application Rejected",
            message=f"Your vendor onboarding application ({ref_num}) was rejected. Reason: {rejection_reason.strip()}",
            notification_type=NotificationType.REJECTION.value,
            vendor_id=str(oid),
            application_id=str(oid),
            metadata={"rejection_reason": rejection_reason.strip()},
        )

        return {
            "message": "Vendor application rejected.",
            "application_id": str(oid),
            "status": VendorStatus.REJECTED.value,
            "rejection_reason": rejection_reason.strip(),
            "rejected_at": now,
        }

    # -----------------------------------------------------------------------
    # Status Update (e.g. Move to Under Review)
    # -----------------------------------------------------------------------

    def update_application_status(
        self,
        application_id: str,
        target_status: str,
        notes: str | None = None,
        actor_name: str = "Admin",
    ) -> dict[str, Any]:
        """Update status with validation of allowed state transitions."""
        oid = _validate_object_id(application_id)
        vendor_doc = self.vendors_col.find_one({"_id": oid})
        if not vendor_doc:
            raise VendorNotFoundError(application_id)

        current_status = vendor_doc.get("status", VendorStatus.DRAFT.value)
        target_status_clean = target_status.lower().strip()

        # Validate transition
        allowed = VALID_TRANSITIONS.get(current_status, set())
        if target_status_clean not in allowed:
            raise InvalidStatusTransitionError(current_status, target_status_clean)

        now = _utcnow()
        update_fields: dict[str, Any] = {
            "status": target_status_clean,
            "updated_at": now,
        }
        if notes:
            update_fields["review_notes"] = notes

        self.vendors_col.update_one({"_id": oid}, {"$set": update_fields})

        # Activity Log
        desc = f"Application status changed from '{current_status}' to '{target_status_clean}'."
        if notes:
            desc += f" Note: {notes}"

        self.log_activity(
            application_id=str(oid),
            vendor_id=str(oid),
            event_type=target_status_clean,
            description=desc,
            actor_type=ActorType.ADMIN.value,
            metadata={"from_status": current_status, "to_status": target_status_clean, "notes": notes},
        )

        # Notify vendor if moved to Under Review
        if target_status_clean == VendorStatus.UNDER_REVIEW.value:
            ref_num = vendor_doc.get("reference_number", "")
            self.create_notification(
                recipient_type=NotificationRecipientType.VENDOR.value,
                title="Application Under Review",
                message=f"Your application ({ref_num}) is now being actively reviewed by our compliance team.",
                notification_type=NotificationType.STATUS_CHANGE.value,
                vendor_id=str(oid),
                application_id=str(oid),
            )

        return {
            "message": f"Status updated to '{target_status_clean}'.",
            "application_id": str(oid),
            "status": target_status_clean,
            "updated_at": now,
        }

    # -----------------------------------------------------------------------
    # Admin Review Comments
    # -----------------------------------------------------------------------

    def add_comment(
        self,
        application_id: str,
        comment: str,
        visibility_type: str = "internal",
        author_name: str = "Admin",
    ) -> dict[str, Any]:
        """Add an internal review comment."""
        oid = _validate_object_id(application_id)
        now = _utcnow()
        doc = AdminCommentModel(
            application_id=str(oid),
            vendor_id=str(oid),
            comment=comment.strip(),
            visibility_type=visibility_type,
            author_name=author_name,
            created_at=now,
        ).to_dict()

        res = self.comments_col.insert_one(doc)
        doc["id"] = str(res.inserted_id)
        if "_id" in doc:
            del doc["_id"]

        # Activity log
        self.log_activity(
            application_id=str(oid),
            vendor_id=str(oid),
            event_type=ActivityEventType.COMMENT_ADDED.value,
            description=f"Admin added an internal review note: {comment.strip()}",
            actor_type=ActorType.ADMIN.value,
        )

        return doc

    def get_comments(self, application_id: str) -> list[dict[str, Any]]:
        """Retrieve internal comments for an application."""
        cursor = self.comments_col.find(
            {"$or": [{"application_id": application_id}, {"vendor_id": application_id}]}
        ).sort("created_at", ASCENDING)

        items: list[dict[str, Any]] = []
        for doc in cursor:
            doc["id"] = str(doc.pop("_id"))
            items.append(doc)
        return items

    # -----------------------------------------------------------------------
    # Application Management Table Querying & Pagination
    # -----------------------------------------------------------------------

    def list_applications(
        self,
        status: str | None = None,
        search: str | None = None,
        sort_by: str = "last_updated_date",  # submission_date | last_updated_date
        sort_order: str = "desc",
        page: int = 1,
        limit: int = 20,
    ) -> dict[str, Any]:
        """
        List applications with filtering, search, sorting, and pagination.
        Includes AI verification status & pending clarifications count.
        """
        query: dict[str, Any] = {}

        if status and status.lower() != "all":
            query["status"] = status.lower().strip()

        if search and search.strip():
            term = search.strip()
            query["$or"] = [
                {"company_info.legal_name": {"$regex": term, "$options": "i"}},
                {"company_info.legal_company_name": {"$regex": term, "$options": "i"}},
                {"company_info.trade_name": {"$regex": term, "$options": "i"}},
                {"contact_info.primary.first_name": {"$regex": term, "$options": "i"}},
                {"contact_info.primary.last_name": {"$regex": term, "$options": "i"}},
                {"contact_info.primary.email": {"$regex": term, "$options": "i"}},
                {"reference_number": {"$regex": term, "$options": "i"}},
            ]
            if ObjectId.is_valid(term):
                query["$or"].append({"_id": ObjectId(term)})

        total = self.vendors_col.count_documents(query)
        pages = max(1, math.ceil(total / limit))
        skip = (page - 1) * limit

        sort_field = "submitted_at" if sort_by == "submission_date" else "updated_at"
        sort_dir = DESCENDING if sort_order.lower() == "desc" else ASCENDING

        cursor = self.vendors_col.find(query).sort(sort_field, sort_dir).skip(skip).limit(limit)

        items: list[dict[str, Any]] = []
        for doc in cursor:
            app_id = str(doc["_id"])
            c_info = doc.get("company_info") or {}
            contact = doc.get("contact_info", {}).get("primary") or {}
            first_name = contact.get("first_name", "")
            last_name = contact.get("last_name", "")
            vendor_name = f"{first_name} {last_name}".strip() or "N/A"
            company_name = (
                c_info.get("legal_company_name")
                or c_info.get("legal_name")
                or c_info.get("trade_name")
                or "Unnamed Vendor"
            )

            # Documents & AI status
            docs = doc.get("documents") or []
            doc_count = len(docs)
            if doc_count == 0:
                try:
                    doc_count = self.db["document_files.files"].count_documents({"metadata.vendor_id": app_id})
                except Exception:
                    pass

            # Check verification collection for this vendor
            verif_cursor = list(self.verification_col.find({"vendor_id": app_id}))
            ai_status = "pending"
            if verif_cursor:
                statuses = [v.get("verification_status") for v in verif_cursor]
                if any(s == "flagged" for s in statuses):
                    ai_status = "flagged"
                elif any(s == "needs_manual_review" for s in statuses):
                    ai_status = "needs_manual_review"
                elif all(s == "completed" for s in statuses):
                    ai_status = "completed"

            # Pending clarifications count
            pending_clarifs = self.clarifications_col.count_documents(
                {"application_id": app_id, "status": ClarificationStatus.PENDING.value}
            )

            items.append({
                "id": app_id,
                "vendor_id": app_id,
                "reference_number": doc.get("reference_number", "DRAFT"),
                "company_name": company_name,
                "vendor_name": vendor_name,
                "email": contact.get("email") or "N/A",
                "status": doc.get("status", VendorStatus.DRAFT.value),
                "submission_date": doc.get("submitted_at"),
                "last_updated_date": doc.get("updated_at") or doc.get("created_at"),
                "document_count": doc_count,
                "ai_verification_status": ai_status,
                "pending_clarifications_count": pending_clarifs,
                "ai_decision": doc.get("ai_decision"),
            })

        # Count per status for metrics
        status_counts = {
            "all": self.vendors_col.count_documents({}),
            "draft": self.vendors_col.count_documents({"status": VendorStatus.DRAFT.value}),
            "submitted": self.vendors_col.count_documents({"status": VendorStatus.SUBMITTED.value}),
            "under_review": self.vendors_col.count_documents({"status": VendorStatus.UNDER_REVIEW.value}),
            "clarification_required": self.vendors_col.count_documents({"status": VendorStatus.CLARIFICATION_REQUIRED.value}),
            "resubmitted": self.vendors_col.count_documents({"status": VendorStatus.RESUBMITTED.value}),
            "approved": self.vendors_col.count_documents({"status": VendorStatus.APPROVED.value}),
            "rejected": self.vendors_col.count_documents({"status": VendorStatus.REJECTED.value}),
        }

        return {
            "items": items,
            "total": total,
            "page": page,
            "limit": limit,
            "pages": pages,
            "status_counts": status_counts,
        }

