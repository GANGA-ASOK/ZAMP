import type { FC } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowRight, ArrowUpRight, Buildings, ShieldCheck, Sparkle } from '@phosphor-icons/react';
import { BrandMark } from '../components/onboarding/ProgressSidebar';

const PIPELINE = [
  { title: 'Parse', text: 'Nemotron reads every document' },
  { title: 'Extract', text: 'Name, PAN, GSTIN, mobile, address' },
  { title: 'Cross-check', text: 'Form vs documents vs other vendors' },
  { title: 'Decide', text: 'Approve, review or reject — with reasons' },
];

const ATTRIBUTES = ['Name', 'PAN', 'GSTIN', 'CIN', 'Mobile', 'Address', 'Account', 'IFSC', 'Holder'];

export const LoginPage: FC = () => {
  const navigate = useNavigate();

  return (
    <div className="min-h-screen bg-canvas font-sans text-ink px-4 py-8 sm:px-8 lg:py-14">
      <div className="mx-auto max-w-6xl">
        {/* Top bar */}
        <header className="flex items-center justify-between mb-8 animate-rise">
          <div className="flex items-center gap-3">
            <BrandMark size={44} />
            <div>
              <p className="text-xl font-medium tracking-tight leading-none">VendorFlow</p>
              <p className="text-xs text-slate-500 mt-1">AI vendor onboarding</p>
            </div>
          </div>
          <span className="hidden sm:inline-flex items-center gap-2 text-[13px] px-4 py-2 rounded-full border border-ink/25">
            <Sparkle size={14} weight="fill" className="text-lilac-deep" /> Powered by NVIDIA Nemotron
          </span>
        </header>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
          {/* Statistics card */}
          <section className="rounded-[36px] bg-ink text-white p-7 sm:p-9 flex flex-col min-h-[340px] animate-rise">
            <div className="flex items-start justify-between gap-4">
              <div>
                <h1 className="text-[28px] sm:text-[34px] leading-tight font-normal tracking-tight">
                  Onboard vendors you can trust
                </h1>
                <p className="text-white/55 mt-2 text-[15px] max-w-sm">
                  Every submission is cross-checked against its own documents before anyone pays it.
                </p>
              </div>
            </div>

            <div className="mt-auto pt-10 flex items-end justify-between gap-6">
              <div>
                <p className="text-white/55 text-sm inline-flex items-center gap-2">
                  Attributes cross-checked
                  <span className="w-6 h-6 rounded-full bg-mint text-ink flex items-center justify-center">
                    <ArrowUpRight size={12} weight="bold" />
                  </span>
                </p>
                <p className="text-6xl sm:text-7xl font-light tracking-tight mt-2 tabular">9</p>
              </div>
              {/* Stacked bars, after the reference's statistics card */}
              <div className="flex items-end gap-2.5 h-36">
                {[
                  { label: 'Form', mint: 62, lilac: 38 },
                  { label: 'Docs', mint: 78, lilac: 22 },
                  { label: 'Match', mint: 92, lilac: 8 },
                ].map((b) => (
                  <div key={b.label} className="w-16 sm:w-20 h-full rounded-[18px] hatch-light flex flex-col justify-end overflow-hidden relative">
                    <span className="absolute top-2 inset-x-0 text-center text-[11px] text-white/70">{b.label}</span>
                    <div className="bg-mint rounded-t-[16px]" style={{ height: `${b.mint * 0.75}%` }} />
                    <div className="bg-lilac -mt-3 rounded-[16px]" style={{ height: `${b.lilac * 0.75 + 12}%` }} />
                  </div>
                ))}
              </div>
            </div>
          </section>

          {/* Entry cards */}
          <div className="flex flex-col gap-5">
            <section className="rounded-[36px] bg-paper p-6 sm:p-7 animate-rise" style={{ animationDelay: '60ms' }}>
              <div className="flex items-center gap-4">
                <span className="w-14 h-14 rounded-full bg-ink text-white flex items-center justify-center shrink-0">
                  <Buildings size={24} />
                </span>
                <div className="flex-1">
                  <h2 className="text-2xl font-normal tracking-tight">New vendor</h2>
                  <p className="text-sm text-slate-500">Register your company in four short steps</p>
                </div>
              </div>
              <button
                type="button"
                onClick={() => navigate('/vendor')}
                className="mt-5 w-full flex items-center justify-between rounded-[20px] bg-[#d9ddd6] hover:bg-mint transition-colors px-5 py-3.5 cursor-pointer group"
              >
                <span className="text-[15px]">Start registration</span>
                <span className="w-9 h-9 rounded-full bg-ink text-white flex items-center justify-center group-hover:translate-x-0.5 transition-transform">
                  <ArrowRight size={16} />
                </span>
              </button>
            </section>

            <section className="rounded-[36px] bg-white p-6 sm:p-7 flex-1 animate-rise" style={{ animationDelay: '120ms' }}>
              <div className="flex items-center gap-4">
                <span className="w-14 h-14 rounded-full bg-mint text-ink flex items-center justify-center shrink-0">
                  <ShieldCheck size={24} />
                </span>
                <div className="flex-1">
                  <h2 className="text-2xl font-normal tracking-tight">Admin portal</h2>
                  <p className="text-sm text-slate-500">Review AI decisions and approve vendors</p>
                </div>
                <button
                  type="button"
                  onClick={() => navigate('/admin')}
                  className="w-12 h-12 rounded-full border border-ink/70 hover:bg-ink hover:text-white transition-colors flex items-center justify-center cursor-pointer shrink-0"
                  aria-label="Open admin portal"
                >
                  <ArrowRight size={18} />
                </button>
              </div>

              <div className="mt-6 grid grid-cols-1 sm:grid-cols-[1fr_auto] gap-5">
                {/* Pipeline timeline */}
                <ol className="relative pl-1">
                  <span className="absolute left-[7px] top-2 bottom-2 w-px bg-slate-300" aria-hidden />
                  {PIPELINE.map((p, i) => (
                    <li key={p.title} className="relative flex gap-4 pb-4 last:pb-0">
                      <span
                        className={`relative z-10 mt-1 w-[13px] h-[13px] rounded-full shrink-0 ${
                          i === PIPELINE.length - 1 ? 'bg-ink' : 'bg-white border border-slate-400'
                        }`}
                      />
                      <span>
                        <span className="block text-[15px] leading-tight">{p.title}</span>
                        <span className="block text-[13px] text-slate-500">{p.text}</span>
                      </span>
                    </li>
                  ))}
                </ol>
                <div className="flex sm:flex-col gap-3">
                  <div className="flex-1 rounded-[22px] bg-mint p-4 min-w-[130px]">
                    <p className="text-xs text-ink/65">Outcomes</p>
                    <p className="text-3xl font-light tabular">3</p>
                    <p className="text-[11px] text-ink/60">approve · review · reject</p>
                  </div>
                  <div className="flex-1 rounded-[22px] bg-lilac p-4 min-w-[130px]">
                    <p className="text-xs text-ink/65">Pipeline stages</p>
                    <p className="text-3xl font-light tabular">9</p>
                    <p className="text-[11px] text-ink/60">shown live per run</p>
                  </div>
                </div>
              </div>
            </section>
          </div>
        </div>

        <div className="mt-5 flex flex-wrap gap-2 justify-center">
          {ATTRIBUTES.map((a) => (
            <span key={a} className="text-xs px-3 py-1.5 rounded-full border border-ink/20 text-slate-600">
              {a}
            </span>
          ))}
        </div>
      </div>
    </div>
  );
};
