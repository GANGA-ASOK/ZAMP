import type { FC } from 'react';
import { useState, useEffect, useCallback, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  WarningCircle,
  ArrowRight,
  X,
  Target,
  CheckCircle,
  XCircle,
  Clock,
  ShieldCheck,
  FilePdf,
} from '@phosphor-icons/react';
import { OnboardingLayout } from '../components/onboarding/OnboardingLayout';
import { StepHeader } from '../components/onboarding/StepHeader';
import { StepNavigation } from '../components/onboarding/StepNavigation';
import { Step1CompanyInfo } from '../forms/Step1CompanyInfo';
import { Step2ContactInfo } from '../forms/Step2ContactInfo';
import { Step3TaxBankingInfo } from '../forms/Step3TaxBankingInfo';
import { Step4DocumentSubmission } from '../forms/Step4DocumentSubmission';
import { NotificationDrawer } from '../components/workflow/NotificationDrawer';
import { VendorClarificationSection } from '../components/workflow/VendorClarificationSection';
import { ActivityTimeline } from '../components/workflow/ActivityTimeline';
import { VendorDocumentManager } from '../components/documents/VendorDocumentManager';
import { TestCasePicker } from '../components/onboarding/TestCasePicker';
import { prefillTestCase, toVendorFormData, type TestCase } from '../services/testCaseService';
import {
  getVendorClarifications,
  getVendorApplicationActivity,
  type ClarificationItem,
  type ActivityEvent,
} from '../services/workflowService';
import type {
  CompanyInformationData,
  ContactInformationData,
  DocumentSubmissionData,
  FormValidationErrors,
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
  loadDraftFromStorage,
  loadVendorId,
  saveDraftToStorage,
  saveSubmission,
  saveVendorId,
} from '../utils/storage';
import {
  buildCompanyInfoPayload,
  buildContactInfoPayload,
  buildTaxDetailsPayload,
  buildBankingDetailsPayload,
  createVendorDraft,
  getVendor,
  patchVendor,
  submitVendor,
  extractErrorMessage,
  extractSubmissionErrors,
  scrollToAndFocusField,
  getFieldStep,
  FIELD_LABELS,
} from '../services/vendorService';

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

type SaveState = 'idle' | 'saving' | 'saved' | 'error';

interface MissingFieldItem {
  key: string;
  label: string;
  step: number;
  reason: string;
}

interface ValidationBannerState {
  summary: string;
  missingFields: MissingFieldItem[];
  activeFieldKey?: string;
}

export const VendorOnboardingPage: FC = () => {
  const navigate = useNavigate();

  // -------------------------------------------------------------------------
  // State
  // -------------------------------------------------------------------------

  const [formData, setFormData] = useState<VendorFormData>(loadDraftFromStorage);
  const [currentStep, setCurrentStep] = useState<number>(1);
  const [completedSteps, setCompletedSteps] = useState<number[]>([]);
  const [errors, setErrors] = useState<FormValidationErrors>({});
  const [saveState, setSaveState] = useState<SaveState>('idle');
  const [saveError, setSaveError] = useState<string>('');
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [backendUnavailable, setBackendUnavailable] = useState<boolean>(false);

  // Rich validation banner state
  const [validationBanner, setValidationBanner] = useState<ValidationBannerState | null>(null);

  const [vendorId, setVendorId] = useState<string | null>(loadVendorId);
  const isCreatingDraft = useRef(false);

  // Phase 9: Workflow Lifecycle States
  const [applicationStatus, setApplicationStatus] = useState<string>('draft');
  const [referenceNumber, setReferenceNumber] = useState<string>('');
  const [rejectionReason, setRejectionReason] = useState<string>('');
  const [clarifications, setClarifications] = useState<ClarificationItem[]>([]);
  const [activity, setActivity] = useState<ActivityEvent[]>([]);
  const [showTimeline, setShowTimeline] = useState<boolean>(false);
  const [activeView, setActiveView] = useState<'form' | 'documents'>('form');

  // -------------------------------------------------------------------------
  // Restore from backend on mount & sync lifecycle
  // -------------------------------------------------------------------------

  const syncWorkflowState = useCallback(async (id: string) => {
    try {
      const v = await getVendor(id);
      setVendorId(id);
      setBackendUnavailable(false);
      if (v.status) setApplicationStatus(v.status);
      if (v.reference_number) setReferenceNumber(v.reference_number);
      if ((v as any).rejection_reason) setRejectionReason((v as any).rejection_reason);

      // Fetch clarifications and activity in parallel
      const [cList, aList] = await Promise.all([
        getVendorClarifications(id).catch(() => []),
        getVendorApplicationActivity(id).catch(() => []),
      ]);
      setClarifications(cList);
      setActivity(aList);
    } catch {
      setBackendUnavailable(true);
    }
  }, []);

  useEffect(() => {
    const storedId = loadVendorId();
    if (!storedId) return;
    syncWorkflowState(storedId);
  }, [syncWorkflowState]);

  // -------------------------------------------------------------------------
  // Auto-save to localStorage
  // -------------------------------------------------------------------------

  const saveTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    if (saveTimerRef.current) clearTimeout(saveTimerRef.current);
    setSaveState('saving');

    saveTimerRef.current = setTimeout(() => {
      saveDraftToStorage(formData);
      setSaveState('saved');
      setTimeout(() => setSaveState('idle'), 2000);
    }, 500);

    return () => {
      if (saveTimerRef.current) clearTimeout(saveTimerRef.current);
    };
  }, [formData]);

  // -------------------------------------------------------------------------
  // Ensure vendor exists on backend
  // -------------------------------------------------------------------------

  const ensureVendorExists = useCallback(async (): Promise<string | null> => {
    if (vendorId) return vendorId;
    if (isCreatingDraft.current) return null;

    isCreatingDraft.current = true;
    try {
      const created = await createVendorDraft();
      saveVendorId(created.id);
      setVendorId(created.id);
      setBackendUnavailable(false);
      return created.id;
    } catch (err) {
      console.warn('[VendorFlow] Backend unavailable, working in offline mode:', err);
      setBackendUnavailable(true);
      return null;
    } finally {
      isCreatingDraft.current = false;
    }
  }, [vendorId]);

  // -------------------------------------------------------------------------
  // Save step to backend
  // -------------------------------------------------------------------------

  const saveStepToBackend = useCallback(
    async (step: number, currentFormData: VendorFormData): Promise<void> => {
      const id = await ensureVendorExists();
      if (!id) return;

      let payload: Record<string, unknown> = {};

      if (step === 1) {
        payload = buildCompanyInfoPayload(currentFormData.company);
      } else if (step === 2) {
        payload = buildContactInfoPayload(currentFormData.contact);
      } else if (step === 3) {
        payload = {
          ...buildTaxDetailsPayload(currentFormData.taxBanking),
          ...buildBankingDetailsPayload(currentFormData.taxBanking),
        };
      }

      if (Object.keys(payload).length === 0) return;

      setSaveState('saving');
      setSaveError('');
      try {
        await patchVendor(id, payload);
        setSaveState('saved');
        setTimeout(() => setSaveState('idle'), 2000);
      } catch (err) {
        const msg = extractErrorMessage(err, 'Failed to save to server');
        setSaveState('error');
        setSaveError(msg);
      }
    },
    [ensureVendorExists]
  );

  // -------------------------------------------------------------------------
  // Field change handlers
  // -------------------------------------------------------------------------

  const handleCompanyChange = useCallback(
    (field: keyof CompanyInformationData, value: unknown) => {
      setFormData((prev) => ({
        ...prev,
        company: { ...prev.company, [field]: value },
      }));
      if (errors[field as string]) {
        setErrors((prev) => { const n = { ...prev }; delete n[field as string]; return n; });
      }
      if (validationBanner?.activeFieldKey === field) {
        setValidationBanner(null);
      }
    },
    [errors, validationBanner]
  );

  const handleContactChange = useCallback(
    (field: keyof ContactInformationData, value: unknown) => {
      setFormData((prev) => ({
        ...prev,
        contact: { ...prev.contact, [field]: value },
      }));
      if (errors[field as string]) {
        setErrors((prev) => { const n = { ...prev }; delete n[field as string]; return n; });
      }
      if (validationBanner?.activeFieldKey === field) {
        setValidationBanner(null);
      }
    },
    [errors, validationBanner]
  );

  const handleTaxBankingChange = useCallback(
    (field: keyof TaxBankingInformationData, value: unknown) => {
      setFormData((prev) => ({
        ...prev,
        taxBanking: { ...prev.taxBanking, [field]: value },
      }));
      if (errors[field as string]) {
        setErrors((prev) => { const n = { ...prev }; delete n[field as string]; return n; });
      }
      if (validationBanner?.activeFieldKey === field) {
        setValidationBanner(null);
      }
    },
    [errors, validationBanner]
  );

  const handleDocumentsChange = useCallback(
    (field: keyof DocumentSubmissionData, value: unknown) => {
      setFormData((prev) => ({
        ...prev,
        documents: { ...prev.documents, [field]: value },
      }));
      if (errors[field as string]) {
        setErrors((prev) => { const n = { ...prev }; delete n[field as string]; return n; });
      }
      if (validationBanner?.activeFieldKey === field) {
        setValidationBanner(null);
      }
    },
    [errors, validationBanner]
  );

  // -------------------------------------------------------------------------
  // Demo fill
  // -------------------------------------------------------------------------

  // Load a test case: fresh draft vendor on the backend with the case's form
  // data saved and documents uploaded, then fill every step locally.
  const handleLoadTestCase = async (testCase: TestCase) => {
    const result = await prefillTestCase(testCase.key);
    saveVendorId(result.vendor_id);
    setVendorId(result.vendor_id);
    setBackendUnavailable(false);
    setFormData(toVendorFormData(result));
    setApplicationStatus('draft');
    setReferenceNumber(result.reference_number);
    setRejectionReason('');
    setClarifications([]);
    setActivity([]);
    setActiveView('form');
    setErrors({});
    setValidationBanner(null);
    setCompletedSteps([1, 2, 3]);
    setCurrentStep(1);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  // -------------------------------------------------------------------------
  // Handle validation failures (Auto-switch step, scroll to field, focus, show reason)
  // -------------------------------------------------------------------------

  const handleValidationFailure = useCallback(
    (
      fieldErrors: FormValidationErrors,
      summary = 'Cannot submit incomplete vendor registration. Missing or invalid required fields.'
    ) => {
      setErrors(fieldErrors);

      const keys = Object.keys(fieldErrors);
      if (keys.length === 0) return;

      // Sort by step order (1 -> 4) to always land on the first missing entry
      keys.sort((a, b) => getFieldStep(a) - getFieldStep(b));
      const firstKey = keys[0];
      const targetStep = getFieldStep(firstKey);

      // Auto-switch to the step with the first missing field
      setCurrentStep(targetStep);

      // Smooth scroll and focus the field
      scrollToAndFocusField(firstKey);

      // Populate rich validation banner
      setValidationBanner({
        summary,
        missingFields: keys.map((k) => ({
          key: k,
          label: FIELD_LABELS[k] || k,
          step: getFieldStep(k),
          reason: fieldErrors[k] || 'This field is required',
        })),
        activeFieldKey: firstKey,
      });
    },
    []
  );

  // -------------------------------------------------------------------------
  // Jump to specific field when clicked from banner
  // -------------------------------------------------------------------------

  const handleJumpToField = (fieldKey: string, stepNumber: number) => {
    setCurrentStep(stepNumber);
    scrollToAndFocusField(fieldKey);
    setValidationBanner((prev) => (prev ? { ...prev, activeFieldKey: fieldKey } : null));
  };

  // -------------------------------------------------------------------------
  // Navigation
  // -------------------------------------------------------------------------

  const handleNext = async () => {
    setValidationBanner(null);

    let stepErrors: FormValidationErrors = {};
    if (currentStep === 1) stepErrors = validateStep1(formData.company);
    else if (currentStep === 2) stepErrors = validateStep2(formData.contact);
    else if (currentStep === 3) stepErrors = validateStep3(formData.taxBanking);
    else if (currentStep === 4) {
      stepErrors = validateStep4(
        formData.documents,
        formData.company.businessEntityType,
        formData.taxBanking.gstStatus
      );
    }

    if (Object.keys(stepErrors).length > 0) {
      handleValidationFailure(
        stepErrors,
        `Please complete the required fields in Step ${currentStep} to continue.`
      );
      return;
    }

    // Save step to backend asynchronously
    if (currentStep < 4) {
      saveStepToBackend(currentStep, formData).catch(() => {});
    }

    if (!completedSteps.includes(currentStep)) {
      setCompletedSteps((prev) => [...prev, currentStep]);
    }

    if (currentStep < 4) {
      setCurrentStep((prev) => prev + 1);
      setErrors({});
      window.scrollTo({ top: 0, behavior: 'smooth' });
    } else {
      await handleSubmit();
    }
  };

  const handleBack = () => {
    if (currentStep > 1) {
      setCurrentStep((prev) => prev - 1);
      setErrors({});
      setValidationBanner(null);
      window.scrollTo({ top: 0, behavior: 'smooth' });
    }
  };

  const handleStepClick = (stepId: number) => {
    if (completedSteps.includes(stepId) || stepId <= currentStep) {
      setCurrentStep(stepId);
      setErrors({});
      setValidationBanner(null);
      window.scrollTo({ top: 0, behavior: 'smooth' });
    }
  };

  // -------------------------------------------------------------------------
  // Final submission
  // -------------------------------------------------------------------------

  const handleSubmit = async () => {
    setValidationBanner(null);

    // Full client-side check across all 4 steps
    const step1Errors = validateStep1(formData.company);
    const step2Errors = validateStep2(formData.contact);
    const step3Errors = validateStep3(formData.taxBanking);
    const step4Errors = validateStep4(
      formData.documents,
      formData.company.businessEntityType,
      formData.taxBanking.gstStatus
    );

    const allErrors = { ...step1Errors, ...step2Errors, ...step3Errors, ...step4Errors };

    if (Object.keys(allErrors).length > 0) {
      handleValidationFailure(allErrors);
      return;
    }

    setIsSubmitting(true);

    try {
      const id = await ensureVendorExists();

      if (id) {
        // Atomic single PATCH updating all sections together
        const fullPayload = {
          ...buildCompanyInfoPayload(formData.company),
          ...buildContactInfoPayload(formData.contact),
          ...buildTaxDetailsPayload(formData.taxBanking),
          ...buildBankingDetailsPayload(formData.taxBanking),
          declarations: {
            confirm_accurate: formData.documents.confirmAccurate,
            authorize_verification: formData.documents.authorizeVerification,
            agree_terms: formData.documents.agreeTerms,
          },
        };

        await patchVendor(id, fullPayload);

        // Submit on backend
        const result = await submitVendor(id);

        const submissionResult = {
          referenceNumber: result.reference_number,
          submittedAt: new Date(result.submitted_at).toLocaleDateString('en-US', {
            month: 'short',
            day: 'numeric',
            year: 'numeric',
            hour: '2-digit',
            minute: '2-digit',
          }),
          status: 'Queued for Verification' as const,
          companyName: formData.company.legalCompanyName,
          primaryContactEmail: formData.contact.primaryEmail,
          formData,
        };

        saveSubmission(submissionResult);
        clearDraftStorage();
        setIsSubmitting(false);
        navigate('/submission-success', { state: { submission: submissionResult } });
      } else {
        // Offline fallback
        const submissionResult = {
          referenceNumber: `VND-${new Date().getFullYear()}-${Math.floor(10000 + Math.random() * 90000)}`,
          submittedAt: new Date().toLocaleDateString('en-US', {
            month: 'short', day: 'numeric', year: 'numeric', hour: '2-digit', minute: '2-digit',
          }),
          status: 'Queued for Verification' as const,
          companyName: formData.company.legalCompanyName,
          primaryContactEmail: formData.contact.primaryEmail,
          formData,
        };
        saveSubmission(submissionResult);
        clearDraftStorage();
        setIsSubmitting(false);
        navigate('/submission-success', { state: { submission: submissionResult } });
      }
    } catch (err) {
      setIsSubmitting(false);
      const parsed = extractSubmissionErrors(err);

      if (Object.keys(parsed.fieldErrors).length > 0) {
        handleValidationFailure(parsed.fieldErrors, parsed.summary);
      } else {
        setValidationBanner({
          summary: parsed.summary,
          missingFields: [],
        });
        window.scrollTo({ top: 0, behavior: 'smooth' });
      }
    }
  };

  const isSaved = saveState === 'saved' || saveState === 'idle';
  const currentMeta = STEP_METADATA[currentStep - 1];

  // Active missing field in banner
  const activeMissingField = validationBanner?.missingFields.find(
    (f) => f.key === validationBanner.activeFieldKey
  ) || validationBanner?.missingFields[0];

  const getStatusBadgeStyle = (status: string) => {
    switch (status?.toLowerCase()) {
      case 'approved':
        return 'bg-emerald-50 text-emerald-700 border-emerald-200';
      case 'rejected':
        return 'bg-rose-50 text-rose-700 border-rose-200';
      case 'clarification_required':
        return 'bg-amber-50 text-amber-800 border-amber-300';
      case 'resubmitted':
        return 'bg-indigo-50 text-indigo-700 border-indigo-200';
      case 'under_review':
        return 'bg-blue-50 text-blue-700 border-blue-200';
      case 'submitted':
        return 'bg-sky-50 text-sky-700 border-sky-200';
      default:
        return 'bg-slate-100 text-slate-600 border-slate-200';
    }
  };

  const headerRight = (
    <div className="w-full flex items-center justify-between gap-3 text-xs">
      <div className="flex items-center space-x-2">
        <span className="font-mono text-[11px] font-semibold text-[#1F211F] bg-blue-50 px-2.5 py-1 rounded-lg border border-blue-100">
          {referenceNumber || 'DRAFT REGISTRATION'}
        </span>
        <span
          className={`px-2.5 py-1 rounded-full text-[10px] font-semibold uppercase tracking-wider border inline-flex items-center space-x-1 ${getStatusBadgeStyle(
            applicationStatus
          )}`}
        >
          <span>{applicationStatus.replace(/_/g, ' ')}</span>
        </span>
      </div>

      <div className="flex items-center space-x-2">
        {/* Toggle Documents Hub Button */}
        {vendorId && (
          <button
            type="button"
            onClick={() => setActiveView((prev) => (prev === 'documents' ? 'form' : 'documents'))}
            className={`px-3 py-1.5 rounded-xl border text-xs font-semibold cursor-pointer flex items-center space-x-1.5 transition-colors ${
              activeView === 'documents'
                ? 'bg-[#1F211F] text-white border-[#1F211F]'
                : 'border-slate-200 bg-white hover:bg-slate-50 text-slate-700'
            }`}
          >
            <FilePdf size={14} weight="bold" />
            <span>{activeView === 'documents' ? 'Registration Form' : 'Documents & AI Hub'}</span>
          </button>
        )}

        {/* Toggle Timeline Button */}
        {activity.length > 0 && (
          <button
            type="button"
            onClick={() => setShowTimeline((prev) => !prev)}
            className="px-2.5 py-1.5 rounded-xl border border-slate-200 bg-slate-50 hover:bg-slate-100 text-slate-700 text-xs font-semibold cursor-pointer flex items-center space-x-1"
          >
            <Clock size={13} weight="bold" />
            <span>{showTimeline ? 'Hide History' : 'View History'}</span>
          </button>
        )}

        {/* Vendor In-App Notifications */}
        <NotificationDrawer recipientType="vendor" vendorId={vendorId} />

        {/* Admin Portal Shortcut */}
        <button
          type="button"
          onClick={() => navigate('/admin')}
          className="px-3 py-1.5 rounded-xl border border-slate-200 hover:border-slate-300 bg-white hover:bg-slate-50 text-slate-700 text-xs font-semibold cursor-pointer flex items-center space-x-1"
        >
          <ShieldCheck size={14} weight="bold" className="text-[#1F211F]" />
          <span>Admin Portal</span>
        </button>
      </div>
    </div>
  );

  return (
    <OnboardingLayout
      currentStep={currentStep}
      onStepClick={handleStepClick}
      completedSteps={completedSteps}
      headerRight={headerRight}
    >
      {/* Activity Timeline Drawer / Expansion */}
      {showTimeline && (
        <div className="mb-6 bg-white border border-slate-200 rounded-[32px] p-6 animate-fadeIn text-left">
          <div className="flex items-center justify-between border-b border-slate-100 pb-3 mb-4">
            <div className="flex items-center space-x-2">
              <Clock size={18} weight="bold" className="text-[#1F211F]" />
              <h3 className="text-sm font-semibold text-slate-900">Application Progression History</h3>
            </div>
            <button
              type="button"
              onClick={() => setShowTimeline(false)}
              className="text-slate-400 hover:text-slate-600 text-xs font-semibold cursor-pointer"
            >
              ✕
            </button>
          </div>
          <ActivityTimeline events={activity} />
        </div>
      )}

      {/* APPROVED BANNER */}
      {applicationStatus === 'approved' && (
        <div className="mb-6 bg-emerald-50 border border-emerald-200/90 rounded-[32px] p-6 shadow-sm text-left flex items-start space-x-4">
          <div className="w-12 h-12 rounded-2xl bg-emerald-100 text-emerald-600 flex items-center justify-center shrink-0">
            <CheckCircle size={28} weight="fill" />
          </div>
          <div>
            <h3 className="text-base font-semibold text-emerald-950">Application Approved!</h3>
            <p className="text-xs text-emerald-800 mt-1 leading-relaxed">
              Your vendor registration has completed compliance checks and is officially approved. Welcome to the ZAMP Vendor Network.
            </p>
          </div>
        </div>
      )}

      {/* REJECTED BANNER */}
      {applicationStatus === 'rejected' && (
        <div className="mb-6 bg-rose-50 border border-rose-200/90 rounded-[32px] p-6 shadow-sm text-left flex items-start space-x-4">
          <div className="w-12 h-12 rounded-2xl bg-rose-100 text-rose-600 flex items-center justify-center shrink-0">
            <XCircle size={28} weight="fill" />
          </div>
          <div>
            <h3 className="text-base font-semibold text-rose-950">Application Rejected</h3>
            <p className="text-xs text-rose-800 mt-1 leading-relaxed">
              Unfortunately, your onboarding application was not approved during administrative review.
            </p>
            {rejectionReason && (
              <div className="mt-2 p-3 rounded-xl bg-white border border-rose-200/70 text-xs text-rose-900">
                <span className="font-semibold block text-[10px] uppercase text-rose-500">Reason Provided:</span>
                <p className="mt-0.5">{rejectionReason}</p>
              </div>
            )}
          </div>
        </div>
      )}

      {/* CLARIFICATION REQUIRED WORKFLOW SECTION */}
      {applicationStatus === 'clarification_required' && vendorId && (
        <div className="mb-8">
          <VendorClarificationSection
            vendorId={vendorId}
            clarifications={clarifications}
            onClarificationUpdated={() => syncWorkflowState(vendorId)}
            onApplicationResubmitted={() => syncWorkflowState(vendorId)}
          />
        </div>
      )}

      {/* UNDER REVIEW / SUBMITTED BANNER */}
      {(applicationStatus === 'submitted' || applicationStatus === 'under_review' || applicationStatus === 'resubmitted') && (
        <div className="mb-6 bg-blue-50/70 border border-blue-200/80 rounded-[32px] p-5 shadow-xs text-left flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="w-9 h-9 rounded-xl bg-blue-100 text-[#1F211F] flex items-center justify-center shrink-0">
              <Clock size={20} weight="bold" />
            </div>
            <div>
              <h4 className="text-xs font-semibold text-slate-900 capitalize">
                Application Status: {applicationStatus.replace(/_/g, ' ')}
              </h4>
              <p className="text-[11px] text-slate-500 mt-0.5">
                Your application is in the verification pipeline. You will be notified of any clarification requests or approval updates.
              </p>
            </div>
          </div>

          <button
            type="button"
            onClick={() => vendorId && syncWorkflowState(vendorId)}
            className="px-3 py-1.5 rounded-xl border border-blue-200 bg-white hover:bg-slate-50 text-[#1F211F] text-xs font-semibold cursor-pointer shrink-0"
          >
            Check Status
          </button>
        </div>
      )}
      {/* Backend unavailable banner */}
      {backendUnavailable && (
        <div className="mb-4 px-4 py-2.5 rounded-xl bg-amber-50 border border-amber-200 text-amber-800 text-xs font-medium flex items-center space-x-2">
          <span>⚠️</span>
          <span>
            Backend server is not reachable. Your data is being saved locally.
            Connect to the backend and refresh to sync.
          </span>
        </div>
      )}

      {/* Prominent Validation / Missing Fields Banner */}
      {validationBanner && (
        <div className="mb-6 rounded-2xl bg-red-50 border border-red-200/90 p-4 sm:p-5 shadow-xs animate-fadeIn text-left">
          <div className="flex items-start justify-between">
            <div className="flex items-start space-x-3">
              <div className="w-8 h-8 rounded-xl bg-red-100 text-red-600 flex items-center justify-center shrink-0 mt-0.5">
                <WarningCircle size={20} weight="fill" />
              </div>
              <div>
                <h3 className="text-sm font-semibold text-red-800">
                  {validationBanner.summary}
                </h3>
                {activeMissingField && (
                  <p className="text-xs text-red-600 mt-1">
                    <span className="font-semibold">Step {activeMissingField.step} • {activeMissingField.label}:</span>{' '}
                    <span>{activeMissingField.reason}</span>
                  </p>
                )}
              </div>
            </div>

            <div className="flex items-center space-x-2 shrink-0 ml-3">
              {activeMissingField && (
                <button
                  type="button"
                  onClick={() => handleJumpToField(activeMissingField.key, activeMissingField.step)}
                  className="inline-flex items-center space-x-1.5 px-3 py-1.5 rounded-xl bg-red-600 hover:bg-red-700 text-white text-xs font-semibold shadow-xs transition-colors cursor-pointer"
                >
                  <Target size={14} weight="bold" />
                  <span>Go to Field</span>
                </button>
              )}
              <button
                type="button"
                onClick={() => setValidationBanner(null)}
                className="p-1 rounded-lg text-red-400 hover:text-red-700 hover:bg-red-100/50 transition-colors cursor-pointer"
                aria-label="Dismiss error banner"
              >
                <X size={16} weight="bold" />
              </button>
            </div>
          </div>

          {/* Clickable pill badges for all remaining missing fields */}
          {validationBanner.missingFields.length > 1 && (
            <div className="mt-3.5 pt-3 border-t border-red-200/70">
              <p className="text-[11px] font-semibold uppercase tracking-wider text-red-600 mb-2">
                All missing or incomplete fields ({validationBanner.missingFields.length}):
              </p>
              <div className="flex flex-wrap gap-2">
                {validationBanner.missingFields.map((item) => {
                  const isActive = validationBanner.activeFieldKey === item.key;
                  return (
                    <button
                      key={item.key}
                      type="button"
                      onClick={() => handleJumpToField(item.key, item.step)}
                      className={`inline-flex items-center space-x-1 px-2.5 py-1 rounded-lg text-xs font-medium cursor-pointer transition-all ${
                        isActive
                          ? 'bg-red-600 text-white ring-2 ring-red-400'
                          : 'bg-white border border-red-200 text-red-700 hover:bg-red-100/60'
                      }`}
                      title={item.reason}
                    >
                      <span>Step {item.step}: {item.label}</span>
                      <ArrowRight size={11} weight="bold" />
                    </button>
                  );
                })}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Save error inline notice */}
      {saveState === 'error' && saveError && (
        <div className="mb-2 px-3 py-1.5 rounded-lg bg-red-50 border border-red-200 text-red-600 text-xs">
          Save failed: {saveError}
        </div>
      )}

      {/* Test-case prefill: available on both the form and the documents view */}
      <TestCasePicker onLoad={handleLoadTestCase} />

      {/* Main Body: Switch between Registration Form and Documents Hub */}
      {activeView === 'documents' && vendorId ? (
        <div className="flex-1 mb-6 animate-fadeIn">
          <VendorDocumentManager
            vendorId={vendorId}
            businessEntityType={formData.company.businessEntityType}
            gstStatus={formData.taxBanking.gstStatus}
            applicationStatus={applicationStatus}
            onDocumentsChanged={() => syncWorkflowState(vendorId)}
          />
        </div>
      ) : (
        <>
          <StepHeader
            stepNumber={currentStep}
            totalSteps={4}
            title={currentMeta.title}
            subtitle={currentMeta.subtitle}
            isSaved={isSaved}
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
                vendorId={vendorId}
                onVendorIdReady={async () => {
                  const id = await ensureVendorExists();
                  return id;
                }}
              />
            )}
          </div>

          {/* Navigation */}
          <StepNavigation
            currentStep={currentStep}
            totalSteps={4}
            onBack={handleBack}
            onNext={handleNext}
            isSubmitting={isSubmitting}
          />
        </>
      )}
    </OnboardingLayout>
  );
};
