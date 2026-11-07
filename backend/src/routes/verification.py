"""
Verification API routes for Phase 8.

Endpoints:
    POST /api/vendors/{vendor_id}/documents/{document_id}/verify
    GET  /api/vendors/{vendor_id}/documents/{document_id}/verification
    GET  /api/vendors/{vendor_id}/verification
    POST /api/admin/documents/{document_id}/verify
    GET  /api/admin/documents/{document_id}/verification
"""

from __future__ import annotations

import logging
from typing import Any

from bson import ObjectId
from fastapi import APIRouter, BackgroundTasks, HTTPException, Query, status

from src.schemas.verification import (
    VendorVerificationSummaryResponse,
    VerificationResultResponse,
)
from src.services.document_service import DocumentNotFoundError, DocumentService
from src.services.vendor_service import InvalidVendorIdError, VendorNotFoundError, VendorService
from src.services.verification_service import VerificationService

logger = logging.getLogger(__name__)

router = APIRouter(tags=["AI Verification"])


def _get_verification_service() -> VerificationService:
    return VerificationService()


# ---------------------------------------------------------------------------
# POST /api/vendors/{vendor_id}/documents/{document_id}/verify
# ---------------------------------------------------------------------------

@router.post(
    "/vendors/{vendor_id}/documents/{document_id}/verify",
    response_model=dict[str, Any],
    status_code=status.HTTP_200_OK,
    summary="Trigger AI extraction and verification for a document",
)
async def verify_vendor_document(
    vendor_id: str,
    document_id: str,
    background_tasks: BackgroundTasks,
    run_async: bool = Query(default=False, description="Whether to run in background or wait for completion"),
) -> dict[str, Any]:
    """
    Initiate document preprocessing, Nemotron 3.5 Parse text extraction,
    deterministic validation, and Nemotron 3.5 Super VL cross-document reasoning.
    """
    svc = _get_verification_service()
    doc_svc = DocumentService()

    # Validate vendor & document exist
    try:
        doc_meta = doc_svc.get_document_metadata(vendor_id, document_id)
    except (DocumentNotFoundError, VendorNotFoundError) as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    if run_async:
        background_tasks.add_task(svc.execute_verification, vendor_id, document_id)
        return {
            "status": "processing",
            "message": "AI verification initiated in background.",
            "vendor_id": vendor_id,
            "document_id": document_id,
        }

    # Execute directly so response has full results
    result = await svc.execute_verification(vendor_id, document_id)
    return result


# ---------------------------------------------------------------------------
# GET /api/vendors/{vendor_id}/documents/{document_id}/verification
# ---------------------------------------------------------------------------

@router.get(
    "/vendors/{vendor_id}/documents/{document_id}/verification",
    response_model=VerificationResultResponse,
    status_code=status.HTTP_200_OK,
    summary="Retrieve AI verification result for a document",
)
async def get_document_verification(
    vendor_id: str,
    document_id: str,
) -> VerificationResultResponse:
    """Retrieve stored verification result, extracted fields, and cross-document findings."""
    svc = _get_verification_service()
    result = svc.get_document_verification(vendor_id, document_id)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No verification result found for document '{document_id}'.",
        )
    return VerificationResultResponse(**result)


# ---------------------------------------------------------------------------
# GET /api/vendors/{vendor_id}/verification
# ---------------------------------------------------------------------------

@router.get(
    "/vendors/{vendor_id}/verification",
    response_model=VendorVerificationSummaryResponse,
    status_code=status.HTTP_200_OK,
    summary="Retrieve overall verification summary for a vendor",
)
async def get_vendor_verification_summary(
    vendor_id: str,
) -> VendorVerificationSummaryResponse:
    """Retrieve all verification records and overall verification status for a vendor."""
    svc = _get_verification_service()
    summary = svc.get_vendor_verification_summary(vendor_id)
    return VendorVerificationSummaryResponse(**summary)


# ---------------------------------------------------------------------------
# Admin Endpoints
# ---------------------------------------------------------------------------

@router.post(
    "/admin/documents/{document_id}/verify",
    response_model=dict[str, Any],
    status_code=status.HTTP_200_OK,
    summary="Admin endpoint to trigger or retry AI verification",
)
async def admin_verify_document(
    document_id: str,
    background_tasks: BackgroundTasks,
    run_async: bool = Query(default=False),
) -> dict[str, Any]:
    """Find vendor for this document and execute verification."""
    svc = _get_verification_service()
    # Find vendor containing this document_id
    vendor_doc = svc.vendors_col.find_one({"documents.document_id": document_id})
    if not vendor_doc and ObjectId.is_valid(document_id):
        # Fallback to GridFS file metadata
        grid_file = svc._db["document_files.files"].find_one({"_id": ObjectId(document_id)})
        if grid_file and grid_file.get("metadata", {}).get("vendor_id"):
            v_id = grid_file["metadata"]["vendor_id"]
            if ObjectId.is_valid(v_id):
                vendor_doc = svc.vendors_col.find_one({"_id": ObjectId(v_id)})

    if not vendor_doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document '{document_id}' not found in any vendor registration.",
        )
    vendor_id = str(vendor_doc["_id"])

    if run_async:
        background_tasks.add_task(svc.execute_verification, vendor_id, document_id)
        return {
            "status": "processing",
            "message": "AI verification initiated by admin in background.",
            "vendor_id": vendor_id,
            "document_id": document_id,
        }

    return await svc.execute_verification(vendor_id, document_id)


@router.get(
    "/admin/documents/{document_id}/verification",
    response_model=VerificationResultResponse,
    status_code=status.HTTP_200_OK,
    summary="Admin endpoint to retrieve verification result",
)
async def admin_get_document_verification(
    document_id: str,
) -> VerificationResultResponse:
    """Retrieve stored verification result by document_id across all vendors."""
    svc = _get_verification_service()
    doc = svc.verification_col.find_one({"document_id": document_id})
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No verification result found for document '{document_id}'.",
        )
    doc["id"] = str(doc.pop("_id"))
    return VerificationResultResponse(**doc)

