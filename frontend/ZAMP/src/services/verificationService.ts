/**
 * Verification service for AI-powered document extraction and audit findings.
 * Integrates with NVIDIA Nemotron 3.5 Parse & Super VL verification endpoints.
 */

import apiClient from './api';

export type FindingStatus = 'match' | 'mismatch' | 'missing_in_document' | 'manual_review';

export interface ConsistencyFinding {
  field_name: string;
  vendor_value?: string | null;
  extracted_value?: string | null;
  status: FindingStatus;
  explanation: string;
  source_document_id?: string | null;
  page_number?: number | null;
}

export interface FieldValidationFinding {
  field_name: string;
  value?: string | null;
  is_valid: boolean;
  rule: string;
  details: string;
}

export interface ParsedPageResult {
  page_number: number;
  text: string;
  tables: string[];
  status: string;
}

export interface VerificationResultResponse {
  id: string;
  vendor_id: string;
  document_id: string;
  document_category: string;
  file_name: string;
  extraction_status: 'pending' | 'processing' | 'completed' | 'flagged' | 'needs_manual_review' | 'failed';
  verification_status: 'pending' | 'processing' | 'completed' | 'flagged' | 'needs_manual_review' | 'failed';
  parsed_pages: ParsedPageResult[];
  parsed_text: string;
  extracted_fields: Record<string, any>;
  field_validations: FieldValidationFinding[];
  consistency_findings: ConsistencyFinding[];
  summary_explanation: string;
  parse_model_id: string;
  super_vl_model_id: string;
  processing_version: string;
  processing_time_ms: number;
  error_details?: string | null;
  created_at: string;
  updated_at: string;
}

export interface VendorVerificationSummaryResponse {
  vendor_id: string;
  total_documents: number;
  verified_documents: number;
  flagged_documents: number;
  pending_documents: number;
  overall_status: 'verified' | 'flagged' | 'needs_manual_review' | 'pending';
  results: VerificationResultResponse[];
}

/**
 * Trigger AI document extraction and verification for a vendor document.
 */
export async function triggerVerification(
  vendorId: string,
  documentId: string,
  runAsync: boolean = false
): Promise<VerificationResultResponse> {
  const response = await apiClient.post<VerificationResultResponse>(
    `/vendors/${vendorId}/documents/${documentId}/verify`,
    null,
    { params: { run_async: runAsync } }
  );
  return response.data;
}

/**
 * Fetch verification results for a single document.
 */
export async function getDocumentVerification(
  vendorId: string,
  documentId: string
): Promise<VerificationResultResponse> {
  const response = await apiClient.get<VerificationResultResponse>(
    `/vendors/${vendorId}/documents/${documentId}/verification`
  );
  return response.data;
}

/**
 * Fetch overall verification summary and all document verification results for a vendor.
 */
export async function getVendorVerificationSummary(
  vendorId: string
): Promise<VendorVerificationSummaryResponse> {
  const response = await apiClient.get<VendorVerificationSummaryResponse>(
    `/vendors/${vendorId}/verification`
  );
  return response.data;
}

/**
 * Admin: Trigger or retry AI verification for a document.
 */
export async function adminTriggerVerification(
  documentId: string,
  runAsync: boolean = false
): Promise<VerificationResultResponse> {
  const response = await apiClient.post<VerificationResultResponse>(
    `/admin/documents/${documentId}/verify`,
    null,
    { params: { run_async: runAsync } }
  );
  return response.data;
}

/**
 * Admin: Retrieve verification result for a document across any vendor.
 */
export async function adminGetDocumentVerification(
  documentId: string
): Promise<VerificationResultResponse> {
  const response = await apiClient.get<VerificationResultResponse>(
    `/admin/documents/${documentId}/verification`
  );
  return response.data;
}
