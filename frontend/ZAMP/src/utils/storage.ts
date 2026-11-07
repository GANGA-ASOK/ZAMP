import type { VendorFormData } from '../types/vendor';

const STORAGE_KEY = 'vendorflow_draft_data';
const SUBMISSION_KEY = 'vendorflow_submissions';

/**
 * TEMPORARY DEVELOPMENT MECHANISM — vendor ID persistence.
 *
 * The vendor ID returned from the backend (MongoDB ObjectId) is stored in
 * localStorage so the same vendor record is reused when the user refreshes
 * the page or returns to the form.
 *
 * ⚠️  This is NOT a secure identity mechanism. It is a placeholder for
 *      Phase 7 authentication (JWT / session-based identity). Any user who
 *      inspects localStorage can see and alter this value.  In production,
 *      the vendor ID must be derived from the authenticated session on the
 *      server side.
 */
const VENDOR_ID_KEY = 'vendorflow_vendor_id';

export function saveVendorId(id: string): void {
  try {
    localStorage.setItem(VENDOR_ID_KEY, id);
  } catch (e) {
    console.error('Failed to save vendor ID to localStorage', e);
  }
}

export function loadVendorId(): string | null {
  try {
    return localStorage.getItem(VENDOR_ID_KEY);
  } catch (e) {
    console.error('Failed to load vendor ID from localStorage', e);
    return null;
  }
}

export function clearVendorId(): void {
  try {
    localStorage.removeItem(VENDOR_ID_KEY);
  } catch (e) {
    console.error('Failed to clear vendor ID from localStorage', e);
  }
}

export const initialFormData: VendorFormData = {
  company: {
    legalCompanyName: '',
    tradeName: '',
    businessEntityType: '',
    country: 'India',
    registrationNumber: '',
    incorporationDate: '',
    industry: '',
    website: '',
    registeredAddress: '',
    registeredCity: '',
    registeredState: '',
    registeredPincode: '',
    isOperationalSameAsRegistered: true,
    operationalAddress: '',
    operationalCity: '',
    operationalState: '',
    operationalPincode: '',
  },
  contact: {
    primaryFirstName: '',
    primaryLastName: '',
    primaryDesignation: '',
    primaryEmail: '',
    primaryMobile: '',
    primaryDepartment: '',
    secondaryName: '',
    secondaryEmail: '',
    secondaryPhone: '',
    signatoryName: '',
    signatoryDesignation: '',
    signatoryEmail: '',
    confirmAuthorized: false,
  },
  taxBanking: {
    panNumber: '',
    gstStatus: 'Registered',
    gstin: '',
    gstState: '',
    tanNumber: '',
    accountHolderName: '',
    bankName: '',
    accountNumber: '',
    confirmAccountNumber: '',
    ifscCode: '',
    accountType: 'Current Account',
    bankBranch: '',
    confirmBankOwnership: false,
  },
  documents: {
    documents: {},
    otherFiles: [],
    confirmAccurate: false,
    authorizeVerification: false,
    agreeTerms: false,
  },
};

export function saveDraftToStorage(data: VendorFormData): void {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(data));
  } catch (e) {
    console.error('Failed to save draft to localStorage', e);
  }
}

export function loadDraftFromStorage(): VendorFormData {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return initialFormData;
    const parsed = JSON.parse(raw);
    return {
      ...initialFormData,
      ...parsed,
      company: { ...initialFormData.company, ...(parsed.company || {}) },
      contact: { ...initialFormData.contact, ...(parsed.contact || {}) },
      taxBanking: { ...initialFormData.taxBanking, ...(parsed.taxBanking || {}) },
      documents: { ...initialFormData.documents, ...(parsed.documents || {}) },
    };
  } catch (e) {
    console.error('Failed to parse draft from localStorage', e);
    return initialFormData;
  }
}

export function clearDraftStorage(): void {
  try {
    localStorage.removeItem(STORAGE_KEY);
    // Preserves vendor ID so vendor remains connected to their submitted application and documents
  } catch (e) {
    console.error('Failed to clear draft from localStorage', e);
  }
}

export function clearAllVendorData(): void {
  try {
    localStorage.removeItem(STORAGE_KEY);
    clearVendorId();
  } catch (e) {
    console.error('Failed to clear all vendor data from localStorage', e);
  }
}

export function saveSubmission(submission: unknown): void {
  try {
    const raw = localStorage.getItem(SUBMISSION_KEY);
    const list = raw ? JSON.parse(raw) : [];
    list.unshift(submission);
    localStorage.setItem(SUBMISSION_KEY, JSON.stringify(list));
  } catch (e) {
    console.error('Failed to save submission to localStorage', e);
  }
}

export function getSubmissions(): unknown[] {
  try {
    const raw = localStorage.getItem(SUBMISSION_KEY);
    return raw ? JSON.parse(raw) : [];
  } catch (e) {
    console.error('Failed to get submissions from localStorage', e);
    return [];
  }
}

export function getDemoFormData(): VendorFormData {
  return {
    company: {
      legalCompanyName: 'Acme Technologies Private Limited',
      tradeName: 'Acme Cloud',
      businessEntityType: 'Private Limited Company',
      country: 'India',
      registrationNumber: 'U72200KA2021PTC145678',
      incorporationDate: '2021-04-15',
      industry: 'Information Technology',
      website: 'https://acmecloud.tech',
      registeredAddress: 'Level 5, Tower B, Cyber City, Whitefield',
      registeredCity: 'Bengaluru',
      registeredState: 'Karnataka',
      registeredPincode: '560066',
      isOperationalSameAsRegistered: true,
      operationalAddress: '',
      operationalCity: '',
      operationalState: '',
      operationalPincode: '',
    },
    contact: {
      primaryFirstName: 'Rahul',
      primaryLastName: 'Sharma',
      primaryDesignation: 'Director of Procurement & Finance',
      primaryEmail: 'rahul.sharma@acmecloud.tech',
      primaryMobile: '+91 98765 43210',
      primaryDepartment: 'Finance',
      secondaryName: 'Priya Nair',
      secondaryEmail: 'priya.nair@acmecloud.tech',
      secondaryPhone: '+91 98765 43211',
      signatoryName: 'Vikramaditya Rao',
      signatoryDesignation: 'Managing Director',
      signatoryEmail: 'v.rao@acmecloud.tech',
      confirmAuthorized: true,
    },
    taxBanking: {
      panNumber: 'AAACA1234F',
      gstStatus: 'Registered',
      gstin: '29AAACA1234F1Z5',
      gstState: 'Karnataka',
      tanNumber: 'BLRA12345E',
      accountHolderName: 'ACME TECHNOLOGIES PVT LTD',
      bankName: 'HDFC Bank',
      accountNumber: '50200012345678',
      confirmAccountNumber: '50200012345678',
      ifscCode: 'HDFC0001234',
      accountType: 'Current Account',
      bankBranch: 'Whitefield Main Branch',
      confirmBankOwnership: true,
    },
    documents: {
      documents: {
        certificateOfIncorporation: {
          id: 'doc-coi-1',
          key: 'certificateOfIncorporation',
          fileName: 'Acme_Certificate_of_Incorporation.pdf',
          fileSize: 1420000,
          fileType: 'application/pdf',
          progress: 100,
          status: 'completed',
          previewUrl: '',
          uploadedAt: 'Just now',
        },
        panCard: {
          id: 'doc-pan-1',
          key: 'panCard',
          fileName: 'Company_PAN_Card.pdf',
          fileSize: 850000,
          fileType: 'application/pdf',
          progress: 100,
          status: 'completed',
          previewUrl: '',
          uploadedAt: 'Just now',
        },
        gstCertificate: {
          id: 'doc-gst-1',
          key: 'gstCertificate',
          fileName: 'GST_Registration_Certificate_REG06.pdf',
          fileSize: 1100000,
          fileType: 'application/pdf',
          progress: 100,
          status: 'completed',
          previewUrl: '',
          uploadedAt: 'Just now',
        },
        bankProof: {
          id: 'doc-bank-1',
          key: 'bankProof',
          fileName: 'Cancelled_Cheque_HDFC.jpg',
          fileSize: 620000,
          fileType: 'image/jpeg',
          progress: 100,
          status: 'completed',
          previewUrl: '',
          uploadedAt: 'Just now',
        },
      },
      otherFiles: [],
      confirmAccurate: true,
      authorizeVerification: true,
      agreeTerms: true,
    },
  };
}
