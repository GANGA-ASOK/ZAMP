"""
AI Insights Service for ZAMP Vendor Management.

Synthesizes document verification findings, deterministic field validations,
and cross-document consistency checks with vendor registration data into
actionable, structured insights and recommendations for compliance teams.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from bson import ObjectId
from pymongo.database import Database

import src.database.mongodb as mongodb_module
from src.services.document_service import DocumentService

logger = logging.getLogger(__name__)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class InsightsService:
    """Service to aggregate, synthesize, and persist comprehensive AI insights for vendors."""

    def __init__(self, db: Database | None = None) -> None:
        if db is not None:
            self._db = db
        elif mongodb_module.db is not None:
            self._db = mongodb_module.db
        else:
            raise RuntimeError("Database connection not initialized.")

    @property
    def insights_col(self):
        return self._db["ai_insights"]

    @property
    def verification_col(self):
        return self._db["verification_results"]

    @property
    def vendors_col(self):
        return self._db["vendors"]

    def ensure_indexes(self) -> None:
        """Create indexes on ai_insights collection."""
        try:
            self.insights_col.create_index("vendor_id", unique=True)
            self.insights_col.create_index("created_at")
        except Exception as exc:
            logger.warning("AI Insights index notice: %s", exc)

    def get_vendor_insights(self, vendor_id: str) -> dict[str, Any] | None:
        """Retrieve stored insights for a vendor."""
        doc = self.insights_col.find_one({"vendor_id": vendor_id})
        if not doc:
            return None
        doc["id"] = str(doc.pop("_id"))
        return doc

    def generate_vendor_insights(self, vendor_id: str) -> dict[str, Any]:
        """
        Synthesize document verifications, deterministic checks, and form data
        into an actionable insight package.
        """
        now = _utcnow()

        # 1. Fetch vendor data
        vendor_doc = None
        if ObjectId.is_valid(vendor_id):
            vendor_doc = self.vendors_col.find_one({"_id": ObjectId(vendor_id)})

        if not vendor_doc:
            vendor_doc = {}

        company_info = vendor_doc.get("company_info") or {}
        contact_info = vendor_doc.get("contact_info") or {}
        tax_details = vendor_doc.get("tax_details") or {}
        banking_details = vendor_doc.get("banking_details") or {}
        entity_type = company_info.get("business_entity_type") or ""
        legal_name = company_info.get("legal_company_name") or company_info.get("legal_name") or ""
        gst_status = tax_details.get("gst_status") or "Registered"

        # 2. Fetch all document verification records for this vendor
        verif_records = list(self.verification_col.find({"vendor_id": vendor_id}))

        # 3. Fetch uploaded documents from GridFS / vendor.documents
        doc_svc = DocumentService(self._db)
        uploaded_docs = []
        try:
            uploaded_docs = doc_svc.list_documents(vendor_id)
        except Exception:
            pass

        if not uploaded_docs:
            uploaded_docs = vendor_doc.get("documents") or []

        uploaded_categories = {
            (d.get("document_category") or d.get("category") or "").lower(): d
            for d in uploaded_docs
        }

        # -------------------------------------------------------------------
        # A. Document Summary
        # -------------------------------------------------------------------
        total_docs = len(uploaded_docs)
        completed_count = sum(
            1 for r in verif_records if r.get("verification_status") == "completed"
        )
        flagged_count = sum(
            1 for r in verif_records if r.get("verification_status") in ("flagged", "failed")
        )
        needs_review_count = sum(
            1 for r in verif_records if r.get("verification_status") == "needs_manual_review"
        )
        processing_count = sum(
            1 for r in verif_records if r.get("verification_status") in ("processing", "uploaded", "pending")
        )

        doc_summary = {
            "total_documents": total_docs,
            "completed": completed_count,
            "flagged": flagged_count,
            "needs_review": needs_review_count,
            "processing": processing_count,
            "categories_present": list(uploaded_categories.keys()),
        }

        # -------------------------------------------------------------------
        # B. Missing Information Auditing
        # -------------------------------------------------------------------
        missing_docs: list[dict[str, str]] = []
        missing_fields: list[dict[str, str]] = []

        # PAN is always required
        if "pan_card" not in uploaded_categories:
            missing_docs.append({
                "category": "pan_card",
                "label": "PAN Card",
                "importance": "mandatory",
                "reason": "Permanent Account Number verification is required for all legal entities in India.",
            })

        # Bank proof is always required
        if "bank_proof" not in uploaded_categories:
            missing_docs.append({
                "category": "bank_proof",
                "label": "Bank Proof",
                "importance": "mandatory",
                "reason": "Cancelled cheque or bank account statement required to verify payout account ownership.",
            })

        # GST Certificate required if Registered
        if gst_status.lower() == "registered" and "gst_certificate" not in uploaded_categories:
            missing_docs.append({
                "category": "gst_certificate",
                "label": "GST Certificate (REG-06)",
                "importance": "mandatory",
                "reason": "Vendor declared GST status as Registered, requiring GSTIN certificate verification.",
            })

        # Certificate of Incorporation required for corporate entities
        corporate_types = (
            "Private Limited Company",
            "Public Limited Company",
            "Limited Liability Partnership (LLP)",
            "One Person Company (OPC)",
        )
        if any(c.lower() in entity_type.lower() for c in corporate_types):
            if "certificate_of_incorporation" not in uploaded_categories:
                missing_docs.append({
                    "category": "certificate_of_incorporation",
                    "label": "Certificate of Incorporation",
                    "importance": "mandatory",
                    "reason": f"Corporate business type '{entity_type}' mandates Registrar of Companies (ROC) certificate.",
                })

        # Form fields check
        if not tax_details.get("pan_number"):
            missing_fields.append({"field": "tax_details.pan_number", "label": "PAN Number", "reason": "PAN is empty in registration form."})
        if not banking_details.get("account_number"):
            missing_fields.append({"field": "banking_details.account_number", "label": "Bank Account Number", "reason": "Account number not provided."})
        if not banking_details.get("ifsc_code"):
            missing_fields.append({"field": "banking_details.ifsc_code", "label": "Bank IFSC Code", "reason": "IFSC code is empty."})
        if not company_info.get("registration_number") and any(c.lower() in entity_type.lower() for c in corporate_types):
            missing_fields.append({"field": "company_info.registration_number", "label": "Company CIN / LLPIN", "reason": "CIN is mandatory for registered companies."})

        # -------------------------------------------------------------------
        # C. Key Findings & Extracted Attributes Synthesis
        # -------------------------------------------------------------------
        key_findings: list[dict[str, Any]] = []
        discrepancies: list[dict[str, Any]] = []
        risk_indicators: list[dict[str, Any]] = []

        all_extracted_fields: dict[str, Any] = {}
        all_field_validations: list[dict[str, Any]] = []
        all_consistency_findings: list[dict[str, Any]] = []

        for record in verif_records:
            extracted = record.get("extracted_fields") or {}
            all_extracted_fields.update(extracted)

            for fv in record.get("field_validations") or []:
                all_field_validations.append(fv)
                if not fv.get("is_valid"):
                    risk_indicators.append({
                        "indicator": f"Format Validation Failed: {fv.get('field_name')}",
                        "severity": "high",
                        "description": fv.get("details") or f"Invalid format in document {record.get('file_name')}",
                    })

            for cf in record.get("consistency_findings") or []:
                all_consistency_findings.append(cf)
                if cf.get("status") == "mismatch":
                    discrepancies.append({
                        "field": cf.get("field_name"),
                        "status": "mismatch",
                        "explanation": cf.get("explanation"),
                        "document": record.get("file_name"),
                    })
                    risk_indicators.append({
                        "indicator": f"Attribute Mismatch: {cf.get('field_name')}",
                        "severity": "medium",
                        "description": cf.get("explanation"),
                    })
                elif cf.get("status") == "match":
                    key_findings.append({
                        "finding": f"Verified {cf.get('field_name')}",
                        "status": "verified",
                        "details": cf.get("explanation"),
                    })

        # Add PAN finding if extracted
        pan_extracted = all_extracted_fields.get("pan_number")
        pan_form = tax_details.get("pan_number")
        if pan_extracted:
            if pan_form and pan_extracted.upper() == pan_form.upper():
                key_findings.append({
                    "finding": "PAN Number Verified",
                    "status": "verified",
                    "details": f"Extracted PAN '{pan_extracted}' matches registration data exactly.",
                })
            elif pan_form:
                discrepancies.append({
                    "field": "PAN Number",
                    "status": "mismatch",
                    "explanation": f"Document extracted PAN '{pan_extracted}' does not match form PAN '{pan_form}'.",
                })

        # Add GSTIN finding if extracted
        gst_extracted = all_extracted_fields.get("gstin")
        gst_form = tax_details.get("gstin")
        if gst_extracted:
            if gst_form and gst_extracted.upper() == gst_form.upper():
                key_findings.append({
                    "finding": "GSTIN Verified",
                    "status": "verified",
                    "details": f"Extracted GSTIN '{gst_extracted}' matches registration data exactly.",
                })
            elif gst_form:
                discrepancies.append({
                    "field": "GSTIN",
                    "status": "mismatch",
                    "explanation": f"Document extracted GSTIN '{gst_extracted}' differs from form GSTIN '{gst_form}'.",
                })

        # Add Bank account finding if extracted
        bank_acc_extracted = all_extracted_fields.get("account_number")
        bank_acc_form = banking_details.get("account_number")
        if bank_acc_extracted and bank_acc_form:
            if bank_acc_extracted == bank_acc_form:
                key_findings.append({
                    "finding": "Bank Account Ownership Verified",
                    "status": "verified",
                    "details": "Cheque/statement account number matches vendor payout account.",
                })
            else:
                discrepancies.append({
                    "field": "Bank Account Number",
                    "status": "mismatch",
                    "explanation": f"Bank document account '{bank_acc_extracted}' does not match registered account '{bank_acc_form}'.",
                })
                risk_indicators.append({
                    "indicator": "Payout Account Mismatch",
                    "severity": "critical",
                    "description": "Risk of misrouted disbursements: Bank proof account does not match registration account.",
                })

        # -------------------------------------------------------------------
        # D. AI Recommendation & Confidence Score
        # -------------------------------------------------------------------
        confidence_score = 95.0
        recommendation = "Approve"
        explanation = "All submitted documents and data are consistent."

        critical_risks = [r for r in risk_indicators if r.get("severity") == "critical"]
        high_risks = [r for r in risk_indicators if r.get("severity") == "high"]

        if critical_risks or len(discrepancies) >= 2:
            recommendation = "Reject"
            confidence_score = 40.0
            explanation = "Critical discrepancies detected between official documents and registered information. Potential compliance failure or fraud risk."
        elif missing_docs:
            recommendation = "Clarification Required"
            confidence_score = 65.0
            missing_names = ", ".join([d["label"] for d in missing_docs])
            explanation = f"Mandatory documents are missing ({missing_names}). Request vendor to submit missing documentation."
        elif discrepancies:
            recommendation = "Clarification Required"
            confidence_score = 70.0
            explanation = f"{len(discrepancies)} attribute mismatch(es) detected across submitted files and registration form."
        elif flagged_count > 0 or high_risks:
            recommendation = "Needs Review"
            confidence_score = 75.0
            explanation = "Some documents produced format or checksum validation warnings that require compliance officer manual verification."
        elif total_docs == 0:
            recommendation = "Needs Review"
            confidence_score = 30.0
            explanation = "No documents have been uploaded by the vendor yet."
        elif completed_count == total_docs:
            recommendation = "Approve"
            confidence_score = 96.0
            explanation = f"All {total_docs} documents successfully verified with high confidence. Extracted attributes match registered vendor profile."

        # Deduplicate findings
        seen_findings = set()
        dedup_findings = []
        for kf in key_findings:
            key = kf.get("finding", "")
            if key not in seen_findings:
                seen_findings.add(key)
                dedup_findings.append(kf)

        insights_payload = {
            "vendor_id": vendor_id,
            "recommendation": recommendation,
            "confidence_score": round(confidence_score, 1),
            "summary_explanation": explanation,
            "document_summary": doc_summary,
            "key_findings": dedup_findings,
            "missing_documents": missing_docs,
            "missing_fields": missing_fields,
            "discrepancies": discrepancies,
            "risk_indicators": risk_indicators,
            "extracted_fields_summary": all_extracted_fields,
            "created_at": now,
            "updated_at": now,
        }

        # Persist to database
        self.insights_col.update_one(
            {"vendor_id": vendor_id},
            {"$set": insights_payload},
            upsert=True,
        )

        saved = self.insights_col.find_one({"vendor_id": vendor_id})
        saved["id"] = str(saved.pop("_id"))
        return saved
