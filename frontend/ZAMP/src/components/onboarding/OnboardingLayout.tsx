import type { FC, ReactNode } from 'react';
import { ProgressSidebar } from './ProgressSidebar';

interface OnboardingLayoutProps {
  currentStep: number;
  onStepClick: (stepId: number) => void;
  completedSteps: number[];
  headerRight?: ReactNode;
  children: ReactNode;
}

export const OnboardingLayout: FC<OnboardingLayoutProps> = ({
  currentStep,
  onStepClick,
  completedSteps,
  headerRight,
  children,
}) => {
  return (
    <div className="min-h-screen w-full bg-canvas font-sans antialiased text-ink p-3 sm:p-5 lg:p-6">
      <div className="mx-auto max-w-[1400px] flex flex-col lg:flex-row gap-3 sm:gap-5 lg:gap-6">
        {/* Progress card */}
        <div className="w-full lg:w-[340px] xl:w-[380px] shrink-0 lg:sticky lg:top-6 lg:h-[calc(100vh-3rem)]">
          <ProgressSidebar currentStep={currentStep} onStepClick={onStepClick} completedSteps={completedSteps} />
        </div>

        {/* Workspace card */}
        <main className="flex-1 min-w-0 min-h-[calc(100vh-3rem)] flex flex-col rounded-[36px] bg-white p-5 sm:p-9 lg:p-12 animate-rise">
          {headerRight && (
            <div className="w-full max-w-3xl mx-auto mb-7 flex flex-wrap items-center justify-between gap-3 rounded-[24px] bg-paper px-4 py-3">
              {headerRight}
            </div>
          )}
          <div className="w-full max-w-3xl mx-auto flex-1 flex flex-col justify-between">{children}</div>
        </main>
      </div>
    </div>
  );
};
