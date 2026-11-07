import type { FC, ChangeEvent } from 'react';
import { useState, useEffect, useCallback } from 'react';
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
import {
  uploadDocument,
  listDocuments,
  deleteDocument,
  replaceDocument,
  categoryToDocKey,
  type BackendDocumentMeta,
} from '../services/documentService';
import { extractErrorMessage } from '../services/vendorService';

interface Step4DocumentSubmissionProps {
  formData: VendorFormData;
  errors: FormValidationErrors;
  onChange: (field: keyof DocumentSubmissionData, value: unknown) => void;
  onEditStep: (stepNumber: number) => void;
  /** MongoDB vendor ID from backend (null if not yet created) */
  vendorId: string | null;
  /** Called to lazily ensure the vendor exists before uploading */
  onVendorIdReady: () => Promise<string | null>;
}

/** Convert a backend document metadata to our frontend UploadedDocInfo shape */
function backendMetaToDocInfo(meta: BackendDocumentMeta, key: DocumentKey): UploadedDocInfo {
  return {
    id: meta.document_id,
    key,
    fileName: meta.original_filename,
    fileSize: meta.file_size,
    fileType: meta.content_type,
    progress: 100,
    status: 'completed',
    uploadedAt: meta.upload_timestamp
      ? new Date(meta.upload_timestamp).toLocaleString()
      : 'Uploaded',
  };
}

export const Step4DocumentSubmission: FC<Step4DocumentSubmissionProps> = ({
  formData,
  errors,
  onChange,
  onEditStep,
  vendorId,
  onVendorIdReady,
}) => {
  const [previewDoc, setPreviewDoc] = useState<UploadedDocInfo | null>(null);
  const [uploadErrors, setUploadErrors] = useState<Record<string, string>>({});

  const { documents } = formData;
  const isGstRegistered = formData.taxBanking.gstStatus === 'Registered';
  const requiresIncorporation = [
    'Private Limited Company',
    'Public Limited Company',
    'Limited Liability Partnership (LLP)',
    'One Person Company (OPC)',
  ].includes(formData.company.businessEntityType);

  // -------------------------------------------------------------------------
  // Load existing documents from backend on mount (when vendorId is known)
  // -------------------------------------------------------------------------

  useEffect(() => {
    if (!vendorId) return;

    listDocuments(vendorId)
      .then((backendDocs) => {
        const updatedDocs = { ...documents.documents };
        const updatedOthers: UploadedDocInfo[] = [...documents.otherFiles];

        backendDocs.forEach((meta) => {
          const docKey = categoryToDocKey(meta.document_category);
          if (docKey && docKey !== 'otherDocuments') {
            // Only restore if not already tracked (avoid overwriting an in-progress upload)
            if (!updatedDocs[docKey] || updatedDocs[docKey].status !== 'uploading') {
              updatedDocs[docKey] = backendMetaToDocInfo(meta, docKey);
            }
          } else if (docKey === 'otherDocuments' || !docKey) {
            // Other / unknown category → otherFiles
            const existing = updatedOthers.find((d) => d.id === meta.document_id);
            if (!existing) {
              updatedOthers.push(backendMetaToDocInfo(meta, 'otherDocuments'));
            }
          }
        });

        onChange('documents', updatedDocs);
        onChange('otherFiles', updatedOthers);
      })
      .catch((err) => {
        console.warn('[VendorFlow] Could not restore documents from backend:', err);
      });
  // We only want to run this once when vendorId first becomes available
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [vendorId]);

  // -------------------------------------------------------------------------
  // Upload handler (real backend call)
  // -------------------------------------------------------------------------

  const handleFileUpload = useCallback(
    async (key: DocumentKey, file: File) => {
      // Optimistically update UI to 'uploading' state
      const tempId = `uploading-${key}-${Date.now()}`;
      const uploading: UploadedDocInfo = {
        id: tempId,
        key,
        fileName: file.name,
        fileSize: file.size,
        fileType: file.type || 'application/pdf',
        progress: 0,
        status: 'uploading',
        previewUrl: file.type.startsWith('image/') ? URL.createObjectURL(file) : undefined,
        uploadedAt: 'Uploading…',
      };

      onChange('documents', { ...documents.documents, [key]: uploading });
      setUploadErrors((prev) => { const n = { ...prev }; delete n[key]; return n; });

      try {
        // Ensure we have a vendor record before uploading
        const id = vendorId ?? await onVendorIdReady();
        if (!id) throw new Error('No vendor record available. Please retry.');

        // Check if there's an existing backend doc to replace
        const existingDocInfo = documents.documents[key];
        let result: BackendDocumentMeta;

        if (existingDocInfo && existingDocInfo.status === 'completed' && !existingDocInfo.id.startsWith('doc-')) {
          // Real backend doc → use PUT /replace
          result = await replaceDocument(
            id,
            existingDocInfo.id,
            file,
            (pct) => {
              onChange('documents', {
                ...documents.documents,
                [key]: { ...uploading, progress: pct },
              });
            }
          );
        } else {
          // New upload
          result = await uploadDocument(id, file, key, (pct) => {
            onChange('documents', {
              ...documents.documents,
              [key]: { ...uploading, progress: pct },
            });
          });
        }

        const completed = backendMetaToDocInfo(result, key);
        onChange('documents', { ...documents.documents, [key]: completed });
      } catch (err) {
        const msg = extractErrorMessage(err, 'Upload failed. Please try again.');
        setUploadErrors((prev) => ({ ...prev, [key]: msg }));
        // Revert to empty slot
        const updatedDocs = { ...documents.documents };
        delete updatedDocs[key];
        onChange('documents', updatedDocs);
      }
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [vendorId, onVendorIdReady, documents.documents, onChange]
  );

  // -------------------------------------------------------------------------
  // Remove handler (delete from backend)
  // -------------------------------------------------------------------------

  const handleRemoveDoc = useCallback(
    async (key: DocumentKey) => {
      const docInfo = documents.documents[key];

      // Remove from local state immediately for responsiveness
      const updatedDocs = { ...documents.documents };
      delete updatedDocs[key];
      onChange('documents', updatedDocs);

      // If the doc was actually stored in the backend, delete it
      if (docInfo && vendorId && !docInfo.id.startsWith('doc-') && !docInfo.id.startsWith('uploading-')) {
        deleteDocument(vendorId, docInfo.id).catch((err) => {
          console.warn('[VendorFlow] Could not delete document from backend:', err);
        });
      }
    },
    [vendorId, documents.documents, onChange]
  );

  // -------------------------------------------------------------------------
  // Other files upload
  // -------------------------------------------------------------------------

  const handleOtherFileUpload = async (e: ChangeEvent<HTMLInputElement>) => {
    if (!e.target.files || e.target.files.length === 0) return;
    const file = e.target.files[0];

    const tempId = `other-uploading-${Date.now()}`;
    const uploading: UploadedDocInfo = {
      id: tempId,
      key: 'otherDocuments',
      fileName: file.name,
      fileSize: file.size,
      fileType: file.type,
      progress: 0,
      status: 'uploading',
      previewUrl: file.type.startsWith('image/') ? URL.createObjectURL(file) : undefined,
      uploadedAt: 'Uploading…',
    };

    onChange('otherFiles', [...documents.otherFiles, uploading]);

    try {
      const id = vendorId ?? await onVendorIdReady();
      if (!id) throw new Error('No vendor record available.');

      const result = await uploadDocument(id, file, 'otherDocuments', (pct) => {
        onChange(
          'otherFiles',
          documents.otherFiles.map((d) =>
            d.id === tempId ? { ...uploading, progress: pct } : d
          )
        );
      });

      const completed = backendMetaToDocInfo(result, 'otherDocuments');
      onChange(
        'otherFiles',
        documents.otherFiles.map((d) => (d.id === tempId ? completed : d))
      );
    } catch (err) {
      const msg = extractErrorMessage(err, 'Upload failed');
      console.error('[VendorFlow] Other file upload failed:', msg);
      // Remove failed upload
      onChange(
        'otherFiles',
        documents.otherFiles.filter((d) => d.id !== tempId)
      );
    }

    // Reset input
    e.target.value = '';
  };

  const handleRemoveOtherDoc = async (index: number) => {
    const docToRemove = documents.otherFiles[index];
    const updated = [...documents.otherFiles];
    updated.splice(index, 1);
    onChange('otherFiles', updated);

    if (docToRemove && vendorId && !docToRemove.id.startsWith('other-uploading-')) {
      deleteDocument(vendorId, docToRemove.id).catch((err) => {
        console.warn('[VendorFlow] Could not delete other doc from backend:', err);
      });
    }
  };

  // -------------------------------------------------------------------------
  // Render
  // -------------------------------------------------------------------------

  return (
    <div className="space-y-8 animate-fadeIn">
      {/* File Preview Modal */}
      <FilePreviewModal document={previewDoc} onClose={() => setPreviewDoc(null)} />

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
            error={errors.certificateOfIncorporation ?? uploadErrors.certificateOfIncorporation}
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
            error={errors.panCard ?? uploadErrors.panCard}
          />

          {/* 3. GST Certificate */}
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
              error={errors.gstCertificate ?? uploadErrors.gstCertificate}
            />
          )}

          {/* 4. Bank Proof */}
          <FileUploadCard
            id="doc-bank"
            title="Cancelled Cheque / Bank Statement"
            description="Cancelled cheque leaf or recent bank statement clearly showing account number and IFSC."
            required
            docInfo={documents.documents.bankProof}
            onFileSelect={(file) => handleFileUpload('bankProof', file)}
            onRemove={() => handleRemoveDoc('bankProof')}
            onPreview={setPreviewDoc}
            error={errors.bankProof ?? uploadErrors.bankProof}
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
            error={uploadErrors.tanCertificate}
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
            error={uploadErrors.msmeCertificate}
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

              <label className="inline-flex items-center space-x-1.5 px-3 py-1.5 rounded-xl text-xs font-semibold text-[#1F211F] bg-sky-50 hover:bg-sky-100 border border-sky-200/60 transition-colors cursor-pointer">
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
                      <Files size={16} className="text-[#1F211F] shrink-0" />
                      <div className="truncate">
                        <span className="font-medium text-slate-800 truncate block">{doc.fileName}</span>
                        {doc.status === 'uploading' && (
                          <span className="text-blue-500">{doc.progress}% uploading…</span>
                        )}
                      </div>
                    </div>
                    <div className="flex items-center space-x-2 shrink-0">
                      {doc.status === 'completed' && (
                        <button
                          type="button"
                          onClick={() => setPreviewDoc(doc)}
                          className="text-[#1F211F] hover:underline cursor-pointer"
                        >
                          Preview
                        </button>
                      )}
                      <button
                        type="button"
                        onClick={() => handleRemoveOtherDoc(idx)}
                        disabled={doc.status === 'uploading'}
                        className="text-red-500 hover:text-red-700 cursor-pointer disabled:opacity-40"
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
        <ReviewSummary formData={formData} onEditStep={onEditStep} />
      </div>

      {/* Final Declarations */}
      <div className="space-y-3.5 p-5 rounded-2xl bg-blue-50/50 border border-blue-100 text-left">
        <h4 className="text-xs font-semibold uppercase tracking-wider text-[#1F211F]">
          Mandatory Declarations &amp; Consent
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
