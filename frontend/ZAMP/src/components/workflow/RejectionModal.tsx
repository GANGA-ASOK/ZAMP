import type { FC } from 'react';
import { useEffect, useState } from 'react';
import { XCircle, X, ArrowClockwise, WarningCircle } from '@phosphor-icons/react';

interface RejectionModalProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: (reason: string) => Promise<void>;
  companyName: string;
  referenceNumber: string;
  /** Optional pre-filled reason (e.g. drafted by the AI Decision Engine). */
  initialReason?: string;
}

export const RejectionModal: FC<RejectionModalProps> = ({
  isOpen,
  onClose,
  onConfirm,
  companyName,
  referenceNumber,
  initialReason,
}) => {
  const [reason, setReason] = useState('');

  useEffect(() => {
    if (isOpen) setReason(initialReason ?? '');
  }, [isOpen, initialReason]);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  if (!isOpen) return null;

  const handleConfirm = async () => {
    if (!reason.trim()) {
      setError('Please provide a specific rejection reason for the vendor.');
      return;
    }
    setError('');
    setLoading(true);
    try {
      await onConfirm(reason.trim());
      onClose();
    } catch (err: any) {
      setError(err.message || 'Failed to reject application.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/40 backdrop-blur-xs animate-fadeIn font-sans">
      <div className="bg-white rounded-3xl shadow-2xl border border-slate-200 max-w-md w-full p-6 text-left space-y-4">
        {/* Header */}
        <div className="flex items-start justify-between">
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 rounded-2xl bg-rose-100/80 text-rose-600 flex items-center justify-center shrink-0">
              <XCircle size={24} weight="fill" />
            </div>
            <div>
              <h3 className="text-base font-bold text-slate-900">
                Reject Vendor Application
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
          Rejecting an application will update the status to <strong className="text-rose-700">Rejected</strong> and send a notification with the rationale to the vendor. Existing documents and records are safely preserved.
        </p>

        {/* Reason Textarea (Mandatory) */}
        <div>
          <label className="block text-xs font-semibold text-slate-700 mb-1.5">
            Rejection Reason <span className="text-rose-600">*</span>
          </label>
          <textarea
            rows={4}
            placeholder="Explain specifically why the application was rejected (e.g. fraudulent business documentation or failed bank verification)."
            value={reason}
            onChange={(e) => {
              setReason(e.target.value);
              if (error) setError('');
            }}
            className={`w-full p-3 rounded-xl border text-xs focus:outline-none bg-slate-50/50 resize-none ${
              error ? 'border-rose-400 focus:border-rose-500' : 'border-slate-200 focus:border-rose-500'
            }`}
          />
          {error && (
            <p className="text-[11px] text-rose-600 mt-1 flex items-center space-x-1 font-medium">
              <WarningCircle size={12} weight="bold" />
              <span>{error}</span>
            </p>
          )}
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
            className="px-4 py-2 rounded-xl bg-rose-600 hover:bg-rose-700 text-white text-xs font-semibold cursor-pointer shadow-sm shadow-rose-600/20 flex items-center space-x-1.5 disabled:opacity-50"
          >
            {loading && <ArrowClockwise size={14} className="animate-spin" />}
            <span>Confirm Rejection</span>
          </button>
        </div>
      </div>
    </div>
  );
};

