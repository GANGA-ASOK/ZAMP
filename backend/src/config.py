"""
VendorFlow application configuration constants.

Document upload constraints and GridFS bucket configuration are centralised
here so they can be referenced consistently from both the service layer and
route handlers.
"""

# ---------------------------------------------------------------------------
# GridFS
# ---------------------------------------------------------------------------

GRIDFS_BUCKET_NAME: str = "document_files"
"""Name of the GridFS bucket used to store vendor uploaded files."""


# ---------------------------------------------------------------------------
# File upload constraints
# ---------------------------------------------------------------------------

MAX_UPLOAD_SIZE_BYTES: int = 10 * 1024 * 1024  # 10 MB
"""Maximum permitted file size for a single document upload (10 MB)."""

ALLOWED_EXTENSIONS: frozenset[str] = frozenset({".pdf", ".jpg", ".jpeg", ".png", ".tiff"})
"""Permitted file extensions (lower-cased).  Checked against the uploaded filename."""

ALLOWED_CONTENT_TYPES: frozenset[str] = frozenset(
    {"application/pdf", "image/jpeg", "image/png", "image/tiff"}
)
"""Permitted MIME types reported by the client. Cross-validated against the
   actual file signature (magic bytes)."""


# ---------------------------------------------------------------------------
# File signature (magic bytes) → canonical MIME type
# ---------------------------------------------------------------------------
# Each key is the byte sequence that must appear at offset 0 of the file.
# Two TIFF variants (little-endian and big-endian) are both included.

FILE_SIGNATURES: dict[bytes, str] = {
    b"\x25\x50\x44\x46": "application/pdf",   # %PDF
    b"\xff\xd8\xff":      "image/jpeg",         # JPEG / JFIF / Exif
    b"\x89\x50\x4e\x47": "image/png",           # PNG
    b"\x49\x49\x2a\x00": "image/tiff",          # TIFF little-endian (II)
    b"\x4d\x4d\x00\x2a": "image/tiff",          # TIFF big-endian (MM)
}
"""Mapping of magic-byte prefixes to their canonical MIME type.
   Used by the document service to validate that the actual file content
   matches the declared content-type."""

