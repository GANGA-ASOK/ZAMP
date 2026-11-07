import type { FC } from 'react';
import { useState } from 'react';
import {
  WarningCircle,
  X,
  ArrowClockwise,
  FilePdf,
  ListBullets,
  ChatCircleText,
} from '@phosphor-icons/react';

interface ClarificationModalProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: (payload: {
    clarification_message: string;
    related_document_id?: string | null;
    related_document_name?: string | null;
    related_field?: string | null;
    admin_notes?: string | null;
  }) => Promise<void>;
  documents: Array<{ id: string; category: string; original_filename?: string; file_name?: string }>;
  companyName: string;
  referenceNumber: string;
}

export const ClarificationModal: FC<ClarificationModalProps> = ({
  isOpen,
  onClose,
  onConfirm,
  documents,
  companyName,
  referenceNumber,
}) => {
  const [targetType, setTargetType] = useState<'document' | 'field' | 'general'>('document');
  const [selectedDocId, setSelectedDocId] = useState<string>(documents[0]?.id || '');
  const [selectedField, setSelectedField] = useState<string>('tax_details.gstin');
  const [customField, setCustomField] = useState<string>('');
  const [message, setMessage] = useState<string>('');
  const [internalNotes, setInternalNotes] = useState<string>('');
  const [error, setError] = useState<string>('');
  const [loading, setLoading] = useState<boolean>(false);

  if (!isOpen) return null;

  const handleConfirm = async () => {
    if (!message.trim() || message.trim().length < 5) {
      setError('Please provide a detailed clarification message (at least 5 characters).');
      return;
    }
    setError('');
    setLoading(true);

    try {
      let docId: string | null = null;
      let docName: string | null = null;
      let fieldVal: string | null = null;

      if (targetType === 'document') {
        docId = selectedDocId || (documents[0]?.id || null);
        const d = documents.find((item) => item.id === docId);
        docName = d?.category?.replace(/_/g, ' ').toUpperCase() || d?.original_filename || 'Uploaded Document';
      } else if (targetType === 'field') {
        fieldVal = selectedField === 'custom' ? customField : selectedField;
      }

      await onConfirm({
        clarification_message: message.trim(),
        related_document_id: docId,
        related_document_name: docName,
        related_field: fieldVal,
        admin_notes: internalNotes.trim() || null,
      });
      onClose();
    } catch (err: any) {
      setError(err.message || 'Failed to submit clarification request.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/40 backdrop-blur-xs animate-fadeIn font-sans">
      <div className="bg-white rounded-3xl shadow-2xl border border-slate-200 max-w-lg w-full p-6 text-left space-y-4">
        {/* Header */}
        <div className="flex items-start justify-between">
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 rounded-2xl bg-amber-100/80 text-amber-700 flex items-center justify-center shrink-0">
              <WarningCircle size={24} weight="fill" />
            </div>
            <div>
              <h3 className="text-base font-bold text-slate-900">
                Request Clarification / Document Correction
              </h3>
              <p className="text-xs text-slate-500 font-mono">
                {referenceNumber} • {companyName}
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="text-slate-400 hover:text-slate-600 p-1 rounded-lg cursor-pointer"
          >
            <X size={16} />
          </button>
        </div>

        <p className="text-xs text-slate-600 leading-relaxed">
          The application status will update to <strong className="text-amber-800">Clarification Required</strong>. The vendor will be notified and given the option to re-upload documents or provide corrected details.
        </p>

        {/* Target Scope Selector */}
        <div>
          <label className="block text-xs font-semibold text-slate-700 mb-1.5">
            Target of Clarification
          </label>
          <div className="grid grid-cols-3 gap-2">
            {[
              { id: 'document', label: 'Document', icon: FilePdf },
              { id: 'field', label: 'Form Field', icon: ListBullets },
              { id: 'general', label: 'General', icon: ChatCircleText },
            ].map((t) => {
              const Icon = t.icon;
              const active = targetType === t.id;
              return (
                <button
                  key={t.id}
                  type="button"
                  onClick={() => setTargetType(t.id as any)}
                  className={`p-2.5 rounded-xl border text-xs font-semibold flex items-center justify-center space-x-1.5 transition-all cursor-pointer ${
                    active
                      ? 'bg-blue-50 border-[#07569B] text-[#07569B] shadow-2xs'
                      : 'bg-slate-50/70 border-slate-200 text-slate-600 hover:bg-slate-100'
                  }`}
                >
                  <Icon size={14} weight="bold" />
                  <span>{t.label}</span>
                </button>
              );
            })}
          </div>
        </div>

        {/* Dynamic target input */}
        {targetType === 'document' && (
          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">
              Select Document Requiring Replacement / Correction
            </label>
            {documents.length === 0 ? (
              <p className="text-xs text-slate-400 italic">No uploaded documents available.</p>
            ) : (
              <select
                value={selectedDocId}
                onChange={(e) => setSelectedDocId(e.target.value)}
                className="w-full px-3 py-2 rounded-xl border border-slate-200 text-xs focus:outline-none focus:border-[#07569B] bg-slate-50/50"
              >
                {documents.map((doc) => (
                  <option key={doc.id} value={doc.id}>
                    {doc.category?.replace(/_/g, ' ').toUpperCase()} ({doc.original_filename || doc.file_name || doc.id})
                  </option>
                ))}
              </select>
            )}
          </div>
        )}

        {targetType === 'field' && (
          <div className="space-y-2">
            <label className="block text-xs font-semibold text-slate-700 mb-1">
              Select Registration Field
            </label>
            <select
              value={selectedField}
              onChange={(e) => setSelectedField(e.target.value)}
              className="w-full px-3 py-2 rounded-xl border border-slate-200 text-xs focus:outline-none focus:border-[#07569B] bg-slate-50/50"
            >
              <option value="company_info.legal_name">Legal Company Name</option>
              <option value="company_info.registration_number">Company Registration / CIN</option>
              <option value="tax_details.pan_number">PAN Number</option>
              <option value="tax_details.gstin">GSTIN</option>
              <option value="banking_details.account_number">Bank Account Number</option>
              <option value="banking_details.ifsc_code">Bank IFSC Code</option>
              <option value="custom">Other / Custom Field</option>
            </select>
            {selectedField === 'custom' && (
              <input
                type="text"
                placeholder="Field name or description"
                value={customField}
                onChange={(e) => setCustomField(e.target.value)}
                className="w-full px-3 py-2 rounded-xl border border-slate-200 text-xs focus:outline-none focus:border-[#07569B]"
              />
            )}
          </div>
        )}

        {/* Message for vendor */}
        <div>
          <label className="block text-xs font-semibold text-slate-700 mb-1.5">
            Clarification Message (Visible to Vendor) <span className="text-amber-600">*</span>
          </label>
          <textarea
            rows={3}
            placeholder="e.g. Uploaded GST Certificate trade name does not match legal entity name. Please upload an updated certificate or amendment."
            value={message}
            onChange={(e) => {
              setMessage(e.target.value);
              if (error) setError('');
            }}
            className={`w-full p-3 rounded-xl border text-xs focus:outline-none bg-slate-50/50 resize-none ${
              error ? 'border-amber-400 focus:border-amber-500' : 'border-slate-200 focus:border-[#07569B]'
            }`}
          />
          {error && (
            <p className="text-[11px] text-rose-600 mt-1 flex items-center space-x-1 font-medium">
              <WarningCircle size={12} weight="bold" />
              <span>{error}</span>
            </p>
          )}
        </div>

        {/* Internal Admin Note */}
        <div>
          <label className="block text-xs font-semibold text-slate-700 mb-1">
            Internal Note (Staff Only)
          </label>
          <input
            type="text"
            placeholder="Optional internal reminder or context"
            value={internalNotes}
            onChange={(e) => setInternalNotes(e.target.value)}
            className="w-full px-3 py-2 rounded-xl border border-slate-200 text-xs focus:outline-none focus:border-[#07569B] bg-slate-50/50"
          />
        </div>

        {/* Action Buttons */}
        <div className="flex items-center justify-end space-x-2 pt-2">
          <button
            type="button"
            disabled={loading}
            onClick={onClose}
            className="px-4 py-2 rounded-xl border border-slate-200 hover:bg-slate-50 text-slate-700 text-xs font-semibold cursor-pointer"
          >
            Cancel
          </button>
          <button
            type="button"
            disabled={loading}
            onClick={handleConfirm}
            className="px-4 py-2 rounded-xl bg-amber-600 hover:bg-amber-700 text-white text-xs font-semibold cursor-pointer shadow-sm shadow-amber-600/20 flex items-center space-x-1.5 disabled:opacity-50"
          >
            {loading && <ArrowClockwise size={14} className="animate-spin" />}
            <span>Send Request</span>
          </button>
        </div>
      </div>
    </div>
  );
};

