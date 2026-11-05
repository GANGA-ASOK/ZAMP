import type { FC, ReactNode } from 'react';
import { ProgressSidebar } from './ProgressSidebar';

interface OnboardingLayoutProps {
  currentStep: number;
  onStepClick: (stepId: number) => void;
  completedSteps: number[];
  children: ReactNode;
}

export const OnboardingLayout: FC<OnboardingLayoutProps> = ({
  currentStep,
  onStepClick,
  completedSteps,
  children,
}) => {
  return (
    <div className="min-h-screen w-full flex flex-col lg:flex-row bg-white font-sans antialiased text-slate-800">
      {/* Left Sidebar Partition - Full Height & Sticky in Viewport */}
      <div className="w-full lg:w-[380px] xl:w-[420px] shrink-0 bg-[#07569B] lg:sticky lg:top-0 lg:h-screen z-20 shadow-xl shadow-blue-950/10">
        <ProgressSidebar
          currentStep={currentStep}
          onStepClick={onStepClick}
          completedSteps={completedSteps}
        />
      </div>

      {/* Right Form Workspace Partition - Full Screen View */}
      <main className="flex-1 min-h-screen flex flex-col justify-between relative bg-white p-6 sm:p-10 lg:p-14 xl:p-16 overflow-x-hidden">
        {/* Subtle Decorative Geometric Arcs on right edge (matching reference image) */}
        <div className="pointer-events-none absolute top-10 right-0 w-80 h-80 opacity-[0.05]">
          <svg viewBox="0 0 200 200" fill="none" xmlns="http://www.w3.org/2000/svg" className="w-full h-full text-slate-900 stroke-current">
            <circle cx="160" cy="40" r="90" strokeWidth="2" />
            <circle cx="160" cy="40" r="50" strokeWidth="2" />
            <path d="M 70 40 Q 160 40 160 130" strokeWidth="2" />
            <path d="M 160 130 Q 160 220 250 220" strokeWidth="2" />
          </svg>
        </div>

        <div className="relative z-10 w-full max-w-3xl mx-auto flex-1 flex flex-col justify-between">
          {children}
        </div>
      </main>
    </div>
  );
};
