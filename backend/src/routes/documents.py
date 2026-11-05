"""
Document management API routes — Phase 5.

Endpoints:
    POST   /api/vendors/{vendor_id}/documents                       — upload
    GET    /api/vendors/{vendor_id}/documents                       — list
    GET    /api/vendors/{vendor_id}/documents/{document_id}         — metadata
    GET    /api/vendors/{vendor_id}/documents/{document_id}/download — download
    PUT    /api/vendors/{vendor_id}/documents/{document_id}         — replace
    DELETE /api/vendors/{vendor_id}/documents/{document_id}         — delete

Security note (Phase 7)
-----------------------
Vendor-ownership checks rely solely on the ``vendor_id`` path parameter.
JWT / session-based authorization must be integrated in Phase 7.
"""

from __future__ import annotations

import io
import logging

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status
from fastapi.responses import StreamingResponse

from src.schemas.document import DocumentListResponse, DocumentMetadataResponse
from src.services.document_service import (
    DocumentNotFoundError,
    DocumentService,
    DocumentServiceError,
    EmptyFileError,
    FileSizeLimitError,
    InvalidDocumentIdError,
    InvalidFileTypeError,
    StorageError,
    VendorOwnershipError,
)
from src.services.vendor_service import InvalidVendorIdError, VendorNotFoundError

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Documents"])


# ---------------------------------------------------------------------------
# Dependency / helper
# ---------------------------------------------------------------------------

def _get_service() -> DocumentService:
    """Return a DocumentService using the live MongoDB connection."""
    return DocumentService()


def _handle_service_error(exc: Exception) -> HTTPException:
    """Map service-layer exceptions to FastAPI HTTPExceptions."""
    if isinstance(exc, (VendorNotFoundError, DocumentNotFoundError)):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    if isinstance(exc, (InvalidVendorIdError, InvalidDocumentIdError)):
        return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    if isinstance(exc, FileSizeLimitError):
        return HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail=str(exc)
        )
    if isinstance(exc, EmptyFileError):
        return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    if isinstance(exc, InvalidFileTypeError):
        return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    if isinstance(exc, VendorOwnershipError):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    if isinstance(exc, StorageError):
        return HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)
        )
    if isinstance(exc, DocumentServiceError):
        return HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)
        )
    # Fallback
    logger.exception("Unexpected document service error: %s", exc)
    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="An unexpected error occurred.",
    )


# ---------------------------------------------------------------------------
# POST /api/vendors/{vendor_id}/documents  — upload
# ---------------------------------------------------------------------------

@router.post(
    "/{vendor_id}/documents",
    response_model=DocumentMetadataResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a vendor document",
)
async def upload_document(
    vendor_id: str,
    category: str = Form(..., description="DocumentCategory value (e.g. pan_card)."),
    file: UploadFile = File(..., description="The file to upload."),
):
    """
    Accept a multipart/form-data upload and store the file in GridFS.

    - Validates vendor existence.
    - Validates document category against the ``DocumentCategory`` enum.
    - Validates file extension and magic bytes.
    - Enforces the 10 MB file-size limit.
    - Returns document metadata (never raw file bytes).
    """
    file_bytes = await file.read()
    svc = _get_service()
    try:
        result = svc.upload_document(
            vendor_id=vendor_id,
            file_bytes=file_bytes,
            filename=file.filename or "upload",
            category=category,
            content_type=file.content_type,
        )
    except Exception as exc:
        raise _handle_service_error(exc)

    return DocumentMetadataResponse(**result)


# ---------------------------------------------------------------------------
# GET /api/vendors/{vendor_id}/documents  — list
# ---------------------------------------------------------------------------

@router.get(
    "/{vendor_id}/documents",
    response_model=DocumentListResponse,
    summary="List all documents for a vendor",
)
async def list_documents(vendor_id: str):
    """Return metadata for every document uploaded by the specified vendor."""
    svc = _get_service()
    try:
        docs = svc.list_documents(vendor_id)
    except Exception as exc:
        raise _handle_service_error(exc)

    return DocumentListResponse(
        vendor_id=vendor_id,
        count=len(docs),
        documents=[DocumentMetadataResponse(**d) for d in docs],
    )


# ---------------------------------------------------------------------------
# GET /api/vendors/{vendor_id}/documents/{document_id}  — metadata
# ---------------------------------------------------------------------------

@router.get(
    "/{vendor_id}/documents/{document_id}",
    response_model=DocumentMetadataResponse,
    summary="Get metadata for a specific document",
)
async def get_document_metadata(vendor_id: str, document_id: str):
    """Return metadata for a single document, verifying vendor ownership."""
    svc = _get_service()
    try:
        result = svc.get_document_metadata(vendor_id, document_id)
    except Exception as exc:
        raise _handle_service_error(exc)

    return DocumentMetadataResponse(**result)


# ---------------------------------------------------------------------------
# GET /api/vendors/{vendor_id}/documents/{document_id}/download  — download
# ---------------------------------------------------------------------------

@router.get(
    "/{vendor_id}/documents/{document_id}/download",
    summary="Download a document file",
)
async def download_document(vendor_id: str, document_id: str):
    """
    Stream the raw file content for the requested document.

    Returns a ``StreamingResponse`` with the original content-type and a
    ``Content-Disposition: attachment`` header.
    """
    svc = _get_service()
    try:
        file_bytes, content_type, original_filename = svc.download_document(
            vendor_id, document_id
        )
    except Exception as exc:
        raise _handle_service_error(exc)

    headers = {
        "Content-Disposition": f'attachment; filename="{original_filename}"',
        "Content-Length": str(len(file_bytes)),
    }
    return StreamingResponse(
        io.BytesIO(file_bytes),
        media_type=content_type,
        headers=headers,
    )


# ---------------------------------------------------------------------------
# PUT /api/vendors/{vendor_id}/documents/{document_id}  — replace
# ---------------------------------------------------------------------------

@router.put(
    "/{vendor_id}/documents/{document_id}",
    response_model=DocumentMetadataResponse,
    summary="Replace an existing document",
)
async def replace_document(
    vendor_id: str,
    document_id: str,
    file: UploadFile = File(..., description="The replacement file."),
    category: str | None = Form(
        default=None,
        description="New document category (optional; inherits existing if omitted).",
    ),
):
    """
    Replace the stored file for an existing document record.

    The old GridFS file is deleted after the new file is successfully stored.
    """
    file_bytes = await file.read()
    svc = _get_service()
    try:
        result = svc.replace_document(
            vendor_id=vendor_id,
            document_id=document_id,
            file_bytes=file_bytes,
            filename=file.filename or "upload",
            category=category,
        )
    except Exception as exc:
        raise _handle_service_error(exc)

    return DocumentMetadataResponse(**result)


# ---------------------------------------------------------------------------
# DELETE /api/vendors/{vendor_id}/documents/{document_id}  — delete
# ---------------------------------------------------------------------------

@router.delete(
    "/{vendor_id}/documents/{document_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a document",
)
async def delete_document(vendor_id: str, document_id: str):
    """
    Permanently delete a document from GridFS.

    Returns HTTP 204 on success (no body).
    Returns HTTP 404 if the document does not exist or belongs to a different vendor.
    """
    svc = _get_service()
    try:
        svc.delete_document(vendor_id, document_id)
    except Exception as exc:
        raise _handle_service_error(exc)
