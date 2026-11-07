import type { FC } from 'react';
import { useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import {
  CheckCircle,
  Copy,
  Check,
  DownloadSimple,
  ArrowRight,
  Clock,
  Sparkle,
} from '@phosphor-icons/react';

export const SubmissionSuccessPage: FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const [copied, setCopied] = useState(false);

  // Retrieve submission details from state or fallback
  const submission = location.state?.submission || {
    referenceNumber: 'VND-2026-00001',
    companyName: 'Your Organization',
    submittedAt: new Date().toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    }),
  };

  const handleCopyReference = () => {
    navigator.clipboard.writeText(submission.referenceNumber);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleDownloadReceipt = () => {
    const content = `VENDORFLOW ONBOARDING RECEIPT
--------------------------------------
Application Reference: ${submission.referenceNumber}
Company Name: ${submission.companyName}
Submission Date: ${submission.submittedAt}
Status: Queued for Verification
--------------------------------------
This document serves as proof of submission for vendor onboarding.
Your application is currently being analyzed by VendorFlow's intelligent verification engine.`;

    const blob = new Blob([content], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `VendorFlow_Receipt_${submission.referenceNumber}.txt`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  return (
    <div className="min-h-screen bg-[#D8DFD7] py-12 px-4 sm:px-6 lg:px-8 flex items-center justify-center relative overflow-hidden font-sans">
      {/* Background Ambient Orbs */}
      <div className="pointer-events-none absolute -top-40 -left-40 w-96 h-96 bg-blue-200/50 rounded-full blur-3xl" />
      <div className="pointer-events-none absolute -bottom-40 -right-40 w-96 h-96 bg-emerald-200/40 rounded-full blur-3xl" />

      <div className="relative z-10 w-full max-w-2xl">
        <div className="bg-white rounded-[32px] border border-slate-200/70 p-6 sm:p-10 relative overflow-hidden text-center">
          {/* Success Icon */}
          <div className="w-18 h-18 sm:w-20 sm:h-20 rounded-full bg-emerald-50 border-4 border-emerald-100 flex items-center justify-center mx-auto text-emerald-500 mb-6">
            <CheckCircle size={44} weight="fill" />
          </div>

          {/* Heading and Subtitle */}
          <h1 className="text-2xl sm:text-3xl font-medium text-slate-900 tracking-tight">
            Your application has been submitted successfully!
          </h1>
          <p className="mt-2 text-sm sm:text-base text-slate-600 max-w-lg mx-auto leading-relaxed">
            Your registration is now queued for verification. You can use your application reference number to track its progress.
          </p>

          {/* Reference Number Card */}
          <div className="my-8 p-5 rounded-2xl bg-slate-50 border border-slate-200/80 max-w-md mx-auto flex flex-col items-center justify-center">
            <span className="text-xs uppercase tracking-wider font-semibold text-slate-400 mb-1">
              Application Reference Number
            </span>
            <div className="flex items-center space-x-3">
              <span className="text-xl sm:text-2xl font-mono font-semibold text-[#1F211F] tracking-wider">
                {submission.referenceNumber}
              </span>
              <button
                type="button"
                onClick={handleCopyReference}
                className="p-2 rounded-xl bg-white border border-slate-200 hover:border-slate-300 text-slate-600 hover:text-[#1F211F] transition-all cursor-pointer"
                title="Copy Reference"
              >
                {copied ? <Check size={16} weight="bold" className="text-emerald-500" /> : <Copy size={16} />}
              </button>
            </div>
            {copied && (
              <span className="text-[11px] font-medium text-emerald-600 mt-1 animate-fadeIn">
                Copied to clipboard!
              </span>
            )}
            <div className="mt-3 inline-flex items-center space-x-1.5 px-3 py-1 rounded-full bg-amber-50 border border-amber-200/60 text-amber-700 text-xs font-semibold">
              <Clock size={13} weight="bold" />
              <span>Status: Queued for Verification</span>
            </div>
          </div>

          {/* Verification Pipeline Timeline */}
          <div className="text-left bg-slate-50/60 rounded-2xl p-5 border border-slate-200/70 mb-8 max-w-md mx-auto">
            <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-500 mb-3 flex items-center space-x-1.5">
              <Sparkle size={14} className="text-[#1F211F]" />
              <span>What Happens Next?</span>
            </h4>
            <div className="space-y-3 text-xs">
              <div className="flex items-start space-x-2.5">
                <div className="w-4 h-4 rounded-full bg-emerald-500 text-white flex items-center justify-center mt-0.5 shrink-0">
                  <Check size={10} weight="bold" />
                </div>
                <div>
                  <span className="font-semibold text-slate-800">1. Intake Received</span>
                  <p className="text-slate-500">Your documents and tax records are recorded in the ledger.</p>
                </div>
              </div>

              <div className="flex items-start space-x-2.5">
                <div className="w-4 h-4 rounded-full bg-[#1F211F] text-white flex items-center justify-center mt-0.5 shrink-0">
                  <Clock size={10} weight="bold" />
                </div>
                <div>
                  <span className="font-semibold text-slate-800">2. Document Cross-Validation (Queued)</span>
                  <p className="text-slate-500">Automated consistency check between PAN, GSTIN, and Bank proofs.</p>
                </div>
              </div>

              <div className="flex items-start space-x-2.5 opacity-60">
                <div className="w-4 h-4 rounded-full bg-slate-300 text-white flex items-center justify-center mt-0.5 shrink-0">
                  <span className="text-[9px] font-semibold">3</span>
                </div>
                <div>
                  <span className="font-semibold text-slate-700">3. Final Onboarding Decision</span>
                  <p className="text-slate-500">You will receive an official approval status notification via email.</p>
                </div>
              </div>
            </div>
          </div>

          {/* Action Buttons */}
          <div className="flex flex-col sm:flex-row items-center justify-center gap-3 max-w-md mx-auto">
            <button
              type="button"
              onClick={handleDownloadReceipt}
              className="w-full sm:w-auto px-5 py-2.5 rounded-xl border border-slate-200 hover:border-slate-300 bg-white hover:bg-slate-50 text-slate-700 text-sm font-semibold transition-colors flex items-center justify-center space-x-2 cursor-pointer"
            >
              <DownloadSimple size={16} weight="bold" />
              <span>Download Receipt</span>
            </button>

            <button
              type="button"
              onClick={() => navigate('/login')}
              className="w-full sm:w-auto px-6 py-2.5 rounded-full bg-[#1F211F] hover:bg-[#3A3D39] text-white text-sm font-semibold transition-all flex items-center justify-center space-x-2 cursor-pointer"
            >
              <span>Return to Home</span>
              <ArrowRight size={15} weight="bold" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
