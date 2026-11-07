/**
 * Vendor API service — Phase 6 integration.
 *
 * Maps frontend VendorFormData (camelCase) to backend snake_case request bodies
 * and maps backend VendorResponse back to frontend types.
 *
 * Endpoints used:
 *   POST   /vendors/           → create draft
 *   GET    /vendors/{id}       → retrieve
 *   PATCH  /vendors/{id}       → partial update (per step)
 *   POST   /vendors/{id}/submit → submit
 *   GET    /vendors/{id}/status → status
 */

import type { AxiosError } from 'axios';
import apiClient from './api';
import type {
  CompanyInformationData,
  ContactInformationData,
  TaxBankingInformationData,
} from '../types/vendor';

// ---------------------------------------------------------------------------
// Backend response shapes (what the API actually returns)
// ---------------------------------------------------------------------------

export interface BackendVendorResponse {
  id: string;
  reference_number: string;
  status: string;
  company_info: {
    legal_company_name: string;
    trade_name: string;
    business_entity_type: string;
    country: string;
    registration_number: string;
    incorporation_date: string;
    industry: string;
    website: string;
    registered_address: {
      street: string;
      city: string;
      state: string;
      pincode: string;
      country: string;
    } | null;
    is_operational_same_as_registered: boolean;
    operational_address: {
      street: string;
      city: string;
      state: string;
      pincode: string;
      country: string;
    } | null;
  };
  contact_info: {
    primary: {
      first_name: string;
      last_name: string;
      designation: string;
      email: string | null;
      phone: string;
      department: string;
    };
    secondary: {
      full_name: string;
      email: string | null;
      phone: string;
    } | null;
    signatory: {
      full_name: string;
      designation: string;
      email: string | null;
    };
    confirm_authorized: boolean;
  };
  tax_details: {
    pan_number_masked: string;
    gst_status: string;
    gstin: string;
    gst_state: string;
    tan_number: string;
  };
  banking_details: {
    account_holder_name: string;
    bank_name: string;
    account_number_masked: string;
    ifsc_code: string;
    account_type: string;
    bank_branch: string;
  };
  created_at: string;
  updated_at: string;
  submitted_at: string | null;
}

export interface BackendSubmissionResponse {
  message: string;
  vendor_id: string;
  reference_number: string;
  status: string;
  submitted_at: string;
}

export interface BackendStatusResponse {
  vendor_id: string;
  reference_number: string;
  status: string;
  submitted_at: string | null;
  updated_at: string;
}

export interface BackendMissingField {
  field: string;
  message: string;
}

export interface ParsedSubmissionError {
  summary: string;
  fieldErrors: Record<string, string>;
  firstErrorKey?: string;
  firstErrorStep?: number;
}

// ---------------------------------------------------------------------------
// Field mappers: frontend → backend request body
// ---------------------------------------------------------------------------

export function buildCompanyInfoPayload(data: CompanyInformationData) {
  return {
    company_info: {
      legal_company_name: data.legalCompanyName,
      trade_name: data.tradeName,
      business_entity_type: data.businessEntityType || undefined,
      country: data.country,
      registration_number: data.registrationNumber,
      incorporation_date: data.incorporationDate,
      industry: data.industry || undefined,
      website: data.website,
      registered_address: data.registeredAddress
        ? {
            street: data.registeredAddress,
            city: data.registeredCity,
            state: data.registeredState,
            pincode: data.registeredPincode,
            country: data.country,
          }
        : undefined,
      is_operational_same_as_registered: data.isOperationalSameAsRegistered,
      operational_address:
        !data.isOperationalSameAsRegistered && data.operationalAddress
          ? {
              street: data.operationalAddress,
              city: data.operationalCity,
              state: data.operationalState,
              pincode: data.operationalPincode,
              country: data.country,
            }
          : null,
    },
  };
}

export function buildContactInfoPayload(data: ContactInformationData) {
  return {
    contact_info: {
      primary: {
        first_name: data.primaryFirstName,
        last_name: data.primaryLastName,
        designation: data.primaryDesignation,
        email: data.primaryEmail || undefined,
        phone: data.primaryMobile,
        department: data.primaryDepartment,
      },
      secondary:
        data.secondaryName || data.secondaryEmail
          ? {
              full_name: data.secondaryName,
              email: data.secondaryEmail || undefined,
              phone: data.secondaryPhone,
            }
          : undefined,
      signatory: {
        full_name: data.signatoryName,
        designation: data.signatoryDesignation,
        email: data.signatoryEmail || undefined,
      },
      confirm_authorized: data.confirmAuthorized,
    },
  };
}

export function buildTaxDetailsPayload(data: TaxBankingInformationData) {
  return {
    tax_details: {
      pan_number: data.panNumber.toUpperCase(),
      gst_status: data.gstStatus,
      gstin: data.gstin.toUpperCase(),
      gst_state: data.gstState,
      tan_number: data.tanNumber.toUpperCase(),
    },
  };
}

export function buildBankingDetailsPayload(data: TaxBankingInformationData) {
  return {
    banking_details: {
      account_holder_name: data.accountHolderName,
      bank_name: data.bankName,
      account_number: data.accountNumber,
      confirm_account_number: data.confirmAccountNumber,
      ifsc_code: data.ifscCode.toUpperCase(),
      account_type: data.accountType || undefined,
      bank_branch: data.bankBranch,
      confirm_bank_ownership: data.confirmBankOwnership,
    },
  };
}

// ---------------------------------------------------------------------------
// Field & Step Metadata
// ---------------------------------------------------------------------------

export const FIELD_LABELS: Record<string, string> = {
  legalCompanyName: 'Legal Company Name',
  tradeName: 'Trade Name / Brand Name',
  businessEntityType: 'Business Entity Type',
  country: 'Country of Registration',
  registrationNumber: 'Registration Number (CIN / LLPIN)',
  incorporationDate: 'Date of Incorporation',
  industry: 'Industry',
  website: 'Company Website',
  registeredAddress: 'Registered Office Address',
  registeredCity: 'City',
  registeredState: 'State',
  registeredPincode: 'PIN Code',
  operationalAddress: 'Operational Address',
  operationalCity: 'Operational City',
  operationalState: 'Operational State',
  operationalPincode: 'Operational PIN Code',

  primaryFirstName: 'Primary Contact First Name',
  primaryLastName: 'Primary Contact Last Name',
  primaryDesignation: 'Primary Contact Designation',
  primaryEmail: 'Primary Business Email Address',
  primaryMobile: 'Primary Mobile Number',
  primaryDepartment: 'Department',
  signatoryName: 'Authorized Signatory Full Name',
  signatoryDesignation: 'Signatory Designation',
  signatoryEmail: 'Signatory Email Address',
  confirmAuthorized: 'Authorization Confirmation',
  secondaryName: 'Secondary Contact Name',
  secondaryEmail: 'Secondary Contact Email',
  secondaryPhone: 'Secondary Contact Phone',

  panNumber: 'PAN Number',
  gstStatus: 'GST Registration Status',
  gstin: 'GSTIN (Goods & Services Tax ID)',
  gstState: 'GST Registration State',
  tanNumber: 'TAN Number',
  accountHolderName: 'Account Holder Name',
  bankName: 'Bank Name',
  accountNumber: 'Bank Account Number',
  confirmAccountNumber: 'Confirm Bank Account Number',
  ifscCode: 'IFSC Code',
  accountType: 'Account Type',
  bankBranch: 'Branch Name',
  confirmBankOwnership: 'Bank Account Ownership Confirmation',

  certificateOfIncorporation: 'Certificate of Incorporation',
  panCard: 'Company PAN Card Document',
  gstCertificate: 'GST Registration Certificate',
  bankProof: 'Cancelled Cheque / Bank Statement',
  tanCertificate: 'TAN Certificate',
  msmeCertificate: 'MSME Certificate',
  confirmAccurate: 'Accuracy Declaration',
  authorizeVerification: 'Verification Authorization',
  agreeTerms: 'Terms & Conditions Agreement',
};

export function getFieldStep(fieldKey: string): number {
  const step1 = [
    'legalCompanyName', 'tradeName', 'businessEntityType', 'country',
    'registrationNumber', 'incorporationDate', 'industry', 'website',
    'registeredAddress', 'registeredCity', 'registeredState', 'registeredPincode',
    'isOperationalSameAsRegistered', 'operationalAddress', 'operationalCity', 'operationalState', 'operationalPincode'
  ];
  const step2 = [
    'primaryFirstName', 'primaryLastName', 'primaryDesignation', 'primaryEmail',
    'primaryMobile', 'primaryDepartment', 'secondaryName', 'secondaryEmail',
    'secondaryPhone', 'signatoryName', 'signatoryDesignation', 'signatoryEmail',
    'confirmAuthorized'
  ];
  const step3 = [
    'panNumber', 'gstStatus', 'gstin', 'gstState', 'tanNumber',
    'accountHolderName', 'bankName', 'accountNumber', 'confirmAccountNumber',
    'ifscCode', 'accountType', 'bankBranch', 'confirmBankOwnership'
  ];
  const step4 = [
    'certificateOfIncorporation', 'panCard', 'gstCertificate', 'bankProof',
    'tanCertificate', 'msmeCertificate', 'confirmAccurate', 'authorizeVerification', 'agreeTerms'
  ];

  if (step1.includes(fieldKey)) return 1;
  if (step2.includes(fieldKey)) return 2;
  if (step3.includes(fieldKey)) return 3;
  if (step4.includes(fieldKey)) return 4;
  return 1;
}

export function mapBackendFieldToFrontend(backendField: string, message?: string): string {
  const f = backendField.toLowerCase();
  const m = (message || '').toLowerCase();

  // Company info (Step 1)
  if (f.includes('legal_company_name')) return 'legalCompanyName';
  if (f.includes('trade_name')) return 'tradeName';
  if (f.includes('business_entity_type')) return 'businessEntityType';
  if (f.includes('registration_number') || m.includes('registration_number')) return 'registrationNumber';
  if (f.includes('incorporation_date') || m.includes('incorporation_date')) return 'incorporationDate';
  if (f.includes('industry')) return 'industry';
  if (f.includes('website')) return 'website';
  if (f.includes('registered_address.street') || f === 'company_info.registered_address') return 'registeredAddress';
  if (f.includes('registered_address.city')) return 'registeredCity';
  if (f.includes('registered_address.state')) return 'registeredState';
  if (f.includes('registered_address.pincode') || f.includes('registered_address')) return 'registeredPincode';
  if (f.includes('operational_address.street') || f === 'company_info.operational_address' || m.includes('operational_address')) return 'operationalAddress';
  if (f.includes('operational_address.city')) return 'operationalCity';
  if (f.includes('operational_address.state')) return 'operationalState';
  if (f.includes('operational_address.pincode')) return 'operationalPincode';
  if (f.includes('country')) return 'country';

  // Contact info (Step 2)
  if (f.includes('primary.first_name') || m.includes('primary.first_name') || m.includes('first_name')) return 'primaryFirstName';
  if (f.includes('primary.last_name') || m.includes('primary.last_name') || m.includes('last_name')) return 'primaryLastName';
  if (f.includes('primary.designation') || m.includes('primary.designation') || m.includes('designation')) return 'primaryDesignation';
  if (f.includes('primary.email') || m.includes('primary.email')) return 'primaryEmail';
  if (f.includes('primary.phone') || m.includes('primary.phone') || m.includes('phone')) return 'primaryMobile';
  if (f.includes('primary.department') || m.includes('primary.department') || m.includes('department')) return 'primaryDepartment';
  if (f.includes('signatory.full_name') || m.includes('signatory.full_name')) return 'signatoryName';
  if (f.includes('signatory.designation') || m.includes('signatory.designation')) return 'signatoryDesignation';
  if (f.includes('signatory.email') || m.includes('signatory.email')) return 'signatoryEmail';
  if (f.includes('confirm_authorized') || m.includes('confirm_authorized') || m.includes('authorized')) return 'confirmAuthorized';
  if (f.includes('secondary.full_name')) return 'secondaryName';
  if (f.includes('secondary.email')) return 'secondaryEmail';
  if (f.includes('secondary.phone')) return 'secondaryPhone';

  // Tax info (Step 3)
  if (f.includes('pan_number') || m.includes('pan')) return 'panNumber';
  if (f.includes('gst_status')) return 'gstStatus';
  if (f.includes('gstin') || m.includes('gstin')) return 'gstin';
  if (f.includes('gst_state') || m.includes('gst_state')) return 'gstState';
  if (f.includes('tan_number')) return 'tanNumber';

  // Banking info (Step 3)
  if (f.includes('account_holder_name') || m.includes('account_holder_name')) return 'accountHolderName';
  if (f.includes('bank_name') || m.includes('bank_name')) return 'bankName';
  if (f.includes('account_number') && !f.includes('confirm')) return 'accountNumber';
  if (f.includes('confirm_account_number')) return 'confirmAccountNumber';
  if (f.includes('ifsc_code') || m.includes('ifsc')) return 'ifscCode';
  if (f.includes('account_type')) return 'accountType';
  if (f.includes('bank_branch')) return 'bankBranch';
  if (f.includes('confirm_bank_ownership') || m.includes('confirm_bank_ownership')) return 'confirmBankOwnership';

  // Declarations (Step 4)
  if (f.includes('confirm_accurate')) return 'confirmAccurate';
  if (f.includes('authorize_verification')) return 'authorizeVerification';
  if (f.includes('agree_terms')) return 'agreeTerms';

  // Documents
  if (f.includes('document')) return 'panCard';

  return backendField;
}

export function extractSubmissionErrors(error: unknown): ParsedSubmissionError {
  const fallbackSummary = 'Cannot submit incomplete vendor registration. Missing or invalid required fields.';
  if (!error) {
    return { summary: fallbackSummary, fieldErrors: {} };
  }

  const axiosErr = error as AxiosError<{
    detail?: string | { message?: string; missing_fields?: BackendMissingField[] };
  }>;

  const detail = axiosErr.response?.data?.detail;
  let summary = fallbackSummary;
  const fieldErrors: Record<string, string> = {};

  if (typeof detail === 'string') {
    summary = detail;
  } else if (detail && typeof detail === 'object') {
    if (detail.message) {
      summary = detail.message;
    }
    if (Array.isArray(detail.missing_fields)) {
      for (const item of detail.missing_fields) {
        const feKey = mapBackendFieldToFrontend(item.field, item.message);
        const cleanMsg = item.message
          ? item.message.replace(/^Value error,\s*/i, '').replace(/string should have at least \d+ character[s]?/i, `${FIELD_LABELS[feKey] || 'This field'} is required`)
          : `${FIELD_LABELS[feKey] || feKey} is required`;
        fieldErrors[feKey] = cleanMsg;
      }
    }
  } else if (axiosErr.message) {
    summary = axiosErr.message;
  }

  const keys = Object.keys(fieldErrors);
  let firstErrorKey: string | undefined;
  let firstErrorStep: number | undefined;

  if (keys.length > 0) {
    keys.sort((a, b) => getFieldStep(a) - getFieldStep(b));
    firstErrorKey = keys[0];
    firstErrorStep = getFieldStep(firstErrorKey);
  }

  return { summary, fieldErrors, firstErrorKey, firstErrorStep };
}

/**
 * Smoothly scrolls the viewport to the target field, focuses it,
 * and adds an animated pulse highlight so the user immediately sees it.
 */
export function scrollToAndFocusField(fieldKey: string) {
  const tryFocus = (): boolean => {
    const candidates = [
      fieldKey,
      // kebab-case
      fieldKey.replace(/([a-z0-9])([A-Z])/g, '$1-$2').toLowerCase(),
      // specific known element IDs
      fieldKey === 'certificateOfIncorporation' ? 'doc-coi' : null,
      fieldKey === 'panCard' ? 'doc-pan' : null,
      fieldKey === 'gstCertificate' ? 'doc-gst' : null,
      fieldKey === 'bankProof' ? 'doc-bank' : null,
      fieldKey === 'msmeCertificate' ? 'doc-msme' : null,
      fieldKey === 'tanProof' ? 'doc-tan' : null,
      fieldKey === 'confirmAccurate' ? 'confirm-accurate' : null,
      fieldKey === 'authorizeVerification' ? 'authorize-verification' : null,
      fieldKey === 'agreeTerms' ? 'agree-terms' : null,
      fieldKey === 'confirmAuthorized' ? 'confirmAuthorized' : null,
      fieldKey === 'confirmBankOwnership' ? 'confirmBankOwnership' : null,
      fieldKey === 'isOperationalSameAsRegistered' ? 'isOperationalSameAsRegistered' : null,
    ].filter(Boolean) as string[];

    let element: HTMLElement | null = null;
    for (const id of candidates) {
      const el = document.getElementById(id);
      if (el) {
        element = el;
        break;
      }
    }

    if (!element) {
      element = document.querySelector(`[name="${fieldKey}"]`) as HTMLElement;
    }

    // Fallback if the field is conditionally hidden:
    if (!element) {
      if (fieldKey.startsWith('operational')) {
        element = document.getElementById('isOperationalSameAsRegistered');
      } else if (fieldKey === 'registrationNumber' || fieldKey === 'incorporationDate') {
        element = document.getElementById('businessEntityType');
      } else if (fieldKey === 'gstin' || fieldKey === 'gstState') {
        element = document.getElementById('gstStatus');
      } else if (fieldKey.startsWith('secondary')) {
        element = document.getElementById('secondaryName');
      }
    }

    if (element) {
      const container = element.closest('.space-y-1\\.5, .rounded-2xl, .flex-col, .pt-2') || element;
      container.scrollIntoView({ behavior: 'smooth', block: 'center' });

      if (typeof element.focus === 'function') {
        element.focus({ preventScroll: true });
      }

      // Highlight target (if input is sr-only checkbox, highlight its container)
      const highlightEl = element.classList.contains('sr-only')
        ? (element.closest('.group, label, div') as HTMLElement) || element
        : element;

      // Add prominent red ring pulse
      highlightEl.classList.add('ring-4', 'ring-red-400', 'ring-opacity-80', 'transition-all');
      setTimeout(() => {
        highlightEl?.classList.remove('ring-4', 'ring-red-400', 'ring-opacity-80');
      }, 3500);
      return true;
    }
    return false;
  };

  // Run on next tick and retry if DOM is still mounting after step transition
  setTimeout(() => {
    if (!tryFocus()) {
      setTimeout(tryFocus, 200);
    }
  }, 120);
}

// ---------------------------------------------------------------------------
// API calls
// ---------------------------------------------------------------------------

/**
 * Create a new vendor draft (POST /vendors/).
 * Sends minimal data — just enough to get a vendor_id back.
 */
export async function createVendorDraft(): Promise<BackendVendorResponse> {
  const response = await apiClient.post<BackendVendorResponse>('/vendors/', {});
  return response.data;
}

/**
 * Retrieve a vendor by ID.
 */
export async function getVendor(vendorId: string): Promise<BackendVendorResponse> {
  const response = await apiClient.get<BackendVendorResponse>(`/vendors/${vendorId}`);
  return response.data;
}

/**
 * PATCH a vendor with whichever section changed.
 */
export async function patchVendor(
  vendorId: string,
  payload: Record<string, unknown>
): Promise<BackendVendorResponse> {
  const response = await apiClient.patch<BackendVendorResponse>(
    `/vendors/${vendorId}`,
    payload
  );
  return response.data;
}

/**
 * Submit vendor registration (POST /vendors/{id}/submit).
 */
export async function submitVendor(vendorId: string): Promise<BackendSubmissionResponse> {
  const response = await apiClient.post<BackendSubmissionResponse>(
    `/vendors/${vendorId}/submit`
  );
  return response.data;
}

/**
 * Retrieve vendor onboarding status.
 */
export async function getVendorStatus(vendorId: string): Promise<BackendStatusResponse> {
  const response = await apiClient.get<BackendStatusResponse>(
    `/vendors/${vendorId}/status`
  );
  return response.data;
}

/**
 * Extract a user-readable error message from an Axios error.
 */
export function extractErrorMessage(error: unknown, fallback = 'An unexpected error occurred.'): string {
  if (!error) return fallback;
  const axiosErr = error as AxiosError<{ detail?: string | { message?: string; missing_fields?: unknown[] } }>;
  const detail = axiosErr.response?.data?.detail;
  if (typeof detail === 'string') return detail;
  if (detail && typeof detail === 'object' && 'message' in detail) {
    return String(detail.message);
  }
  if (axiosErr.message) return axiosErr.message;
  return fallback;
}
