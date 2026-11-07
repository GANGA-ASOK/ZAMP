import type { FC, ReactNode } from 'react';
import { ArrowLeft, ArrowsClockwise, ArrowUpRight, Buildings } from '@phosphor-icons/react';
import { BrandMark } from '../onboarding/ProgressSidebar';
import type { ApplicationListItem } from '../../services/workflowService';

interface AdminDashboardHeaderProps {
  loading: boolean;
  statusCounts: Record<string, number>;
  applications: ApplicationListItem[];
  statusFilter: string;
  onFilter: (key: string) => void;
  onRefresh: () => void;
  onVendorPortal: () => void;
  onExit: () => void;
  notifications?: ReactNode;
}

const STATUSES: Array<{ key: string; label: string; short: string }> = [
  { key: 'all', label: 'All', short: 'All' },
  { key: 'submitted', label: 'Submitted', short: 'New' },
  { key: 'under_review', label: 'Under review', short: 'Review' },
  { key: 'clarification_required', label: 'Clarification', short: 'Clarif.' },
  { key: 'resubmitted', label: 'Resubmitted', short: 'Resub.' },
  { key: 'approved', label: 'Approved', short: 'Appr.' },
  { key: 'rejected', label: 'Rejected', short: 'Rej.' },
];

const pillBtn =
  'inline-flex items-center gap-2 px-4 py-2 rounded-full border border-ink/25 hover:border-ink text-[13px] text-ink transition-colors cursor-pointer';

export const AdminDashboardHeader: FC<AdminDashboardHeaderProps> = ({
  loading,
  statusCounts,
  applications,
  statusFilter,
  onFilter,
  onRefresh,
  onVendorPortal,
  onExit,
  notifications,
}) => {
  const total = statusCounts.all ?? applications.length;
  const bars = STATUSES.slice(1).map((s) => ({ ...s, count: statusCounts[s.key] ?? 0 }));
  const maxBar = Math.max(1, ...bars.map((b) => b.count));

  const ai = { approve: 0, review: 0, reject: 0, none: 0 };
  for (const a of applications) {
    const o = a.ai_decision?.outcome;
    if (o === 'approve' || o === 'review' || o === 'reject') ai[o] += 1;
    else ai.none += 1;
  }
  const aiTotal = Math.max(1, applications.length);

  return (
    <div className="space-y-5">
      {/* Top bar */}
      <header className="flex flex-wrap items-center justify-between gap-4 animate-rise">
        <div className="flex items-center gap-3">
          <BrandMark size={44} />
          <div>
            <h1 className="text-2xl font-normal tracking-tight leading-none">Admin portal</h1>
            <p className="text-[13px] text-slate-500 mt-1">Vendor applications, AI decisions and approvals</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {notifications}
          <button type="button" onClick={onRefresh} className={pillBtn} title="Refresh queue">
            <ArrowsClockwise size={14} className={loading ? 'animate-spin' : ''} />
            Refresh
          </button>
          <button
            type="button"
            onClick={onVendorPortal}
            className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-ink text-white text-[13px] cursor-pointer hover:bg-ink-soft"
          >
            <Buildings size={14} />
            Vendor portal
          </button>
          <button
            type="button"
            onClick={onExit}
            className="w-10 h-10 rounded-full border border-ink/25 hover:border-ink flex items-center justify-center cursor-pointer"
            title="Exit"
          >
            <ArrowLeft size={16} />
          </button>
        </div>
      </header>

      {/* Dashboard */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-5">
        {/* Applications statistics */}
        <section className="lg:col-span-7 rounded-[36px] bg-ink text-white p-6 sm:p-8 flex flex-col min-h-[260px] animate-rise">
          <div className="flex items-start justify-between">
            <div>
              <h2 className="text-2xl font-normal tracking-tight">Applications</h2>
              <p className="text-[13px] text-white/50 mt-0.5">By onboarding status</p>
            </div>
            <span className="text-[13px] px-4 py-1.5 rounded-full border border-white/25 text-white/80">Live</span>
          </div>
          <div className="mt-auto pt-6 flex items-end justify-between gap-6">
            <div className="shrink-0">
              <p className="text-white/55 text-sm inline-flex items-center gap-2">
                Total
                <span className="w-6 h-6 rounded-full bg-mint text-ink flex items-center justify-center">
                  <ArrowUpRight size={12} weight="bold" />
                </span>
              </p>
              <p className="text-6xl font-light tracking-tight mt-1 tabular">{total}</p>
            </div>
            <div className="flex items-end gap-1.5 sm:gap-2 h-32 flex-1 justify-end max-w-[460px]">
              {bars.map((b) => {
                const h = b.count ? 22 + (b.count / maxBar) * 78 : 10;
                const isGood = b.key === 'approved';
                const isBad = b.key === 'rejected';
                return (
                  <button
                    key={b.key}
                    type="button"
                    onClick={() => onFilter(b.key)}
                    title={`${b.label}: ${b.count}`}
                    className="group flex-1 h-full rounded-[14px] hatch-light flex flex-col justify-end items-stretch cursor-pointer min-w-0"
                  >
                    <span
                      className={`rounded-[14px] flex items-start justify-center pt-1.5 text-[11px] tabular text-ink transition-all ${
                        statusFilter === b.key ? 'ring-2 ring-white' : ''
                      } ${isGood ? 'bg-mint' : isBad ? 'bg-coral' : 'bg-lilac'}`}
                      style={{ height: `${h}%` }}
                    >
                      {b.count > 0 ? b.count : ''}
                    </span>
                    <span className="text-[10px] text-white/55 mt-1.5 truncate">{b.short}</span>
                  </button>
                );
              })}
            </div>
          </div>
        </section>

        {/* AI outcome tiles */}
        <section className="lg:col-span-5 grid grid-cols-3 gap-3 animate-rise" style={{ animationDelay: '60ms' }}>
          {[
            { key: 'approve', label: 'AI approve', bg: 'bg-mint', count: ai.approve },
            { key: 'review', label: 'Needs review', bg: 'bg-sand', count: ai.review },
            { key: 'reject', label: 'AI reject', bg: 'bg-coral', count: ai.reject },
          ].map((t) => (
            <div key={t.key} className={`rounded-[30px] ${t.bg} p-4 sm:p-5 flex flex-col text-ink`}>
              <div className="flex items-center justify-between">
                <span className="text-[12px] text-ink/70 leading-tight">{t.label}</span>
                <ArrowUpRight size={14} />
              </div>
              <p className="text-4xl sm:text-5xl font-light tracking-tight mt-2 tabular">{t.count}</p>
              <div className="mt-auto pt-4">
                <div className="h-4 rounded-full border border-ink/70 overflow-hidden">
                  <div className="h-full hatch border-r border-ink/70" style={{ width: `${(t.count / aiTotal) * 100}%` }} />
                </div>
                <p className="text-[10px] text-ink/60 mt-1.5 tabular">{Math.round((t.count / aiTotal) * 100)}% of listed</p>
              </div>
            </div>
          ))}
        </section>
      </div>

      {/* Status filter pills */}
      <div className="flex flex-wrap gap-2">
        {STATUSES.map((s) => {
          const active = statusFilter === s.key;
          const count = s.key === 'all' ? total : statusCounts[s.key] ?? 0;
          return (
            <button
              key={s.key}
              type="button"
              onClick={() => onFilter(s.key)}
              className={`inline-flex items-center gap-2 pl-4 pr-1.5 py-1.5 rounded-full text-[13px] transition-colors cursor-pointer ${
                active ? 'bg-ink text-white' : 'bg-white/70 hover:bg-white text-ink'
              }`}
            >
              {s.label}
              <span
                className={`min-w-6 h-6 px-1.5 rounded-full text-[11px] flex items-center justify-center tabular ${
                  active ? 'bg-mint text-ink' : 'bg-paper text-slate-600'
                }`}
              >
                {count}
              </span>
            </button>
          );
        })}
      </div>
    </div>
  );
};

export default AdminDashboardHeader;
