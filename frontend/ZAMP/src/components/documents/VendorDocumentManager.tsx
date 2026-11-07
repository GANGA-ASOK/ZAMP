import type { FC } from 'react';
import { useState, useEffect, useRef, useCallback } from 'react';
import {
  FilePdf,
  UploadSimple,
  CheckCircle,
  WarningCircle,
  ArrowClockwise,
  DownloadSimple,
  ArrowsClockwise,
  Trash,
  Sparkle,
  Check,
} from '@phosphor-icons/react';
import {
  uploadDocument,
  listDocuments,
  deleteDocument,
  replaceDocument,
  getDocumentDownloadUrl,
  DOC_KEY_TO_CATEGORY,
  type BackendDocumentMeta,
} from '../../services/documentService';
import {
  getVendorInsights,
  type AIInsightsResponse,
} from '../../services/workflowService';
import {
  getVendorVerificationSummary,
  type VerificationResultResponse,
} from '../../services/verificationService';
import type { DocumentKey } from '../../types/vendor';

interface VendorDocumentManagerProps {
  vendorId: string;
  businessEntityType?: string;
  gstStatus?: string;
  applicationStatus?: string;
  onDocumentsChanged?: () => void;
}

interface CategoryConfig {
  key: DocumentKey;
  backendCategory: string;
  label: string;
  description: string;
  isMandatory: boolean;
  acceptedFormats: string;
}

export const VendorDocumentManager: FC<VendorDocumentManagerProps> = ({
  vendorId,
  businessEntityType = '',
  gstStatus = 'Registered',
  applicationStatus = 'draft',
  onDocumentsChanged,
}) => {
  const [documents, setDocuments] = useState<BackendDocumentMeta[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [uploadingCategory, setUploadingCategory] = useState<string | null>(null);
  const [uploadProgress, setUploadProgress] = useState<number>(0);
  const [actionError, setActionError] = useState<string | null>(null);
  const [actionSuccess, setActionSuccess] = useState<string | null>(null);

  // Verification & AI Insights
  const [verificationMap, setVerificationMap] = useState<Record<string, VerificationResultResponse>>({});
  const [aiInsights, setAiInsights] = useState<AIInsightsResponse | null>(null);
  const [refreshingAi, setRefreshingAi] = useState<boolean>(false);

  // Hidden file inputs
  const fileInputRefs = useRef<Record<string, HTMLInputElement | null>>({});

  const isCorporate = [
    'Private Limited Company',
    'Public Limited Company',
    'Limited Liability Partnership (LLP)',
    'One Person Company (OPC)',
  ].some((t) => businessEntityType.toLowerCase().includes(t.toLowerCase()));

  const isGstRegistered = gstStatus.toLowerCase() === 'registered';

  // Configured document categories aligned with ZAMP requirements
  const categories: CategoryConfig[] = [
    {
      key: 'panCard',
      backendCategory: 'pan_card',
      label: 'PAN Card',
      description: 'Permanent Account Number card issued by the Income Tax Department.',
      isMandatory: true,
      acceptedFormats: '.pdf, .jpg, .jpeg, .png',
    },
    {
      key: 'bankProof',
      backendCategory: 'bank_proof',
      label: 'Bank Account Proof',
      description: 'Cancelled cheque or bank account statement showing Account Name, Number, and IFSC.',
      isMandatory: true,
      acceptedFormats: '.pdf, .jpg, .jpeg, .png',
    },
    {
      key: 'gstCertificate',
      backendCategory: 'gst_certificate',
      label: 'GST Registration Certificate (REG-06)',
      description: 'Principal place of business registration issued by CBIC/State Tax Authorities.',
      isMandatory: isGstRegistered,
      acceptedFormats: '.pdf, .jpg, .jpeg, .png',
    },
    {
      key: 'certificateOfIncorporation',
      backendCategory: 'certificate_of_incorporation',
      label: 'Certificate of Incorporation / Registration',
      description: 'ROC Incorporation Certificate or LLP Agreement with official seal.',
      isMandatory: isCorporate,
      acceptedFormats: '.pdf',
    },
    {
      key: 'msmeCertificate',
      backendCategory: 'msme_certificate',
      label: 'MSME / Udyam Registration Certificate',
      description: 'Optional Udyam registration for priority payment eligibility under MSMED Act.',
      isMandatory: false,
      acceptedFormats: '.pdf',
    },
    {
      key: 'tanCertificate',
      backendCategory: 'tan_certificate',
      label: 'TAN Allotment Letter',
      description: 'Tax Deduction and Collection Account Number proof for TDS purposes.',
      isMandatory: false,
      acceptedFormats: '.pdf, .jpg, .jpeg, .png',
    },
    {
      key: 'otherDocuments',
      backendCategory: 'other',
      label: 'Other Supporting Documents',
      description: 'Additional board resolutions, authorization letters, or certifications.',
      isMandatory: false,
      acceptedFormats: '.pdf, .jpg, .jpeg, .png',
    },
  ];

  // Load documents and AI findings
  const fetchDocuments = useCallback(async () => {
    if (!vendorId) return;
    setLoading(true);
    setActionError(null);
    try {
      const [docList, summary, insights] = await Promise.all([
        listDocuments(vendorId).catch(() => []),
        getVendorVerificationSummary(vendorId).catch(() => null),
        getVendorInsights(vendorId).catch(() => null),
      ]);

      setDocuments(docList);
      if (insights) setAiInsights(insights);

      if (summary?.results) {
        const vMap: Record<string, VerificationResultResponse> = {};
        for (const res of summary.results) {
          vMap[res.document_id] = res;
        }
        setVerificationMap(vMap);
      }
    } catch (err: any) {
      console.error('Failed to load vendor documents:', err);
      setActionError(err.message || 'Failed to load documents.');
    } finally {
      setLoading(false);
    }
  }, [vendorId]);

  useEffect(() => {
    fetchDocuments();
  }, [fetchDocuments]);

  // Handle file selection and upload
  const handleFileUpload = async (key: DocumentKey, file: File) => {
    setActionError(null);
    setActionSuccess(null);
    setUploadingCategory(key);
    setUploadProgress(0);

    try {
      // Find existing doc of this category to replace if single slot
      const existingDoc = documents.find(
        (d) => d.document_category === DOC_KEY_TO_CATEGORY[key] && key !== 'otherDocuments'
      );

      if (existingDoc) {
        await replaceDocument(vendorId, existingDoc.document_id, file, (pct) => setUploadProgress(pct));
        setActionSuccess(`Successfully updated ${file.name}`);
      } else {
        await uploadDocument(vendorId, file, key, (pct) => setUploadProgress(pct));
        setActionSuccess(`Successfully uploaded ${file.name}`);
      }

      await fetchDocuments();
      if (onDocumentsChanged) onDocumentsChanged();
    } catch (err: any) {
      console.error('Document upload failed:', err);
      setActionError(err.response?.data?.detail || err.message || 'Upload failed. Please ensure file is under 10MB.');
    } finally {
      setUploadingCategory(null);
      setUploadProgress(0);
    }
  };

  // Handle document delete
  const handleDeleteDoc = async (documentId: string, docName: string) => {
    if (!window.confirm(`Are you sure you want to delete "${docName}"?`)) return;
    setActionError(null);
    setActionSuccess(null);
    try {
      await deleteDocument(vendorId, documentId);
      setActionSuccess(`Deleted document "${docName}"`);
      await fetchDocuments();
      if (onDocumentsChanged) onDocumentsChanged();
    } catch (err: any) {
      console.error('Delete failed:', err);
      setActionError(err.response?.data?.detail || err.message || 'Failed to delete document.');
    }
  };

  const handleRefreshAi = async () => {
    setRefreshingAi(true);
    await fetchDocuments();
    setRefreshingAi(false);
  };

  // Metrics
  const uploadedCategoriesSet = new Set(documents.map((d) => d.document_category));
  const mandatoryCount = categories.filter((c) => c.isMandatory).length;
  const mandatoryUploaded = categories.filter((c) => c.isMandatory && uploadedCategoriesSet.has(c.backendCategory)).length;
  const isAllMandatoryUploaded = mandatoryUploaded >= mandatoryCount;

  return (
    <div className="space-y-6 text-left">
      {/* Header & Metrics Card */}
      <div className="bg-white rounded-3xl p-6 border border-slate-200/90 shadow-xl shadow-slate-200/50 space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-100 pb-4">
          <div>
            <div className="flex items-center space-x-2">
              <div className="w-8 h-8 rounded-xl bg-blue-100 text-[#07569B] flex items-center justify-center font-bold">
                <FilePdf size={18} weight="fill" />
              </div>
              <h3 className="text-base font-bold text-slate-900">
                Documents & Verification Hub
              </h3>
            </div>
            <p className="text-xs text-slate-500 mt-1">
              Upload compliance documents stored securely in MongoDB GridFS and audited via NVIDIA Nemotron AI.
            </p>
          </div>

          <button
            type="button"
            onClick={handleRefreshAi}
            disabled={refreshingAi || loading}
            className="inline-flex items-center space-x-1.5 px-3 py-1.5 rounded-xl border border-slate-200 hover:border-slate-300 bg-slate-50 hover:bg-slate-100 text-slate-700 text-xs font-semibold cursor-pointer transition-colors"
          >
            <ArrowsClockwise size={13} className={refreshingAi ? 'animate-spin' : ''} />
            <span>Refresh Status</span>
          </button>
        </div>

        {/* Progress & Compliance Summary */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          <div className="p-3.5 rounded-2xl bg-slate-50 border border-slate-200/80">
            <span className="text-[10px] uppercase font-bold text-slate-400 block tracking-wider">
              Mandatory Documents
            </span>
            <div className="flex items-center justify-between mt-1">
              <span className="text-lg font-bold text-slate-900">
                {mandatoryUploaded} of {mandatoryCount} Uploaded
              </span>
              {isAllMandatoryUploaded ? (
                <span className="inline-flex items-center space-x-1 px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-800 text-[10px] font-bold">
                  <Check size={11} weight="bold" />
                  <span>Complete</span>
                </span>
              ) : (
                <span className="inline-flex items-center space-x-1 px-2 py-0.5 rounded-full bg-amber-100 text-amber-800 text-[10px] font-bold">
                  <span>{mandatoryCount - mandatoryUploaded} Missing</span>
                </span>
              )}
            </div>
          </div>

          <div className="p-3.5 rounded-2xl bg-slate-50 border border-slate-200/80">
            <span className="text-[10px] uppercase font-bold text-slate-400 block tracking-wider">
              Total Stored Files
            </span>
            <div className="flex items-center justify-between mt-1">
              <span className="text-lg font-bold text-slate-900">
                {documents.length} File{documents.length === 1 ? '' : 's'}
              </span>
              <span className="text-[11px] text-slate-500 font-mono">
                {Math.round(documents.reduce((acc, d) => acc + (d.file_size || 0), 0) / 1024)} KB Total
              </span>
            </div>
          </div>

          <div className="p-3.5 rounded-2xl bg-slate-50 border border-slate-200/80">
            <span className="text-[10px] uppercase font-bold text-slate-400 block tracking-wider">
              AI Verification Health
            </span>
            <div className="flex items-center justify-between mt-1">
              <span className="text-lg font-bold text-slate-900">
                {aiInsights ? `${aiInsights.confidence_score}% Confidence` : 'Pending'}
              </span>
              <span
                className={`px-2 py-0.5 rounded-full text-[10px] font-bold uppercase ${
                  aiInsights?.recommendation === 'Approve'
                    ? 'bg-emerald-100 text-emerald-800'
                    : aiInsights?.recommendation === 'Clarification Required'
                    ? 'bg-amber-100 text-amber-800'
                    : 'bg-blue-100 text-[#07569B]'
                }`}
              >
                {aiInsights?.recommendation || 'Auditing'}
              </span>
            </div>
          </div>
        </div>

        {/* AI Insight Advisory Banner */}
        {aiInsights?.summary_explanation && (
          <div className="p-3 rounded-2xl bg-indigo-50/70 border border-indigo-200/80 text-xs flex items-start space-x-2 text-indigo-950">
            <Sparkle size={16} weight="bold" className="text-indigo-600 shrink-0 mt-0.5" />
            <div>
              <span className="font-bold text-indigo-900">NVIDIA AI Auditor Insight:</span>{' '}
              <span className="text-indigo-900/90 leading-relaxed">{aiInsights.summary_explanation}</span>
            </div>
          </div>
        )}

        {/* Action feedback banners */}
        {actionSuccess && (
          <div className="p-3 rounded-xl bg-emerald-50 border border-emerald-200 text-xs text-emerald-900 flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <CheckCircle size={16} weight="bold" className="text-emerald-600 shrink-0" />
              <span>{actionSuccess}</span>
            </div>
            <button onClick={() => setActionSuccess(null)} className="text-slate-400 hover:text-slate-600 font-bold ml-2">✕</button>
          </div>
        )}

        {actionError && (
          <div className="p-3 rounded-xl bg-rose-50 border border-rose-200 text-xs text-rose-900 flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <WarningCircle size={16} weight="bold" className="text-rose-600 shrink-0" />
              <span>{actionError}</span>
            </div>
            <button onClick={() => setActionError(null)} className="text-slate-400 hover:text-slate-600 font-bold ml-2">✕</button>
          </div>
        )}
      </div>

      {/* Category Upload Cards */}
      <div className="space-y-4">
        {categories.map((cfg) => {
          // Find uploaded doc(s) for this category
          const matchingDocs = documents.filter(
            (d) => d.document_category === cfg.backendCategory
          );
          const isUploaded = matchingDocs.length > 0;
          const isUploading = uploadingCategory === cfg.key;

          return (
            <div
              key={cfg.key}
              className={`bg-white rounded-3xl p-5 border transition-all ${
                isUploaded
                  ? 'border-emerald-200/80 shadow-md shadow-emerald-900/5'
                  : cfg.isMandatory
                  ? 'border-amber-200/80 shadow-sm'
                  : 'border-slate-200/80 shadow-2xs'
              }`}
            >
              <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-4">
                <div className="flex items-start space-x-3.5">
                  <div
                    className={`w-10 h-10 rounded-2xl flex items-center justify-center shrink-0 mt-0.5 ${
                      isUploaded
                        ? 'bg-emerald-100 text-emerald-700'
                        : 'bg-slate-100 text-slate-500'
                    }`}
                  >
                    <FilePdf size={22} weight="fill" />
                  </div>

                  <div className="space-y-1">
                    <div className="flex items-center space-x-2 flex-wrap">
                      <h4 className="text-sm font-bold text-slate-900">{cfg.label}</h4>
                      {cfg.isMandatory ? (
                        <span className="px-2 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider bg-rose-50 text-rose-700 border border-rose-200">
                          Mandatory
                        </span>
                      ) : (
                        <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold uppercase tracking-wider bg-slate-100 text-slate-600">
                          Optional
                        </span>
                      )}

                      {isUploaded && (
                        <span className="px-2 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider bg-emerald-50 text-emerald-700 border border-emerald-200 inline-flex items-center space-x-1">
                          <CheckCircle size={11} weight="fill" />
                          <span>Uploaded</span>
                        </span>
                      )}
                    </div>

                    <p className="text-xs text-slate-500 leading-relaxed max-w-xl">
                      {cfg.description}
                    </p>
                    <p className="text-[11px] text-slate-400 font-mono">
                      Allowed: PDF, JPEG, PNG • Limit: 10 MB
                    </p>
                  </div>
                </div>

                {/* Upload Button or Actions */}
                <div className="flex items-center space-x-2 shrink-0 self-end sm:self-start">
                  <input
                    ref={(el) => { fileInputRefs.current[cfg.key] = el; }}
                    type="file"
                    accept=".pdf,.jpg,.jpeg,.png,.tiff"
                    className="hidden"
                    onChange={(e) => {
                      const file = e.target.files?.[0];
                      if (file) handleFileUpload(cfg.key, file);
                      e.target.value = '';
                    }}
                  />

                  {isUploading ? (
                    <div className="flex items-center space-x-2 px-3 py-1.5 rounded-xl bg-blue-50 text-[#07569B] text-xs font-semibold">
                      <ArrowClockwise size={14} className="animate-spin" />
                      <span>{uploadProgress > 0 ? `${uploadProgress}%` : 'Uploading...'}</span>
                    </div>
                  ) : isUploaded ? (
                    <button
                      type="button"
                      onClick={() => fileInputRefs.current[cfg.key]?.click()}
                      className="inline-flex items-center space-x-1 px-3 py-1.5 rounded-xl border border-slate-200 bg-white hover:bg-slate-50 text-slate-700 text-xs font-semibold cursor-pointer shadow-2xs transition-colors"
                    >
                      <ArrowsClockwise size={13} weight="bold" />
                      <span>Replace</span>
                    </button>
                  ) : (
                    <button
                      type="button"
                      onClick={() => fileInputRefs.current[cfg.key]?.click()}
                      className="inline-flex items-center space-x-1.5 px-3.5 py-1.5 rounded-xl bg-[#07569B] hover:bg-[#064780] text-white text-xs font-semibold cursor-pointer shadow-xs transition-colors"
                    >
                      <UploadSimple size={14} weight="bold" />
                      <span>Upload File</span>
                    </button>
                  )}
                </div>
              </div>

              {/* Progress bar during upload */}
              {isUploading && (
                <div className="mt-3 w-full bg-slate-100 rounded-full h-1.5 overflow-hidden">
                  <div
                    className="bg-[#07569B] h-1.5 rounded-full transition-all duration-300"
                    style={{ width: `${Math.max(5, uploadProgress)}%` }}
                  />
                </div>
              )}

              {/* Uploaded Documents List for this category */}
              {matchingDocs.length > 0 && (
                <div className="mt-3.5 pt-3.5 border-t border-slate-100 space-y-2">
                  {matchingDocs.map((doc) => {
                    const downloadUrl = getDocumentDownloadUrl(vendorId, doc.document_id);
                    const verif = verificationMap[doc.document_id];
                    const vStatus = verif?.verification_status || doc.verification_status || 'uploaded';

                    return (
                      <div
                        key={doc.document_id}
                        className="p-3 rounded-2xl bg-slate-50/70 border border-slate-200/80 flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs"
                      >
                        <div className="flex items-center space-x-3 overflow-hidden">
                          <FilePdf size={18} weight="fill" className="text-slate-400 shrink-0" />
                          <div className="truncate">
                            <p className="font-semibold text-slate-800 truncate">
                              {doc.original_filename}
                            </p>
                            <p className="text-[11px] text-slate-400 font-mono mt-0.5">
                              {Math.round(doc.file_size / 1024)} KB •{' '}
                              {doc.upload_timestamp ? new Date(doc.upload_timestamp).toLocaleDateString() : 'Uploaded'}
                            </p>
                          </div>
                        </div>

                        <div className="flex items-center space-x-2 shrink-0">
                          {/* Verification badge */}
                          <span
                            className={`px-2.5 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider ${
                              vStatus === 'completed'
                                ? 'bg-emerald-100 text-emerald-800'
                                : vStatus === 'flagged'
                                ? 'bg-rose-100 text-rose-800'
                                : vStatus === 'needs_manual_review'
                                ? 'bg-amber-100 text-amber-800'
                                : 'bg-slate-200 text-slate-700'
                            }`}
                          >
                            {vStatus === 'completed' ? 'Verified' : vStatus}
                          </span>

                          {/* Download Link */}
                          <a
                            href={downloadUrl}
                            target="_blank"
                            rel="noreferrer"
                            className="p-1.5 rounded-xl border border-slate-200 bg-white hover:bg-slate-100 text-slate-700 cursor-pointer shadow-2xs"
                            title="Download file"
                          >
                            <DownloadSimple size={14} weight="bold" />
                          </a>

                          {/* Delete button (allowed when not locked in approved status) */}
                          {applicationStatus !== 'approved' && (
                            <button
                              type="button"
                              onClick={() => handleDeleteDoc(doc.document_id, doc.original_filename)}
                              className="p-1.5 rounded-xl border border-rose-200 bg-white hover:bg-rose-50 text-rose-600 cursor-pointer shadow-2xs"
                              title="Delete document"
                            >
                              <Trash size={14} weight="bold" />
                            </button>
                          )}
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
};
