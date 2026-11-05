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
    <div className="flex items-center justify-between pt-8 mt-auto border-t border-slate-100 select-none">
      {/* Back Button */}
      <div>
        {!isFirstStep && (
          <button
            type="button"
            onClick={onBack}
            disabled={disableBack || isSubmitting}
            className="w-11 h-11 rounded-xl border border-slate-200 bg-slate-50 hover:bg-slate-100 text-slate-700 hover:text-slate-900 transition-all duration-150 flex items-center justify-center cursor-pointer shadow-2xs hover:shadow-xs disabled:opacity-50 disabled:cursor-not-allowed"
            aria-label="Go to previous step"
          >
            <ArrowLeft size={18} weight="bold" />
          </button>
        )}
      </div>

      {/* Next / Submit Button */}
      <button
        type="button"
        onClick={onNext}
        disabled={isSubmitting}
        className={`inline-flex items-center space-x-2 px-6 py-2.5 rounded-xl font-medium text-sm text-white transition-all duration-200 cursor-pointer shadow-md shadow-blue-500/15 disabled:opacity-50 disabled:cursor-not-allowed ${
          isLastStep
            ? 'bg-[#07569B] hover:bg-[#06457D] active:scale-[0.98]'
            : 'bg-[#0875D1] hover:bg-[#0764B5] active:scale-[0.98]'
        }`}
      >
        <span>
          {nextLabel || (isLastStep ? 'Submit for Verification' : 'Next')}
        </span>
        {isSubmitting ? (
          <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
        ) : isLastStep ? (
          <PaperPlaneTilt size={16} weight="bold" />
        ) : (
          <ArrowRight size={16} weight="bold" />
        )}
      </button>
    </div>
  );
};
