import type { FC, ChangeEvent } from 'react';
import { useState } from 'react';
import { Plus, Files } from '@phosphor-icons/react';
import { FileUploadCard } from '../components/onboarding/FileUploadCard';
import { FilePreviewModal } from '../components/onboarding/FilePreviewModal';
import { ReviewSummary } from '../components/onboarding/ReviewSummary';
import { FormCheckbox } from '../components/common/FormCheckbox';
import type {
  DocumentKey,
  DocumentSubmissionData,
  FormValidationErrors,
  UploadedDocInfo,
  VendorFormData,
} from '../types/vendor';

interface Step4DocumentSubmissionProps {
  formData: VendorFormData;
  errors: FormValidationErrors;
  onChange: (field: keyof DocumentSubmissionData, value: unknown) => void;
  onEditStep: (stepNumber: number) => void;
}

export const Step4DocumentSubmission: FC<Step4DocumentSubmissionProps> = ({
  formData,
  errors,
  onChange,
  onEditStep,
}) => {
  const [previewDoc, setPreviewDoc] = useState<UploadedDocInfo | null>(null);

  const { documents } = formData;
  const isGstRegistered = formData.taxBanking.gstStatus === 'Registered';
  const requiresIncorporation = [
    'Private Limited Company',
    'Public Limited Company',
    'Limited Liability Partnership (LLP)',
    'One Person Company (OPC)',
  ].includes(formData.company.businessEntityType);

  // Upload simulation handler
  const handleFileUpload = (key: DocumentKey, file: File) => {
    const docId = `doc-${key}-${Date.now()}`;
    const newDoc: UploadedDocInfo = {
      id: docId,
      key,
      fileName: file.name,
      fileSize: file.size,
      fileType: file.type || 'application/pdf',
      progress: 0,
      status: 'uploading',
      previewUrl: file.type.startsWith('image/') ? URL.createObjectURL(file) : undefined,
      uploadedAt: 'Just now',
    };

    // Update state to uploading
    const updatedDocs = { ...documents.documents, [key]: newDoc };
    onChange('documents', updatedDocs);

    // Simulate upload progress
    let currentProgress = 20;
    const interval = setInterval(() => {
      currentProgress += 30;
      if (currentProgress >= 100) {
        clearInterval(interval);
        newDoc.progress = 100;
        newDoc.status = 'completed';
        onChange('documents', { ...updatedDocs, [key]: { ...newDoc } });
      } else {
        newDoc.progress = currentProgress;
        onChange('documents', { ...updatedDocs, [key]: { ...newDoc } });
      }
    }, 150);
  };

  const handleRemoveDoc = (key: DocumentKey) => {
    const updatedDocs = { ...documents.documents };
    delete updatedDocs[key];
    onChange('documents', updatedDocs);
  };

  // Multiple other supporting documents handler
  const handleOtherFileUpload = (e: ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      const file = e.target.files[0];
      const docId = `other-doc-${Date.now()}`;
      const newDoc: UploadedDocInfo = {
        id: docId,
        key: 'otherDocuments',
        fileName: file.name,
        fileSize: file.size,
        fileType: file.type,
        progress: 100,
        status: 'completed',
        previewUrl: file.type.startsWith('image/') ? URL.createObjectURL(file) : undefined,
        uploadedAt: 'Just now',
      };
      onChange('otherFiles', [...documents.otherFiles, newDoc]);
    }
  };

  const handleRemoveOtherDoc = (index: number) => {
    const updated = [...documents.otherFiles];
    updated.splice(index, 1);
    onChange('otherFiles', updated);
  };

  return (
    <div className="space-y-8 animate-fadeIn">
      {/* File Preview Modal */}
      <FilePreviewModal
        document={previewDoc}
        onClose={() => setPreviewDoc(null)}
      />

      {/* Mandatory Documents Section */}
      <div className="space-y-4">
        <div className="flex items-center justify-between border-b border-slate-100 pb-2">
          <h3 className="text-sm font-semibold text-slate-800">
            Mandatory Supporting Documents
          </h3>
          <span className="text-xs text-red-500 font-medium">* Required for compliance</span>
        </div>

        <div className="space-y-3.5">
          {/* 1. Certificate of Incorporation */}
          <FileUploadCard
            id="doc-coi"
            title="Certificate of Incorporation / Registration"
            description="Official corporate registration certificate issued by the Registrar of Companies."
            required={requiresIncorporation}
            docInfo={documents.documents.certificateOfIncorporation}
            onFileSelect={(file) => handleFileUpload('certificateOfIncorporation', file)}
            onRemove={() => handleRemoveDoc('certificateOfIncorporation')}
            onPreview={setPreviewDoc}
            error={errors.certificateOfIncorporation}
          />

          {/* 2. PAN Card */}
          <FileUploadCard
            id="doc-pan"
            title="Company / Entity PAN Card"
            description="Copy of the Permanent Account Number card issued by the Income Tax Department."
            required
            docInfo={documents.documents.panCard}
            onFileSelect={(file) => handleFileUpload('panCard', file)}
            onRemove={() => handleRemoveDoc('panCard')}
            onPreview={setPreviewDoc}
            error={errors.panCard}
          />

          {/* 3. GST Registration Certificate */}
          {isGstRegistered && (
            <FileUploadCard
              id="doc-gst"
              title="GST Registration Certificate (Form REG-06)"
              description="Official certificate of provisional or final registration under GST law."
              required
              docInfo={documents.documents.gstCertificate}
              onFileSelect={(file) => handleFileUpload('gstCertificate', file)}
              onRemove={() => handleRemoveDoc('gstCertificate')}
              onPreview={setPreviewDoc}
              error={errors.gstCertificate}
            />
          )}

          {/* 4. Cancelled Cheque / Bank Proof */}
          <FileUploadCard
            id="doc-bank"
            title="Cancelled Cheque / Bank Statement"
            description="Cancelled cheque leaf or recent bank statement clearly showing account number and IFSC."
            required
            docInfo={documents.documents.bankProof}
            onFileSelect={(file) => handleFileUpload('bankProof', file)}
            onRemove={() => handleRemoveDoc('bankProof')}
            onPreview={setPreviewDoc}
            error={errors.bankProof}
          />
        </div>
      </div>

      {/* Optional Documents Section */}
      <div className="space-y-4 pt-2">
        <div className="flex items-center justify-between border-b border-slate-100 pb-2">
          <h3 className="text-sm font-semibold text-slate-800">
            Optional Supporting Documents
          </h3>
          <span className="text-xs text-slate-400">Enhance your verification trust score</span>
        </div>

        <div className="space-y-3.5">
          {/* TAN Certificate */}
          <FileUploadCard
            id="doc-tan"
            title="TAN Allotment Letter / Certificate"
            description="Tax Deduction and Collection Account Number proof."
            required={false}
            docInfo={documents.documents.tanCertificate}
            onFileSelect={(file) => handleFileUpload('tanCertificate', file)}
            onRemove={() => handleRemoveDoc('tanCertificate')}
            onPreview={setPreviewDoc}
          />

          {/* MSME / Udyam Certificate */}
          <FileUploadCard
            id="doc-msme"
            title="MSME / Udyam Registration Certificate"
            description="Applicable for micro, small, and medium enterprise classification."
            required={false}
            docInfo={documents.documents.msmeCertificate}
            onFileSelect={(file) => handleFileUpload('msmeCertificate', file)}
            onRemove={() => handleRemoveDoc('msmeCertificate')}
            onPreview={setPreviewDoc}
          />

          {/* Other Supporting Documents (Multi-file) */}
          <div className="rounded-2xl border border-slate-200 bg-white p-4 sm:p-5">
            <div className="flex items-start justify-between mb-3">
              <div>
                <h4 className="text-sm font-semibold text-slate-800">
                  Other Supporting Documents
                </h4>
                <p className="text-xs text-slate-500">
                  Upload trade licenses, ISO certificates, or additional authorizations.
                </p>
              </div>

              <label className="inline-flex items-center space-x-1.5 px-3 py-1.5 rounded-xl text-xs font-semibold text-[#0875D1] bg-sky-50 hover:bg-sky-100 border border-sky-200/60 transition-colors cursor-pointer">
                <Plus size={14} weight="bold" />
                <span>Add Document</span>
                <input
                  type="file"
                  accept=".pdf,.png,.jpg,.jpeg"
                  onChange={handleOtherFileUpload}
                  className="hidden"
                />
              </label>
            </div>

            {documents.otherFiles.length > 0 ? (
              <div className="space-y-2 mt-3">
                {documents.otherFiles.map((doc, idx) => (
                  <div
                    key={doc.id || idx}
                    className="flex items-center justify-between p-3 bg-slate-50 rounded-xl border border-slate-200 text-xs"
                  >
                    <div className="flex items-center space-x-2 truncate">
                      <Files size={16} className="text-[#0875D1] shrink-0" />
                      <span className="font-medium text-slate-800 truncate">{doc.fileName}</span>
                    </div>
                    <div className="flex items-center space-x-2 shrink-0">
                      <button
                        type="button"
                        onClick={() => setPreviewDoc(doc)}
                        className="text-[#0875D1] hover:underline cursor-pointer"
                      >
                        Preview
                      </button>
                      <button
                        type="button"
                        onClick={() => handleRemoveOtherDoc(idx)}
                        className="text-red-500 hover:text-red-700 cursor-pointer"
                      >
                        Remove
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-xs text-slate-400 italic">No additional documents added.</p>
            )}
          </div>
        </div>
      </div>

      {/* Review Summary Accordion */}
      <div className="pt-2">
        <ReviewSummary
          formData={formData}
          onEditStep={onEditStep}
        />
      </div>

      {/* Final Declarations */}
      <div className="space-y-3.5 p-5 rounded-2xl bg-blue-50/50 border border-blue-100 text-left">
        <h4 className="text-xs font-bold uppercase tracking-wider text-[#07569B]">
          Mandatory Declarations & Consent
        </h4>

        <FormCheckbox
          id="confirm-accurate"
          required
          checked={documents.confirmAccurate}
          onChange={(checked) => onChange('confirmAccurate', checked)}
          label="I confirm that all information provided in this application is accurate and complete."
          error={errors.confirmAccurate}
        />

        <FormCheckbox
          id="authorize-verification"
          required
          checked={documents.authorizeVerification}
          onChange={(checked) => onChange('authorizeVerification', checked)}
          label="I authorize the organization to verify the submitted company, tax, banking, and supporting documentation."
          error={errors.authorizeVerification}
        />

        <FormCheckbox
          id="agree-terms"
          required
          checked={documents.agreeTerms}
          onChange={(checked) => onChange('agreeTerms', checked)}
          label="I agree to the terms and conditions of vendor registration."
          error={errors.agreeTerms}
        />
      </div>
    </div>
  );
};
