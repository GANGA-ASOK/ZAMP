import type { FC } from 'react';
import { ArrowLeft, ArrowRight, PaperPlaneTilt } from '@phosphor-icons/react';

interface StepNavigationProps {
  currentStep: number;
  totalSteps?: number;
  onBack: () => void;
  onNext: () => void;
  isSubmitting?: boolean;
  nextLabel?: string;
  disableBack?: boolean;
}

export const StepNavigation: FC<StepNavigationProps> = ({
  currentStep,
  totalSteps = 4,
  onBack,
  onNext,
  isSubmitting = false,
  nextLabel,
  disableBack = false,
}) => {
  const isFirstStep = currentStep === 1;
  const isLastStep = currentStep === totalSteps;

  return (
    <div className="flex items-center justify-between pt-8 mt-auto select-none">
      <div>
        {!isFirstStep && (
          <button
            type="button"
            onClick={onBack}
            disabled={disableBack || isSubmitting}
            className="w-12 h-12 rounded-full border border-ink/70 text-ink hover:bg-ink hover:text-white transition-colors flex items-center justify-center cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed"
            aria-label="Go to previous step"
          >
            <ArrowLeft size={18} />
          </button>
        )}
      </div>

      <button
        type="button"
        onClick={onNext}
        disabled={isSubmitting}
        className="group inline-flex items-center gap-3 pl-6 pr-1.5 py-1.5 rounded-full bg-ink text-white text-[15px] transition-all cursor-pointer active:scale-[0.98] disabled:opacity-50 disabled:cursor-not-allowed"
      >
        <span>{nextLabel || (isLastStep ? 'Submit for verification' : 'Continue')}</span>
        <span className="w-9 h-9 rounded-full bg-mint text-ink flex items-center justify-center transition-transform group-hover:translate-x-0.5">
          {isSubmitting ? (
            <span className="w-4 h-4 border-2 border-ink/25 border-t-ink rounded-full animate-spin" />
          ) : isLastStep ? (
            <PaperPlaneTilt size={16} weight="bold" />
          ) : (
            <ArrowRight size={16} weight="bold" />
          )}
        </span>
      </button>
    </div>
  );
};
