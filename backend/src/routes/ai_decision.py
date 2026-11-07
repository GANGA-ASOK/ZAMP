"""
AI Decision Engine API routes.

Endpoints (admin):
    POST /api/admin/applications/{id}/ai-decision/run            start a run (background by default)
    GET  /api/admin/applications/{id}/ai-decision                latest run for an application
    GET  /api/admin/applications/{id}/ai-decision/runs           run history for an application
    POST /api/admin/applications/{id}/ai-decision/send-to-vendor send the AI-drafted request to the vendor
    GET  /api/admin/ai-decision/runs                             recent runs across all applications
    GET  /api/admin/ai-decision/runs/{run_id}                    one run (poll this for the live view)
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query, status
from pydantic import BaseModel, Field

from src.dependencies.auth import AdminUserDep
from src.schemas.workflow import ClarificationItemResponse
from src.services.application_decision_service import ApplicationDecisionService
from src.services.vendor_service import InvalidVendorIdError, VendorNotFoundError
from src.services.workflow_service import InvalidStatusTransitionError, WorkflowService

logger = logging.getLogger(__name__)

router = APIRouter(tags=["AI Decision Engine"])


def _svc() -> ApplicationDecisionService:
    return ApplicationDecisionService()


class SendToVendorPayload(BaseModel):
    message: str | None = Field(default=None, description="Override the AI-drafted message.")


@router.post(
    "/admin/applications/{application_id}/ai-decision/run",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Run the AI Decision Engine for an application",
)
async def run_ai_decision(
    application_id: str,
    admin: AdminUserDep,
    background_tasks: BackgroundTasks,
    wait: bool = Query(default=False, description="Run synchronously and return the completed run."),
    force_reparse: bool = Query(default=False, description="Ignore cached Nemotron Parse output."),
) -> dict[str, Any]:
    svc = _svc()
    actor = admin.name or "Admin"
    try:
        if wait:
            return svc_result(await svc.run_now(application_id, "manual", actor, force_reparse=force_reparse))
        run = svc.create_run(application_id, trigger="manual", triggered_by=actor)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))

    if run["status"] == "queued":
        background_tasks.add_task(svc.execute_run, run["id"], force_reparse)
    return svc_result(run)


def svc_result(run: dict[str, Any] | None) -> dict[str, Any]:
    if not run:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found.")
    return run


@router.get(
    "/admin/applications/{application_id}/ai-decision",
    summary="Latest AI decision for an application",
)
async def get_latest_ai_decision(application_id: str, admin: AdminUserDep) -> dict[str, Any]:
    return {"run": _svc().get_latest(application_id)}


@router.get(
    "/admin/applications/{application_id}/ai-decision/runs",
    summary="AI decision run history for an application",
)
async def list_application_runs(
    application_id: str,
    admin: AdminUserDep,
    limit: int = Query(default=20, ge=1, le=100),
) -> dict[str, Any]:
    return {"items": _svc().list_runs(application_id, limit)}


@router.get("/admin/ai-decision/runs", summary="Recent AI decision runs across all applications")
async def list_recent_runs(admin: AdminUserDep, limit: int = Query(default=30, ge=1, le=200)) -> dict[str, Any]:
    return {"items": _svc().list_runs(None, limit)}


@router.get("/admin/ai-decision/runs/{run_id}", summary="Get one AI decision run (poll for live progress)")
async def get_run(run_id: str, admin: AdminUserDep) -> dict[str, Any]:
    return svc_result(_svc().get_run(run_id))


@router.post(
    "/admin/applications/{application_id}/ai-decision/send-to-vendor",
    summary="Send the AI-drafted list of required actions to the vendor as a clarification request",
)
async def send_ai_request_to_vendor(
    application_id: str,
    admin: AdminUserDep,
    payload: SendToVendorPayload | None = None,
) -> dict[str, Any]:
    run = _svc().get_latest(application_id)
    if not run or run.get("status") != "completed" or not run.get("decision"):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Run the AI Decision Engine first.")
    decision = run["decision"]
    message = (payload.message if payload and payload.message else None) or decision.get("vendor_message")
    if not message:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="The AI decision has no outstanding vendor actions.")

    fields = sorted({f.get("field") for f in decision.get("reasons", []) if f.get("vendor_action") and f.get("field")})
    try:
        item = WorkflowService().request_clarification(
            application_id=application_id,
            clarification_message=message,
            related_field=", ".join(fields)[:200] or None,
            admin_notes=f"Generated by AI Decision Engine run {run['id']} ({decision.get('label')}, risk {decision.get('risk_score')}/100).",
        )
        return ClarificationItemResponse(**item).model_dump()
    except InvalidStatusTransitionError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except (InvalidVendorIdError, VendorNotFoundError) as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
