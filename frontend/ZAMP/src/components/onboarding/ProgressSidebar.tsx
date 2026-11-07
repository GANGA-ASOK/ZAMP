import type { FC, ComponentType } from 'react';
import { Buildings, User, Bank, FileText, Check, ArrowUpRight } from '@phosphor-icons/react';

export interface StepItem {
  id: number;
  title: string;
  description: string;
  icon: ComponentType<{ size?: number; weight?: 'bold' | 'fill' | 'regular' | 'light'; className?: string }>;
}

export const STEPS: StepItem[] = [
  { id: 1, title: 'Company', description: 'Legal name, entity type & address', icon: Buildings },
  { id: 2, title: 'Contacts', description: 'Primary contact & signatory', icon: User },
  { id: 3, title: 'Tax & banking', description: 'PAN, GSTIN and payout account', icon: Bank },
  { id: 4, title: 'Documents', description: 'Proofs, declarations & review', icon: FileText },
];

interface ProgressSidebarProps {
  currentStep: number;
  onStepClick: (stepId: number) => void;
  completedSteps: number[];
}

/** Brand mark: two overlapping discs in mint and lilac. */
export const BrandMark: FC<{ size?: number; onDark?: boolean }> = ({ size = 40, onDark = false }) => (
  <div
    className={`rounded-full flex items-center justify-center shrink-0 ${onDark ? 'bg-white/10' : 'bg-ink'}`}
    style={{ width: size, height: size }}
  >
    <svg width={size * 0.58} height={size * 0.58} viewBox="0 0 24 24" fill="none">
      <circle cx="9" cy="12" r="6.5" fill="#A6EF9F" />
      <circle cx="15" cy="12" r="6.5" fill="#B3A6FB" fillOpacity="0.92" />
    </svg>
  </div>
);

export const ProgressSidebar: FC<ProgressSidebarProps> = ({ currentStep, onStepClick, completedSteps }) => {
  const done = completedSteps.filter((s) => s < 5).length;
  const pct = Math.round((Math.min(done, 4) / 4) * 100);

  return (
    <aside className="h-full rounded-[36px] bg-ink text-white p-6 sm:p-8 flex flex-col gap-8 select-none overflow-hidden">
      {/* Brand */}
      <div className="flex items-center gap-3">
        <BrandMark onDark />
        <div>
          <p className="text-xl font-medium tracking-tight leading-none">VendorFlow</p>
          <p className="text-xs text-white/50 mt-1">Vendor onboarding</p>
        </div>
      </div>

      {/* Timeline */}
      <nav aria-label="Registration progress" className="relative flex-1">
        <p className="text-[13px] text-white/50 mb-5">Your application</p>
        <ol className="relative">
          <span className="absolute left-[11px] top-3 bottom-3 w-px bg-white/15" aria-hidden />
          {STEPS.map((step) => {
            const isCurrent = step.id === currentStep;
            const isCompleted = completedSteps.includes(step.id) && !isCurrent;
            const isClickable = isCompleted || step.id <= currentStep;
            const Icon = step.icon;
            return (
              <li key={step.id} className="relative pb-7 last:pb-0">
                <button
                  type="button"
                  onClick={() => isClickable && onStepClick(step.id)}
                  disabled={!isClickable}
                  className={`relative flex items-start gap-4 text-left w-full outline-hidden ${
                    isClickable ? 'cursor-pointer' : 'cursor-not-allowed'
                  }`}
                >
                  <span
                    className={`relative z-10 mt-0.5 shrink-0 flex items-center justify-center rounded-full transition-all duration-300 ${
                      isCurrent
                        ? 'w-[23px] h-[23px] bg-mint text-ink ring-[6px] ring-mint/15'
                        : isCompleted
                        ? 'w-[23px] h-[23px] bg-white text-ink'
                        : 'w-[23px] h-[23px] bg-ink border border-white/35'
                    }`}
                  >
                    {isCompleted ? <Check size={12} weight="bold" /> : isCurrent ? <Icon size={12} weight="bold" /> : null}
                  </span>
                  <span className="min-w-0">
                    <span className={`block text-[11px] tabular ${isCurrent ? 'text-mint' : 'text-white/40'}`}>
                      Step {step.id}
                    </span>
                    <span className={`block text-lg leading-tight ${isCurrent ? 'text-white' : isCompleted ? 'text-white/85' : 'text-white/45'}`}>
                      {step.title}
                    </span>
                    <span className={`block text-xs mt-0.5 ${isCurrent ? 'text-white/60' : 'text-white/35'}`}>{step.description}</span>
                  </span>
                </button>
              </li>
            );
          })}
        </ol>
      </nav>

      {/* Progress tile */}
      <div className="rounded-[26px] bg-mint text-ink p-5">
        <div className="flex items-center justify-between">
          <span className="text-[13px] text-ink/70">Completed</span>
          <ArrowUpRight size={16} />
        </div>
        <p className="text-4xl font-light tracking-tight mt-1 tabular">
          {Math.min(done, 4)}
          <span className="text-ink/45">/4</span>
        </p>
        <div className="mt-4 h-5 rounded-full border border-ink/80 overflow-hidden flex">
          <div className="h-full hatch border-r border-ink/80 transition-all duration-500" style={{ width: `${pct}%` }} />
        </div>
        <p className="text-[11px] text-ink/60 mt-2">{pct === 100 ? 'Ready to submit' : 'Auto-saved as you go'}</p>
      </div>
    </aside>
  );
};
