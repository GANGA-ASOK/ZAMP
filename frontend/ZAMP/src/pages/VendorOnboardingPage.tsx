import type { FC } from 'react';
import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { OnboardingLayout } from '../components/onboarding/OnboardingLayout';
import { StepHeader } from '../components/onboarding/StepHeader';
import { StepNavigation } from '../components/onboarding/StepNavigation';
import { Step1CompanyInfo } from '../forms/Step1CompanyInfo';
import { Step2ContactInfo } from '../forms/Step2ContactInfo';
import { Step3TaxBankingInfo } from '../forms/Step3TaxBankingInfo';
import { Step4DocumentSubmission } from '../forms/Step4DocumentSubmission';
import type {
  CompanyInformationData,
  ContactInformationData,
  DocumentSubmissionData,
  FormValidationErrors,
  SubmissionResult,
  TaxBankingInformationData,
  VendorFormData,
} from '../types/vendor';
import {
  validateStep1,
  validateStep2,
  validateStep3,
  validateStep4,
} from '../utils/validation';
import {
  clearDraftStorage,
  getDemoFormData,
  loadDraftFromStorage,
  saveDraftToStorage,
  saveSubmission,
} from '../utils/storage';
import { generateReferenceNumber } from '../utils/formatters';

const STEP_METADATA = [
  {
    number: 1,
    title: 'Tell us about your company',
    subtitle: "Let's start with some basic information about your organization.",
  },
  {
    number: 2,
    title: 'Who should we contact?',
    subtitle: 'Provide the details of the primary person responsible for this vendor relationship.',
  },
  {
    number: 3,
    title: 'Tax and banking information',
    subtitle: "Provide your company's tax registration and payment details.",
  },
  {
    number: 4,
    title: 'Upload your documents',
    subtitle: 'Submit the required documents to help us verify your organization.',
  },
];

export const VendorOnboardingPage: FC = () => {
  const navigate = useNavigate();

  // Central form state
  const [formData, setFormData] = useState<VendorFormData>(loadDraftFromStorage);
  const [currentStep, setCurrentStep] = useState<number>(1);
  const [completedSteps, setCompletedSteps] = useState<number[]>([]);
  const [errors, setErrors] = useState<FormValidationErrors>({});
  const [isSaved, setIsSaved] = useState<boolean>(true);
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);

  // Auto-save debounced effect
  useEffect(() => {
    setIsSaved(false);
    const timer = setTimeout(() => {
      saveDraftToStorage(formData);
      setIsSaved(true);
    }, 400);

    return () => clearTimeout(timer);
  }, [formData]);

  // Field change handlers for each section
  const handleCompanyChange = useCallback(
    (field: keyof CompanyInformationData, value: unknown) => {
      setFormData((prev) => ({
        ...prev,
        company: { ...prev.company, [field]: value },
      }));
      if (errors[field as string]) {
        setErrors((prev) => {
          const next = { ...prev };
          delete next[field as string];
          return next;
        });
      }
    },
    [errors]
  );

  const handleContactChange = useCallback(
    (field: keyof ContactInformationData, value: unknown) => {
      setFormData((prev) => ({
        ...prev,
        contact: { ...prev.contact, [field]: value },
      }));
      if (errors[field as string]) {
        setErrors((prev) => {
          const next = { ...prev };
          delete next[field as string];
          return next;
        });
      }
    },
    [errors]
  );

  const handleTaxBankingChange = useCallback(
    (field: keyof TaxBankingInformationData, value: unknown) => {
      setFormData((prev) => ({
        ...prev,
        taxBanking: { ...prev.taxBanking, [field]: value },
      }));
      if (errors[field as string]) {
        setErrors((prev) => {
          const next = { ...prev };
          delete next[field as string];
          return next;
        });
      }
    },
    [errors]
  );

  const handleDocumentsChange = useCallback(
    (field: keyof DocumentSubmissionData, value: unknown) => {
      setFormData((prev) => ({
        ...prev,
        documents: { ...prev.documents, [field]: value },
      }));
      if (errors[field as string]) {
        setErrors((prev) => {
          const next = { ...prev };
          delete next[field as string];
          return next;
        });
      }
    },
    [errors]
  );

  // Quick Demo Pre-fill for reviewers & testers
  const handleFillDemoData = () => {
    const demoData = getDemoFormData();
    setFormData(demoData);
    setErrors({});
    setCompletedSteps([1, 2, 3]);
  };

  // Step validation
  const validateCurrentStep = (step: number): boolean => {
    let stepErrors: FormValidationErrors = {};

    if (step === 1) {
      stepErrors = validateStep1(formData.company);
    } else if (step === 2) {
      stepErrors = validateStep2(formData.contact);
    } else if (step === 3) {
      stepErrors = validateStep3(formData.taxBanking);
    } else if (step === 4) {
      stepErrors = validateStep4(
        formData.documents,
        formData.company.businessEntityType,
        formData.taxBanking.gstStatus
      );
    }

    setErrors(stepErrors);
    return Object.keys(stepErrors).length === 0;
  };

  // Navigation handlers
  const handleNext = () => {
    const isValid = validateCurrentStep(currentStep);
    if (!isValid) {
      window.scrollTo({ top: 0, behavior: 'smooth' });
      return;
    }

    if (!completedSteps.includes(currentStep)) {
      setCompletedSteps((prev) => [...prev, currentStep]);
    }

    if (currentStep < 4) {
      setCurrentStep((prev) => prev + 1);
      setErrors({});
      window.scrollTo({ top: 0, behavior: 'smooth' });
    } else {
      handleSubmit();
    }
  };

  const handleBack = () => {
    if (currentStep > 1) {
      setCurrentStep((prev) => prev - 1);
      setErrors({});
      window.scrollTo({ top: 0, behavior: 'smooth' });
    }
  };

  const handleStepClick = (stepId: number) => {
    if (completedSteps.includes(stepId) || stepId <= currentStep) {
      setCurrentStep(stepId);
      setErrors({});
      window.scrollTo({ top: 0, behavior: 'smooth' });
    }
  };

  const handleSubmit = () => {
    const step1Errors = validateStep1(formData.company);
    const step2Errors = validateStep2(formData.contact);
    const step3Errors = validateStep3(formData.taxBanking);
    const step4Errors = validateStep4(
      formData.documents,
      formData.company.businessEntityType,
      formData.taxBanking.gstStatus
    );

    const allErrors = {
      ...step1Errors,
      ...step2Errors,
      ...step3Errors,
      ...step4Errors,
    };

    if (Object.keys(allErrors).length > 0) {
      setErrors(allErrors);
      if (Object.keys(step1Errors).length > 0) setCurrentStep(1);
      else if (Object.keys(step2Errors).length > 0) setCurrentStep(2);
      else if (Object.keys(step3Errors).length > 0) setCurrentStep(3);
      else setCurrentStep(4);
      return;
    }

    setIsSubmitting(true);

    setTimeout(() => {
      const referenceNumber = generateReferenceNumber();
      const submissionResult: SubmissionResult = {
        referenceNumber,
        submittedAt: new Date().toLocaleDateString('en-US', {
          month: 'short',
          day: 'numeric',
          year: 'numeric',
          hour: '2-digit',
          minute: '2-digit',
        }),
        status: 'Queued for Verification',
        companyName: formData.company.legalCompanyName,
        primaryContactEmail: formData.contact.primaryEmail,
        formData,
      };

      saveSubmission(submissionResult);
      clearDraftStorage();
      setIsSubmitting(false);

      navigate('/submission-success', {
        state: { submission: submissionResult },
      });
    }, 700);
  };

  const currentMeta = STEP_METADATA[currentStep - 1];

  return (
    <OnboardingLayout
      currentStep={currentStep}
      onStepClick={handleStepClick}
      completedSteps={completedSteps}
    >
      <StepHeader
        stepNumber={currentStep}
        totalSteps={4}
        title={currentMeta.title}
        subtitle={currentMeta.subtitle}
        isSaved={isSaved}
        onFillDemo={handleFillDemoData}
      />

      {/* Dynamic Form Step */}
      <div className="flex-1 mb-6">
        {currentStep === 1 && (
          <Step1CompanyInfo
            data={formData.company}
            errors={errors}
            onChange={handleCompanyChange}
          />
        )}

        {currentStep === 2 && (
          <Step2ContactInfo
            data={formData.contact}
            errors={errors}
            onChange={handleContactChange}
          />
        )}

        {currentStep === 3 && (
          <Step3TaxBankingInfo
            data={formData.taxBanking}
            errors={errors}
            onChange={handleTaxBankingChange}
          />
        )}

        {currentStep === 4 && (
          <Step4DocumentSubmission
            formData={formData}
            errors={errors}
            onChange={handleDocumentsChange}
            onEditStep={(step) => {
              setCurrentStep(step);
              window.scrollTo({ top: 0, behavior: 'smooth' });
            }}
          />
        )}
      </div>

      {/* Navigation Buttons */}
      <StepNavigation
        currentStep={currentStep}
        totalSteps={4}
        onBack={handleBack}
        onNext={handleNext}
        isSubmitting={isSubmitting}
      />
    </OnboardingLayout>
  );
};
