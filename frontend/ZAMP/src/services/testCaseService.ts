/**
 * Test-case pre-fill for the vendor portal (testing / demo only).
 *
 * Each test case is a realistic submission designed to exercise the AI
 * Decision Engine. Loading one creates a fresh draft vendor on the backend
 * with the form saved and the case's documents (PAN card, GST certificate,
 * CoI, cancelled cheque) uploaded, then fills every step of the form.
 */

import apiClient from './api';
import { categoryToDocKey, type BackendDocumentMeta } from './documentService';
import type { UploadedDocInfo, VendorFormData } from '../types/vendor';

export interface TestCase {
  key: string;
  title: string;
  expected: 'approve' | 'review' | 'reject';
  story: string;
  documents: Array<{ category: string; file_name: string }>;
  requires_first: string | null;
}

export interface PrefillResult {
  vendor_id: string;
  reference_number: string;
  key: string;
  title: string;
  expected: TestCase['expected'];
  removed_previous: number;
  form: Record<string, any>;
  documents: BackendDocumentMeta[];
}

export async function listTestCases(): Promise<TestCase[]> {
  const res = await apiClient.get<TestCase[]>('/demo/scenarios');
  return res.data;
}

export async function prefillTestCase(key: string): Promise<PrefillResult> {
  const res = await apiClient.post<PrefillResult>(`/demo/scenarios/${key}/prefill`);
  return res.data;
}

/** Map the backend's stored form sections onto the onboarding form state. */
export function toVendorFormData(result: PrefillResult): VendorFormData {
  const ci = result.form.company_info || {};
  const addr = ci.registered_address || {};
  const ct = result.form.contact_info || {};
  const primary = ct.primary || {};
  const secondary = ct.secondary || {};
  const signatory = ct.signatory || {};
  const tx = result.form.tax_details || {};
  const bk = result.form.banking_details || {};

  const docs: Record<string, UploadedDocInfo> = {};
  for (const meta of result.documents) {
    const key = categoryToDocKey(meta.document_category);
    if (!key || key === 'otherDocuments') continue;
    docs[key] = {
      id: meta.document_id,
      key,
      fileName: meta.original_filename,
      fileSize: meta.file_size,
      fileType: meta.content_type,
      progress: 100,
      status: 'completed',
      uploadedAt: 'Just now',
    };
  }

  return {
    company: {
      legalCompanyName: ci.legal_company_name || '',
      tradeName: ci.trade_name || '',
      businessEntityType: ci.business_entity_type || '',
      country: ci.country || 'India',
      registrationNumber: ci.registration_number || '',
      incorporationDate: ci.incorporation_date || '',
      industry: ci.industry || '',
      website: ci.website || '',
      registeredAddress: addr.street || '',
      registeredCity: addr.city || '',
      registeredState: addr.state || '',
      registeredPincode: addr.pincode || '',
      isOperationalSameAsRegistered: ci.is_operational_same_as_registered ?? true,
      operationalAddress: '',
      operationalCity: '',
      operationalState: '',
      operationalPincode: '',
    },
    contact: {
      primaryFirstName: primary.first_name || '',
      primaryLastName: primary.last_name || '',
      primaryDesignation: primary.designation || '',
      primaryEmail: primary.email || '',
      primaryMobile: primary.phone || '',
      primaryDepartment: primary.department || '',
      secondaryName: secondary.full_name || '',
      secondaryEmail: secondary.email || '',
      secondaryPhone: secondary.phone || '',
      signatoryName: signatory.full_name || '',
      signatoryDesignation: signatory.designation || '',
      signatoryEmail: signatory.email || '',
      confirmAuthorized: ct.confirm_authorized ?? true,
    },
    taxBanking: {
      panNumber: tx.pan_number || '',
      gstStatus: tx.gst_status || 'Registered',
      gstin: tx.gstin || '',
      gstState: tx.gst_state || '',
      tanNumber: tx.tan_number || '',
      accountHolderName: bk.account_holder_name || '',
      bankName: bk.bank_name || '',
      accountNumber: bk.account_number || '',
      confirmAccountNumber: bk.account_number || '',
      ifscCode: bk.ifsc_code || '',
      accountType: bk.account_type || '',
      bankBranch: bk.bank_branch || '',
      confirmBankOwnership: bk.confirm_bank_ownership ?? true,
    },
    documents: {
      documents: docs,
      otherFiles: [],
      confirmAccurate: true,
      authorizeVerification: true,
      agreeTerms: true,
    },
  };
}
