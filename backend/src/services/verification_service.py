"""
Verification orchestration service for VendorFlow.

Coordinates file retrieval from GridFS, preprocessing, Nemotron 3.5 Parse extraction,
deterministic Python validation, Nemotron 3.5 Super VL cross-document reasoning,
and persistence into the ``verification_results`` MongoDB collection.
"""

from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from typing import Any

from bson import ObjectId
from pymongo import ASCENDING
from pymongo.database import Database

import src.database.mongodb as mongodb_module
from src.schemas.verification import (
    ConsistencyFinding,
    FieldValidationFinding,
    ParsedPageResult,
    VerificationResultResponse,
)
from src.services.document_service import DocumentNotFoundError, DocumentService
from src.services.extraction.preprocessor import DocumentPreprocessor, PreprocessingError
from src.services.nvidia_parse_service import NvidiaParseError, NvidiaParseService
from src.services.nvidia_super_vl_service import NvidiaSuperVLService
from src.services.vendor_service import VendorNotFoundError, VendorService
from src.services.verification.field_validator import DeterministicFieldValidator

logger = logging.getLogger(__name__)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class VerificationService:
    """Orchestrates end-to-end document extraction and AI verification."""

    def __init__(self, db: Database | None = None) -> None:
        if db is not None:
            self._db = db
        elif mongodb_module.db is not None:
            self._db = mongodb_module.db
        else:
            raise RuntimeError("Database connection not initialized.")

        self.parse_service = NvidiaParseService()
        self.super_vl_service = NvidiaSuperVLService()

    @property
    def verification_col(self):
        return self._db["verification_results"]

    @property
    def vendors_col(self):
        return self._db["vendors"]

    def ensure_indexes(self) -> None:
        """Create indexes on verification_results collection."""
        try:
            self.verification_col.create_index(
                [("vendor_id", ASCENDING), ("document_id", ASCENDING)],
                unique=True,
                name="vendor_doc_verification_idx",
            )
            self.verification_col.create_index([("status", ASCENDING)])
            self.verification_col.create_index([("created_at", ASCENDING)])
        except Exception as exc:
            logger.warning("Verification index notice: %s", exc)

    async def execute_verification(
        self,
        vendor_id: str,
        document_id: str,
    ) -> dict[str, Any]:
        """
        Execute full verification pipeline for a vendor document.
        Can run synchronously or as a FastAPI BackgroundTask.
        """
        start_time = time.time()
        logger.info("Starting verification for vendor=%s, document=%s", vendor_id, document_id)

        # 1. Fetch vendor & document metadata
        vendor_svc = VendorService(self._db)
        doc_svc = DocumentService(self._db)

        raw_vendor = await vendor_svc.get_raw_vendor_doc(vendor_id)
        doc_meta = doc_svc.get_document_metadata(vendor_id, document_id)

        category = doc_meta.get("document_category") or doc_meta.get("category", "other")
        filename = doc_meta.get("original_filename") or doc_meta.get("file_name", "document")

        # 2. Duplicate processing check: check if already running
        existing_res = self.verification_col.find_one(
            {"vendor_id": vendor_id, "document_id": document_id}
        )
        if existing_res and existing_res.get("extraction_status") == "processing":
            logger.info("Verification for document %s is already running.", document_id)
            existing_res["id"] = str(existing_res.pop("_id"))
            return existing_res

        # Set status to processing
        now = _utcnow()
        self.verification_col.update_one(
            {"vendor_id": vendor_id, "document_id": document_id},
            {
                "$set": {
                    "extraction_status": "processing",
                    "verification_status": "processing",
                    "document_category": category,
                    "file_name": filename,
                    "updated_at": now,
                },
                "$setOnInsert": {
                    "created_at": now,
                    "parsed_pages": [],
                    "parsed_text": "",
                    "extracted_fields": {},
                    "field_validations": [],
                    "consistency_findings": [],
                },
            },
            upsert=True,
        )

        try:
            # 3. Download document bytes from GridFS
            file_bytes, content_type, orig_filename = doc_svc.download_document(vendor_id, document_id)

            # 4. Technical file validation
            detected_mime = DocumentPreprocessor.validate_file_bytes(file_bytes, orig_filename)

            # 5. Check if cached parse results exist (so Super VL comparison retries skip re-parsing)
            cached_pages = existing_res.get("parsed_pages", []) if existing_res else []
            cached_text = existing_res.get("parsed_text", "") if existing_res else ""

            parsed_pages: list[ParsedPageResult] = []
            parsed_text = ""
            # Exact text layer of born-digital PDFs (empty for scans / images).
            embedded_text = existing_res.get("embedded_text", "") if existing_res else ""

            if cached_pages and cached_text:
                logger.info("Using cached Nemotron Parse results for document %s", document_id)
                parsed_pages = [ParsedPageResult(**p) for p in cached_pages]
                parsed_text = cached_text
            else:
                # Render pages & run Nemotron 3.5 Parse
                page_images = DocumentPreprocessor.render_pages_for_parse(file_bytes, detected_mime)
                embedded_text = "\n".join(p.embedded_text for p in page_images if p.embedded_text)
                parsed_pages = await self.parse_service.parse_pages(page_images)
                parsed_text = "\n\n--- Page Break ---\n\n".join([p.text for p in parsed_pages if p.text])

            # 6. Extract fields & cross-document reasoning via Nemotron 3.5 Super VL
            super_vl_output = await self.super_vl_service.extract_and_verify(
                document_category=category,
                parsed_text=parsed_text,
                vendor_data=raw_vendor,
            )

            extracted_fields = super_vl_output.get("extracted_fields", {})
            consistency_findings = super_vl_output.get("consistency_findings", [])
            super_vl_status = super_vl_output.get("verification_status", "completed")
            summary_explanation = super_vl_output.get("summary_explanation", "")

            # 7. Deterministic Python field validation
            field_validations = DeterministicFieldValidator.run_all_field_validations(
                document_category=category,
                extracted_fields=extracted_fields,
            )

            # If any deterministic check failed, flag or mark for manual review
            failed_field_checks = [v for v in field_validations if not v.is_valid]
            if failed_field_checks and super_vl_status == "completed":
                super_vl_status = "flagged"
                summary_explanation += f" ({len(failed_field_checks)} format validation check(s) failed)."

            duration_ms = int((time.time() - start_time) * 1000)

            # 8. Persist results in MongoDB
            result_doc = {
                "vendor_id": vendor_id,
                "document_id": document_id,
                "document_category": category,
                "file_name": orig_filename,
                "extraction_status": "completed",
                "verification_status": super_vl_status,
                "parsed_pages": [p.model_dump() for p in parsed_pages],
                "parsed_text": parsed_text,
                "embedded_text": embedded_text,
                "extracted_fields": extracted_fields,
                "field_validations": [f.model_dump() for f in field_validations],
                "consistency_findings": [c.model_dump() for c in consistency_findings],
                "summary_explanation": summary_explanation,
                "parse_model_id": self.parse_service.model_id,
                "super_vl_model_id": self.super_vl_service.model_id,
                "processing_version": "1.0.0",
                "processing_time_ms": duration_ms,
                "error_details": None,
                "updated_at": _utcnow(),
            }

            self.verification_col.update_one(
                {"vendor_id": vendor_id, "document_id": document_id},
                {"$set": result_doc},
                upsert=True,
            )

            # 9. Update document verification_status in vendors collection
            self.vendors_col.update_one(
                {"_id": ObjectId(vendor_id), "documents.document_id": document_id},
                {
                    "$set": {
                        "documents.$.verification_status": super_vl_status,
                        "documents.$.verified_at": _utcnow().isoformat(),
                        "updated_at": _utcnow(),
                    }
                },
            )

            logger.info(
                "Verification completed for document %s (status=%s, time=%dms)",
                document_id,
                super_vl_status,
                duration_ms,
            )
            saved = self.verification_col.find_one({"vendor_id": vendor_id, "document_id": document_id})
            saved["id"] = str(saved.pop("_id"))
            return saved

        except Exception as exc:
            duration_ms = int((time.time() - start_time) * 1000)
            err_msg = str(exc)
            logger.exception("Verification failed for document %s: %s", document_id, err_msg)

            fail_doc = {
                "extraction_status": "failed",
                "verification_status": "failed",
                "error_details": err_msg,
                "summary_explanation": f"Processing encountered an error: {err_msg}",
                "processing_time_ms": duration_ms,
                "updated_at": _utcnow(),
            }
            self.verification_col.update_one(
                {"vendor_id": vendor_id, "document_id": document_id},
                {"$set": fail_doc},
            )
            # Update vendors collection doc status
            self.vendors_col.update_one(
                {"_id": ObjectId(vendor_id), "documents.document_id": document_id},
                {"$set": {"documents.$.verification_status": "failed", "updated_at": _utcnow()}},
            )
            saved = self.verification_col.find_one({"vendor_id": vendor_id, "document_id": document_id})
            saved["id"] = str(saved.pop("_id"))
            return saved

    def get_document_verification(self, vendor_id: str, document_id: str) -> dict[str, Any] | None:
        """Fetch verification result for a single document."""
        doc = self.verification_col.find_one({"vendor_id": vendor_id, "document_id": document_id})
        if not doc:
            return None
        doc["id"] = str(doc.pop("_id"))
        return doc

    def get_vendor_verification_summary(self, vendor_id: str) -> dict[str, Any]:
        """Fetch all verification results and summary status for a vendor."""
        cursor = self.verification_col.find({"vendor_id": vendor_id}).sort("created_at", ASCENDING)
        results = []
        verified_count = 0
        flagged_count = 0
        pending_count = 0

        for r in cursor:
            r["id"] = str(r.pop("_id"))
            results.append(r)
            status = r.get("verification_status", "pending")
            if status == "completed":
                verified_count += 1
            elif status in ("flagged", "needs_manual_review"):
                flagged_count += 1
            else:
                pending_count += 1

        total = len(results)
        if flagged_count > 0:
            overall_status = "flagged"
        elif total > 0 and verified_count == total:
            overall_status = "verified"
        elif total > 0:
            overall_status = "needs_manual_review"
        else:
            overall_status = "pending"

        return {
            "vendor_id": vendor_id,
            "total_documents": total,
            "verified_documents": verified_count,
            "flagged_documents": flagged_count,
            "pending_documents": pending_count,
            "overall_status": overall_status,
            "results": results,
        }

