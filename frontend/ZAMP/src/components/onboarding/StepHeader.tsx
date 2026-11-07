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
    <div className="mb-8 select-none">
      <div className="flex items-center justify-between mb-4">
        <span className="inline-flex items-center gap-2 text-[13px] text-slate-500">
          <span className="px-3 py-1 rounded-full border border-slate-300 text-ink tabular">
            Step {stepNumber} of {totalSteps}
          </span>
        </span>

        <div className="flex items-center gap-2">
          {onFillDemo && (
            <button
              type="button"
              onClick={onFillDemo}
              className="inline-flex items-center gap-1 text-xs text-ink px-3 py-1 rounded-full border border-slate-300 hover:bg-paper cursor-pointer"
            >
              <Lightning size={13} weight="fill" />
              <span>Fill sample data</span>
            </button>
          )}
          <span className="inline-flex items-center gap-1.5 text-xs text-slate-500">
            <CheckCircle size={14} weight="fill" className={isSaved ? 'text-emerald-500' : 'text-slate-300'} />
            {isSaved ? 'Saved' : 'Saving…'}
          </span>
        </div>
      </div>

      <h1 className="text-3xl sm:text-[40px] leading-[1.1] font-normal tracking-tight text-ink">{title}</h1>
      <p className="mt-2 text-[15px] text-slate-500 leading-relaxed max-w-xl">{subtitle}</p>
    </div>
  );
};
