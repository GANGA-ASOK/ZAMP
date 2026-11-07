/**
 * Phase 9: Workflow, Clarification, Notification, and Activity API Client.
 */

import apiClient from './api';

import type { AIDecisionSummary } from './aiDecisionService';

export interface ApplicationListItem {
  id: string;
  vendor_id: string;
  reference_number: string;
  company_name: string;
  vendor_name: string;
  email: string;
  status: string;
  submission_date?: string | null;
  last_updated_date?: string | null;
  document_count: number;
  ai_verification_status: 'pending' | 'completed' | 'flagged' | 'needs_manual_review' | string;
  pending_clarifications_count: number;
  ai_decision?: AIDecisionSummary | null;
}

export interface ApplicationPaginationResponse {
  items: ApplicationListItem[];
  total: number;
  page: number;
  limit: number;
  pages: number;
  status_counts: Record<string, number>;
}

export interface ListApplicationsParams {
  page?: number;
  limit?: number;
  status?: string;
  search?: string;
  sort_by?: 'submission_date' | 'last_updated_date';
  sort_order?: 'asc' | 'desc';
}

export interface ClarificationItem {
  id: string;
  application_id: string;
  vendor_id: string;
  clarification_message: string;
  related_document_id?: string | null;
  related_document_name?: string | null;
  related_field?: string | null;
  admin_notes?: string | null;
  vendor_response?: string | null;
  replaced_document_id?: string | null;
  status: 'pending' | 'resolved';
  created_at: string;
  resolved_at?: string | null;
}

export interface NotificationItem {
  id: string;
  recipient_type: 'admin' | 'vendor';
  title: string;
  message: string;
  notification_type: string;
  vendor_id?: string | null;
  application_id?: string | null;
  is_read: boolean;
  metadata?: Record<string, any>;
  created_at: string;
}

export interface NotificationListResponse {
  items: NotificationItem[];
  unread_count: number;
  total_count: number;
}

export interface ActivityEvent {
  id: string;
  application_id: string;
  vendor_id: string;
  event_type: string;
  description: string;
  actor_type: 'vendor' | 'admin' | 'system';
  metadata?: Record<string, any>;
  timestamp: string;
}

export interface AdminComment {
  id: string;
  application_id: string;
  vendor_id: string;
  comment: string;
  visibility_type: string;
  author_name: string;
  created_at: string;
}

export interface AIInsightsResponse {
  id?: string;
  vendor_id: string;
  recommendation: 'Approve' | 'Clarification Required' | 'Needs Review' | 'Reject' | string;
  confidence_score: number;
  summary_explanation: string;
  document_summary: {
    total_documents: number;
    completed: number;
    flagged: number;
    needs_review: number;
    processing: number;
    categories_present: string[];
  };
  key_findings: Array<{
    finding: string;
    status: string;
    details: string;
  }>;
  missing_documents: Array<{
    category: string;
    label: string;
    importance: string;
    reason: string;
  }>;
  missing_fields: Array<{
    field: string;
    label: string;
    reason: string;
  }>;
  discrepancies: Array<{
    field: string;
    status: string;
    explanation: string;
    document?: string;
  }>;
  risk_indicators: Array<{
    indicator: string;
    severity: 'low' | 'medium' | 'high' | 'critical' | string;
    description: string;
  }>;
  created_at?: string;
  updated_at?: string;
}

export interface ApplicationDetailResponse {
  vendor: any;
  verification_summary?: any;
  ai_insights?: AIInsightsResponse | null;
  clarifications: ClarificationItem[];
  comments: AdminComment[];
  activity: ActivityEvent[];
}

// ---------------------------------------------------------------------------
// 1. Application Management
// ---------------------------------------------------------------------------

export async function listApplications(
  params?: ListApplicationsParams
): Promise<ApplicationPaginationResponse> {
  const response = await apiClient.get<ApplicationPaginationResponse>(
    '/admin/applications',
    { params }
  );
  return response.data;
}

export async function getApplicationDetail(
  applicationId: string
): Promise<ApplicationDetailResponse> {
  const response = await apiClient.get<ApplicationDetailResponse>(
    `/admin/applications/${applicationId}`
  );
  return response.data;
}

export async function updateApplicationStatus(
  applicationId: string,
  targetStatus: string,
  notes?: string
): Promise<{ message: string; status: string }> {
  const response = await apiClient.patch(
    `/admin/applications/${applicationId}/status`,
    {
      status: targetStatus,
      notes,
    }
  );
  return response.data;
}

// ---------------------------------------------------------------------------
// 2. Approval and Rejection
// ---------------------------------------------------------------------------

export async function approveApplication(
  applicationId: string,
  comment?: string
): Promise<{ message: string; status: string; approved_at: string }> {
  const response = await apiClient.post(
    `/admin/applications/${applicationId}/approve`,
    { comment }
  );
  return response.data;
}

export async function rejectApplication(
  applicationId: string,
  rejectionReason: string
): Promise<{ message: string; status: string; rejection_reason: string }> {
  const response = await apiClient.post(
    `/admin/applications/${applicationId}/reject`,
    { rejection_reason: rejectionReason }
  );
  return response.data;
}

// ---------------------------------------------------------------------------
// 3. Clarifications
// ---------------------------------------------------------------------------

export async function requestClarification(
  applicationId: string,
  payload: {
    clarification_message: string;
    related_document_id?: string | null;
    related_document_name?: string | null;
    related_field?: string | null;
    admin_notes?: string | null;
  }
): Promise<ClarificationItem> {
  const response = await apiClient.post<ClarificationItem>(
    `/admin/applications/${applicationId}/clarifications`,
    payload
  );
  return response.data;
}

export async function getVendorClarifications(
  vendorId: string
): Promise<ClarificationItem[]> {
  const response = await apiClient.get<ClarificationItem[]>(
    `/vendors/${vendorId}/clarifications`
  );
  return response.data;
}

export async function respondToClarification(
  vendorId: string,
  clarificationId: string,
  payload: {
    vendor_response: string;
    replaced_document_id?: string | null;
    updated_fields?: Record<string, any>;
  }
): Promise<ClarificationItem> {
  const response = await apiClient.post<ClarificationItem>(
    `/vendors/${vendorId}/clarifications/${clarificationId}/respond`,
    payload
  );
  return response.data;
}

export async function resubmitApplication(
  vendorId: string,
  resubmissionNotes?: string
): Promise<{ message: string; status: string; resubmitted_at: string }> {
  const response = await apiClient.post(
    `/vendors/${vendorId}/resubmit`,
    { resubmission_notes: resubmissionNotes }
  );
  return response.data;
}

// ---------------------------------------------------------------------------
// 4. Admin Comments
// ---------------------------------------------------------------------------

export async function addAdminComment(
  applicationId: string,
  comment: string,
  visibilityType: string = 'internal'
): Promise<AdminComment> {
  const response = await apiClient.post<AdminComment>(
    `/admin/applications/${applicationId}/comments`,
    {
      comment,
      visibility_type: visibilityType,
    }
  );
  return response.data;
}

export async function getAdminComments(
  applicationId: string
): Promise<AdminComment[]> {
  const response = await apiClient.get<AdminComment[]>(
    `/admin/applications/${applicationId}/comments`
  );
  return response.data;
}

// ---------------------------------------------------------------------------
// 5. Notifications
// ---------------------------------------------------------------------------

export async function getAdminNotifications(
  limit: number = 50
): Promise<NotificationListResponse> {
  const response = await apiClient.get<NotificationListResponse>(
    '/admin/notifications',
    { params: { limit } }
  );
  return response.data;
}

export async function getVendorNotifications(
  vendorId: string,
  limit: number = 50
): Promise<NotificationListResponse> {
  const response = await apiClient.get<NotificationListResponse>(
    `/vendors/${vendorId}/notifications`,
    { params: { limit } }
  );
  return response.data;
}

export async function markNotificationRead(
  notificationId: string
): Promise<void> {
  await apiClient.patch(`/notifications/${notificationId}/read`);
}

export async function markAllNotificationsRead(
  recipientType: 'admin' | 'vendor',
  vendorId?: string
): Promise<number> {
  const response = await apiClient.patch('/notifications/read-all', null, {
    params: {
      recipient_type: recipientType,
      vendor_id: vendorId,
    },
  });
  return response.data?.count || 0;
}

// ---------------------------------------------------------------------------
// 6. Chronological Activity Timeline
// ---------------------------------------------------------------------------

export async function getAdminApplicationActivity(
  applicationId: string
): Promise<ActivityEvent[]> {
  const response = await apiClient.get<ActivityEvent[]>(
    `/admin/applications/${applicationId}/activity`
  );
  return response.data;
}

export async function getVendorApplicationActivity(
  vendorId: string
): Promise<ActivityEvent[]> {
  const response = await apiClient.get<ActivityEvent[]>(
    `/vendors/${vendorId}/activity`
  );
  return response.data;
}

// ---------------------------------------------------------------------------
// 7. AI Insights
// ---------------------------------------------------------------------------

export async function getApplicationInsights(
  applicationId: string
): Promise<AIInsightsResponse> {
  const response = await apiClient.get<AIInsightsResponse>(
    `/admin/applications/${applicationId}/insights`
  );
  return response.data;
}

export async function generateApplicationInsights(
  applicationId: string
): Promise<AIInsightsResponse> {
  const response = await apiClient.post<AIInsightsResponse>(
    `/admin/applications/${applicationId}/insights/generate`
  );
  return response.data;
}

export async function getVendorInsights(
  vendorId: string
): Promise<AIInsightsResponse> {
  const response = await apiClient.get<AIInsightsResponse>(
    `/vendors/${vendorId}/insights`
  );
  return response.data;
}

