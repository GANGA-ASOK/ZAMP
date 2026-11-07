import type { FC } from 'react';
import { useState, useRef } from 'react';
import {
  WarningCircle,
  CheckCircle,
  ArrowClockwise,
  ArrowUpRight,
  UploadSimple,
  ChatCircleText,
  FileArrowUp,
} from '@phosphor-icons/react';
import {
  respondToClarification,
  resubmitApplication,
  type ClarificationItem,
} from '../../services/workflowService';
import { uploadDocument } from '../../services/documentService';
import type { DocumentKey } from '../../types/vendor';

interface VendorClarificationSectionProps {
  vendorId: string;
  clarifications: ClarificationItem[];
  onClarificationUpdated: () => void;
  onApplicationResubmitted: () => void;
}

export const VendorClarificationSection: FC<VendorClarificationSectionProps> = ({
  vendorId,
  clarifications,
  onClarificationUpdated,
  onApplicationResubmitted,
}) => {
  const [responseTexts, setResponseTexts] = useState<Record<string, string>>({});
  const [submittingClarificationId, setSubmittingClarificationId] = useState<string | null>(null);
  const [replacingDocClarificationId, setReplacingDocClarificationId] = useState<string | null>(null);
  const [replacedDocs, setReplacedDocs] = useState<Record<string, { id: string; name: string }>>({});
  const [resubmitting, setResubmitting] = useState(false);
  const [resubmissionNotes, setResubmissionNotes] = useState('');
  const [statusMessage, setStatusMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  const fileInputRef = useRef<HTMLInputElement>(null);
  const activeClarificationRef = useRef<ClarificationItem | null>(null);

  const pendingClarifications = clarifications.filter((c) => c.status === 'pending');
  const resolvedClarifications = clarifications.filter((c) => c.status === 'resolved');

  // Handle file selection for document replacement
  const handleSelectReplacementFile = (clarification: ClarificationItem) => {
    activeClarificationRef.current = clarification;
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
      fileInputRef.current.click();
    }
  };

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    const clarification = activeClarificationRef.current;
    if (!file || !clarification) return;

    setReplacingDocClarificationId(clarification.id);
    setStatusMessage(null);

    try {
      const docKey: DocumentKey = clarification.related_document_name?.toLowerCase().includes('pan')
        ? 'panCard'
        : clarification.related_document_name?.toLowerCase().includes('gst')
        ? 'gstCertificate'
        : clarification.related_document_name?.toLowerCase().includes('bank')
        ? 'bankProof'
        : 'otherDocuments';

      const uploadRes = await uploadDocument(vendorId, file, docKey);
      setReplacedDocs((prev) => ({
        ...prev,
        [clarification.id]: { id: uploadRes.document_id, name: file.name },
      }));
      setStatusMessage({
        type: 'success',
        text: `Successfully uploaded replacement: ${file.name}. Please submit your response below.`,
      });
    } catch (err: any) {
      console.error('Error uploading replacement document:', err);
      setStatusMessage({
        type: 'error',
        text: err.message || 'Failed to upload replacement document.',
      });
    } finally {
      setReplacingDocClarificationId(null);
    }
  };

  // Submit response to single clarification item
  const handleSubmitResponse = async (clarificationId: string) => {
    const text = responseTexts[clarificationId];
    if (!text || text.trim().length < 2) {
      setStatusMessage({
        type: 'error',
        text: 'Please write a brief explanation of the correction made.',
      });
      return;
    }

    setSubmittingClarificationId(clarificationId);
    setStatusMessage(null);

    try {
      const replacedDoc = replacedDocs[clarificationId];
      await respondToClarification(vendorId, clarificationId, {
        vendor_response: text.trim(),
        replaced_document_id: replacedDoc?.id || null,
      });

      setStatusMessage({
        type: 'success',
        text: 'Clarification response recorded successfully.',
      });
      onClarificationUpdated();
    } catch (err: any) {
      setStatusMessage({
        type: 'error',
        text: err.message || 'Failed to submit response.',
      });
    } finally {
      setSubmittingClarificationId(null);
    }
  };

  // Resubmit application after addressing clarifications
  const handleResubmit = async () => {
    setResubmitting(true);
    setStatusMessage(null);

    try {
      await resubmitApplication(vendorId, resubmissionNotes || undefined);
      setStatusMessage({
        type: 'success',
        text: 'Application resubmitted successfully! It is now under review by compliance.',
      });
      onApplicationResubmitted();
    } catch (err: any) {
      setStatusMessage({
        type: 'error',
        text: err.message || 'Failed to resubmit application.',
      });
    } finally {
      setResubmitting(false);
    }
  };

  return (
    <div className="space-y-6 text-left">
      {/* Hidden file input for document replacement */}
      <input
        type="file"
        ref={fileInputRef}
        onChange={handleFileChange}
        accept=".pdf,.png,.jpg,.jpeg"
        className="hidden"
      />

      {/* Main Alert Banner */}
      <div className="bg-amber-50 border border-amber-200/90 rounded-[32px] p-6 space-y-3">
        <div className="flex items-start space-x-3.5">
          <div className="w-10 h-10 rounded-2xl bg-amber-100 text-amber-700 flex items-center justify-center shrink-0 mt-0.5">
            <WarningCircle size={24} weight="fill" />
          </div>
          <div className="flex-1">
            <div className="flex items-center space-x-2">
              <h2 className="text-base font-semibold text-amber-950">
                Action Required: Clarification Requested
              </h2>
              <span className="text-[11px] font-semibold px-2 py-0.5 rounded-full bg-amber-200/70 text-amber-900">
                {pendingClarifications.length} Pending
              </span>
            </div>
            <p className="text-xs text-amber-800/90 mt-1 leading-relaxed">
              Our compliance team reviewed your application and requested clarification or updated documentation.
              Review the details below, upload replacement files if requested, and resubmit your application.
            </p>
          </div>
        </div>
      </div>

      {/* Status feedback banner */}
      {statusMessage && (
        <div
          className={`p-4 rounded-2xl border text-xs flex items-center justify-between ${
            statusMessage.type === 'success'
              ? 'bg-emerald-50 text-emerald-900 border-emerald-200'
              : 'bg-rose-50 text-rose-900 border-rose-200'
          }`}
        >
          <div className="flex items-center space-x-2">
            {statusMessage.type === 'success' ? (
              <CheckCircle size={18} weight="bold" className="text-emerald-600 shrink-0" />
            ) : (
              <WarningCircle size={18} weight="bold" className="text-rose-600 shrink-0" />
            )}
            <span>{statusMessage.text}</span>
          </div>
          <button
            onClick={() => setStatusMessage(null)}
            className="text-slate-400 hover:text-slate-600 cursor-pointer ml-4 font-semibold"
          >
            ✕
          </button>
        </div>
      )}

      {/* Pending Clarification Cards */}
      <div className="space-y-4">
        <h3 className="text-xs font-semibold text-slate-700 uppercase tracking-wider">
          Pending Clarifications ({pendingClarifications.length})
        </h3>

        {pendingClarifications.length === 0 ? (
          <div className="bg-emerald-50 border border-emerald-200 rounded-2xl p-4 text-xs text-emerald-800 flex items-center space-x-2">
            <CheckCircle size={18} weight="fill" className="text-emerald-600 shrink-0" />
            <span>All clarification items have been answered! You may now resubmit your application below.</span>
          </div>
        ) : (
          pendingClarifications.map((item) => {
            const isSubmittingThis = submittingClarificationId === item.id;
            const isUploadingThis = replacingDocClarificationId === item.id;
            const replacement = replacedDocs[item.id];

            return (
              <div
                key={item.id}
                className="bg-white rounded-[32px] p-5 border border-slate-200 shadow-sm space-y-4"
              >
                {/* Header row */}
                <div className="flex items-start justify-between border-b border-slate-100 pb-3">
                  <div className="flex items-center space-x-2">
                    <span className="p-1 rounded-lg bg-amber-50 text-amber-700">
                      <ChatCircleText size={16} weight="bold" />
                    </span>
                    <span className="text-xs font-semibold text-slate-900">
                      {item.related_document_name
                        ? `Document: ${item.related_document_name}`
                        : item.related_field
                        ? `Field: ${item.related_field}`
                        : 'General Clarification'}
                    </span>
                  </div>
                  <span className="text-[10px] text-slate-400 font-mono">
                    {new Date(item.created_at).toLocaleDateString('en-US', {
                      month: 'short',
                      day: 'numeric',
                      hour: '2-digit',
                      minute: '2-digit',
                    })}
                  </span>
                </div>

                {/* Admin Message */}
                <div className="p-3.5 rounded-2xl bg-slate-50 border border-slate-200/80 text-xs text-slate-800 space-y-1">
                  <span className="text-[10px] font-semibold uppercase tracking-wider text-slate-500 block">
                    Admin Request:
                  </span>
                  <p className="leading-relaxed font-medium">{item.clarification_message}</p>
                </div>

                {/* Document Replacement Option if applicable */}
                <div className="p-3.5 rounded-2xl bg-blue-50/50 border border-blue-200/70 text-xs space-y-2">
                  <div className="flex items-center justify-between">
                    <div>
                      <span className="font-semibold text-slate-800 block">
                        Upload Corrected Document (GridFS)
                      </span>
                      <span className="text-[11px] text-slate-500">
                        {replacement
                          ? `Selected replacement: ${replacement.name}`
                          : 'If this request requires a new file, select your corrected document'}
                      </span>
                    </div>

                    <button
                      type="button"
                      disabled={isUploadingThis}
                      onClick={() => handleSelectReplacementFile(item)}
                      className="px-3 py-1.5 rounded-xl bg-white hover:bg-slate-50 text-[#1F211F] border border-blue-200 text-xs font-semibold cursor-pointer flex items-center space-x-1.5 shrink-0 disabled:opacity-50"
                    >
                      {isUploadingThis ? (
                        <>
                          <ArrowClockwise size={13} className="animate-spin" />
                          <span>Uploading...</span>
                        </>
                      ) : (
                        <>
                          <UploadSimple size={13} weight="bold" />
                          <span>{replacement ? 'Change File' : 'Choose File'}</span>
                        </>
                      )}
                    </button>
                  </div>

                  {replacement && (
                    <div className="p-2 rounded-xl bg-emerald-50 border border-emerald-200 text-[11px] text-emerald-800 flex items-center space-x-2">
                      <CheckCircle size={14} weight="fill" className="text-emerald-600 shrink-0" />
                      <span>Ready to link: <strong>{replacement.name}</strong></span>
                    </div>
                  )}
                </div>

                {/* Vendor Response Field */}
                <div className="space-y-2">
                  <label className="block text-xs font-semibold text-slate-700">
                    Your Response to Compliance <span className="text-amber-600">*</span>
                  </label>
                  <textarea
                    rows={2}
                    placeholder="Describe the changes made or provide the requested information..."
                    value={responseTexts[item.id] || ''}
                    onChange={(e) =>
                      setResponseTexts((prev) => ({ ...prev, [item.id]: e.target.value }))
                    }
                    className="w-full p-3 rounded-xl border border-slate-200 text-xs focus:outline-none focus:border-[#1F211F] bg-slate-50/40 resize-none"
                  />

                  <div className="flex justify-end">
                    <button
                      type="button"
                      disabled={isSubmittingThis}
                      onClick={() => handleSubmitResponse(item.id)}
                      className="px-4 py-1.5 rounded-full bg-[#1F211F] hover:bg-[#3A3D39] text-white text-xs font-semibold cursor-pointer flex items-center space-x-1.5 disabled:opacity-50"
                    >
                      {isSubmittingThis && <ArrowClockwise size={13} className="animate-spin" />}
                      <span>Save Response</span>
                    </button>
                  </div>
                </div>
              </div>
            );
          })
        )}
      </div>

      {/* Resolved Clarifications History */}
      {resolvedClarifications.length > 0 && (
        <div className="space-y-3 pt-2">
          <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
            Resolved Clarifications ({resolvedClarifications.length})
          </h3>
          <div className="space-y-2.5">
            {resolvedClarifications.map((item) => (
              <div
                key={item.id}
                className="bg-slate-50/70 border border-slate-200/80 rounded-2xl p-4 text-xs space-y-2"
              >
                <div className="flex items-center justify-between text-[11px]">
                  <span className="font-semibold text-slate-700">
                    {item.related_document_name || item.related_field || 'General Inquiry'}
                  </span>
                  <span className="px-2 py-0.5 rounded-full bg-emerald-50 text-emerald-700 font-semibold border border-emerald-200">
                    Resolved
                  </span>
                </div>
                <p className="text-slate-600 italic">"{item.clarification_message}"</p>
                <div className="p-2.5 rounded-xl bg-white border border-slate-200 text-slate-800">
                  <span className="font-semibold text-[10px] text-slate-400 uppercase block">Your Response:</span>
                  <p className="mt-0.5">{item.vendor_response}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Resubmit Application Box */}
      <div className="bg-white rounded-[32px] p-6 border border-slate-200 space-y-4">
        <div className="flex items-center space-x-3">
          <div className="w-10 h-10 rounded-2xl bg-indigo-100 text-indigo-700 flex items-center justify-center shrink-0">
            <FileArrowUp size={22} weight="bold" />
          </div>
          <div>
            <h3 className="text-base font-semibold text-slate-900">
              Resubmit Application for Compliance Review
            </h3>
            <p className="text-xs text-slate-500">
              Once all corrections are made, resubmit your application. An administrator will be notified immediately.
            </p>
          </div>
        </div>

        <div>
          <label className="block text-xs font-semibold text-slate-700 mb-1">
            Optional Resubmission Summary
          </label>
          <input
            type="text"
            placeholder="e.g. Uploaded revised GST certificate with matched trade name."
            value={resubmissionNotes}
            onChange={(e) => setResubmissionNotes(e.target.value)}
            className="w-full px-3 py-2 rounded-xl border border-slate-200 text-xs focus:outline-none focus:border-[#1F211F] bg-slate-50/50"
          />
        </div>

        <div className="pt-2 flex justify-end">
          <button
            type="button"
            disabled={resubmitting || pendingClarifications.length > 0}
            onClick={handleResubmit}
            className="px-6 py-2.5 rounded-full bg-[#1F211F] hover:bg-[#3A3D39] text-white text-xs font-semibold cursor-pointer flex items-center space-x-2 disabled:opacity-40 disabled:cursor-not-allowed"
          >
            {resubmitting ? (
              <>
                <ArrowClockwise size={14} className="animate-spin" />
                <span>Resubmitting...</span>
              </>
            ) : (
              <>
                <span>Resubmit Application</span>
                <ArrowUpRight size={14} weight="bold" />
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
};
