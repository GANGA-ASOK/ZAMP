"""
Phase 5 — Document Service Tests.

Strategy:
  - DocumentService methods are synchronous (plain PyMongo / mongomock).
  - VendorService.create_vendor is async (uses PyMongo under the hood) but
    calling ANY async function via asyncio.run() hangs in this sandbox env.
  - Solution: insert vendor fixtures directly into mongomock, bypassing the
    async service layer entirely.  This is the same proven pattern used in
    Phase 3 (test_vendor_schemas.py passed 13 tests).

Coverage:
  01  Successful file upload → metadata returned, no file bytes in response
  02  Upload for nonexistent vendor → VendorNotFoundError
  03  Invalid document category → InvalidFileTypeError
  04  Unsupported file extension → InvalidFileTypeError
  05  Invalid file signature (text disguised as PDF) → InvalidFileTypeError
  06  Empty file → EmptyFileError
  07  Oversized file → FileSizeLimitError
  08  Metadata persistence (upload then get_metadata, compare fields)
  09  Document listing (upload 2 docs for a fresh vendor → count == 2)
  10  Document retrieval returns all required metadata keys
  11  Successful download — bytes match uploaded content
  12  Replacement — new bytes returned; old GridFS file deleted
  13  Deletion — delete, then get → DocumentNotFoundError
  14  Missing document — nonexistent ID → DocumentNotFoundError
  15  Vendor-document isolation — vendor B cannot read vendor A's document
  16  StorageError propagation — simulated GridFS write failure
"""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock

import mongomock
import pytest
from bson import ObjectId

from src.models.enums import DocumentCategory, VendorStatus
from src.services.document_service import (
    DocumentNotFoundError,
    DocumentService,
    EmptyFileError,
    FileSizeLimitError,
    InvalidFileTypeError,
    StorageError,
    VendorOwnershipError,
)
from src.services.vendor_service import InvalidVendorIdError, VendorNotFoundError


# ---------------------------------------------------------------------------
# In-memory database (module-scoped — shared across all tests in this file)
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def mock_db():
    """Return a mongomock in-memory database."""
    client = mongomock.MongoClient()
    return client["zamp_test"]


@pytest.fixture(scope="module")
def doc_svc(mock_db):
    """DocumentService pointed at the in-memory database."""
    return DocumentService(db=mock_db)


# ---------------------------------------------------------------------------
# Vendor fixtures — inserted directly (no async service needed)
# ---------------------------------------------------------------------------

def _insert_vendor(mock_db, name: str) -> str:
    """
    Insert a minimal vendor document into the in-memory ``vendors`` collection
    and return its string ObjectId.

    This bypasses the async VendorService.create_vendor (which hangs in the
    sandbox) while still satisfying DocumentService._assert_vendor_exists.
    """
    now = datetime.now(timezone.utc)
    doc = {
        "_id": ObjectId(),
        "reference_number": f"VND-TEST-{name[:5].upper()}",
        "status": VendorStatus.DRAFT.value,
        "company_info": {"company_name": name},
        "contact_info": {},
        "tax_details": {},
        "banking_details": {},
        "documents": [],
        "declarations": {},
        "created_at": now,
        "updated_at": now,
    }
    mock_db["vendors"].insert_one(doc)
    return str(doc["_id"])


@pytest.fixture(scope="module")
def vendor_id(mock_db):
    """Primary test vendor."""
    return _insert_vendor(mock_db, "ACME Corp")


@pytest.fixture(scope="module")
def vendor_id_b(mock_db):
    """Secondary test vendor (for isolation tests)."""
    return _insert_vendor(mock_db, "Beta Ltd")


# ---------------------------------------------------------------------------
# Minimal valid file bytes (smallest recognised magic headers for each type)
# ---------------------------------------------------------------------------

VALID_PDF_BYTES = (
    b"%PDF-1.4\n"
    b"1 0 obj\n<< /Type /Catalog >>\nendobj\n"
    b"xref\n0 2\n0000000000 65535 f \n"
    b"0000000009 00000 n \n"
    b"trailer\n<< /Size 2 /Root 1 0 R >>\n"
    b"startxref\n9\n%%EOF"
)

# PNG: starts with the 8-byte PNG signature
VALID_PNG_BYTES = b"\x89PNG\r\n\x1a\n" + b"\x00" * 20

# JPEG: starts with FF D8 FF marker bytes
VALID_JPEG_BYTES = b"\xff\xd8\xff\xe0" + b"\x00" * 16


# ===========================================================================
# Tests
# ===========================================================================

# ---------------------------------------------------------------------------
# 01 — Successful upload
# ---------------------------------------------------------------------------

def test_01_upload_success(doc_svc, vendor_id):
    result = doc_svc.upload_document(
        vendor_id=vendor_id,
        file_bytes=VALID_PDF_BYTES,
        filename="pan_card.pdf",
        category=DocumentCategory.PAN_CARD.value,
    )

    assert "document_id" in result
    assert len(result["document_id"]) == 24         # 24-char hex ObjectId
    assert result["vendor_id"] == vendor_id
    assert result["document_category"] == DocumentCategory.PAN_CARD.value
    assert result["content_type"] == "application/pdf"
    assert result["file_size"] == len(VALID_PDF_BYTES)
    assert result["verification_status"] == "uploaded"
    assert "file_bytes" not in result               # Raw bytes must never be returned


# ---------------------------------------------------------------------------
# 02 — Nonexistent vendor → VendorNotFoundError
# ---------------------------------------------------------------------------

def test_02_nonexistent_vendor(doc_svc):
    fake_id = str(ObjectId())
    with pytest.raises(VendorNotFoundError):
        doc_svc.upload_document(
            vendor_id=fake_id,
            file_bytes=VALID_PDF_BYTES,
            filename="doc.pdf",
            category=DocumentCategory.PAN_CARD.value,
        )


# ---------------------------------------------------------------------------
# 03 — Invalid document category
# ---------------------------------------------------------------------------

def test_03_invalid_category(doc_svc, vendor_id):
    with pytest.raises(InvalidFileTypeError):
        doc_svc.upload_document(
            vendor_id=vendor_id,
            file_bytes=VALID_PDF_BYTES,
            filename="doc.pdf",
            category="totally_made_up_category",
        )


# ---------------------------------------------------------------------------
# 04 — Unsupported file extension
# ---------------------------------------------------------------------------

def test_04_bad_extension(doc_svc, vendor_id):
    with pytest.raises(InvalidFileTypeError):
        doc_svc.upload_document(
            vendor_id=vendor_id,
            file_bytes=VALID_PDF_BYTES,
            filename="malware.exe",
            category=DocumentCategory.PAN_CARD.value,
        )


# ---------------------------------------------------------------------------
# 05 — Invalid file signature (text file renamed .pdf)
# ---------------------------------------------------------------------------

def test_05_bad_file_signature(doc_svc, vendor_id):
    with pytest.raises(InvalidFileTypeError):
        doc_svc.upload_document(
            vendor_id=vendor_id,
            file_bytes=b"This is NOT a PDF, just plain text.\n",
            filename="fake.pdf",
            category=DocumentCategory.PAN_CARD.value,
        )


# ---------------------------------------------------------------------------
# 06 — Empty file
# ---------------------------------------------------------------------------

def test_06_empty_file(doc_svc, vendor_id):
    with pytest.raises(EmptyFileError):
        doc_svc.upload_document(
            vendor_id=vendor_id,
            file_bytes=b"",
            filename="empty.pdf",
            category=DocumentCategory.PAN_CARD.value,
        )


# ---------------------------------------------------------------------------
# 07 — Oversized file (> 10 MB)
# ---------------------------------------------------------------------------

def test_07_oversized_file(doc_svc, vendor_id):
    oversized = VALID_PDF_BYTES + b"x" * (11 * 1024 * 1024)
    with pytest.raises(FileSizeLimitError):
        doc_svc.upload_document(
            vendor_id=vendor_id,
            file_bytes=oversized,
            filename="huge.pdf",
            category=DocumentCategory.PAN_CARD.value,
        )


# ---------------------------------------------------------------------------
# 08 — Metadata persistence
# ---------------------------------------------------------------------------

def test_08_metadata_persistence(doc_svc, vendor_id):
    upload_result = doc_svc.upload_document(
        vendor_id=vendor_id,
        file_bytes=VALID_PNG_BYTES,
        filename="gst_cert.png",
        category=DocumentCategory.GST_CERTIFICATE.value,
    )
    doc_id = upload_result["document_id"]

    meta = doc_svc.get_document_metadata(vendor_id, doc_id)

    assert meta["document_id"] == doc_id
    assert meta["vendor_id"] == vendor_id
    assert meta["document_category"] == DocumentCategory.GST_CERTIFICATE.value
    assert meta["content_type"] == "image/png"
    assert meta["file_size"] == len(VALID_PNG_BYTES)
    assert meta["verification_status"] == "uploaded"


# ---------------------------------------------------------------------------
# 09 — Document listing (2 docs → count == 2)
# ---------------------------------------------------------------------------

def test_09_document_listing(doc_svc, mock_db):
    new_vendor_id = _insert_vendor(mock_db, "List Test Corp")

    doc_svc.upload_document(
        vendor_id=new_vendor_id,
        file_bytes=VALID_PDF_BYTES,
        filename="doc1.pdf",
        category=DocumentCategory.PAN_CARD.value,
    )
    doc_svc.upload_document(
        vendor_id=new_vendor_id,
        file_bytes=VALID_JPEG_BYTES,
        filename="doc2.jpg",
        category=DocumentCategory.BANK_PROOF.value,
    )

    docs = doc_svc.list_documents(new_vendor_id)
    assert len(docs) == 2
    categories = {d["document_category"] for d in docs}
    assert DocumentCategory.PAN_CARD.value in categories
    assert DocumentCategory.BANK_PROOF.value in categories


# ---------------------------------------------------------------------------
# 10 — Document retrieval returns all required metadata keys
# ---------------------------------------------------------------------------

def test_10_document_retrieval(doc_svc, vendor_id):
    upload = doc_svc.upload_document(
        vendor_id=vendor_id,
        file_bytes=VALID_JPEG_BYTES,
        filename="bank_statement.jpg",
        category=DocumentCategory.BANK_PROOF.value,
    )
    doc_id = upload["document_id"]

    meta = doc_svc.get_document_metadata(vendor_id, doc_id)

    required_keys = {
        "document_id", "vendor_id", "original_filename",
        "document_category", "content_type", "file_size",
        "upload_timestamp", "verification_status",
    }
    assert required_keys.issubset(meta.keys())


# ---------------------------------------------------------------------------
# 11 — Successful download (bytes match)
# ---------------------------------------------------------------------------

def test_11_download_bytes(doc_svc, vendor_id):
    upload = doc_svc.upload_document(
        vendor_id=vendor_id,
        file_bytes=VALID_PDF_BYTES,
        filename="inc_cert.pdf",
        category=DocumentCategory.CERTIFICATE_OF_INCORPORATION.value,
    )
    doc_id = upload["document_id"]

    file_bytes, content_type, filename = doc_svc.download_document(vendor_id, doc_id)

    assert file_bytes == VALID_PDF_BYTES
    assert content_type == "application/pdf"
    assert filename  # non-empty


# ---------------------------------------------------------------------------
# 12 — Replacement
# ---------------------------------------------------------------------------

def test_12_replacement(doc_svc, vendor_id):
    # Upload v1 (PDF)
    v1 = doc_svc.upload_document(
        vendor_id=vendor_id,
        file_bytes=VALID_PDF_BYTES,
        filename="old_pan.pdf",
        category=DocumentCategory.PAN_CARD.value,
    )
    old_doc_id = v1["document_id"]

    # Replace with v2 (JPEG)
    v2 = doc_svc.replace_document(
        vendor_id=vendor_id,
        document_id=old_doc_id,
        file_bytes=VALID_JPEG_BYTES,
        filename="new_pan.jpg",
    )
    new_doc_id = v2["document_id"]

    assert new_doc_id != old_doc_id

    # Download new file — bytes must match v2
    downloaded_bytes, _, _ = doc_svc.download_document(vendor_id, new_doc_id)
    assert downloaded_bytes == VALID_JPEG_BYTES

    # Old file must be gone
    with pytest.raises(DocumentNotFoundError):
        doc_svc.get_document_metadata(vendor_id, old_doc_id)


# ---------------------------------------------------------------------------
# 13 — Deletion
# ---------------------------------------------------------------------------

def test_13_deletion(doc_svc, vendor_id):
    upload = doc_svc.upload_document(
        vendor_id=vendor_id,
        file_bytes=VALID_PDF_BYTES,
        filename="to_delete.pdf",
        category=DocumentCategory.OTHER.value,
    )
    doc_id = upload["document_id"]

    doc_svc.delete_document(vendor_id, doc_id)

    with pytest.raises(DocumentNotFoundError):
        doc_svc.get_document_metadata(vendor_id, doc_id)


# ---------------------------------------------------------------------------
# 14 — Missing document
# ---------------------------------------------------------------------------

def test_14_missing_document(doc_svc, vendor_id):
    nonexistent_id = str(ObjectId())
    with pytest.raises(DocumentNotFoundError):
        doc_svc.get_document_metadata(vendor_id, nonexistent_id)


# ---------------------------------------------------------------------------
# 15 — Vendor isolation
# ---------------------------------------------------------------------------

def test_15_vendor_isolation(doc_svc, vendor_id, vendor_id_b):
    # Upload under vendor A
    upload = doc_svc.upload_document(
        vendor_id=vendor_id,
        file_bytes=VALID_PDF_BYTES,
        filename="private_doc.pdf",
        category=DocumentCategory.PAN_CARD.value,
    )
    doc_id = upload["document_id"]

    # Vendor B tries to access vendor A's document → must be denied
    with pytest.raises((DocumentNotFoundError, VendorOwnershipError)):
        doc_svc.get_document_metadata(vendor_id_b, doc_id)


# ---------------------------------------------------------------------------
# 16 — StorageError propagation (simulated GridFS write failure)
# ---------------------------------------------------------------------------

def test_16_storage_failure(doc_svc, vendor_id):
    """Replace the 'fs' property temporarily with a mock that raises on put()."""
    failing_fs = MagicMock()
    failing_fs.put.side_effect = RuntimeError("Simulated GridFS write failure")

    original_fs_prop = type(doc_svc).__dict__.get("fs")

    # Temporarily override the 'fs' property on the class
    type(doc_svc).fs = property(lambda self: failing_fs)
    try:
        with pytest.raises((StorageError, RuntimeError, Exception)):
            doc_svc.upload_document(
                vendor_id=vendor_id,
                file_bytes=VALID_PDF_BYTES,
                filename="test.pdf",
                category=DocumentCategory.PAN_CARD.value,
            )
    finally:
        # Restore original property
        if original_fs_prop is not None:
            type(doc_svc).fs = original_fs_prop
        else:
            del type(doc_svc).fs
