import type { FC } from 'react';
import { CheckCircle, Lightning } from '@phosphor-icons/react';

interface StepHeaderProps {
  stepNumber: number;
  totalSteps?: number;
  title: string;
  subtitle: string;
  isSaved?: boolean;
  onFillDemo?: () => void;
}

export const StepHeader: FC<StepHeaderProps> = ({
  stepNumber,
  totalSteps = 4,
  title,
  subtitle,
  isSaved = true,
  onFillDemo,
}) => {
  return (
    <div className="mb-6 select-none">
      <div className="flex items-center justify-between mb-2">
        <span className="text-xs font-semibold tracking-wider text-slate-400 uppercase">
          Step {stepNumber}/{totalSteps}
        </span>

        <div className="flex items-center space-x-2">
          {onFillDemo && (
            <button
              type="button"
              onClick={onFillDemo}
              className="inline-flex items-center space-x-1 text-xs text-[#0875D1] hover:text-[#07569B] bg-sky-50 hover:bg-sky-100/80 px-2.5 py-1 rounded-lg transition-colors cursor-pointer border border-sky-200/60"
              title="Pre-populate with sample vendor data for quick testing"
            >
              <Lightning size={13} weight="fill" />
              <span>Fill Sample Data</span>
            </button>
          )}

          <div className="inline-flex items-center space-x-1 text-xs text-emerald-600 bg-emerald-50 px-2 py-0.5 rounded-full border border-emerald-200/50">
            <CheckCircle size={13} weight="fill" />
            <span>{isSaved ? 'Auto-saved' : 'Saving...'}</span>
          </div>
        </div>
      </div>

      <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-slate-900 font-sans">
        {title}
      </h1>
      <p className="mt-1.5 text-sm text-slate-500 leading-relaxed max-w-lg">
        {subtitle}
      </p>
    </div>
  );
};
