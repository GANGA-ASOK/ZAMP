import type {
  CompanyInformationData,
  ContactInformationData,
  DocumentSubmissionData,
  FormValidationErrors,
  TaxBankingInformationData,
} from '../types/vendor';

export const PAN_REGEX = /^[A-Z]{5}[0-9]{4}[A-Z]{1}$/;
export const GSTIN_REGEX = /^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$/;
export const IFSC_REGEX = /^[A-Z]{4}0[A-Z0-9]{6}$/;
export const EMAIL_REGEX = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
export const PHONE_REGEX = /^[+]?[(]?[0-9]{1,4}[)]?[-\s./0-9]{8,14}$/;
export const PINCODE_REGEX = /^[1-9][0-9]{5}$/;
export const URL_REGEX = /^(https?:\/\/)?(www\.)?[-a-zA-Z0-9@:%._+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b([-a-zA-Z0-9()@:%_+.~#?&//=]*)$/;

export const INDIAN_STATES = [
  'Andhra Pradesh',
  'Arunachal Pradesh',
  'Assam',
  'Bihar',
  'Chhattisgarh',
  'Goa',
  'Gujarat',
  'Haryana',
  'Himachal Pradesh',
  'Jharkhand',
  'Karnataka',
  'Kerala',
  'Madhya Pradesh',
  'Maharashtra',
  'Manipur',
  'Meghalaya',
  'Mizoram',
  'Nagaland',
  'Odisha',
  'Punjab',
  'Rajasthan',
  'Sikkim',
  'Tamil Nadu',
  'Telangana',
  'Tripura',
  'Uttar Pradesh',
  'Uttarakhand',
  'West Bengal',
  'Andaman and Nicobar Islands',
  'Chandigarh',
  'Dadra and Nagar Haveli and Daman and Diu',
  'Delhi (NCT)',
  'Jammu and Kashmir',
  'Ladakh',
  'Lakshadweep',
  'Puducherry',
];

export const INDUSTRIES = [
  'Information Technology',
  'Manufacturing',
  'Construction',
  'Healthcare',
  'Financial Services',
  'Education',
  'Agriculture',
  'Logistics and Transportation',
  'Consulting and Professional Services',
  'Retail and E-commerce',
  'Other',
];

export const DEPARTMENTS = [
  'Finance',
  'Accounts',
  'Sales',
  'Operations',
  'Administration',
  'Management',
  'Other',
];

export function validateStep1(data: CompanyInformationData): FormValidationErrors {
  const errors: FormValidationErrors = {};

  if (!data.legalCompanyName.trim()) {
    errors.legalCompanyName = 'Legal company name is required';
  }

  if (!data.businessEntityType) {
    errors.businessEntityType = 'Business entity type is required';
  }

  if (!data.country) {
    errors.country = 'Country is required';
  }

  // Registration number & Date of incorporation required for corporate entities
  const requiresCorporateDetails = [
    'Private Limited Company',
    'Public Limited Company',
    'Limited Liability Partnership (LLP)',
    'One Person Company (OPC)',
  ].includes(data.businessEntityType);

  if (requiresCorporateDetails) {
    if (!data.registrationNumber.trim()) {
      errors.registrationNumber = 'Company registration number (CIN / LLPIN) is required';
    }
    if (!data.incorporationDate) {
      errors.incorporationDate = 'Date of incorporation is required';
    }
  }

  if (!data.industry) {
    errors.industry = 'Industry selection is required';
  }

  if (data.website.trim() && !URL_REGEX.test(data.website.trim())) {
    errors.website = 'Please enter a valid website URL (e.g. https://example.com)';
  }

  if (!data.registeredAddress.trim()) {
    errors.registeredAddress = 'Registered office address is required';
  }

  if (!data.registeredCity.trim()) {
    errors.registeredCity = 'City is required';
  }

  if (!data.registeredState.trim()) {
    errors.registeredState = 'State is required';
  }

  if (!data.registeredPincode.trim()) {
    errors.registeredPincode = 'PIN Code is required';
  } else if (data.country === 'India' && !PINCODE_REGEX.test(data.registeredPincode.trim())) {
    errors.registeredPincode = 'Please enter a valid 6-digit Indian PIN Code';
  }

  if (!data.isOperationalSameAsRegistered) {
    if (!data.operationalAddress.trim()) {
      errors.operationalAddress = 'Operational address is required';
    }
    if (!data.operationalCity.trim()) {
      errors.operationalCity = 'City is required';
    }
    if (!data.operationalState.trim()) {
      errors.operationalState = 'State is required';
    }
    if (!data.operationalPincode.trim()) {
      errors.operationalPincode = 'PIN Code is required';
    } else if (data.country === 'India' && !PINCODE_REGEX.test(data.operationalPincode.trim())) {
      errors.operationalPincode = 'Please enter a valid 6-digit Indian PIN Code';
    }
  }

  return errors;
}

export function validateStep2(data: ContactInformationData): FormValidationErrors {
  const errors: FormValidationErrors = {};

  // Primary contact
  if (!data.primaryFirstName.trim()) {
    errors.primaryFirstName = 'First name is required';
  }
  if (!data.primaryLastName.trim()) {
    errors.primaryLastName = 'Last name is required';
  }
  if (!data.primaryDesignation.trim()) {
    errors.primaryDesignation = 'Designation is required';
  }
  if (!data.primaryEmail.trim()) {
    errors.primaryEmail = 'Business email address is required';
  } else if (!EMAIL_REGEX.test(data.primaryEmail.trim())) {
    errors.primaryEmail = 'Please enter a valid email address';
  }
  if (!data.primaryMobile.trim()) {
    errors.primaryMobile = 'Mobile number is required';
  } else if (!PHONE_REGEX.test(data.primaryMobile.trim())) {
    errors.primaryMobile = 'Please enter a valid phone number';
  }
  if (!data.primaryDepartment) {
    errors.primaryDepartment = 'Department selection is required';
  }

  // Secondary contact (optional, but validate format if entered)
  if (data.secondaryEmail.trim() && !EMAIL_REGEX.test(data.secondaryEmail.trim())) {
    errors.secondaryEmail = 'Please enter a valid email address';
  }
  if (data.secondaryPhone.trim() && !PHONE_REGEX.test(data.secondaryPhone.trim())) {
    errors.secondaryPhone = 'Please enter a valid phone number';
  }

  // Authorized signatory
  if (!data.signatoryName.trim()) {
    errors.signatoryName = 'Authorized signatory name is required';
  }
  if (!data.signatoryDesignation.trim()) {
    errors.signatoryDesignation = 'Signatory designation is required';
  }
  if (!data.signatoryEmail.trim()) {
    errors.signatoryEmail = 'Signatory email is required';
  } else if (!EMAIL_REGEX.test(data.signatoryEmail.trim())) {
    errors.signatoryEmail = 'Please enter a valid email address';
  }

  // Mandatory authorization declaration
  if (!data.confirmAuthorized) {
    errors.confirmAuthorized = 'You must confirm that you are authorized to submit this application';
  }

  return errors;
}

export function validateStep3(data: TaxBankingInformationData): FormValidationErrors {
  const errors: FormValidationErrors = {};

  // Tax Validation
  const pan = data.panNumber.trim().toUpperCase();
  if (!pan) {
    errors.panNumber = 'PAN number is required';
  } else if (!PAN_REGEX.test(pan)) {
    errors.panNumber = 'Invalid PAN format. Must be 10 characters (e.g. ABCDE1234F)';
  }

  if (!data.gstStatus) {
    errors.gstStatus = 'GST status is required';
  }

  if (data.gstStatus === 'Registered') {
    const gstin = data.gstin.trim().toUpperCase();
    if (!gstin) {
      errors.gstin = 'GSTIN is required for GST registered vendors';
    } else if (!GSTIN_REGEX.test(gstin)) {
      errors.gstin = 'Invalid GSTIN format. Must be 15 characters (e.g. 29ABCDE1234F1Z5)';
    } else {
      // Consistency check: GSTIN chars 3 to 12 must match the entered PAN
      const embeddedPan = gstin.substring(2, 12);
      if (pan && embeddedPan !== pan) {
        errors.gstin = `GSTIN inconsistency: Embedded PAN (${embeddedPan}) does not match entered PAN (${pan})`;
      }
    }

    if (!data.gstState.trim()) {
      errors.gstState = 'GST registration state is required';
    }
  }

  if (data.tanNumber.trim()) {
    const tan = data.tanNumber.trim().toUpperCase();
    if (!/^[A-Z]{4}[0-9]{5}[A-Z]{1}$/.test(tan)) {
      errors.tanNumber = 'Invalid TAN format. Must be 10 characters (e.g. ABCD12345E)';
    }
  }

  // Banking Validation
  if (!data.accountHolderName.trim()) {
    errors.accountHolderName = 'Account holder name is required';
  }
  if (!data.bankName.trim()) {
    errors.bankName = 'Bank name is required';
  }
  if (!data.accountNumber.trim()) {
    errors.accountNumber = 'Bank account number is required';
  } else if (data.accountNumber.length < 8 || data.accountNumber.length > 20) {
    errors.accountNumber = 'Account number must be between 8 and 20 digits';
  }

  if (!data.confirmAccountNumber.trim()) {
    errors.confirmAccountNumber = 'Please confirm the bank account number';
  } else if (data.accountNumber !== data.confirmAccountNumber) {
    errors.confirmAccountNumber = 'Account numbers do not match';
  }

  const ifsc = data.ifscCode.trim().toUpperCase();
  if (!ifsc) {
    errors.ifscCode = 'IFSC code is required';
  } else if (!IFSC_REGEX.test(ifsc)) {
    errors.ifscCode = 'Invalid IFSC format. Must be 11 characters (e.g. HDFC0001234)';
  }

  if (!data.accountType) {
    errors.accountType = 'Account type is required';
  }

  if (!data.confirmBankOwnership) {
    errors.confirmBankOwnership = 'You must confirm that the account belongs to the business/proprietor';
  }

  return errors;
}

export function validateStep4(
  documentsData: DocumentSubmissionData,
  entityType: string,
  gstStatus: string
): FormValidationErrors {
  const errors: FormValidationErrors = {};

  const docs = documentsData.documents;

  // Check mandatory docs
  const requiresIncorporation = [
    'Private Limited Company',
    'Public Limited Company',
    'Limited Liability Partnership (LLP)',
    'One Person Company (OPC)',
  ].includes(entityType);

  if (requiresIncorporation && (!docs.certificateOfIncorporation || docs.certificateOfIncorporation.status !== 'completed')) {
    errors.certificateOfIncorporation = 'Certificate of Incorporation is required';
  }

  if (!docs.panCard || docs.panCard.status !== 'completed') {
    errors.panCard = 'PAN Card / Certificate is required';
  }

  if (gstStatus === 'Registered' && (!docs.gstCertificate || docs.gstCertificate.status !== 'completed')) {
    errors.gstCertificate = 'GST Registration Certificate is required';
  }

  if (!docs.bankProof || docs.bankProof.status !== 'completed') {
    errors.bankProof = 'Cancelled Cheque or Bank Proof is required';
  }

  // Mandatory Declarations
  if (!documentsData.confirmAccurate) {
    errors.confirmAccurate = 'Please confirm all information is accurate and complete';
  }
  if (!documentsData.authorizeVerification) {
    errors.authorizeVerification = 'Please authorize document and information verification';
  }
  if (!documentsData.agreeTerms) {
    errors.agreeTerms = 'Please agree to the vendor registration terms and conditions';
  }

  return errors;
}
