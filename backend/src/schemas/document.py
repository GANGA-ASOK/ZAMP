"""
Document schemas for the VendorFlow API.

Defines Pydantic v2 models for document upload responses, metadata responses,
and document listing responses.  These are intentionally kept separate from
vendor schemas to maintain a clean separation of concerns.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------------------
# Document upload / metadata response
# ---------------------------------------------------------------------------

class DocumentMetadataResponse(BaseModel):
    """
    Returned after a successful upload or when fetching document metadata.

    Intentionally omits raw file bytes — the caller must use the dedicated
    download endpoint to retrieve file content.
    """

    model_config = ConfigDict(populate_by_name=True)

    document_id: str = Field(..., description="GridFS file ObjectId (string).")
    vendor_id: str = Field(..., description="Owning vendor ObjectId (string).")
    original_filename: str = Field(..., description="Sanitised original filename.")
    document_category: str = Field(..., description="DocumentCategory enum value.")
    content_type: str = Field(..., description="MIME type of the stored file.")
    file_size: int = Field(..., description="File size in bytes.")
    upload_timestamp: str = Field(..., description="ISO-8601 upload timestamp (UTC).")
    verification_status: str = Field(
        ..., description="DocumentVerificationStatus enum value."
    )


# ---------------------------------------------------------------------------
# Document list response
# ---------------------------------------------------------------------------

class DocumentListResponse(BaseModel):
    """
    Returned when listing all documents belonging to a vendor.
    """

    model_config = ConfigDict(populate_by_name=True)

    vendor_id: str = Field(..., description="Owning vendor ObjectId (string).")
    count: int = Field(..., description="Total number of documents found.")
    documents: list[DocumentMetadataResponse] = Field(
        default_factory=list, description="List of document metadata records."
    )

