import type { FC } from 'react';
import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  ShieldCheck,
  ArrowLeft,
  Clock,
  Sparkle,
  Buildings,
  FileText,
} from '@phosphor-icons/react';
import { getSubmissions } from '../utils/storage';

export const AdminPlaceholderPage: FC = () => {
  const navigate = useNavigate();
  const [submissions, setSubmissions] = useState<any[]>([]);

  useEffect(() => {
    const list = getSubmissions();
    setSubmissions(list);
  }, []);

  return (
    <div className="min-h-screen bg-[#EEF3F8] py-10 px-4 sm:px-6 lg:px-8 font-sans">
      <div className="max-w-5xl mx-auto space-y-6">
        {/* Header Bar */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-white p-6 rounded-3xl shadow-xl shadow-slate-200/70 border border-slate-200/80">
          <div className="flex items-center space-x-3.5">
            <div className="w-12 h-12 rounded-2xl bg-[#07569B] text-white flex items-center justify-center shadow-md shadow-blue-900/20">
              <ShieldCheck size={28} weight="bold" />
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <h1 className="text-xl font-bold text-slate-900">
                  VendorFlow Admin Portal
                </h1>
                <span className="text-[11px] font-semibold text-amber-700 bg-amber-50 px-2.5 py-0.5 rounded-full border border-amber-200/60">
                  Verification Dashboard Preview
                </span>
              </div>
              <p className="text-xs text-slate-500 mt-0.5">
                Central vendor review and AI-powered document verification hub
              </p>
            </div>
          </div>

          <button
            type="button"
            onClick={() => navigate('/login')}
            className="inline-flex items-center space-x-2 px-4 py-2 rounded-xl border border-slate-200 hover:border-slate-300 bg-slate-50 hover:bg-slate-100 text-slate-700 text-xs font-semibold transition-colors cursor-pointer self-start sm:self-auto"
          >
            <ArrowLeft size={14} weight="bold" />
            <span>Back to Login</span>
          </button>
        </div>

        {/* Informative Notice */}
        <div className="bg-gradient-to-r from-blue-50 to-indigo-50/50 p-6 rounded-3xl border border-blue-200/60 shadow-2xs">
          <div className="flex items-start space-x-3">
            <div className="w-9 h-9 rounded-xl bg-blue-100 text-[#07569B] flex items-center justify-center shrink-0 mt-0.5">
              <Sparkle size={20} weight="bold" />
            </div>
            <div>
              <h3 className="text-sm font-bold text-slate-800">
                Phase 1 Preview: Frontend Onboarding Complete
              </h3>
              <p className="text-xs text-slate-600 mt-1 leading-relaxed">
                As per specifications, the AI document verification engine, automatic inconsistency detection, and approval workflow integrations are scheduled for the next phase. Below you can monitor real-time vendor applications submitted through the <code className="bg-white/80 px-1.5 py-0.5 rounded text-blue-700 font-mono text-[11px]">/vendor</code> onboarding portal.
              </p>
            </div>
          </div>
        </div>

        {/* Submissions Table / Queue */}
        <div className="bg-white rounded-3xl shadow-xl shadow-slate-200/70 border border-slate-200/80 overflow-hidden">
          <div className="p-6 border-b border-slate-100 flex items-center justify-between">
            <div>
              <h2 className="text-base font-bold text-slate-900">
                Incoming Onboarding Applications ({submissions.length})
              </h2>
              <p className="text-xs text-slate-500 mt-0.5">
                Vendors queued for automated verification
              </p>
            </div>

            <button
              type="button"
              onClick={() => navigate('/vendor')}
              className="inline-flex items-center space-x-1.5 px-3 py-1.5 rounded-xl bg-[#0875D1] hover:bg-[#0764B5] text-white text-xs font-semibold transition-colors cursor-pointer"
            >
              <Buildings size={14} weight="bold" />
              <span>Submit New Vendor</span>
            </button>
          </div>

          {submissions.length === 0 ? (
            <div className="p-12 text-center">
              <div className="w-12 h-12 rounded-2xl bg-slate-100 text-slate-400 flex items-center justify-center mx-auto mb-3">
                <FileText size={24} />
              </div>
              <h4 className="text-sm font-semibold text-slate-700">
                No submissions in local queue yet
              </h4>
              <p className="text-xs text-slate-400 max-w-sm mx-auto mt-1 mb-4">
                Submit an onboarding application from the vendor portal to see it tracked here.
              </p>
              <button
                type="button"
                onClick={() => navigate('/vendor')}
                className="inline-flex items-center space-x-1.5 px-4 py-2 rounded-xl bg-[#0875D1] text-white text-xs font-semibold hover:bg-[#0764B5] transition-colors cursor-pointer"
              >
                Go to Vendor Registration
              </button>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="bg-slate-50/80 text-slate-500 uppercase tracking-wider font-semibold border-b border-slate-100">
                  <tr>
                    <th className="px-6 py-3.5">Reference ID</th>
                    <th className="px-6 py-3.5">Company Name</th>
                    <th className="px-6 py-3.5">Contact Email</th>
                    <th className="px-6 py-3.5">Submission Time</th>
                    <th className="px-6 py-3.5">Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {submissions.map((item, idx) => (
                    <tr key={idx} className="hover:bg-slate-50/60 transition-colors">
                      <td className="px-6 py-4 font-mono font-bold text-[#07569B]">
                        {item.referenceNumber}
                      </td>
                      <td className="px-6 py-4 font-semibold text-slate-800">
                        {item.companyName}
                      </td>
                      <td className="px-6 py-4 text-slate-600">
                        {item.primaryContactEmail || '—'}
                      </td>
                      <td className="px-6 py-4 text-slate-500">
                        {item.submittedAt}
                      </td>
                      <td className="px-6 py-4">
                        <span className="inline-flex items-center space-x-1 px-2.5 py-1 rounded-full bg-amber-50 text-amber-700 border border-amber-200/60 font-semibold text-[11px]">
                          <Clock size={12} weight="bold" />
                          <span>Queued for Verification</span>
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
