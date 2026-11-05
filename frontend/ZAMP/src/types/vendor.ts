export type BusinessEntityType =
  | 'Private Limited Company'
  | 'Public Limited Company'
  | 'Limited Liability Partnership (LLP)'
  | 'Partnership'
  | 'Sole Proprietorship'
  | 'One Person Company (OPC)'
  | 'Other';

export type GSTStatus = 'Registered' | 'Not Registered' | 'Exempt';

export type AccountType = 'Current Account' | 'Savings Account' | 'Other';

export type DocumentKey =
  | 'certificateOfIncorporation'
  | 'panCard'
  | 'gstCertificate'
  | 'bankProof'
  | 'tanCertificate'
  | 'msmeCertificate'
  | 'otherDocuments';

export interface UploadedDocInfo {
  id: string;
  key: DocumentKey;
  fileName: string;
  fileSize: number;
  fileType: string;
  progress: number;
  status: 'idle' | 'uploading' | 'completed' | 'error';
  errorMessage?: string;
  previewUrl?: string;
  uploadedAt?: string;
}

export interface CompanyInformationData {
  legalCompanyName: string;
  tradeName: string;
  businessEntityType: BusinessEntityType | '';
  country: string;
  registrationNumber: string;
  incorporationDate: string;
  industry: string;
  website: string;
  registeredAddress: string;
  registeredCity: string;
  registeredState: string;
  registeredPincode: string;
  isOperationalSameAsRegistered: boolean;
  operationalAddress: string;
  operationalCity: string;
  operationalState: string;
  operationalPincode: string;
}

export interface ContactInformationData {
  primaryFirstName: string;
  primaryLastName: string;
  primaryDesignation: string;
  primaryEmail: string;
  primaryMobile: string;
  primaryDepartment: string;
  secondaryName: string;
  secondaryEmail: string;
  secondaryPhone: string;
  signatoryName: string;
  signatoryDesignation: string;
  signatoryEmail: string;
  confirmAuthorized: boolean;
}

export interface TaxBankingInformationData {
  panNumber: string;
  gstStatus: GSTStatus;
  gstin: string;
  gstState: string;
  tanNumber: string;
  accountHolderName: string;
  bankName: string;
  accountNumber: string;
  confirmAccountNumber: string;
  ifscCode: string;
  accountType: AccountType | '';
  bankBranch: string;
  confirmBankOwnership: boolean;
}

export interface DocumentSubmissionData {
  documents: Record<string, UploadedDocInfo>;
  otherFiles: UploadedDocInfo[];
  confirmAccurate: boolean;
  authorizeVerification: boolean;
  agreeTerms: boolean;
}

export interface VendorFormData {
  company: CompanyInformationData;
  contact: ContactInformationData;
  taxBanking: TaxBankingInformationData;
  documents: DocumentSubmissionData;
}

export interface FormValidationErrors {
  [key: string]: string | undefined;
}

export interface SubmissionResult {
  referenceNumber: string;
  submittedAt: string;
  status: 'Queued for Verification';
  companyName: string;
  primaryContactEmail: string;
  formData: VendorFormData;
}

