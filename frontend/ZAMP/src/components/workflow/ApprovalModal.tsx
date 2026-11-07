import type { FC } from 'react';
import { useState } from 'react';
import { CheckCircle, X, ArrowClockwise } from '@phosphor-icons/react';

interface ApprovalModalProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: (comment: string) => Promise<void>;
  companyName: string;
  referenceNumber: string;
}

export const ApprovalModal: FC<ApprovalModalProps> = ({
  isOpen,
  onClose,
  onConfirm,
  companyName,
  referenceNumber,
}) => {
  const [comment, setComment] = useState('');
  const [loading, setLoading] = useState(false);

  if (!isOpen) return null;

  const handleConfirm = async () => {
    setLoading(true);
    try {
      await onConfirm(comment);
      onClose();
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/40 backdrop-blur-xs animate-fadeIn font-sans">
      <div className="bg-white rounded-[32px] shadow-2xl border border-slate-200 max-w-md w-full p-6 text-left space-y-4">
        {/* Header */}
        <div className="flex items-start justify-between">
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 rounded-2xl bg-emerald-100/80 text-emerald-600 flex items-center justify-center shrink-0">
              <CheckCircle size={24} weight="fill" />
            </div>
            <div>
              <h3 className="text-base font-semibold text-slate-900">
                Approve Vendor Application
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
          Are you sure you want to approve this application? The vendor will receive an official approval notification, and their onboarding status will transition to <strong className="text-emerald-700">Approved</strong>.
        </p>

        {/* Optional Comment */}
        <div>
          <label className="block text-xs font-semibold text-slate-700 mb-1.5">
            Approval Remark (Optional)
          </label>
          <textarea
            rows={3}
            placeholder="e.g. All documents, GSTIN and PAN records validated successfully."
            value={comment}
            onChange={(e) => setComment(e.target.value)}
            className="w-full p-3 rounded-xl border border-slate-200 text-xs focus:outline-none focus:border-emerald-500 bg-slate-50/50 resize-none"
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
            className="px-4 py-2 rounded-full bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-semibold cursor-pointer flex items-center space-x-1.5"
          >
            {loading && <ArrowClockwise size={14} className="animate-spin" />}
            <span>Confirm Approval</span>
          </button>
        </div>
      </div>
    </div>
  );
};

