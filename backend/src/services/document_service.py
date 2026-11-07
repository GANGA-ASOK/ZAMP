"""
Document storage service for VendorFlow — Phase 5.

Uses PyMongo's synchronous GridFS API (``gridfs.GridFS``) to store and
retrieve vendor-uploaded files inside the MongoDB Atlas ``zamp`` database.

Design decisions
----------------
* We deliberately do NOT use ``asyncio.to_thread()`` / ``run_in_executor``
  because that pattern caused event-loop deadlocks in the test environment
  (see Phase 4 post-mortem).  Direct synchronous PyMongo calls inside async
  FastAPI route handlers are safe and correct for this workload.
* GridFS bucket name: ``document_files``  (creates ``document_files.files``
  and ``document_files.chunks`` collections automatically).
* The ``db`` property falls back to the global ``mongo_module.db`` so the
  service works both in production (after lifespan) and in unit tests (by
  passing a mock db directly).

Security note (Phase 7)
-----------------------
Vendor-ownership checks are based solely on the ``vendor_id`` path parameter
supplied by the client.  Any caller who knows a valid vendor ID can access its
documents.  Proper JWT / session-based authorization MUST be added in Phase 7
before this API is exposed publicly.
"""

from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from typing import Any

import gridfs
from bson import ObjectId
from pymongo.database import Database

import src.database.mongodb as mongo_module
from src.config import (
    ALLOWED_CONTENT_TYPES,
    ALLOWED_EXTENSIONS,
    FILE_SIGNATURES,
    GRIDFS_BUCKET_NAME,
    MAX_UPLOAD_SIZE_BYTES,
)
from src.models.enums import DocumentCategory, DocumentVerificationStatus

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Custom exceptions
# ---------------------------------------------------------------------------

class DocumentServiceError(Exception):
    """Base exception for document service errors."""


class DocumentNotFoundError(DocumentServiceError):
    """Raised when a GridFS file cannot be found."""
    def __init__(self, document_id: str):
        super().__init__(f"Document '{document_id}' not found.")
        self.document_id = document_id


class InvalidDocumentIdError(DocumentServiceError):
    """Raised when a document ID is not a valid ObjectId."""
    def __init__(self, document_id: str):
        super().__init__(f"Invalid document ID '{document_id}'.")
        self.document_id = document_id


class FileSizeLimitError(DocumentServiceError):
    """Raised when an uploaded file exceeds the size limit."""
    def __init__(self, actual: int, limit: int):
        super().__init__(
            f"File size {actual} bytes exceeds the {limit // (1024 * 1024)} MB limit."
        )
        self.actual = actual
        self.limit = limit


class EmptyFileError(DocumentServiceError):
    """Raised when an uploaded file contains no bytes."""


class InvalidFileTypeError(DocumentServiceError):
    """Raised when file extension or magic bytes are not permitted."""
    def __init__(self, reason: str):
        super().__init__(reason)


class VendorOwnershipError(DocumentServiceError):
    """Raised when the document does not belong to the requested vendor."""
    def __init__(self, document_id: str, vendor_id: str):
        super().__init__(
            f"Document '{document_id}' does not belong to vendor '{vendor_id}'."
        )


class StorageError(DocumentServiceError):
    """Raised when a GridFS read/write operation fails unexpectedly."""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _sanitize_filename(filename: str) -> str:
    """
    Replace any character that is not alphanumeric, hyphen, underscore,
    or period with an underscore.  Collapses consecutive underscores.
    """
    safe = re.sub(r"[^\w\-.]", "_", filename)
    safe = re.sub(r"_+", "_", safe).strip("_")
    return safe or "upload"


def _validate_object_id(document_id: str) -> ObjectId:
    """Return parsed ObjectId or raise InvalidDocumentIdError."""
    if not ObjectId.is_valid(document_id):
        raise InvalidDocumentIdError(document_id)
    return ObjectId(document_id)


def _detect_mime_from_bytes(file_bytes: bytes) -> str | None:
    """Return the MIME type deduced from magic bytes, or None if unknown."""
    for sig, mime in FILE_SIGNATURES.items():
        if file_bytes.startswith(sig):
            return mime
    return None


def _validate_file(file_bytes: bytes, filename: str) -> str:
    """
    Run all pre-storage file checks.

    Returns the detected MIME type on success.
    Raises EmptyFileError, FileSizeLimitError, or InvalidFileTypeError on failure.
    """
    if not file_bytes:
        raise EmptyFileError("Uploaded file is empty.")

    if len(file_bytes) > MAX_UPLOAD_SIZE_BYTES:
        raise FileSizeLimitError(len(file_bytes), MAX_UPLOAD_SIZE_BYTES)

    # Extension check (case-insensitive)
    suffix = ""
    if "." in filename:
        suffix = "." + filename.rsplit(".", 1)[-1].lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise InvalidFileTypeError(
            f"File extension '{suffix}' is not permitted. "
            f"Allowed: {sorted(ALLOWED_EXTENSIONS)}"
        )

    # Magic-byte check
    detected_mime = _detect_mime_from_bytes(file_bytes)
    if detected_mime is None:
        raise InvalidFileTypeError(
            "File content does not match any recognised format "
            "(PDF, JPEG, PNG, TIFF)."
        )

    if detected_mime not in ALLOWED_CONTENT_TYPES:
        raise InvalidFileTypeError(
            f"Detected file type '{detected_mime}' is not permitted."
        )

    return detected_mime


def _gridfs_meta_to_response(grid_file: Any) -> dict[str, Any]:
    """Convert a GridFS file object to a plain dict suitable for the response schema."""
    meta: dict[str, Any] = grid_file.metadata or {}
    return {
        "document_id": str(grid_file._id),
        "vendor_id":   meta.get("vendor_id", ""),
        "original_filename": meta.get("original_filename", grid_file.filename or ""),
        "document_category": meta.get("document_category", ""),
        "content_type": meta.get("content_type", ""),
        "file_size":    meta.get("file_size", grid_file.length),
        "upload_timestamp": meta.get("upload_timestamp", ""),
        "verification_status": meta.get(
            "verification_status", DocumentVerificationStatus.UPLOADED.value
        ),
    }


# ---------------------------------------------------------------------------
# Document Service
# ---------------------------------------------------------------------------

class DocumentService:
    """
    Encapsulates all GridFS operations for vendor document management.

    Pass ``db`` explicitly to use a mock database in unit tests; omit it
    to fall through to the global ``mongo_module.db`` in production.
    """

    def __init__(self, db: Database | None = None):
        self._db = db

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def db(self) -> Database:
        # PyMongo Database objects raise on bool(), so never use `or` here.
        db = self._db if self._db is not None else mongo_module.db
        if db is None:
            raise RuntimeError(
                "Database not initialised. Ensure connect_to_mongodb() has been called."
            )
        return db

    @property
    def fs(self) -> gridfs.GridFS:
        """Return a fresh GridFS handle for the document_files bucket."""
        return gridfs.GridFS(self.db, collection=GRIDFS_BUCKET_NAME)

    @property
    def vendors(self):
        """Direct access to the vendors collection (for existence checks)."""
        return self.db["vendors"]

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _assert_vendor_exists(self, vendor_id: str) -> None:
        """Raise DocumentNotFoundError (repurposed) if vendor not found."""
        from src.services.vendor_service import InvalidVendorIdError, VendorNotFoundError
        if not ObjectId.is_valid(vendor_id):
            raise InvalidVendorIdError(vendor_id)
        doc = self.vendors.find_one({"_id": ObjectId(vendor_id)})
        if doc is None:
            raise VendorNotFoundError(vendor_id)

    def _get_grid_file(self, document_id: str, vendor_id: str) -> Any:
        """
        Retrieve a GridFS file object by ID and validate vendor ownership.
        Raises InvalidDocumentIdError, DocumentNotFoundError, VendorOwnershipError.
        """
        oid = _validate_object_id(document_id)
        fs = self.fs
        try:
            grid_out = fs.get(oid)
        except gridfs.errors.NoFile:
            raise DocumentNotFoundError(document_id)
        except Exception as exc:
            raise StorageError(f"GridFS read failed: {exc}") from exc

        meta = grid_out.metadata or {}
        if meta.get("vendor_id") != vendor_id:
            raise VendorOwnershipError(document_id, vendor_id)

        return grid_out

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def upload_document(
        self,
        vendor_id: str,
        file_bytes: bytes,
        filename: str,
        category: str,
        content_type: str | None = None,
    ) -> dict[str, Any]:
        """
        Validate and store a document in GridFS.

        Parameters
        ----------
        vendor_id:
            String ObjectId of the vendor who owns this document.
        file_bytes:
            Raw file content.
        filename:
            Original filename supplied by the client.
        category:
            One of the ``DocumentCategory`` enum values.
        content_type:
            MIME type as declared by the HTTP client (optional; will be
            cross-validated against magic bytes).

        Returns
        -------
        dict
            Document metadata dict ready to be fed into ``DocumentMetadataResponse``.
        """
        # 1. Validate vendor existence
        self._assert_vendor_exists(vendor_id)

        # 2. Validate document category
        try:
            DocumentCategory(category)
        except ValueError:
            valid = [e.value for e in DocumentCategory]
            raise InvalidFileTypeError(
                f"Invalid document category '{category}'. Valid values: {valid}"
            )

        # 3. Validate file content
        safe_name = _sanitize_filename(filename)
        detected_mime = _validate_file(file_bytes, safe_name)

        # Use detected MIME (more trustworthy than client-declared)
        final_content_type = detected_mime

        # 4. Build metadata
        now = _utcnow()
        metadata: dict[str, Any] = {
            "vendor_id":           vendor_id,
            "original_filename":   safe_name,
            "document_category":   category,
            "content_type":        final_content_type,
            "file_size":           len(file_bytes),
            "upload_timestamp":    now.isoformat(),
            "verification_status": DocumentVerificationStatus.UPLOADED.value,
        }

        # 5. Store in GridFS
        try:
            fs = self.fs
            file_id = fs.put(
                file_bytes,
                filename=safe_name,
                content_type=final_content_type,
                metadata=metadata,
            )
        except Exception as exc:
            logger.error("GridFS upload failed for vendor %s: %s", vendor_id, exc)
            raise StorageError(f"Failed to store document: {exc}") from exc

        # 6. Synchronize with vendors collection documents array
        doc_entry = {
            "document_id":         str(file_id),
            "category":            category,
            "file_name":           safe_name,
            "file_size":           len(file_bytes),
            "file_type":           final_content_type,
            "storage_path":        f"gridfs://{GRIDFS_BUCKET_NAME}/{file_id}",
            "verification_status": DocumentVerificationStatus.UPLOADED.value,
            "uploaded_at":         now.isoformat(),
            "verified_at":         "",
            "rejection_reason":    "",
        }
        try:
            # If replacing an existing document of same single-value category, pull first
            if category != DocumentCategory.OTHER.value:
                self.vendors.update_one(
                    {"_id": ObjectId(vendor_id)},
                    {"$pull": {"documents": {"category": category}}},
                )
            self.vendors.update_one(
                {"_id": ObjectId(vendor_id)},
                {
                    "$push": {"documents": doc_entry},
                    "$set": {"updated_at": now},
                },
            )
        except Exception as exc:
            logger.warning("Failed to sync uploaded document into vendors collection: %s", exc)

        logger.info(
            "Document uploaded — vendor=%s category=%s file_id=%s size=%d",
            vendor_id, category, file_id, len(file_bytes),
        )

        return {
            "document_id":         str(file_id),
            "vendor_id":           vendor_id,
            "original_filename":   safe_name,
            "document_category":   category,
            "content_type":        final_content_type,
            "file_size":           len(file_bytes),
            "upload_timestamp":    now.isoformat(),
            "verification_status": DocumentVerificationStatus.UPLOADED.value,
        }

    def list_documents(self, vendor_id: str) -> list[dict[str, Any]]:
        """
        Return metadata for all documents belonging to ``vendor_id``.
        Does NOT validate vendor existence — returns empty list if none found.
        """
        # Validate vendor_id format
        if not ObjectId.is_valid(vendor_id):
            from src.services.vendor_service import InvalidVendorIdError
            raise InvalidVendorIdError(vendor_id)

        fs = self.fs
        try:
            # Query the files collection directly (most efficient for listing)
            files_col = self.db[f"{GRIDFS_BUCKET_NAME}.files"]
            cursor = files_col.find({"metadata.vendor_id": vendor_id})
            results = []
            for file_doc in cursor:
                meta = file_doc.get("metadata") or {}
                results.append({
                    "document_id":         str(file_doc["_id"]),
                    "vendor_id":           meta.get("vendor_id", vendor_id),
                    "original_filename":   meta.get("original_filename", file_doc.get("filename", "")),
                    "document_category":   meta.get("document_category", ""),
                    "content_type":        meta.get("content_type", file_doc.get("contentType", "")),
                    "file_size":           meta.get("file_size", file_doc.get("length", 0)),
                    "upload_timestamp":    meta.get("upload_timestamp", ""),
                    "verification_status": meta.get("verification_status", DocumentVerificationStatus.UPLOADED.value),
                })
            return results
        except Exception as exc:
            logger.error("GridFS list failed for vendor %s: %s", vendor_id, exc)
            raise StorageError(f"Failed to list documents: {exc}") from exc

    def get_document_metadata(self, vendor_id: str, document_id: str) -> dict[str, Any]:
        """
        Return metadata for a single document, verifying vendor ownership.
        """
        grid_out = self._get_grid_file(document_id, vendor_id)
        return _gridfs_meta_to_response(grid_out)

    def download_document(self, vendor_id: str, document_id: str) -> tuple[bytes, str, str]:
        """
        Return (file_bytes, content_type, filename) for the requested document.
        Verifies vendor ownership before returning data.
        """
        grid_out = self._get_grid_file(document_id, vendor_id)
        try:
            file_bytes = grid_out.read()
        except Exception as exc:
            raise StorageError(f"Failed to read document from GridFS: {exc}") from exc

        meta = grid_out.metadata or {}
        content_type = meta.get("content_type") or grid_out.content_type or "application/octet-stream"
        original_filename = meta.get("original_filename") or grid_out.filename or document_id

        return file_bytes, content_type, original_filename

    def replace_document(
        self,
        vendor_id: str,
        document_id: str,
        file_bytes: bytes,
        filename: str,
        category: str | None = None,
    ) -> dict[str, Any]:
        """
        Replace an existing document with a new file.

        Steps:
        1. Verify old document exists and belongs to vendor.
        2. Validate new file.
        3. Upload new file to GridFS (inheriting old category if not supplied).
        4. Delete old GridFS file.
        """
        # Retrieve old file for category inheritance and ownership check
        old_grid = self._get_grid_file(document_id, vendor_id)
        old_meta = old_grid.metadata or {}
        inherited_category = category or old_meta.get("document_category", "other")

        # Validate new file content
        safe_name = _sanitize_filename(filename)
        detected_mime = _validate_file(file_bytes, safe_name)

        now = _utcnow()
        new_metadata: dict[str, Any] = {
            "vendor_id":           vendor_id,
            "original_filename":   safe_name,
            "document_category":   inherited_category,
            "content_type":        detected_mime,
            "file_size":           len(file_bytes),
            "upload_timestamp":    now.isoformat(),
            "verification_status": DocumentVerificationStatus.UPLOADED.value,
        }

        # Upload replacement
        try:
            fs = self.fs
            new_file_id = fs.put(
                file_bytes,
                filename=safe_name,
                content_type=detected_mime,
                metadata=new_metadata,
            )
        except Exception as exc:
            raise StorageError(f"Failed to store replacement document: {exc}") from exc

        # Delete the old file
        try:
            self.fs.delete(ObjectId(document_id))
        except Exception as exc:
            logger.warning(
                "Could not delete old GridFS file %s after replacement: %s",
                document_id, exc,
            )

        # Synchronize with vendors collection
        new_entry = {
            "document_id":         str(new_file_id),
            "category":            inherited_category,
            "file_name":           safe_name,
            "file_size":           len(file_bytes),
            "file_type":           detected_mime,
            "storage_path":        f"gridfs://{GRIDFS_BUCKET_NAME}/{new_file_id}",
            "verification_status": DocumentVerificationStatus.UPLOADED.value,
            "uploaded_at":         now.isoformat(),
            "verified_at":         "",
            "rejection_reason":    "",
        }
        try:
            res = self.vendors.update_one(
                {"_id": ObjectId(vendor_id), "documents.document_id": document_id},
                {
                    "$set": {
                        "documents.$": new_entry,
                        "updated_at": now,
                    }
                },
            )
            if res.matched_count == 0:
                self.vendors.update_one(
                    {"_id": ObjectId(vendor_id)},
                    {"$push": {"documents": new_entry}, "$set": {"updated_at": now}},
                )
        except Exception as exc:
            logger.warning("Could not sync replaced document to vendors collection: %s", exc)

        logger.info(
            "Document replaced — vendor=%s old=%s new=%s",
            vendor_id, document_id, new_file_id,
        )

        return {
            "document_id":         str(new_file_id),
            "vendor_id":           vendor_id,
            "original_filename":   safe_name,
            "document_category":   inherited_category,
            "content_type":        detected_mime,
            "file_size":           len(file_bytes),
            "upload_timestamp":    now.isoformat(),
            "verification_status": DocumentVerificationStatus.UPLOADED.value,
        }

    def delete_document(self, vendor_id: str, document_id: str) -> None:
        """
        Delete a document from GridFS after verifying vendor ownership.
        """
        # Verify ownership (raises if not found or wrong vendor)
        self._get_grid_file(document_id, vendor_id)

        try:
            self.fs.delete(ObjectId(document_id))
        except Exception as exc:
            raise StorageError(f"Failed to delete document from GridFS: {exc}") from exc

        # Synchronize deletion from vendors collection
        try:
            self.vendors.update_one(
                {"_id": ObjectId(vendor_id)},
                {
                    "$pull": {"documents": {"document_id": document_id}},
                    "$set": {"updated_at": _utcnow()},
                },
            )
        except Exception as exc:
            logger.warning("Could not remove document %s from vendors collection: %s", document_id, exc)

        logger.info("Document deleted — vendor=%s document=%s", vendor_id, document_id)

    def update_document_status(
        self,
        vendor_id: str,
        document_id: str,
        verification_status: str,
        rejection_reason: str = "",
    ) -> None:
        """Update verification status in both GridFS metadata and vendors collection."""
        now = _utcnow()
        try:
            files_col = self.db[f"{GRIDFS_BUCKET_NAME}.files"]
            files_col.update_one(
                {"_id": ObjectId(document_id), "metadata.vendor_id": vendor_id},
                {
                    "$set": {
                        "metadata.verification_status": verification_status,
                        "metadata.verified_at": now.isoformat(),
                    }
                },
            )
        except Exception as exc:
            logger.warning("Failed to update GridFS verification metadata: %s", exc)

        try:
            self.vendors.update_one(
                {"_id": ObjectId(vendor_id), "documents.document_id": document_id},
                {
                    "$set": {
                        "documents.$.verification_status": verification_status,
                        "documents.$.verified_at": now.isoformat(),
                        "documents.$.rejection_reason": rejection_reason,
                        "updated_at": now,
                    }
                },
            )
        except Exception as exc:
            logger.warning("Failed to update vendor document verification status: %s", exc)
