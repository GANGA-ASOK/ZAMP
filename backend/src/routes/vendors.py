"""
Vendor onboarding API routes.

Provides endpoints for creating, retrieving, updating, partially updating,
submitting, and checking the status of vendor onboarding registrations.
Includes Phase 7 RBAC and vendor ownership protection.
"""

from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status

from src.dependencies.auth import (
    CurrentUserDep,
    get_current_user,
    get_current_user_optional,
    require_vendor,
    verify_vendor_ownership,
)
from src.models.user import UserModel
from src.schemas.vendor import (
    VendorCreate,
    VendorDraftCreate,
    VendorResponse,
    VendorStatusResponse,
    VendorSubmissionResponse,
    VendorUpdate,
)
from src.services.application_decision_service import run_decision_in_background
from src.services.auth_service import AuthService
from src.services.vendor_service import (
    DuplicateVendorError,
    IncompleteRegistrationError,
    InvalidVendorIdError,
    VendorNotFoundError,
    VendorService,
)

router = APIRouter(prefix="/vendors", tags=["Vendors"])


def get_vendor_service() -> VendorService:
    """Dependency provider for VendorService."""
    return VendorService()


VendorServiceDep = Annotated[VendorService, Depends(get_vendor_service)]


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post(
    "/",
    response_model=VendorResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new vendor registration (draft or full)",
    description="Initializes a new vendor onboarding record. Supports partial drafts or complete payloads.",
)
async def create_vendor(
    payload: VendorDraftCreate | VendorCreate,
    service: VendorServiceDep,
    current_user: UserModel | None = Depends(get_current_user_optional),
) -> VendorResponse:
    try:
        user_id = current_user.user_id if current_user else None
        return await service.create_vendor(payload, user_id=user_id)
    except DuplicateVendorError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create vendor registration: {exc}",
        )


@router.get(
    "/my-profile",
    response_model=VendorResponse,
    status_code=status.HTTP_200_OK,
    summary="Retrieve authenticated vendor's own profile",
    description="Returns the vendor registration record associated with the authenticated vendor account.",
)
async def get_my_vendor_profile(
    current_user: UserModel = Depends(require_vendor),
    service: VendorServiceDep = None,
) -> VendorResponse:
    vendor = await service.get_vendor_by_user_id(current_user.user_id)
    if not vendor:
        auth_svc = AuthService()
        vendor_id = auth_svc.get_or_create_vendor_profile(
            current_user.user_id,
            contact_name=current_user.name,
            email=current_user.email,
        )
        return await service.get_vendor_by_id(vendor_id)
    return vendor


@router.get(
    "/{vendor_id}",
    response_model=VendorResponse,
    status_code=status.HTTP_200_OK,
    summary="Retrieve a vendor registration",
    description="Retrieves vendor onboarding details by MongoDB ObjectId. Sensitive data (PAN, bank account) is masked.",
)
async def get_vendor(
    vendor_id: str,
    service: VendorServiceDep,
    _auth: UserModel = Depends(verify_vendor_ownership),
) -> VendorResponse:
    try:
        return await service.get_vendor_by_id(vendor_id)
    except InvalidVendorIdError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )
    except VendorNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )


@router.put(
    "/{vendor_id}",
    response_model=VendorResponse,
    status_code=status.HTTP_200_OK,
    summary="Update vendor registration details",
    description="Updates supplied vendor sections while preserving internal fields (reference number, created_at, status).",
)
async def update_vendor(
    vendor_id: str,
    payload: VendorDraftCreate | VendorCreate,
    service: VendorServiceDep,
    _auth: UserModel = Depends(verify_vendor_ownership),
) -> VendorResponse:
    try:
        return await service.update_vendor(vendor_id, payload)
    except InvalidVendorIdError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )
    except VendorNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )
    except DuplicateVendorError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        )


@router.patch(
    "/{vendor_id}",
    response_model=VendorResponse,
    status_code=status.HTTP_200_OK,
    summary="Partially update vendor registration",
    description="Updates specific fields without overwriting unrelated sibling fields within nested sections.",
)
async def partial_update_vendor(
    vendor_id: str,
    payload: VendorUpdate,
    service: VendorServiceDep,
    _auth: UserModel = Depends(verify_vendor_ownership),
) -> VendorResponse:
    try:
        return await service.partial_update_vendor(vendor_id, payload)
    except InvalidVendorIdError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )
    except VendorNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )
    except DuplicateVendorError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        )


@router.post(
    "/{vendor_id}/submit",
    response_model=VendorSubmissionResponse,
    status_code=status.HTTP_200_OK,
    summary="Submit vendor registration for review",
    description="Validates completeness across all 4 onboarding steps and marks status as 'submitted'.",
)
async def submit_vendor(
    vendor_id: str,
    service: VendorServiceDep,
    background_tasks: BackgroundTasks,
    _auth: UserModel = Depends(verify_vendor_ownership),
) -> VendorSubmissionResponse:
    try:
        result = await service.submit_vendor(vendor_id)
        background_tasks.add_task(run_decision_in_background, vendor_id, "submission")
        return result
    except InvalidVendorIdError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )
    except VendorNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )
    except IncompleteRegistrationError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "message": str(exc),
                "missing_fields": exc.missing_fields,
            },
        )


@router.get(
    "/{vendor_id}/status",
    response_model=VendorStatusResponse,
    status_code=status.HTTP_200_OK,
    summary="Retrieve vendor onboarding status",
    description="Returns the current application status, reference number, and timestamps.",
)
async def get_vendor_status(
    vendor_id: str,
    service: VendorServiceDep,
    _auth: UserModel = Depends(verify_vendor_ownership),
) -> VendorStatusResponse:
    try:
        return await service.get_vendor_status(vendor_id)
    except InvalidVendorIdError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )
    except VendorNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )
