"""
Test-case pre-fill routes for the vendor portal (testing / demo only).

    GET  /api/demo/scenarios                 list the AI Decision Engine test cases
    POST /api/demo/scenarios/{key}/prefill   create a fresh draft vendor for a case:
                                             form data saved + scenario PDFs uploaded

Selecting the same case again first removes earlier copies of that case
(matched on BOTH its PAN and legal name), so the duplicate-PAN guard does not
block re-testing. Disable entirely with ENABLE_DEMO_SCENARIOS=false.
"""

from __future__ import annotations

import copy
import logging
import os
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status

import src.database.mongodb as mongo_module
from src.dependencies.auth import get_current_user_optional
from src.models.user import UserModel
from src.scripts.demo_scenarios import build_scenarios, make_blank_scan, make_pdf
from src.services.document_service import DocumentService
from src.services.vendor_service import generate_reference_number

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/demo", tags=["Test Cases (demo only)"])

# Cases that only behave as described when another case was submitted first.
DEPENDS_ON = {"duplicate_bank": "happy_path"}


def _enabled() -> None:
    if os.getenv("ENABLE_DEMO_SCENARIOS", "true").lower() == "false":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Test cases are disabled.")


def _scenarios() -> dict[str, dict[str, Any]]:
    return {s["key"]: s for s in build_scenarios()}


@router.get("/scenarios", summary="List vendor test cases")
async def list_scenarios() -> list[dict[str, Any]]:
    _enabled()
    titles = {k: s["title"] for k, s in _scenarios().items()}
    return [
        {
            "key": s["key"],
            "title": s["title"],
            "expected": s["expected"],
            "story": s["story"],
            "documents": [{"category": c, "file_name": f} for c, f, _ in s["documents"]],
            "requires_first": titles.get(DEPENDS_ON.get(s["key"], "")),
        }
        for s in _scenarios().values()
    ]


def _purge_previous_copies(db, form: dict[str, Any]) -> int:
    """Delete earlier test copies of this case (same PAN *and* same legal name) with their files and runs."""
    query = {
        "tax_details.pan_number": form["tax_details"]["pan_number"],
        "company_info.legal_company_name": form["company_info"]["legal_company_name"],
    }
    removed = 0
    for old in db["vendors"].find(query, {"_id": 1}):
        vid = str(old["_id"])
        for col in ("verification_results", "ai_decision_runs", "ai_insights", "application_history",
                    "clarification_requests", "notifications", "admin_comments"):
            db[col].delete_many({"$or": [{"vendor_id": vid}, {"application_id": vid}]})
        for f in db["document_files.files"].find({"metadata.vendor_id": vid}, {"_id": 1}):
            db["document_files.chunks"].delete_many({"files_id": f["_id"]})
            db["document_files.files"].delete_one({"_id": f["_id"]})
        db["vendors"].delete_one({"_id": old["_id"]})
        removed += 1
    return removed


@router.post("/scenarios/{key}/prefill", status_code=status.HTTP_201_CREATED, summary="Create a draft vendor for a test case")
async def prefill_scenario(
    key: str,
    background_tasks: BackgroundTasks,
    current_user: UserModel | None = Depends(get_current_user_optional),
) -> dict[str, Any]:
    _enabled()
    scenario = _scenarios().get(key)
    if not scenario:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Unknown test case '{key}'.")

    db = mongo_module.db
    form = copy.deepcopy(scenario["form"])
    removed = _purge_previous_copies(db, form)

    now = datetime.now(timezone.utc)
    ref = generate_reference_number()
    while db["vendors"].find_one({"reference_number": ref}):
        ref = generate_reference_number()
    form.update(
        reference_number=ref, status="draft", submitted_at=None, created_at=now, updated_at=now,
        user_id=current_user.user_id if current_user else None, documents=[],
    )
    vendor_id = str(db["vendors"].insert_one(form).inserted_id)

    docs = DocumentService(db)
    uploaded = []
    for category, filename, text in scenario["documents"]:
        data = make_blank_scan() if text is None else make_pdf(text)
        uploaded.append(docs.upload_document(vendor_id=vendor_id, file_bytes=data, filename=filename, category=category))

    # Pre-parse the documents now so the AI decision after submission is fast.
    from src.routes.documents import _run_ai_pipeline
    for meta in uploaded:
        background_tasks.add_task(_run_ai_pipeline, vendor_id, meta["document_id"])

    logger.info("Test case '%s' pre-filled as vendor %s (%d earlier copies removed)", key, vendor_id, removed)
    form.pop("_id", None)
    return {
        "vendor_id": vendor_id,
        "reference_number": ref,
        "key": key,
        "title": scenario["title"],
        "expected": scenario["expected"],
        "removed_previous": removed,
        "form": {k: form[k] for k in ("company_info", "contact_info", "tax_details", "banking_details", "declarations")},
        "documents": uploaded,
    }
