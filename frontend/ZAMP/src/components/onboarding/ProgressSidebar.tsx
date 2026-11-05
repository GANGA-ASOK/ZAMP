import type { FC, ComponentType } from 'react';
import {
  Buildings,
  User,
  Bank,
  FileText,
  Check,
} from '@phosphor-icons/react';

export interface StepItem {
  id: number;
  title: string;
  description: string;
  icon: ComponentType<{ size?: number; weight?: 'bold' | 'fill' | 'regular' | 'light'; className?: string }>;
}

export const STEPS: StepItem[] = [
  {
    id: 1,
    title: 'Company Information',
    description: "Company's basic information",
    icon: Buildings,
  },
  {
    id: 2,
    title: 'Contact Information',
    description: 'Primary & signatory details',
    icon: User,
  },
  {
    id: 3,
    title: 'Tax & Banking Details',
    description: 'Registration & payment info',
    icon: Bank,
  },
  {
    id: 4,
    title: 'Document Submission & Review',
    description: 'Required proofs & review',
    icon: FileText,
  },
];

interface ProgressSidebarProps {
  currentStep: number;
  onStepClick: (stepId: number) => void;
  completedSteps: number[];
}

export const ProgressSidebar: FC<ProgressSidebarProps> = ({
  currentStep,
  onStepClick,
  completedSteps,
}) => {
  return (
    <aside className="relative flex flex-col justify-between bg-[#07569B] text-white p-8 sm:p-10 lg:p-12 overflow-hidden select-none h-full min-h-screen lg:h-screen">
      {/* Decorative Geometric Outline Watermarks (matching reference image) */}
      <div className="pointer-events-none absolute -bottom-16 -left-16 w-80 h-80 opacity-15">
        <svg viewBox="0 0 200 200" fill="none" xmlns="http://www.w3.org/2000/svg" className="w-full h-full text-white stroke-current">
          <circle cx="100" cy="100" r="90" strokeWidth="1.5" />
          <circle cx="100" cy="100" r="60" strokeWidth="1.5" />
          <circle cx="10" cy="100" r="70" strokeWidth="1.5" />
          <circle cx="100" cy="190" r="70" strokeWidth="1.5" />
          <path d="M 10 100 Q 100 100 100 10" strokeWidth="1.5" />
          <path d="M 100 190 Q 100 100 190 100" strokeWidth="1.5" />
        </svg>
      </div>

      {/* Top Brand Header */}
      <div className="relative z-10 flex items-center space-x-3 mb-6 lg:mb-0">
        <div className="w-10 h-10 rounded-xl bg-white/10 backdrop-blur-xs border border-white/20 flex items-center justify-center text-white shadow-sm">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
            <circle cx="8" cy="12" r="6" fill="#38BDF8" fillOpacity="0.8" />
            <circle cx="16" cy="12" r="6" fill="#FFFFFF" fillOpacity="0.9" />
            <path d="M12 7.5C13.2 8.7 14 10.3 14 12C14 13.7 13.2 15.3 12 16.5C10.8 15.3 10 13.7 10 12C10 10.3 10.8 8.7 12 7.5Z" fill="#07569B" />
          </svg>
        </div>
        <span className="text-2xl font-bold tracking-tight text-white font-sans">
          VendorFlow
        </span>
      </div>

      {/* Middle: Vertical Step Progress List */}
      <nav aria-label="Registration Progress" className="relative z-10 my-auto py-6">
        <div className="space-y-8 relative">
          {STEPS.map((step, index) => {
            const isCurrent = step.id === currentStep;
            const isCompleted = completedSteps.includes(step.id);
            const isClickable = isCompleted || step.id <= currentStep;
            const IconComponent = step.icon;
            const isLast = index === STEPS.length - 1;

            return (
              <div key={step.id} className="relative flex items-start group">
                {/* Connecting Vertical Line linking bottom of node to top of next */}
                {!isLast && (
                  <div
                    className={`absolute left-5 top-10 w-0.5 h-8 transition-colors duration-300 ${
                      isCompleted ? 'bg-sky-400' : 'bg-white/20'
                    }`}
                  />
                )}

                {/* Step Node */}
                <button
                  type="button"
                  onClick={() => isClickable && onStepClick(step.id)}
                  disabled={!isClickable}
                  className={`relative z-10 flex items-start space-x-4 text-left transition-all duration-200 outline-hidden ${
                    isClickable ? 'cursor-pointer' : 'cursor-not-allowed opacity-60'
                  }`}
                >
                  {/* Circle Node Icon */}
                  <div
                    className={`w-10 h-10 rounded-full flex items-center justify-center transition-all duration-300 shrink-0 ${
                      isCurrent
                        ? 'bg-white text-[#07569B] shadow-lg shadow-black/20 ring-4 ring-white/30 scale-105'
                        : isCompleted
                        ? 'bg-sky-400 text-white shadow-xs'
                        : 'bg-white/10 text-white/70 border border-white/20'
                    }`}
                  >
                    {isCompleted ? (
                      <Check size={18} weight="bold" />
                    ) : (
                      <IconComponent
                        size={18}
                        weight={isCurrent ? 'bold' : 'regular'}
                      />
                    )}
                  </div>

                  {/* Step Details */}
                  <div className="pt-0.5 pr-2">
                    <p
                      className={`text-sm font-semibold transition-colors duration-200 ${
                        isCurrent
                          ? 'text-white'
                          : isCompleted
                          ? 'text-white/90 group-hover:text-white'
                          : 'text-white/60'
                      }`}
                    >
                      {step.title}
                    </p>
                    <p
                      className={`text-xs mt-0.5 transition-colors duration-200 ${
                        isCurrent
                          ? 'text-sky-200'
                          : isCompleted
                          ? 'text-sky-300/80'
                          : 'text-white/40'
                      }`}
                    >
                      {step.description}
                    </p>
                  </div>
                </button>
              </div>
            );
          })}
        </div>
      </nav>

      {/* Bottom Footer Copyright */}
      <div className="relative z-10 pt-6 mt-auto text-xs text-white/50 border-t border-white/10">
        <p>© 2026 VendorFlow. All rights reserved.</p>
      </div>
    </aside>
  );
};
