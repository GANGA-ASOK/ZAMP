import type { FC } from 'react';
import { useNavigate } from 'react-router-dom';
import { ShieldCheck, Buildings, ArrowRight, Sparkle } from '@phosphor-icons/react';

export const LoginPage: FC = () => {
  const navigate = useNavigate();

  return (
    <div className="min-h-screen bg-[#EEF3F8] py-12 px-4 sm:px-6 lg:px-8 flex items-center justify-center relative overflow-hidden font-sans">
      {/* Background Ambient Orbs */}
      <div className="pointer-events-none absolute -top-40 -left-40 w-96 h-96 bg-blue-200/50 rounded-full blur-3xl" />
      <div className="pointer-events-none absolute -bottom-40 -right-40 w-96 h-96 bg-sky-200/50 rounded-full blur-3xl" />

      <div className="relative z-10 w-full max-w-4xl">
        {/* Brand Header */}
        <div className="text-center mb-10 select-none">
          <div className="inline-flex items-center space-x-2 px-3.5 py-1.5 rounded-full bg-blue-50 border border-blue-200/70 text-[#07569B] text-xs font-semibold mb-4 shadow-2xs">
            <Sparkle size={14} weight="fill" className="text-[#0875D1]" />
            <span>Enterprise Vendor Onboarding</span>
          </div>

          <h1 className="text-3xl sm:text-4xl font-extrabold tracking-tight text-slate-900 font-sans">
            Welcome to <span className="text-[#07569B]">VendorFlow</span>
          </h1>
          <p className="mt-2.5 text-base sm:text-lg text-slate-600 max-w-xl mx-auto leading-relaxed">
            Streamlining vendor registration and onboarding through intelligent automation.
          </p>
        </div>

        {/* Main Interaction Card */}
        <div className="bg-white rounded-3xl shadow-2xl shadow-slate-200/80 border border-slate-200/70 p-6 sm:p-10 lg:p-12 relative overflow-hidden">
          {/* Subtle watermark outline */}
          <div className="pointer-events-none absolute -top-12 -right-12 w-64 h-64 opacity-5">
            <svg viewBox="0 0 200 200" fill="none" xmlns="http://www.w3.org/2000/svg" className="w-full h-full text-slate-900 stroke-current">
              <circle cx="100" cy="100" r="90" strokeWidth="2" />
              <circle cx="100" cy="100" r="50" strokeWidth="2" />
            </svg>
          </div>

          <div className="text-center mb-8">
            <h2 className="text-xl font-bold text-slate-900">
              How would you like to proceed?
            </h2>
            <p className="text-xs sm:text-sm text-slate-500 mt-1">
              Select your role to access the portal
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 max-w-2xl mx-auto">
            {/* Option 1: Admin */}
            <div className="group rounded-2xl border-2 border-slate-200 hover:border-[#0875D1] bg-white p-6 sm:p-7 flex flex-col justify-between transition-all duration-200 hover:shadow-lg hover:shadow-blue-500/5">
              <div>
                <div className="w-12 h-12 rounded-2xl bg-slate-100 group-hover:bg-blue-50 text-slate-700 group-hover:text-[#0875D1] flex items-center justify-center transition-colors mb-5 shadow-2xs">
                  <ShieldCheck size={26} weight="bold" />
                </div>
                <h3 className="text-lg font-bold text-slate-900 mb-1">
                  Admin
                </h3>
                <p className="text-xs sm:text-sm text-slate-500 leading-relaxed">
                  Access the vendor management and verification dashboard.
                </p>
              </div>

              <div className="pt-6 mt-6 border-t border-slate-100">
                <button
                  type="button"
                  onClick={() => navigate('/admin')}
                  className="w-full py-2.5 px-4 rounded-xl border border-slate-200 hover:border-slate-300 bg-slate-50 hover:bg-slate-100 text-slate-800 text-sm font-semibold transition-all duration-150 flex items-center justify-center space-x-2 cursor-pointer shadow-2xs"
                >
                  <span>Login as Admin</span>
                  <ArrowRight size={15} weight="bold" />
                </button>
              </div>
            </div>

            {/* Option 2: New Vendor */}
            <div className="group rounded-2xl border-2 border-[#0875D1]/40 hover:border-[#0875D1] bg-linear-to-b from-blue-50/40 to-white p-6 sm:p-7 flex flex-col justify-between transition-all duration-200 hover:shadow-xl hover:shadow-blue-500/10 ring-2 ring-[#0875D1]/10">
              <div>
                <div className="flex items-center justify-between mb-5">
                  <div className="w-12 h-12 rounded-2xl bg-[#07569B] text-white flex items-center justify-center shadow-md shadow-blue-900/20 group-hover:scale-105 transition-transform">
                    <Buildings size={26} weight="bold" />
                  </div>
                  <span className="text-[11px] font-bold text-[#0875D1] bg-blue-50 px-2.5 py-0.5 rounded-full border border-blue-200/60 uppercase tracking-wider">
                    Registration
                  </span>
                </div>
                <h3 className="text-lg font-bold text-slate-900 mb-1">
                  New Vendor
                </h3>
                <p className="text-xs sm:text-sm text-slate-500 leading-relaxed">
                  Register your organization and submit your details for vendor onboarding.
                </p>
              </div>

              <div className="pt-6 mt-6 border-t border-blue-100/60">
                <button
                  type="button"
                  onClick={() => navigate('/vendor')}
                  className="w-full py-2.5 px-4 rounded-xl bg-[#0875D1] hover:bg-[#0764B5] active:scale-[0.98] text-white text-sm font-semibold transition-all duration-150 flex items-center justify-center space-x-2 cursor-pointer shadow-md shadow-blue-500/20"
                >
                  <span>Register as Vendor</span>
                  <ArrowRight size={15} weight="bold" />
                </button>
              </div>
            </div>
          </div>

          {/* Footer Note */}
          <div className="mt-10 pt-6 border-t border-slate-100 text-center text-xs text-slate-400">
            Protected by enterprise-grade 256-bit encryption • © 2026 VendorFlow Inc.
          </div>
        </div>
      </div>
    </div>
  );
};
