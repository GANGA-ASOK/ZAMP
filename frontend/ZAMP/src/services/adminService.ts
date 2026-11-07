/**
 * Admin portal API service.
 * Manages vendor queue, detail view, approval status, and metrics.
 */

import apiClient from './api';
import type { BackendVendorResponse } from './vendorService';

export interface AdminMetrics {
  total_vendors: number;
  draft: number;
  submitted: number;
  under_review: number;
  approved: number;
  rejected: number;
}

export interface AdminVendorListItem {
  id: string;
  company_name: string;
  contact_name: string;
  email: string;
  phone: string;
  status: string;
  reference_number: string;
  created_at: string;
  updated_at: string;
  documents_count: number;
}

export interface AdminVendorPaginationResponse {
  items: AdminVendorListItem[];
  total: number;
  page: number;
  limit: number;
  pages: number;
  metrics: AdminMetrics;
}

export interface ListVendorsParams {
  page?: number;
  limit?: number;
  status?: string;
  search?: string;
  sort_by?: string;
  sort_order?: 'asc' | 'desc';
}

/**
 * Fetch summary metrics for admin dashboard.
 */
export async function getAdminMetrics(): Promise<AdminMetrics> {
  const response = await apiClient.get<AdminMetrics>('/admin/metrics');
  return response.data;
}

/**
 * List vendor applications with search, status filters, and pagination.
 */
export async function listAdminVendors(
  params?: ListVendorsParams
): Promise<AdminVendorPaginationResponse> {
  const response = await apiClient.get<AdminVendorPaginationResponse>('/admin/vendors', {
    params,
  });
  return response.data;
}

/**
 * Fetch full vendor application details for an administrator.
 */
export async function getAdminVendorDetail(
  vendorId: string
): Promise<BackendVendorResponse> {
  const response = await apiClient.get<BackendVendorResponse>(`/admin/vendors/${vendorId}`);
  return response.data;
}

/**
 * Update vendor review status (e.g. under_review, approved, rejected).
 */
export async function updateVendorStatusByAdmin(
  vendorId: string,
  newStatus: string,
  reviewNotes?: string
): Promise<BackendVendorResponse> {
  const response = await apiClient.patch<BackendVendorResponse>(
    `/admin/vendors/${vendorId}/status`,
    {
      status: newStatus,
      review_notes: reviewNotes,
    }
  );
  return response.data;
}
