"""
Document file validation and page-image preprocessing for NVIDIA Nemotron Parse.

Renders PDF pages into base64-encoded JPEG images suitable for multimodal
input to Nemotron 3.5 Parse, and preprocesses image files.
"""

from __future__ import annotations

import base64
import io
import logging
from typing import NamedTuple

import pymupdf as fitz  # PyMuPDF
from PIL import Image

from src.config import ALLOWED_EXTENSIONS, FILE_SIGNATURES, MAX_UPLOAD_SIZE_BYTES

logger = logging.getLogger(__name__)


class PreprocessingError(Exception):
    """Raised when file preprocessing fails."""


class PageImage(NamedTuple):
    page_number: int
    image_bytes: bytes
    base64_data_uri: str
    embedded_text: str = ""


class DocumentPreprocessor:
    """Prepares PDF and image documents for NVIDIA Nemotron 3.5 Parse."""

    @staticmethod
    def validate_file_bytes(
        file_bytes: bytes,
        filename: str,
    ) -> str:
        """
        Validate technical integrity, size, and magic bytes.
        Returns detected canonical MIME type or raises PreprocessingError.
        """
        if not file_bytes:
            raise PreprocessingError("The uploaded file is empty (0 bytes).")

        if len(file_bytes) > MAX_UPLOAD_SIZE_BYTES:
            raise PreprocessingError(
                f"File size exceeds maximum permitted limit of {MAX_UPLOAD_SIZE_BYTES // (1024*1024)} MB."
            )

        # Validate magic bytes against configured signatures
        detected_mime = None
        for sig, mime in FILE_SIGNATURES.items():
            if file_bytes.startswith(sig):
                detected_mime = mime
                break

        if not detected_mime:
            raise PreprocessingError(
                f"Unsupported or corrupted file format. Magic byte signature did not match supported types."
            )

        # Validate extension
        lower_name = filename.lower()
        if not any(lower_name.endswith(ext) for ext in ALLOWED_EXTENSIONS):
            raise PreprocessingError(
                f"File extension is not permitted. Supported: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
            )

        return detected_mime

    @classmethod
    def render_pages_for_parse(
        cls,
        file_bytes: bytes,
        mime_type: str,
        max_pages: int = 10,
    ) -> list[PageImage]:
        """
        Render document pages to base64 JPEG images for Nemotron 3.5 Parse.
        Also extracts any embedded PDF text to complement vision analysis.
        """
        if mime_type == "application/pdf":
            return cls._render_pdf(file_bytes, max_pages=max_pages)
        elif mime_type.startswith("image/"):
            return [cls._preprocess_image(file_bytes)]
        else:
            raise PreprocessingError(f"Cannot render pages for MIME type: {mime_type}")

    @classmethod
    def _render_pdf(cls, file_bytes: bytes, max_pages: int = 10) -> list[PageImage]:
        """Render each PDF page using PyMuPDF at ~150 DPI into JPEG."""
        try:
            doc = fitz.open(stream=file_bytes, filetype="pdf")
        except Exception as exc:
            raise PreprocessingError(f"Failed to open PDF document: {exc}")

        if doc.page_count == 0:
            doc.close()
            raise PreprocessingError("The PDF contains no pages.")

        pages_to_process = min(doc.page_count, max_pages)
        results: list[PageImage] = []

        try:
            # Zoom matrix for ~150 DPI (72 dpi * 2.0833 = 150 dpi)
            zoom = 2.0
            mat = fitz.Matrix(zoom, zoom)

            for i in range(pages_to_process):
                page = doc.load_page(i)
                # Respect rotation if embedded
                if page.rotation != 0:
                    page.set_rotation(0)

                pix = page.get_pixmap(matrix=mat, alpha=False)
                img_bytes = pix.tobytes("jpeg")

                # Extract selectable text directly if present
                embedded_text = page.get_text("text").strip()

                b64_str = base64.b64encode(img_bytes).decode("utf-8")
                data_uri = f"data:image/jpeg;base64,{b64_str}"

                results.append(
                    PageImage(
                        page_number=i + 1,
                        image_bytes=img_bytes,
                        base64_data_uri=data_uri,
                        embedded_text=embedded_text,
                    )
                )
        finally:
            doc.close()

        logger.info("Rendered %d PDF pages for Nemotron Parse.", len(results))
        return results

    @classmethod
    def _preprocess_image(cls, file_bytes: bytes) -> PageImage:
        """Process and normalize standalone image (JPG, PNG) for Nemotron Parse."""
        try:
            with Image.open(io.BytesIO(file_bytes)) as img:
                # Convert RGBA/Palette to standard RGB
                if img.mode != "RGB":
                    img = img.convert("RGB")

                # Resize if oversized (max width/height 2048) preserving aspect ratio
                max_dim = 2048
                if img.width > max_dim or img.height > max_dim:
                    img.thumbnail((max_dim, max_dim), Image.Resampling.LANCZOS)

                buf = io.BytesIO()
                img.save(buf, format="JPEG", quality=90)
                jpeg_bytes = buf.getvalue()

                b64_str = base64.b64encode(jpeg_bytes).decode("utf-8")
                data_uri = f"data:image/jpeg;base64,{b64_str}"

                return PageImage(
                    page_number=1,
                    image_bytes=jpeg_bytes,
                    base64_data_uri=data_uri,
                    embedded_text="",
                )
        except Exception as exc:
            raise PreprocessingError(f"Failed to process image document: {exc}")

