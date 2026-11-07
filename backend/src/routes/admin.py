"""
Administrator routes for VendorFlow.

Protected endpoints for administrator management, vendor application listing,
metrics, search/filtering, and reviewing vendor submissions.
"""

from __future__ import annotations

import logging
import math
from typing import Annotated

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from pymongo import DESCENDING, ASCENDING

from src.dependencies.auth import AdminUserDep
from src.schemas.admin import (
    AdminMetricsResponse,
    AdminVendorListItem,
    AdminVendorPaginationResponse,
)
from src.services.auth_service import AuthService
from src.services.vendor_service import VendorService, VendorNotFoundError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["Admin Portal"])


class StatusUpdateRequest(BaseModel):
    """Payload for updating vendor onboarding status by an admin."""
    status: str = Field(..., description="New status: 'under_review', 'approved', 'rejected'")
    review_notes: str | None = Field(default=None, description="Internal review notes")
    rejection_reason: str | None = Field(default=None, description="Reason if rejected")


@router.get(
    "/metrics",
    response_model=AdminMetricsResponse,
    status_code=status.HTTP_200_OK,
    summary="Retrieve vendor application summary metrics",
)
async def get_admin_metrics(
    admin: AdminUserDep,
) -> AdminMetricsResponse:
    """Calculates counts of vendors by onboarding status."""
    service = VendorService()
    col = service.collection

    total = col.count_documents({})
    draft = col.count_documents({"status": "draft"})
    submitted = col.count_documents({"status": "submitted"})
    under_review = col.count_documents({"status": "under_review"})
    approved = col.count_documents({"status": "approved"})
    rejected = col.count_documents({"status": "rejected"})

    return AdminMetricsResponse(
        total_vendors=total,
        draft=draft,
        submitted=submitted,
        under_review=under_review,
        approved=approved,
        rejected=rejected,
    )


@router.get(
    "/vendors",
    response_model=AdminVendorPaginationResponse,
    status_code=status.HTTP_200_OK,
    summary="List vendor applications with search, filter, and pagination",
)
async def list_admin_vendors(
    admin: AdminUserDep,
    page: int = Query(default=1, ge=1, description="Page number (1-based)"),
    limit: int = Query(default=10, ge=1, le=100, description="Items per page"),
    status: str | None = Query(default=None, description="Filter by vendor status"),
    search: str | None = Query(default=None, description="Search by company name or email"),
    sort_order: str = Query(default="desc", pattern="^(asc|desc)$", description="Sort order by created_at"),
) -> AdminVendorPaginationResponse:
    """
    Search, filter, and paginate vendor applications for administrator review.
    """
    service = VendorService()
    col = service.collection

    query: dict = {}

    if status and status.lower() != "all":
        query["status"] = status.lower()

    if search and search.strip():
        term = search.strip()
        query["$or"] = [
            {"company_info.legal_name": {"$regex": term, "$options": "i"}},
            {"company_info.trade_name": {"$regex": term, "$options": "i"}},
            {"contact_info.primary.email": {"$regex": term, "$options": "i"}},
            {"contact_info.primary.first_name": {"$regex": term, "$options": "i"}},
            {"contact_info.primary.last_name": {"$regex": term, "$options": "i"}},
            {"reference_number": {"$regex": term, "$options": "i"}},
        ]

    total = col.count_documents(query)
    pages = max(1, math.ceil(total / limit))
    skip = (page - 1) * limit

    sort_direction = DESCENDING if sort_order == "desc" else ASCENDING

    cursor = col.find(query).sort("created_at", sort_direction).skip(skip).limit(limit)

    items: list[AdminVendorListItem] = []
    for doc in cursor:
        company_info = doc.get("company_info", {})
        contact_info = doc.get("contact_info", {})
        primary = contact_info.get("primary", {})
        first = primary.get("first_name", "")
        last = primary.get("last_name", "")
        contact_name = f"{first} {last}".strip() or "N/A"

        items.append(
            AdminVendorListItem(
                id=str(doc["_id"]),
                company_name=company_info.get("legal_name") or company_info.get("trade_name") or "Unnamed Vendor",
                contact_name=contact_name,
                email=primary.get("email") or "N/A",
                phone=primary.get("phone") or "",
                status=doc.get("status", "draft"),
                reference_number=doc.get("reference_number") or "",
                created_at=doc.get("created_at"),
                updated_at=doc.get("updated_at"),
                documents_count=len(doc.get("documents", [])),
            )
        )

    # Get metrics
    metrics = AdminMetricsResponse(
        total_vendors=col.count_documents({}),
        draft=col.count_documents({"status": "draft"}),
        submitted=col.count_documents({"status": "submitted"}),
        under_review=col.count_documents({"status": "under_review"}),
        approved=col.count_documents({"status": "approved"}),
        rejected=col.count_documents({"status": "rejected"}),
    )

    return AdminVendorPaginationResponse(
        items=items,
        total=total,
        page=page,
        limit=limit,
        pages=pages,
        metrics=metrics,
    )


@router.get(
    "/vendors/{vendor_id}",
    status_code=status.HTTP_200_OK,
    summary="Get full vendor details including unmasked banking details for admin",
)
async def get_admin_vendor_detail(
    vendor_id: str,
    admin: AdminUserDep,
) -> dict:
    """
    Retrieve complete vendor record.
    Unmasked banking and tax information is authorized exclusively for admin.
    """
    try:
        oid = ObjectId(vendor_id)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid vendor identifier: '{vendor_id}'.",
        )

    service = VendorService()
    doc = service.collection.find_one({"_id": oid})
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Vendor with id '{vendor_id}' was not found.",
        )

    doc["id"] = str(doc.pop("_id"))
    return doc


@router.patch(
    "/vendors/{vendor_id}/status",
    status_code=status.HTTP_200_OK,
    summary="Update vendor onboarding review status",
)
async def update_vendor_status_by_admin(
    vendor_id: str,
    payload: StatusUpdateRequest,
    admin: AdminUserDep,
) -> dict:
    """
    Admin updates vendor review status (e.g. approve, reject, or place under review).
    """
    try:
        oid = ObjectId(vendor_id)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid vendor identifier: '{vendor_id}'.",
        )

    service = VendorService()
    doc = service.collection.find_one({"_id": oid})
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Vendor with id '{vendor_id}' was not found.",
        )

    update_fields: dict = {
        "status": payload.status,
    }
    if payload.review_notes is not None:
        update_fields["review_notes"] = payload.review_notes
    if payload.rejection_reason is not None:
        update_fields["rejection_reason"] = payload.rejection_reason

    service.collection.update_one({"_id": oid}, {"$set": update_fields})
    return {
        "message": f"Vendor status updated to '{payload.status}'.",
        "vendor_id": vendor_id,
        "status": payload.status,
    }

