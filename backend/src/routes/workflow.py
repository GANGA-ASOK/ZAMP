"""
FastAPI route handlers for Phase 9:
- Application Review & Listing
- Approval & Rejection
- Clarification Request & Response Workflow
- Notifications Center
- Activity History Timeline
- Internal Admin Comments
"""

from __future__ import annotations

import logging
from typing import Annotated, Any

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from pydantic import BaseModel

from src.dependencies.auth import (
    AdminUserDep,
    get_current_user_optional,
    verify_vendor_ownership,
)
from src.models.enums import NotificationRecipientType
from src.models.user import UserModel
from src.schemas.workflow import (
    ActivityEventResponse,
    AdminCommentCreatePayload,
    AdminCommentResponse,
    ApplicationListItem,
    ApplicationPaginationResponse,
    ApprovePayload,
    ClarificationCreatePayload,
    ClarificationItemResponse,
    ClarificationRespondPayload,
    NotificationListResponse,
    NotificationResponse,
    RejectPayload,
    StatusUpdatePayload,
    VendorResubmitPayload,
)
from src.services.vendor_service import InvalidVendorIdError, VendorNotFoundError, VendorService
from src.services.verification_service import VerificationService
from src.services.application_decision_service import run_decision_in_background
from src.services.workflow_service import (
    InvalidStatusTransitionError,
    WorkflowService,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Approval Workflow & Vendor Communication"])


def get_workflow_service() -> WorkflowService:
    return WorkflowService()


WorkflowDep = Annotated[WorkflowService, Depends(get_workflow_service)]


# ---------------------------------------------------------------------------
# 1. Application Management (Admin)
# ---------------------------------------------------------------------------

@router.get(
    "/admin/applications",
    response_model=ApplicationPaginationResponse,
    status_code=status.HTTP_200_OK,
    summary="List vendor applications with search, status filters, sorting, and pagination",
)
async def list_applications(
    admin: AdminUserDep,
    workflow_svc: WorkflowDep,
    page: int = Query(default=1, ge=1, description="1-based page number"),
    limit: int = Query(default=15, ge=1, le=100, description="Items per page"),
    status: str | None = Query(default=None, description="Filter by status (e.g. submitted, under_review, clarification_required, resubmitted, approved, rejected, all)"),
    search: str | None = Query(default=None, description="Search by vendor name, company name, reference number, or ID"),
    sort_by: str = Query(default="last_updated_date", description="Sort by: 'submission_date' or 'last_updated_date'"),
    sort_order: str = Query(default="desc", pattern="^(asc|desc)$", description="Sort direction"),
) -> ApplicationPaginationResponse:
    """Admin table listing with server-side filters and metrics counts."""
    data = workflow_svc.list_applications(
        status=status,
        search=search,
        sort_by=sort_by,
        sort_order=sort_order,
        page=page,
        limit=limit,
    )
    return ApplicationPaginationResponse(
        items=[ApplicationListItem(**item) for item in data["items"]],
        total=data["total"],
        page=data["page"],
        limit=data["limit"],
        pages=data["pages"],
        status_counts=data["status_counts"],
    )


@router.get(
    "/admin/applications/{application_id}",
    status_code=status.HTTP_200_OK,
    summary="Retrieve full vendor application review details for admin",
)
async def get_application_detail(
    application_id: str,
    admin: AdminUserDep,
    workflow_svc: WorkflowDep,
) -> dict[str, Any]:
    """
    Returns full vendor registration, uploaded documents, AI verification summary,
    clarification requests, internal comments, and activity timeline.
    """
    vendor_svc = VendorService()
    try:
        raw_doc = await vendor_svc.get_raw_vendor_doc(application_id)
    except (InvalidVendorIdError, VendorNotFoundError) as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))

    raw_doc["id"] = str(raw_doc.pop("_id"))

    # Reconcile documents from GridFS if vendor.documents is empty
    from src.services.document_service import DocumentService
    try:
        doc_svc = DocumentService()
        grid_docs = doc_svc.list_documents(application_id)
        if not raw_doc.get("documents") and grid_docs:
            raw_doc["documents"] = [
                {
                    "document_id": d["document_id"],
                    "category": d.get("document_category", "other"),
                    "file_name": d.get("original_filename", "document.pdf"),
                    "file_size": d.get("file_size", 0),
                    "file_type": d.get("content_type", "application/pdf"),
                    "verification_status": d.get("verification_status", "uploaded"),
                    "uploaded_at": d.get("upload_timestamp", ""),
                }
                for d in grid_docs
            ]
    except Exception as exc:
        logger.debug("GridFS document reconcile notice: %s", exc)

    # Fetch AI Verification summary
    verif_svc = VerificationService()
    verif_summary = None
    try:
        verif_summary = verif_svc.get_vendor_verification_summary(application_id)
    except Exception as exc:
        logger.debug("Verification summary fetch skipped: %s", exc)

    # Fetch or generate AI Insights
    from src.services.insights_service import InsightsService
    ai_insights = None
    try:
        insights_svc = InsightsService()
        ai_insights = insights_svc.get_vendor_insights(application_id)
        if not ai_insights:
            ai_insights = insights_svc.generate_vendor_insights(application_id)
    except Exception as exc:
        logger.debug("Insights fetch/generation notice: %s", exc)

    # Fetch clarifications
    clarifications = workflow_svc.get_clarifications(application_id)

    # Fetch internal comments
    comments = workflow_svc.get_comments(application_id)

    # Fetch activity timeline
    activity = workflow_svc.get_activity_timeline(application_id)

    return {
        "vendor": raw_doc,
        "verification_summary": verif_summary,
        "ai_insights": ai_insights,
        "clarifications": clarifications,
        "comments": comments,
        "activity": activity,
    }


@router.get(
    "/admin/applications/{application_id}/insights",
    status_code=status.HTTP_200_OK,
    summary="Retrieve consolidated AI insights for an application",
)
async def get_application_insights(
    application_id: str,
    admin: AdminUserDep,
) -> dict[str, Any]:
    """Retrieve synthesized AI findings, missing docs, discrepancies, and recommendation."""
    from src.services.insights_service import InsightsService
    insights_svc = InsightsService()
    insights = insights_svc.get_vendor_insights(application_id)
    if not insights:
        insights = insights_svc.generate_vendor_insights(application_id)
    return insights


@router.post(
    "/admin/applications/{application_id}/insights/generate",
    status_code=status.HTTP_200_OK,
    summary="Trigger immediate re-synthesis of AI insights for an application",
)
async def generate_application_insights(
    application_id: str,
    admin: AdminUserDep,
) -> dict[str, Any]:
    """Recompute all AI cross-document findings and risk metrics."""
    from src.services.insights_service import InsightsService
    insights_svc = InsightsService()
    return insights_svc.generate_vendor_insights(application_id)


@router.get(
    "/vendors/{vendor_id}/insights",
    status_code=status.HTTP_200_OK,
    summary="Vendor endpoint to retrieve their AI verification insights and status",
)
async def get_vendor_insights(
    vendor_id: str,
    _auth: UserModel = Depends(verify_vendor_ownership),
) -> dict[str, Any]:
    """Vendor view of findings, missing information, and verification status."""
    from src.services.insights_service import InsightsService
    insights_svc = InsightsService()
    insights = insights_svc.get_vendor_insights(vendor_id)
    if not insights:
        insights = insights_svc.generate_vendor_insights(vendor_id)
    return insights


@router.patch(
    "/admin/applications/{application_id}/status",
    status_code=status.HTTP_200_OK,
    summary="Update application onboarding status with state machine validation",
)
async def update_application_status(
    application_id: str,
    payload: StatusUpdatePayload,
    admin: AdminUserDep,
    workflow_svc: WorkflowDep,
) -> dict[str, Any]:
    """Validate and transition application status (e.g. from submitted to under_review)."""
    try:
        return workflow_svc.update_application_status(
            application_id=application_id,
            target_status=payload.status,
            notes=payload.notes,
            actor_name=admin.name or "Admin",
        )
    except InvalidStatusTransitionError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except (InvalidVendorIdError, VendorNotFoundError) as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


# ---------------------------------------------------------------------------
# 2. Approval and Rejection
# ---------------------------------------------------------------------------

@router.post(
    "/admin/applications/{application_id}/approve",
    status_code=status.HTTP_200_OK,
    summary="Approve vendor onboarding application",
)
async def approve_application(
    application_id: str,
    payload: ApprovePayload,
    admin: AdminUserDep,
    workflow_svc: WorkflowDep,
) -> dict[str, Any]:
    """Admin officially approves the application. Sends notification to vendor."""
    try:
        return workflow_svc.approve_application(
            application_id=application_id,
            comment=payload.comment,
            actor_name=admin.name or "Admin",
        )
    except InvalidStatusTransitionError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except (InvalidVendorIdError, VendorNotFoundError) as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.post(
    "/admin/applications/{application_id}/reject",
    status_code=status.HTTP_200_OK,
    summary="Reject vendor onboarding application",
)
async def reject_application(
    application_id: str,
    payload: RejectPayload,
    admin: AdminUserDep,
    workflow_svc: WorkflowDep,
) -> dict[str, Any]:
    """Admin rejects the application with mandatory reason. Preserves files and data."""
    try:
        return workflow_svc.reject_application(
            application_id=application_id,
            rejection_reason=payload.rejection_reason,
            actor_name=admin.name or "Admin",
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
    except InvalidStatusTransitionError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except (InvalidVendorIdError, VendorNotFoundError) as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


# ---------------------------------------------------------------------------
# 3. Clarification Workflow
# ---------------------------------------------------------------------------

@router.post(
    "/admin/applications/{application_id}/clarifications",
    response_model=ClarificationItemResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Admin requests clarification or corrected document",
)
async def request_clarification(
    application_id: str,
    payload: ClarificationCreatePayload,
    admin: AdminUserDep,
    workflow_svc: WorkflowDep,
) -> ClarificationItemResponse:
    """Admin specifies what document, field, or details need correction."""
    try:
        item = workflow_svc.request_clarification(
            application_id=application_id,
            clarification_message=payload.clarification_message,
            related_document_id=payload.related_document_id,
            related_document_name=payload.related_document_name,
            related_field=payload.related_field,
            admin_notes=payload.admin_notes,
        )
        return ClarificationItemResponse(**item)
    except InvalidStatusTransitionError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except (InvalidVendorIdError, VendorNotFoundError) as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.get(
    "/vendors/{vendor_id}/clarifications",
    response_model=list[ClarificationItemResponse],
    status_code=status.HTTP_200_OK,
    summary="Vendor retrieves pending and past clarification requests",
)
async def get_vendor_clarifications(
    vendor_id: str,
    workflow_svc: WorkflowDep,
    _auth: UserModel = Depends(verify_vendor_ownership),
) -> list[ClarificationItemResponse]:
    """Retrieve all clarification requests for the given vendor."""
    items = workflow_svc.get_clarifications(vendor_id)
    return [ClarificationItemResponse(**i) for i in items]


@router.post(
    "/vendors/{vendor_id}/clarifications/{clarification_id}/respond",
    response_model=ClarificationItemResponse,
    status_code=status.HTTP_200_OK,
    summary="Vendor responds to clarification request",
)
async def respond_to_clarification(
    vendor_id: str,
    clarification_id: str,
    payload: ClarificationRespondPayload,
    workflow_svc: WorkflowDep,
    _auth: UserModel = Depends(verify_vendor_ownership),
) -> ClarificationItemResponse:
    """Submit vendor response, optional replacement doc ID, or updated fields."""
    try:
        item = workflow_svc.respond_to_clarification(
            vendor_id=vendor_id,
            clarification_id=clarification_id,
            vendor_response=payload.vendor_response,
            replaced_document_id=payload.replaced_document_id,
            updated_fields=payload.updated_fields,
        )
        return ClarificationItemResponse(**item)
    except (InvalidVendorIdError, VendorNotFoundError) as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.post(
    "/vendors/{vendor_id}/resubmit",
    status_code=status.HTTP_200_OK,
    summary="Vendor resubmits application after corrections",
)
async def resubmit_application(
    vendor_id: str,
    payload: VendorResubmitPayload,
    workflow_svc: WorkflowDep,
    background_tasks: BackgroundTasks,
    _auth: UserModel = Depends(verify_vendor_ownership),
) -> dict[str, Any]:
    """Resubmit corrected application, changing status to 'resubmitted'."""
    try:
        result = workflow_svc.resubmit_application(
            vendor_id=vendor_id,
            resubmission_notes=payload.resubmission_notes,
        )
        background_tasks.add_task(run_decision_in_background, vendor_id, "resubmission")
        return result
    except InvalidStatusTransitionError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except (InvalidVendorIdError, VendorNotFoundError) as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


# ---------------------------------------------------------------------------
# 4. Internal Admin Comments
# ---------------------------------------------------------------------------

@router.post(
    "/admin/applications/{application_id}/comments",
    response_model=AdminCommentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add internal administrator review note",
)
async def add_admin_comment(
    application_id: str,
    payload: AdminCommentCreatePayload,
    admin: AdminUserDep,
    workflow_svc: WorkflowDep,
) -> AdminCommentResponse:
    """Record an internal review comment separate from vendor-visible communications."""
    item = workflow_svc.add_comment(
        application_id=application_id,
        comment=payload.comment,
        visibility_type=payload.visibility_type,
        author_name=admin.name or "Admin",
    )
    return AdminCommentResponse(**item)


@router.get(
    "/admin/applications/{application_id}/comments",
    response_model=list[AdminCommentResponse],
    status_code=status.HTTP_200_OK,
    summary="Retrieve internal review comments for an application",
)
async def get_admin_comments(
    application_id: str,
    admin: AdminUserDep,
    workflow_svc: WorkflowDep,
) -> list[AdminCommentResponse]:
    """List all internal comments for the application."""
    items = workflow_svc.get_comments(application_id)
    return [AdminCommentResponse(**i) for i in items]


# ---------------------------------------------------------------------------
# 5. In-App Notifications
# ---------------------------------------------------------------------------

@router.get(
    "/admin/notifications",
    response_model=NotificationListResponse,
    status_code=status.HTTP_200_OK,
    summary="Retrieve admin notification feed with unread count",
)
async def get_admin_notifications(
    admin: AdminUserDep,
    workflow_svc: WorkflowDep,
    limit: int = Query(default=50, ge=1, le=200),
) -> NotificationListResponse:
    """Retrieve notifications intended for administrators."""
    data = workflow_svc.get_notifications(
        recipient_type=NotificationRecipientType.ADMIN.value,
        limit=limit,
    )
    return NotificationListResponse(
        items=[NotificationResponse(**i) for i in data["items"]],
        unread_count=data["unread_count"],
        total_count=data["total_count"],
    )


@router.get(
    "/vendors/{vendor_id}/notifications",
    response_model=NotificationListResponse,
    status_code=status.HTTP_200_OK,
    summary="Retrieve notifications for a specific vendor",
)
async def get_vendor_notifications(
    vendor_id: str,
    workflow_svc: WorkflowDep,
    _auth: UserModel = Depends(verify_vendor_ownership),
    limit: int = Query(default=50, ge=1, le=200),
) -> NotificationListResponse:
    """Retrieve vendor-specific notifications."""
    data = workflow_svc.get_notifications(
        recipient_type=NotificationRecipientType.VENDOR.value,
        vendor_id=vendor_id,
        limit=limit,
    )
    return NotificationListResponse(
        items=[NotificationResponse(**i) for i in data["items"]],
        unread_count=data["unread_count"],
        total_count=data["total_count"],
    )


@router.patch(
    "/notifications/{notification_id}/read",
    status_code=status.HTTP_200_OK,
    summary="Mark single notification as read",
)
async def mark_notification_read(
    notification_id: str,
    workflow_svc: WorkflowDep,
) -> dict[str, Any]:
    """Mark notification read by ID."""
    success = workflow_svc.mark_notification_read(notification_id)
    return {"message": "Notification marked as read.", "success": success}


@router.patch(
    "/notifications/read-all",
    status_code=status.HTTP_200_OK,
    summary="Mark all notifications as read for recipient",
)
async def mark_all_notifications_read(
    workflow_svc: WorkflowDep,
    recipient_type: str = Query(default="admin", description="'admin' or 'vendor'"),
    vendor_id: str | None = Query(default=None, description="Required when recipient_type is 'vendor'"),
) -> dict[str, Any]:
    """Bulk mark notifications as read."""
    modified = workflow_svc.mark_all_notifications_read(
        recipient_type=recipient_type,
        vendor_id=vendor_id,
    )
    return {"message": f"{modified} notifications marked as read.", "count": modified}


# ---------------------------------------------------------------------------
# 6. Chronological Activity Timeline
# ---------------------------------------------------------------------------

@router.get(
    "/admin/applications/{application_id}/activity",
    response_model=list[ActivityEventResponse],
    status_code=status.HTTP_200_OK,
    summary="Retrieve complete activity timeline for an application (Admin)",
)
async def get_admin_application_activity(
    application_id: str,
    admin: AdminUserDep,
    workflow_svc: WorkflowDep,
) -> list[ActivityEventResponse]:
    """Complete history of milestones, transitions, and decisions."""
    events = workflow_svc.get_activity_timeline(application_id)
    return [ActivityEventResponse(**e) for e in events]


@router.get(
    "/vendors/{vendor_id}/activity",
    response_model=list[ActivityEventResponse],
    status_code=status.HTTP_200_OK,
    summary="Retrieve application activity timeline for vendor",
)
async def get_vendor_application_activity(
    vendor_id: str,
    workflow_svc: WorkflowDep,
    _auth: UserModel = Depends(verify_vendor_ownership),
) -> list[ActivityEventResponse]:
    """Chronological milestone progression for the vendor."""
    events = workflow_svc.get_activity_timeline(vendor_id)
    return [ActivityEventResponse(**e) for e in events]

