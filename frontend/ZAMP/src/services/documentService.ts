/**
 * Document API service — Phase 6 integration.
 *
 * Maps to Phase 5 endpoints:
 *   POST   /vendors/{id}/documents                       — upload
 *   GET    /vendors/{id}/documents                       — list
 *   GET    /vendors/{id}/documents/{docId}               — metadata
 *   GET    /vendors/{id}/documents/{docId}/download      — download
 *   PUT    /vendors/{id}/documents/{docId}               — replace
 *   DELETE /vendors/{id}/documents/{docId}               — delete
 *
 * DocumentKey → document_category mapping (frontend camelCase → backend snake_case):
 *   certificateOfIncorporation → certificate_of_incorporation
 *   panCard                    → pan_card
 *   gstCertificate             → gst_certificate
 *   bankProof                  → bank_proof
 *   tanCertificate             → tan_certificate
 *   msmeCertificate            → msme_certificate
 *   otherDocuments             → other
 */

import apiClient from './api';
import type { DocumentKey } from '../types/vendor';

// ---------------------------------------------------------------------------
// DocumentKey → backend category value
// ---------------------------------------------------------------------------

export const DOC_KEY_TO_CATEGORY: Record<DocumentKey, string> = {
  certificateOfIncorporation: 'certificate_of_incorporation',
  panCard: 'pan_card',
  gstCertificate: 'gst_certificate',
  bankProof: 'bank_proof',
  tanCertificate: 'tan_certificate',
  msmeCertificate: 'msme_certificate',
  otherDocuments: 'other',
};

// ---------------------------------------------------------------------------
// Backend document metadata shape
// ---------------------------------------------------------------------------

export interface BackendDocumentMeta {
  document_id: string;
  vendor_id: string;
  original_filename: string;
  document_category: string;
  content_type: string;
  file_size: number;
  upload_timestamp: string;
  verification_status: string;
}

export interface BackendDocumentListResponse {
  vendor_id: string;
  count: number;
  documents: BackendDocumentMeta[];
}

// ---------------------------------------------------------------------------
// API calls
// ---------------------------------------------------------------------------

/**
 * Upload a document for the given vendor.
 * Uses multipart/form-data — do NOT set Content-Type manually (browser sets it with boundary).
 */
export async function uploadDocument(
  vendorId: string,
  file: File,
  docKey: DocumentKey,
  onProgress?: (pct: number) => void
): Promise<BackendDocumentMeta> {
  const category = DOC_KEY_TO_CATEGORY[docKey];
  const form = new FormData();
  form.append('file', file);
  form.append('category', category);

  const response = await apiClient.post<BackendDocumentMeta>(
    `/vendors/${vendorId}/documents`,
    form,
    {
      headers: {
        // Let the browser set Content-Type with the proper boundary
        'Content-Type': undefined as unknown as string,
      },
      onUploadProgress: (evt) => {
        if (onProgress && evt.total) {
          onProgress(Math.round((evt.loaded / evt.total) * 100));
        }
      },
    }
  );
  return response.data;
}

/**
 * List all documents for a vendor.
 */
export async function listDocuments(vendorId: string): Promise<BackendDocumentMeta[]> {
  const response = await apiClient.get<BackendDocumentListResponse>(
    `/vendors/${vendorId}/documents`
  );
  return response.data.documents;
}

/**
 * Get metadata for a single document.
 */
export async function getDocumentMetadata(
  vendorId: string,
  documentId: string
): Promise<BackendDocumentMeta> {
  const response = await apiClient.get<BackendDocumentMeta>(
    `/vendors/${vendorId}/documents/${documentId}`
  );
  return response.data;
}

/**
 * Delete a document.
 */
export async function deleteDocument(vendorId: string, documentId: string): Promise<void> {
  await apiClient.delete(`/vendors/${vendorId}/documents/${documentId}`);
}

/**
 * Replace an existing document.
 */
export async function replaceDocument(
  vendorId: string,
  documentId: string,
  file: File,
  onProgress?: (pct: number) => void
): Promise<BackendDocumentMeta> {
  const form = new FormData();
  form.append('file', file);

  const response = await apiClient.put<BackendDocumentMeta>(
    `/vendors/${vendorId}/documents/${documentId}`,
    form,
    {
      headers: { 'Content-Type': undefined as unknown as string },
      onUploadProgress: (evt) => {
        if (onProgress && evt.total) {
          onProgress(Math.round((evt.loaded / evt.total) * 100));
        }
      },
    }
  );
  return response.data;
}

/**
 * Map a backend category value back to a frontend DocumentKey.
 */
export function categoryToDocKey(category: string): DocumentKey | null {
  for (const [key, val] of Object.entries(DOC_KEY_TO_CATEGORY)) {
    if (val === category) return key as DocumentKey;
  }
  return null;
}

/**
 * Return direct download URL for a document stored in GridFS.
 */
export function getDocumentDownloadUrl(vendorId: string, documentId: string): string {
  const base = apiClient.defaults.baseURL || 'http://localhost:8000/api';
  return `${base}/vendors/${vendorId}/documents/${documentId}/download`;
}

