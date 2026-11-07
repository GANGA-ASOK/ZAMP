"""
Administrator dashboard schemas: metrics, vendor listings, pagination, and admin detail views.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from pydantic import BaseModel, Field


class AdminMetricsResponse(BaseModel):
    """Summary counts for admin dashboard."""
    total_vendors: int = 0
    draft: int = 0
    submitted: int = 0
    under_review: int = 0
    approved: int = 0
    rejected: int = 0


class AdminVendorListItem(BaseModel):
    """Vendor row item in admin dashboard table."""
    id: str
    company_name: str
    contact_name: str
    email: str
    phone: str = ""
    status: str
    reference_number: str = ""
    created_at: datetime
    updated_at: datetime
    documents_count: int = 0


class AdminVendorPaginationResponse(BaseModel):
    """Paginated list of vendors with summary metrics."""
    items: list[AdminVendorListItem]
    total: int
    page: int
    limit: int
    pages: int
    metrics: AdminMetricsResponse

