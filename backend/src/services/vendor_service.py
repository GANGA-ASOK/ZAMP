"""
Vendor service layer for VendorFlow.

Encapsulates all database operations, business logic, validation checks,
and state transitions for vendor onboarding.
"""

from __future__ import annotations

import logging
import random
from datetime import datetime, timezone
from typing import Any

from bson import ObjectId
from pydantic import ValidationError
from pymongo.collection import Collection
from pymongo.database import Database

import src.database.mongodb as mongo_module
from src.models.enums import VendorStatus
from src.models.vendor import VendorDocument
from src.schemas.vendor import (
    VendorCreate,
    VendorDraftCreate,
    VendorResponse,
    VendorStatusResponse,
    VendorSubmissionResponse,
    VendorUpdate,
    mask_pan,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Custom Domain Exceptions
# ---------------------------------------------------------------------------

class VendorServiceError(Exception):
    """Base exception for vendor service errors."""
    pass


class InvalidVendorIdError(VendorServiceError):
    """Raised when a vendor ID is not a valid 24-character hexadecimal ObjectId."""
    def __init__(self, vendor_id: str):
        super().__init__(f"Invalid vendor ID '{vendor_id}'. Must be a 24-character hexadecimal string.")
        self.vendor_id = vendor_id


class VendorNotFoundError(VendorServiceError):
    """Raised when a vendor record cannot be found."""
    def __init__(self, vendor_id: str):
        super().__init__(f"Vendor with ID '{vendor_id}' not found.")
        self.vendor_id = vendor_id


class DuplicateVendorError(VendorServiceError):
    """Raised when a registration with the same unique identifier (e.g. PAN) already exists."""
    def __init__(self, identifier: str, existing_ref: str = ""):
        ref_msg = f" (Existing reference: {existing_ref})" if existing_ref else ""
        super().__init__(f"A vendor registration with PAN '{identifier}' already exists{ref_msg}.")
        self.identifier = identifier
        self.existing_ref = existing_ref


class IncompleteRegistrationError(VendorServiceError):
    """Raised when attempting to submit an onboarding registration that is missing required fields."""
    def __init__(self, missing_fields: list[dict[str, str]]):
        super().__init__("Cannot submit incomplete vendor registration. Missing or invalid required fields.")
        self.missing_fields = missing_fields


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _validate_object_id(vendor_id: str) -> ObjectId:
    """Validate string and return BSON ObjectId, or raise InvalidVendorIdError."""
    if not isinstance(vendor_id, str) or not ObjectId.is_valid(vendor_id):
        raise InvalidVendorIdError(str(vendor_id))
    return ObjectId(vendor_id)


def _to_dot_notation(data: dict[str, Any], prefix: str = "") -> dict[str, Any]:
    """
    Recursively flatten nested dictionaries into dot-notation keys for MongoDB $set.
    Lists and non-dict values are kept intact. None values are skipped.
    """
    items: dict[str, Any] = {}
    for k, v in data.items():
        if v is None:
            continue
        new_key = f"{prefix}.{k}" if prefix else k
        if isinstance(v, dict):
            items.update(_to_dot_notation(v, new_key))
        else:
            items[new_key] = v
    return items


def generate_reference_number(year: int | None = None) -> str:
    """Generate a unique human-readable vendor reference number (e.g. VND-2026-84729)."""
    current_year = year or datetime.now(timezone.utc).year
    random_num = random.randint(10000, 99999)
    return f"VND-{current_year}-{random_num}"


# ---------------------------------------------------------------------------
# Vendor Service Class
# ---------------------------------------------------------------------------

class VendorService:
    """
    Encapsulates vendor CRUD and workflow operations against MongoDB.
    """

    def __init__(self, db: Database | None = None):
        self._db = db

    @property
    def db(self) -> Database:
        if self._db is not None:
            return self._db
        if mongo_module.db is not None:
            return mongo_module.db
        raise RuntimeError("Database not initialized. Please ensure connect_to_mongodb() has been called.")

    @property
    def collection(self) -> Collection:
        return self.db["vendors"]

    def ensure_indexes(self) -> None:
        """Create indexes on the vendors collection for performance and constraints."""
        try:
            self.collection.create_index("reference_number", unique=True, sparse=True)
            self.collection.create_index("tax_details.pan_number", sparse=True)
            self.collection.create_index("status")
            self.collection.create_index("created_at")
        except Exception as exc:
            logger.warning("Could not create indexes on vendors collection: %s", exc)

    async def check_duplicate_pan(self, pan: str, exclude_id: ObjectId | None = None) -> None:
        """
        Check if an active vendor registration with the given PAN already exists.
        Raises DuplicateVendorError if found.
        """
        if not pan or not pan.strip():
            return

        cleaned_pan = pan.strip().upper()
        query: dict[str, Any] = {
            "tax_details.pan_number": cleaned_pan,
            "status": {"$ne": VendorStatus.REJECTED.value},
        }
        if exclude_id is not None:
            query["_id"] = {"$ne": exclude_id}

        existing = self.collection.find_one(query)
        if existing:
            ref = existing.get("reference_number", "")
            raise DuplicateVendorError(identifier=mask_pan(cleaned_pan), existing_ref=ref)

    async def create_vendor(
        self,
        payload: VendorDraftCreate | VendorCreate | dict[str, Any],
        user_id: str | None = None,
    ) -> VendorResponse:
        """
        Create a new vendor registration (initial status: draft).
        Accepts full or partial/draft payloads.
        """
        # Dump payload into clean dict
        if isinstance(payload, (VendorDraftCreate, VendorCreate)):
            data = payload.model_dump(exclude_unset=True)
        elif isinstance(payload, dict):
            data = payload.copy()
        else:
            raise ValueError("Unsupported payload type for vendor creation.")

        # Check duplicate PAN if provided
        tax = data.get("tax_details") or {}
        pan = tax.get("pan_number") if isinstance(tax, dict) else None
        if pan:
            await self.check_duplicate_pan(pan)

        # Generate unique reference number
        ref_num = generate_reference_number()
        # Verify reference uniqueness
        while self.collection.find_one({"reference_number": ref_num}):
            ref_num = generate_reference_number()

        now = _utcnow()

        # Build document structure using VendorDocument defaults
        doc_template = VendorDocument(
            reference_number=ref_num,
            status=VendorStatus.DRAFT.value,
            user_id=user_id,
            created_at=now,
            updated_at=now,
        ).to_dict()

        # Merge supplied sections
        for section in ["company_info", "contact_info", "tax_details", "banking_details", "declarations"]:
            if section in data and isinstance(data[section], dict):
                # Ensure confirm_account_number is never persisted
                if section == "banking_details":
                    data[section].pop("confirm_account_number", None)
                doc_template[section].update(data[section])

        if "documents" in data and isinstance(data["documents"], list):
            doc_template["documents"] = data["documents"]

        # Insert into MongoDB
        result = self.collection.insert_one(doc_template)
        doc_template["_id"] = result.inserted_id

        try:
            from src.services.workflow_service import WorkflowService
            wf = WorkflowService(db=self.db)
            wf.log_activity(
                application_id=str(result.inserted_id),
                vendor_id=str(result.inserted_id),
                event_type="created",
                description="Vendor registration initialized.",
                actor_type="vendor",
            )
        except Exception as exc:
            logger.warning("Workflow hook during create skipped: %s", exc)

        logger.info("Vendor registration created with ID: %s, Ref: %s", result.inserted_id, ref_num)
        return VendorResponse.from_mongo(doc_template)

    async def get_vendor_by_id(self, vendor_id: str) -> VendorResponse:
        """Retrieve vendor by ID and return masked response."""
        oid = _validate_object_id(vendor_id)
        doc = self.collection.find_one({"_id": oid})
        if not doc:
            raise VendorNotFoundError(vendor_id)
        return VendorResponse.from_mongo(doc)

    async def get_vendor_by_user_id(self, user_id: str) -> VendorResponse | None:
        """Retrieve vendor profile associated with an authenticated user ID."""
        doc = self.collection.find_one({"user_id": user_id})
        if not doc:
            return None
        return VendorResponse.from_mongo(doc)

    async def get_raw_vendor_doc(self, vendor_id: str) -> dict[str, Any]:
        """Internal helper to retrieve raw unmasked vendor document."""
        oid = _validate_object_id(vendor_id)
        doc = self.collection.find_one({"_id": oid})
        if not doc:
            raise VendorNotFoundError(vendor_id)
        return doc

    async def update_vendor(
        self,
        vendor_id: str,
        payload: VendorDraftCreate | VendorCreate | dict[str, Any],
    ) -> VendorResponse:
        """
        Full update (PUT) of vendor onboarding information.
        Preserves internal fields (_id, reference_number, created_at, status).
        """
        oid = _validate_object_id(vendor_id)
        existing = self.collection.find_one({"_id": oid})
        if not existing:
            raise VendorNotFoundError(vendor_id)

        if isinstance(payload, (VendorDraftCreate, VendorCreate)):
            data = payload.model_dump(exclude_unset=True)
        elif isinstance(payload, dict):
            data = payload.copy()
        else:
            raise ValueError("Unsupported payload type for vendor update.")

        # Check duplicate PAN if changed
        tax = data.get("tax_details") or {}
        pan = tax.get("pan_number") if isinstance(tax, dict) else None
        if pan:
            await self.check_duplicate_pan(pan, exclude_id=oid)

        now = _utcnow()
        update_doc: dict[str, Any] = {"updated_at": now}

        for section in ["company_info", "contact_info", "tax_details", "banking_details", "declarations"]:
            if section in data and isinstance(data[section], dict):
                if section == "banking_details":
                    data[section].pop("confirm_account_number", None)
                # Merge into existing section to avoid losing untouched sub-fields
                merged_section = existing.get(section, {})
                merged_section.update(data[section])
                update_doc[section] = merged_section

        if "documents" in data and isinstance(data["documents"], list):
            update_doc["documents"] = data["documents"]

        self.collection.update_one(
            {"_id": oid},
            {"$set": update_doc},
        )

        updated_doc = self.collection.find_one({"_id": oid})
        logger.info("Vendor %s updated successfully", vendor_id)
        return VendorResponse.from_mongo(updated_doc)

    async def partial_update_vendor(
        self,
        vendor_id: str,
        payload: VendorUpdate | dict[str, Any],
    ) -> VendorResponse:
        """
        Partial update (PATCH) of vendor onboarding information.
        Uses dot notation to update specific nested fields without overwriting siblings.
        """
        oid = _validate_object_id(vendor_id)
        existing = self.collection.find_one({"_id": oid})
        if not existing:
            raise VendorNotFoundError(vendor_id)

        if isinstance(payload, VendorUpdate):
            data = payload.model_dump(exclude_unset=True)
        elif isinstance(payload, dict):
            data = payload.copy()
        else:
            raise ValueError("Unsupported payload type for partial update.")

        # Check duplicate PAN if updated
        tax = data.get("tax_details") or {}
        if isinstance(tax, dict) and "pan_number" in tax and tax["pan_number"]:
            await self.check_duplicate_pan(tax["pan_number"], exclude_id=oid)

        # Remove confirm_account_number if present
        if "banking_details" in data and isinstance(data["banking_details"], dict):
            data["banking_details"].pop("confirm_account_number", None)

        # Flatten into dot notation
        dot_updates = _to_dot_notation(data)
        dot_updates["updated_at"] = _utcnow()

        if dot_updates:
            self.collection.update_one(
                {"_id": oid},
                {"$set": dot_updates},
            )

        updated_doc = self.collection.find_one({"_id": oid})
        logger.info("Vendor %s partially updated successfully", vendor_id)
        return VendorResponse.from_mongo(updated_doc)

    def validate_submission_readiness(self, raw_doc: dict[str, Any]) -> None:
        """
        Validate that the stored vendor document has all required fields across all 4 steps.
        Raises IncompleteRegistrationError if required fields are missing or invalid.
        """
        # Prepare validation payload by copying sections
        val_payload = {
            "company_info": (raw_doc.get("company_info") or {}).copy(),
            "contact_info": raw_doc.get("contact_info") or {},
            "tax_details": raw_doc.get("tax_details") or {},
            "banking_details": (raw_doc.get("banking_details") or {}).copy(),
            "documents": raw_doc.get("documents") or [],
            "declarations": raw_doc.get("declarations") or {},
        }

        # If operational address is marked same as registered, ensure operational_address is not validated as separate
        if val_payload["company_info"].get("is_operational_same_as_registered", True):
            val_payload["company_info"]["operational_address"] = None

        # BankingDetailsCreate expects confirm_account_number == account_number
        if "account_number" in val_payload["banking_details"]:
            val_payload["banking_details"]["confirm_account_number"] = val_payload["banking_details"]["account_number"]

        try:
            VendorCreate(**val_payload)
        except ValidationError as exc:
            missing: list[dict[str, str]] = []
            for err in exc.errors():
                loc = ".".join(str(p) for p in err.get("loc", []))
                msg = err.get("msg", "Invalid value")
                missing.append({"field": loc, "message": msg})
            raise IncompleteRegistrationError(missing_fields=missing)

    async def submit_vendor(self, vendor_id: str) -> VendorSubmissionResponse:
        """
        Validate completeness and transition vendor status to 'submitted'.
        """
        oid = _validate_object_id(vendor_id)
        raw_doc = self.collection.find_one({"_id": oid})
        if not raw_doc:
            raise VendorNotFoundError(vendor_id)

        # Check completeness
        self.validate_submission_readiness(raw_doc)

        now = _utcnow()
        update_fields = {
            "status": VendorStatus.SUBMITTED.value,
            "submitted_at": now,
            "updated_at": now,
        }

        self.collection.update_one(
            {"_id": oid},
            {"$set": update_fields},
        )

        try:
            from src.services.workflow_service import WorkflowService
            wf = WorkflowService(db=self.db)
            wf.log_activity(
                application_id=str(oid),
                vendor_id=str(oid),
                event_type="submitted",
                description="Vendor submitted application for compliance review.",
                actor_type="vendor",
            )
            comp_name = raw_doc.get("company_info", {}).get("legal_company_name", "Vendor")
            ref_num = raw_doc.get("reference_number", "")
            wf.create_notification(
                recipient_type="admin",
                title="New Vendor Application",
                message=f"New application submitted by {comp_name} ({ref_num}).",
                notification_type="info",
                vendor_id=str(oid),
                application_id=str(oid),
            )
            wf.create_notification(
                recipient_type="vendor",
                title="Application Submitted",
                message=f"Your onboarding application ({ref_num}) has been successfully submitted.",
                notification_type="info",
                vendor_id=str(oid),
                application_id=str(oid),
            )
        except Exception as exc:
            logger.warning("Workflow hooks during submission skipped: %s", exc)

        logger.info("Vendor %s successfully submitted with ref: %s", vendor_id, raw_doc.get("reference_number"))
        return VendorSubmissionResponse(
            message="Vendor registration submitted successfully.",
            vendor_id=str(oid),
            reference_number=raw_doc.get("reference_number", ""),
            status=VendorStatus.SUBMITTED.value,
            submitted_at=now,
        )

    async def get_vendor_status(self, vendor_id: str) -> VendorStatusResponse:
        """Retrieve the current onboarding status for a vendor."""
        oid = _validate_object_id(vendor_id)
        doc = self.collection.find_one({"_id": oid})
        if not doc:
            raise VendorNotFoundError(vendor_id)

        return VendorStatusResponse(
            vendor_id=str(oid),
            reference_number=doc.get("reference_number", ""),
            status=doc.get("status", VendorStatus.DRAFT.value),
            submitted_at=doc.get("submitted_at"),
            updated_at=doc.get("updated_at") or _utcnow(),
        )
