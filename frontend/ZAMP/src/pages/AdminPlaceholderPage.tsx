import type { FC } from 'react';
import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Sparkle,
  FileText,
  CheckCircle,
  XCircle,
  WarningCircle,
  ArrowClockwise,
  MagnifyingGlass,
  Cpu,
  FilePdf,
  DownloadSimple,
  ChatCircleDots,
  SortAscending,
  SortDescending,
} from '@phosphor-icons/react';
import {
  listApplications,
  getApplicationDetail,
  updateApplicationStatus,
  approveApplication,
  rejectApplication,
  requestClarification,
  addAdminComment,
  generateApplicationInsights,
  type ApplicationListItem,
  type ApplicationDetailResponse,
  type AdminComment,
  type ClarificationItem,
} from '../services/workflowService';
import { getDocumentDownloadUrl } from '../services/documentService';
import {
  adminTriggerVerification,
  type VerificationResultResponse,
  type ConsistencyFinding,
  type FieldValidationFinding,
} from '../services/verificationService';
import { ActivityTimeline } from '../components/workflow/ActivityTimeline';
import { NotificationDrawer } from '../components/workflow/NotificationDrawer';
import { ApprovalModal } from '../components/workflow/ApprovalModal';
import { RejectionModal } from '../components/workflow/RejectionModal';
import { ClarificationModal } from '../components/workflow/ClarificationModal';
import { AIDecisionPanel } from '../components/ai/AIDecisionPanel';
import { AdminDashboardHeader } from '../components/admin/AdminDashboardHeader';

const AI_CHIP: Record<string, string> = {
  approve: 'bg-emerald-50 text-emerald-700 border-emerald-200',
  review: 'bg-amber-50 text-amber-800 border-amber-300',
  reject: 'bg-rose-50 text-rose-700 border-rose-200',
};

export const AdminPlaceholderPage: FC = () => {
  const navigate = useNavigate();

  // State
  const [applications, setApplications] = useState<ApplicationListItem[]>([]);
  const [statusCounts, setStatusCounts] = useState<Record<string, number>>({});
  const [loading, setLoading] = useState<boolean>(true);
  const [searchTerm, setSearchTerm] = useState<string>('');
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [sortBy, setSortBy] = useState<'last_updated_date' | 'submission_date'>('last_updated_date');
  const [sortOrder, setSortOrder] = useState<'desc' | 'asc'>('desc');

  const [selectedAppId, setSelectedAppId] = useState<string | null>(null);
  const [appDetail, setAppDetail] = useState<ApplicationDetailResponse | null>(null);
  const [loadingDetail, setLoadingDetail] = useState<boolean>(false);
  const [detailTab, setDetailTab] = useState<'ai' | 'info' | 'documents' | 'clarifications' | 'comments' | 'timeline'>('ai');
  const [rejectPrefill, setRejectPrefill] = useState<string>('');

  const [verificationMap, setVerificationMap] = useState<Record<string, VerificationResultResponse>>({});
  const [verifyingDocId, setVerifyingDocId] = useState<string | null>(null);
  const [actionLoading, setActionLoading] = useState<boolean>(false);
  const [newComment, setNewComment] = useState<string>('');
  const [commentLoading, setCommentLoading] = useState<boolean>(false);

  const [statusMessage, setStatusMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  // Modals state
  const [isApprovalOpen, setIsApprovalOpen] = useState(false);
  const [isRejectionOpen, setIsRejectionOpen] = useState(false);
  const [isClarificationOpen, setIsClarificationOpen] = useState(false);

  // Load applications list
  const loadData = async () => {
    setLoading(true);
    setStatusMessage(null);
    try {
      const res = await listApplications({
        status: statusFilter === 'all' ? undefined : statusFilter,
        search: searchTerm.trim() || undefined,
        sort_by: sortBy,
        sort_order: sortOrder,
        limit: 100,
      });
      setApplications(res.items || []);
      setStatusCounts(res.status_counts || {});
    } catch (err: any) {
      console.error('Failed to load applications:', err);
      setStatusMessage({
        type: 'error',
        text: err.message || 'Failed to connect to backend API. Please ensure the server is active.',
      });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [statusFilter, sortBy, sortOrder]);

  // Deep link: /admin?app=<applicationId> opens that application directly.
  useEffect(() => {
    const appId = new URLSearchParams(window.location.search).get('app');
    if (appId) handleSelectApplication(appId);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Load application detail
  const handleSelectApplication = async (applicationId: string) => {
    setSelectedAppId(applicationId);
    setLoadingDetail(true);
    try {
      const detail = await getApplicationDetail(applicationId);
      setAppDetail(detail);

      // Build verification map
      const vMap: Record<string, VerificationResultResponse> = {};
      if (detail.verification_summary?.results) {
        for (const res of detail.verification_summary.results) {
          vMap[res.document_id] = res;
        }
      }
      setVerificationMap(vMap);
    } catch (err: any) {
      console.error('Failed to load application detail:', err);
      setStatusMessage({
        type: 'error',
        text: err.message || 'Failed to load application details.',
      });
    } finally {
      setLoadingDetail(false);
    }
  };

  // Refresh the open application without unmounting the detail view
  const refreshDetail = async () => {
    if (!selectedAppId) return;
    try {
      setAppDetail(await getApplicationDetail(selectedAppId));
    } catch {
      // Non-critical
    }
    loadData();
  };

  // Move status (e.g. to under_review)
  const handleMoveToUnderReview = async () => {
    if (!selectedAppId) return;
    setActionLoading(true);
    setStatusMessage(null);
    try {
      await updateApplicationStatus(selectedAppId, 'under_review', 'Review commenced by compliance team.');
      setStatusMessage({
        type: 'success',
        text: "Application successfully transitioned to 'Under Review'.",
      });
      // Refresh
      await handleSelectApplication(selectedAppId);
      loadData();
    } catch (err: any) {
      setStatusMessage({
        type: 'error',
        text: err.message || 'Failed to update status.',
      });
    } finally {
      setActionLoading(false);
    }
  };

  // Approve action
  const handleConfirmApproval = async (comment: string) => {
    if (!selectedAppId) return;
    setActionLoading(true);
    try {
      await approveApplication(selectedAppId, comment);
      setStatusMessage({
        type: 'success',
        text: 'Vendor application successfully Approved!',
      });
      await handleSelectApplication(selectedAppId);
      loadData();
    } catch (err: any) {
      setStatusMessage({
        type: 'error',
        text: err.message || 'Failed to approve application.',
      });
    } finally {
      setActionLoading(false);
    }
  };

  // Reject action
  const handleConfirmRejection = async (reason: string) => {
    if (!selectedAppId) return;
    setActionLoading(true);
    try {
      await rejectApplication(selectedAppId, reason);
      setStatusMessage({
        type: 'success',
        text: 'Vendor application rejected. Notification sent.',
      });
      await handleSelectApplication(selectedAppId);
      loadData();
    } catch (err: any) {
      setStatusMessage({
        type: 'error',
        text: err.message || 'Failed to reject application.',
      });
    } finally {
      setActionLoading(false);
    }
  };

  // Request Clarification action
  const handleConfirmClarification = async (payload: {
    clarification_message: string;
    related_document_id?: string | null;
    related_document_name?: string | null;
    related_field?: string | null;
    admin_notes?: string | null;
  }) => {
    if (!selectedAppId) return;
    setActionLoading(true);
    try {
      await requestClarification(selectedAppId, payload);
      setStatusMessage({
        type: 'success',
        text: 'Clarification request dispatched to vendor.',
      });
      await handleSelectApplication(selectedAppId);
      loadData();
    } catch (err: any) {
      setStatusMessage({
        type: 'error',
        text: err.message || 'Failed to submit clarification request.',
      });
    } finally {
      setActionLoading(false);
    }
  };

  // Add internal comment
  const handleAddComment = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedAppId || !newComment.trim()) return;
    setCommentLoading(true);
    try {
      const added = await addAdminComment(selectedAppId, newComment.trim());
      setAppDetail((prev) =>
        prev
          ? {
              ...prev,
              comments: [...prev.comments, added],
            }
          : prev
      );
      setNewComment('');
      setStatusMessage({
        type: 'success',
        text: 'Internal review note added.',
      });
    } catch (err: any) {
      setStatusMessage({
        type: 'error',
        text: err.message || 'Failed to add comment.',
      });
    } finally {
      setCommentLoading(false);
    }
  };

  // Trigger or re-verify AI on a document
  const handleVerifyDocument = async (documentId: string) => {
    setVerifyingDocId(documentId);
    setStatusMessage(null);
    try {
      const res = await adminTriggerVerification(documentId, false);
      setVerificationMap((prev) => ({ ...prev, [documentId]: res }));
      setStatusMessage({
        type: 'success',
        text: `AI verification completed: Status is '${res.verification_status}'.`,
      });

      // Refresh insights and application data
      if (selectedAppId) {
        try {
          const freshInsights = await generateApplicationInsights(selectedAppId);
          setAppDetail((prev) => (prev ? { ...prev, ai_insights: freshInsights } : prev));
        } catch {
          // Non-critical
        }
      }
      loadData();
    } catch (err: any) {
      setStatusMessage({
        type: 'error',
        text: `AI Verification failed: ${err.message || 'Unknown error'}`,
      });
    } finally {
      setVerifyingDocId(null);
    }
  };

  // Helper for status badge styling
  const getStatusBadge = (status: string) => {
    const s = status?.toLowerCase();
    switch (s) {
      case 'approved':
        return 'bg-emerald-50 text-emerald-700 border-emerald-200';
      case 'rejected':
        return 'bg-rose-50 text-rose-700 border-rose-200';
      case 'under_review':
        return 'bg-blue-50 text-blue-700 border-blue-200';
      case 'clarification_required':
        return 'bg-amber-50 text-amber-800 border-amber-300';
      case 'resubmitted':
        return 'bg-indigo-50 text-indigo-700 border-indigo-200';
      case 'submitted':
        return 'bg-sky-50 text-sky-700 border-sky-200';
      default:
        return 'bg-slate-100 text-slate-600 border-slate-200';
    }
  };

  const vendor = appDetail?.vendor;

  return (
    <div className="min-h-screen bg-canvas py-6 sm:py-8 px-3 sm:px-6 lg:px-8 font-sans text-ink">
      <div className="max-w-[1400px] mx-auto space-y-5">
        <AdminDashboardHeader
          loading={loading}
          statusCounts={statusCounts}
          applications={applications}
          statusFilter={statusFilter}
          onFilter={setStatusFilter}
          onRefresh={loadData}
          onVendorPortal={() => navigate('/vendor')}
          onExit={() => navigate('/login')}
          notifications={
            <NotificationDrawer recipientType="admin" onSelectApplication={(id) => handleSelectApplication(id)} />
          }
        />

        {/* Global Feedback Banner */}
        {statusMessage && (
          <div
            className={`p-4 rounded-2xl border text-xs flex items-center justify-between ${
              statusMessage.type === 'success'
                ? 'bg-emerald-50 text-emerald-900 border-emerald-200'
                : 'bg-rose-50 text-rose-900 border-rose-200'
            }`}
          >
            <div className="flex items-center space-x-2">
              {statusMessage.type === 'success' ? (
                <CheckCircle size={18} weight="bold" className="text-emerald-600 shrink-0" />
              ) : (
                <WarningCircle size={18} weight="bold" className="text-rose-600 shrink-0" />
              )}
              <span>{statusMessage.text}</span>
            </div>
            <button
              onClick={() => setStatusMessage(null)}
              className="text-slate-400 hover:text-slate-600 cursor-pointer ml-4 font-semibold"
            >
              ✕
            </button>
          </div>
        )}

        {/* Main Grid: Applications Table (Left) + Detail Review Drawer (Right) */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
          {/* Applications List Table */}
          <div
            className={`bg-white rounded-[32px] overflow-hidden transition-all ${
              selectedAppId ? 'lg:col-span-5' : 'lg:col-span-12'
            }`}
          >
            {/* Search & Sort Header */}
            <div className="p-4 border-b border-slate-100 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
              <div>
                <h2 className="text-sm font-semibold text-slate-900">
                  Applications ({applications.length})
                </h2>
                <p className="text-[11px] text-slate-400 mt-0.5">
                  Select an application to inspect documents and take action
                </p>
              </div>

              <div className="flex items-center space-x-2">
                {/* Search */}
                <div className="relative min-w-[180px]">
                  <MagnifyingGlass
                    size={13}
                    className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400"
                  />
                  <input
                    type="text"
                    placeholder="Search name, ref, ID..."
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                    onKeyDown={(e) => e.key === 'Enter' && loadData()}
                    className="w-full pl-8 pr-3 py-1.5 rounded-xl border border-slate-200 text-xs focus:outline-none focus:border-[#1F211F] bg-slate-50/50"
                  />
                </div>

                {/* Sort selector */}
                <select
                  value={sortBy}
                  onChange={(e) => setSortBy(e.target.value as any)}
                  className="px-2 py-1.5 rounded-xl border border-slate-200 text-xs bg-slate-50 text-slate-700 focus:outline-none"
                >
                  <option value="last_updated_date">Last Updated</option>
                  <option value="submission_date">Submission Date</option>
                </select>

                {/* Sort Toggle */}
                <button
                  type="button"
                  onClick={() => setSortOrder((o) => (o === 'desc' ? 'asc' : 'desc'))}
                  className="p-1.5 rounded-xl border border-slate-200 bg-slate-50 text-slate-600 hover:bg-slate-100 cursor-pointer"
                  title={`Sort ${sortOrder === 'desc' ? 'Ascending' : 'Descending'}`}
                >
                  {sortOrder === 'desc' ? <SortDescending size={14} /> : <SortAscending size={14} />}
                </button>
              </div>
            </div>

            {loading ? (
              <div className="p-12 text-center text-slate-400">
                <ArrowClockwise size={24} className="animate-spin mx-auto mb-2 text-[#1F211F]" />
                <p className="text-xs">Loading application queue...</p>
              </div>
            ) : applications.length === 0 ? (
              <div className="p-12 text-center">
                <FileText size={28} className="mx-auto mb-2 text-slate-300" />
                <p className="text-xs font-semibold text-slate-600">No applications found.</p>
                <p className="text-[11px] text-slate-400 mt-1">Try resetting the status filter or search query.</p>
              </div>
            ) : (
              <div className="overflow-x-auto max-h-[720px] overflow-y-auto">
                <table className="w-full text-left text-xs">
                  <thead className="bg-slate-50 text-slate-500 uppercase tracking-wider font-semibold border-b border-slate-100 sticky top-0 z-10">
                    <tr>
                      <th className="px-3.5 py-3">Reference / Company</th>
                      {!selectedAppId && <th className="px-3.5 py-3">Contact</th>}
                      {!selectedAppId && <th className="px-3.5 py-3">Submission</th>}
                      {!selectedAppId && <th className="px-3.5 py-3">Docs</th>}
                      <th className="px-3.5 py-3">AI</th>
                      <th className="px-3.5 py-3">Status</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {applications.map((item) => {
                      const isSelected = item.id === selectedAppId;
                      return (
                        <tr
                          key={item.id}
                          onClick={() => handleSelectApplication(item.id)}
                          className={`cursor-pointer transition-colors ${
                            isSelected
                              ? 'bg-blue-50/80 hover:bg-blue-50'
                              : 'hover:bg-slate-50/70'
                          }`}
                        >
                          <td className="px-3.5 py-3">
                            <span className="font-mono text-[11px] font-semibold text-[#1F211F] block">
                              {item.reference_number || 'DRAFT'}
                            </span>
                            <span className="font-semibold text-slate-800 text-xs line-clamp-1 mt-0.5">
                              {item.company_name}
                            </span>
                          </td>

                          {!selectedAppId && (
                            <td className="px-3.5 py-3 text-slate-600">
                              <span className="block font-medium">{item.vendor_name}</span>
                              <span className="text-[11px] text-slate-400 block font-mono">{item.email}</span>
                            </td>
                          )}

                          {!selectedAppId && (
                            <td className="px-3.5 py-3 text-slate-500 text-[11px]">
                              {item.submission_date
                                ? new Date(item.submission_date).toLocaleDateString('en-US', {
                                    month: 'short',
                                    day: 'numeric',
                                    year: 'numeric',
                                  })
                                : '—'}
                            </td>
                          )}

                          {!selectedAppId && (
                            <td className="px-3.5 py-3">
                              <span className="inline-flex items-center space-x-1 px-2 py-0.5 rounded-md bg-slate-100 text-slate-700 text-[11px] font-medium">
                                <FilePdf size={12} />
                                <span>{item.document_count}</span>
                              </span>
                            </td>
                          )}

                          <td className="px-3.5 py-3">
                            {item.ai_decision ? (
                              <span
                                title={item.ai_decision.headline}
                                className={`inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-semibold uppercase tracking-wider border whitespace-nowrap ${AI_CHIP[item.ai_decision.outcome] || ''}`}
                              >
                                {item.ai_decision.label} · {item.ai_decision.risk_score}
                              </span>
                            ) : (
                              <span className="text-[10px] text-slate-400">—</span>
                            )}
                          </td>

                          <td className="px-3.5 py-3">
                            <span
                              className={`inline-flex items-center space-x-1 px-2 py-0.5 rounded-full text-[10px] font-semibold uppercase tracking-wider border ${getStatusBadge(
                                item.status
                              )}`}
                            >
                              <span>{item.status.replace(/_/g, ' ')}</span>
                            </span>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </div>

          {/* Selected Application Review Drawer */}
          {selectedAppId && (
            <div className="lg:col-span-7 space-y-5">
              {loadingDetail ? (
                <div className="bg-white p-12 rounded-[32px] text-center">
                  <ArrowClockwise size={28} className="animate-spin mx-auto mb-2 text-[#1F211F]" />
                  <p className="text-xs text-slate-500">Loading comprehensive application file...</p>
                </div>
              ) : appDetail && vendor ? (
                <div className="space-y-5">
                  {/* Review Top Banner & Decision Action Bar */}
                  <div className="bg-white p-6 rounded-[32px] space-y-4">
                    {/* Header Row */}
                    <div className="flex items-start justify-between border-b border-slate-100 pb-4">
                      <div>
                        <div className="flex items-center space-x-2">
                          <span className="font-mono text-xs font-semibold text-[#1F211F] bg-blue-50 px-2.5 py-0.5 rounded-md border border-blue-100">
                            {vendor.reference_number || 'DRAFT'}
                          </span>
                          <span
                            className={`text-[10px] font-semibold uppercase tracking-wider px-2.5 py-0.5 rounded-full border ${getStatusBadge(
                              vendor.status
                            )}`}
                          >
                            {vendor.status?.replace(/_/g, ' ')}
                          </span>
                        </div>
                        <h2 className="text-lg font-semibold text-slate-900 mt-1.5">
                          {vendor.company_info?.legal_company_name ||
                            vendor.company_info?.legal_name ||
                            'Company Name Not Set'}
                        </h2>
                        <p className="text-xs text-slate-500">
                          {vendor.company_info?.business_entity_type || 'Entity Type'} •{' '}
                          {vendor.company_info?.industry || 'Industry'}
                        </p>
                      </div>

                      <button
                        type="button"
                        onClick={() => setSelectedAppId(null)}
                        className="text-slate-400 hover:text-slate-600 p-1.5 rounded-lg hover:bg-slate-100 cursor-pointer"
                        title="Close Review Drawer"
                      >
                        ✕
                      </button>
                    </div>

                    {/* Action Bar (PART 3 & PART 4) */}
                    <div className="flex flex-wrap items-center justify-between gap-2.5 pt-1">
                      <div className="flex items-center space-x-2">
                        {/* Move to Under Review button if status is submitted or resubmitted */}
                        {(vendor.status === 'submitted' || vendor.status === 'resubmitted') && (
                          <button
                            type="button"
                            disabled={actionLoading}
                            onClick={handleMoveToUnderReview}
                            className="px-3.5 py-1.5 rounded-xl border border-blue-200 bg-blue-50 hover:bg-blue-100 text-[#1F211F] text-xs font-semibold cursor-pointer disabled:opacity-50"
                          >
                            Move to Under Review
                          </button>
                        )}

                        <button
                          type="button"
                          disabled={actionLoading || vendor.status === 'approved' || vendor.status === 'rejected'}
                          onClick={() => setIsClarificationOpen(true)}
                          className="px-3.5 py-1.5 rounded-xl border border-amber-300 bg-amber-50 hover:bg-amber-100 text-amber-800 text-xs font-semibold cursor-pointer disabled:opacity-50"
                        >
                          Request Clarification
                        </button>
                      </div>

                      <div className="flex items-center space-x-2">
                        <button
                          type="button"
                          disabled={actionLoading || vendor.status === 'approved' || vendor.status === 'rejected'}
                          onClick={() => setIsRejectionOpen(true)}
                          className="px-3.5 py-1.5 rounded-xl border border-rose-300 bg-rose-50 hover:bg-rose-100 text-rose-800 text-xs font-semibold cursor-pointer disabled:opacity-50"
                        >
                          Reject
                        </button>

                        <button
                          type="button"
                          disabled={actionLoading || vendor.status === 'approved' || vendor.status === 'rejected'}
                          onClick={() => setIsApprovalOpen(true)}
                          className="px-4 py-1.5 rounded-full bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-semibold cursor-pointer disabled:opacity-50 flex items-center space-x-1.5"
                        >
                          <CheckCircle size={14} weight="bold" />
                          <span>Approve Application</span>
                        </button>
                      </div>
                    </div>
                  </div>

                  {/* Tab Navigation for Detailed Inspection */}
                  <div className="flex items-center space-x-1 bg-white p-1.5 rounded-2xl border border-slate-200 overflow-x-auto text-xs font-semibold">
                    {[
                      { key: 'ai', label: 'AI Decision' },
                      { key: 'info', label: 'Vendor Info' },
                      { key: 'documents', label: `Documents & AI (${vendor.documents?.length || 0})` },
                      { key: 'clarifications', label: `Clarifications (${appDetail.clarifications?.length || 0})` },
                      { key: 'comments', label: `Internal Notes (${appDetail.comments?.length || 0})` },
                      { key: 'timeline', label: `Activity Timeline (${appDetail.activity?.length || 0})` },
                    ].map((t) => {
                      const active = detailTab === t.key;
                      return (
                        <button
                          key={t.key}
                          type="button"
                          onClick={() => setDetailTab(t.key as any)}
                          className={`px-3.5 py-1.5 rounded-xl transition-all cursor-pointer whitespace-nowrap ${
                            active
                              ? 'bg-[#1F211F] text-white shadow-xs'
                              : 'text-slate-600 hover:bg-slate-100 hover:text-slate-900'
                          }`}
                        >
                          {t.label}
                        </button>
                      );
                    })}
                  </div>

                  {/* TAB 0: AI DECISION ENGINE */}
                  {detailTab === 'ai' && (
                    <AIDecisionPanel
                      applicationId={selectedAppId}
                      applicationStatus={vendor.status}
                      onChanged={refreshDetail}
                      onApprove={() => setIsApprovalOpen(true)}
                      onRejectWithReasons={(reason) => {
                        setRejectPrefill(reason);
                        setIsRejectionOpen(true);
                      }}
                    />
                  )}

                  {/* TAB 1: VENDOR INFORMATION */}
                  {detailTab === 'info' && (
                    <div className="bg-white p-6 rounded-[32px] space-y-6 text-xs text-left">
                      {/* Company Info */}
                      <div>
                        <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-500 mb-3 border-b border-slate-100 pb-2">
                          Company & Incorporation Details
                        </h4>
                        <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
                          <div>
                            <span className="text-[10px] text-slate-400 uppercase font-semibold block">Legal Name</span>
                            <span className="font-semibold text-slate-800">{vendor.company_info?.legal_company_name || '—'}</span>
                          </div>
                          <div>
                            <span className="text-[10px] text-slate-400 uppercase font-semibold block">Trade Name</span>
                            <span className="font-semibold text-slate-800">{vendor.company_info?.trade_name || '—'}</span>
                          </div>
                          <div>
                            <span className="text-[10px] text-slate-400 uppercase font-semibold block">Entity Type</span>
                            <span className="font-semibold text-slate-800">{vendor.company_info?.business_entity_type || '—'}</span>
                          </div>
                          <div>
                            <span className="text-[10px] text-slate-400 uppercase font-semibold block">Registration / CIN</span>
                            <span className="font-mono font-semibold text-slate-800">{vendor.company_info?.registration_number || '—'}</span>
                          </div>
                          <div>
                            <span className="text-[10px] text-slate-400 uppercase font-semibold block">Incorporation Date</span>
                            <span className="font-semibold text-slate-800">{vendor.company_info?.incorporation_date || '—'}</span>
                          </div>
                          <div>
                            <span className="text-[10px] text-slate-400 uppercase font-semibold block">Industry</span>
                            <span className="font-semibold text-slate-800">{vendor.company_info?.industry || '—'}</span>
                          </div>
                        </div>

                        {/* Addresses */}
                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 mt-3 pt-3 border-t border-slate-100">
                          <div>
                            <span className="text-[10px] text-slate-400 uppercase font-semibold block">Registered Address</span>
                            <p className="text-slate-700 mt-0.5">
                              {vendor.company_info?.registered_address?.street || ''},{' '}
                              {vendor.company_info?.registered_address?.city || ''},{' '}
                              {vendor.company_info?.registered_address?.state || ''} -{' '}
                              {vendor.company_info?.registered_address?.pincode || ''}
                            </p>
                          </div>
                          <div>
                            <span className="text-[10px] text-slate-400 uppercase font-semibold block">Operational Address</span>
                            <p className="text-slate-700 mt-0.5">
                              {vendor.company_info?.is_operational_same_as_registered
                                ? 'Same as Registered Address'
                                : `${vendor.company_info?.operational_address?.street || ''}, ${vendor.company_info?.operational_address?.city || ''}`}
                            </p>
                          </div>
                        </div>
                      </div>

                      {/* Contact Details */}
                      <div>
                        <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-500 mb-3 border-b border-slate-100 pb-2">
                          Key Contact Persons
                        </h4>
                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                          <div className="p-3 rounded-2xl bg-slate-50 border border-slate-200/80">
                            <span className="text-[10px] uppercase font-semibold text-slate-400 block">Primary Contact</span>
                            <p className="font-semibold text-slate-900 mt-1">
                              {vendor.contact_info?.primary?.first_name} {vendor.contact_info?.primary?.last_name}
                            </p>
                            <p className="text-slate-500 text-[11px] font-mono">{vendor.contact_info?.primary?.email}</p>
                            <p className="text-slate-500 text-[11px] font-mono">{vendor.contact_info?.primary?.phone}</p>
                            <p className="text-slate-400 text-[10px] mt-1">{vendor.contact_info?.primary?.designation}</p>
                          </div>

                          <div className="p-3 rounded-2xl bg-slate-50 border border-slate-200/80">
                            <span className="text-[10px] uppercase font-semibold text-slate-400 block">Authorized Signatory</span>
                            <p className="font-semibold text-slate-900 mt-1">
                              {vendor.contact_info?.signatory?.full_name || vendor.contact_info?.signatory?.first_name || '—'}
                            </p>
                            <p className="text-slate-500 text-[11px] font-mono">{vendor.contact_info?.signatory?.email || '—'}</p>
                            <p className="text-slate-400 text-[10px] mt-1">{vendor.contact_info?.signatory?.designation || 'Signatory'}</p>
                          </div>
                        </div>
                      </div>

                      {/* Tax & Banking Details */}
                      <div>
                        <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-500 mb-3 border-b border-slate-100 pb-2">
                          Tax & Banking Information (Authorized Admin Access)
                        </h4>
                        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                          <div>
                            <span className="text-[10px] text-slate-400 uppercase font-semibold block">PAN Number</span>
                            <span className="font-mono font-semibold text-slate-800">{vendor.tax_details?.pan_number || '—'}</span>
                          </div>
                          <div>
                            <span className="text-[10px] text-slate-400 uppercase font-semibold block">GSTIN</span>
                            <span className="font-mono font-semibold text-slate-800">{vendor.tax_details?.gstin || '—'}</span>
                          </div>
                          <div>
                            <span className="text-[10px] text-slate-400 uppercase font-semibold block">GST Status</span>
                            <span className="font-semibold text-slate-800">{vendor.tax_details?.gst_status || '—'}</span>
                          </div>
                          <div>
                            <span className="text-[10px] text-slate-400 uppercase font-semibold block">TAN Number</span>
                            <span className="font-mono font-semibold text-slate-800">{vendor.tax_details?.tan_number || '—'}</span>
                          </div>
                        </div>

                        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mt-3 pt-3 border-t border-slate-100">
                          <div>
                            <span className="text-[10px] text-slate-400 uppercase font-semibold block">Bank Name</span>
                            <span className="font-semibold text-slate-800">{vendor.banking_details?.bank_name || '—'}</span>
                          </div>
                          <div>
                            <span className="text-[10px] text-slate-400 uppercase font-semibold block">Account Holder</span>
                            <span className="font-semibold text-slate-800">{vendor.banking_details?.account_holder_name || '—'}</span>
                          </div>
                          <div>
                            <span className="text-[10px] text-slate-400 uppercase font-semibold block">Account Number</span>
                            <span className="font-mono font-semibold text-slate-800">{vendor.banking_details?.account_number || '—'}</span>
                          </div>
                          <div>
                            <span className="text-[10px] text-slate-400 uppercase font-semibold block">IFSC Code</span>
                            <span className="font-mono font-semibold text-slate-800">{vendor.banking_details?.ifsc_code || '—'}</span>
                          </div>
                        </div>
                      </div>
                    </div>
                  )}

                  {/* TAB 2: UPLOADED DOCUMENTS & AI VERIFICATION RESULTS */}
                  {detailTab === 'documents' && (
                    <div className="bg-white p-6 rounded-[32px] space-y-6 text-left">
                      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-100 pb-4">
                        <div className="flex items-center space-x-2.5">
                          <div className="w-9 h-9 rounded-xl bg-indigo-100 text-indigo-700 flex items-center justify-center shrink-0">
                            <Cpu size={20} weight="bold" />
                          </div>
                          <div>
                            <h3 className="text-sm font-semibold text-slate-900">
                              Documents & AI Verification Hub
                            </h3>
                            <p className="text-[11px] text-slate-500">
                              GridFS binary document storage with NVIDIA Nemotron 3.5 Parse & Super VL reasoning
                            </p>
                          </div>
                        </div>

                      </div>

                      {/* Pointer to the application-level AI decision */}
                      <button
                        type="button"
                        onClick={() => setDetailTab('ai')}
                        className="w-full p-3.5 rounded-2xl border border-indigo-200 bg-indigo-50/60 hover:bg-indigo-50 text-left text-xs flex items-center justify-between gap-3 cursor-pointer"
                      >
                        <span className="flex items-center gap-2 text-indigo-950">
                          <Sparkle size={16} weight="bold" className="text-indigo-600 shrink-0" />
                          <span>
                            Per-document results are shown below. The application-level recommendation, which cross-checks every
                            document against the form and against each other, is on the <b>AI Decision</b> tab.
                          </span>
                        </span>
                        <span className="font-semibold text-indigo-700 shrink-0">Open →</span>
                      </button>

                      {/* UPLOADED DOCUMENTS LIST */}
                      <div>
                        <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-500 mb-3 border-b border-slate-100 pb-2">
                          Uploaded Files ({vendor.documents?.length || 0})
                        </h4>

                        {(!vendor.documents || vendor.documents.length === 0) ? (
                          <div className="p-8 text-center bg-slate-50/60 rounded-2xl border border-dashed border-slate-200 space-y-2">
                            <FilePdf size={28} className="mx-auto text-slate-300" />
                            <p className="text-xs text-slate-700 font-semibold">No documents uploaded for this vendor.</p>
                            <p className="text-[11px] text-slate-500 max-w-md mx-auto">
                              Based on entity type ({vendor.company_info?.business_entity_type || 'Vendor'}), this application requires PAN Card, Bank Proof, and applicable registration certificates.
                            </p>
                          </div>
                        ) : (
                          <div className="space-y-4">
                            {vendor.documents.map((doc: any) => {
                              const docId = doc.document_id || doc.id;
                              const verifResult = verificationMap[docId];
                              const isVerifying = verifyingDocId === docId;
                              const downloadUrl = getDocumentDownloadUrl(vendor.id, docId);

                              return (
                                <div
                                  key={docId}
                                  className="border border-slate-200/90 rounded-2xl p-4 bg-slate-50/40 hover:bg-white transition-all space-y-3"
                                >
                                  {/* Header */}
                                  <div className="flex items-start justify-between gap-3">
                                    <div className="flex items-start space-x-3">
                                      <div className="w-9 h-9 rounded-xl bg-blue-100/70 text-[#1F211F] flex items-center justify-center shrink-0 mt-0.5">
                                        <FilePdf size={20} weight="fill" />
                                      </div>
                                      <div>
                                        <div className="flex items-center space-x-2">
                                          <h4 className="text-xs font-semibold text-slate-900">
                                            {doc.category?.replace(/_/g, ' ').toUpperCase() || 'DOCUMENT'}
                                          </h4>
                                          <span
                                            className={`px-2 py-0.5 rounded-full text-[10px] font-semibold uppercase tracking-wider inline-flex items-center space-x-1 ${
                                              verifResult?.verification_status === 'completed' || doc.verification_status === 'completed'
                                                ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                                                : verifResult?.verification_status === 'flagged' || doc.verification_status === 'flagged'
                                                ? 'bg-rose-50 text-rose-700 border border-rose-200'
                                                : verifResult?.verification_status === 'needs_manual_review' || doc.verification_status === 'needs_manual_review'
                                                ? 'bg-amber-50 text-amber-700 border border-amber-200'
                                                : 'bg-slate-100 text-slate-600 border border-slate-200'
                                            }`}
                                          >
                                            <span>
                                              {verifResult?.verification_status || doc.verification_status || 'Pending'}
                                            </span>
                                          </span>
                                        </div>
                                        <p className="text-[11px] text-slate-500 mt-0.5 font-mono">
                                          {doc.original_filename || doc.file_name || 'document.pdf'} •{' '}
                                          {doc.file_size ? `${Math.round(doc.file_size / 1024)} KB` : 'PDF'} •{' '}
                                          {doc.uploaded_at || doc.upload_timestamp ? new Date(doc.uploaded_at || doc.upload_timestamp).toLocaleDateString() : 'Uploaded'}
                                        </p>
                                      </div>
                                    </div>

                                    <div className="flex items-center space-x-2 shrink-0">
                                      {/* Download button from GridFS */}
                                      <a
                                        href={downloadUrl}
                                        target="_blank"
                                        rel="noreferrer"
                                        className="inline-flex items-center space-x-1 px-2.5 py-1.5 rounded-xl border border-slate-200 bg-white hover:bg-slate-50 text-slate-700 text-[11px] font-semibold transition-colors cursor-pointer"
                                        title="Download file from GridFS"
                                      >
                                        <DownloadSimple size={12} weight="bold" />
                                        <span>Download</span>
                                      </a>

                                      {/* AI verify button */}
                                      <button
                                        type="button"
                                        disabled={isVerifying}
                                        onClick={() => handleVerifyDocument(docId)}
                                        className="inline-flex items-center space-x-1 px-3 py-1.5 rounded-full bg-[#1F211F] hover:bg-[#3A3D39] text-white text-[11px] font-semibold transition-colors cursor-pointer disabled:opacity-50 shadow-xs"
                                      >
                                        {isVerifying ? (
                                          <>
                                            <ArrowClockwise size={12} className="animate-spin" />
                                            <span>Auditing...</span>
                                          </>
                                        ) : (
                                          <>
                                            <Sparkle size={12} weight="bold" />
                                            <span>{verifResult ? 'Re-Verify' : 'Run AI Verify'}</span>
                                          </>
                                        )}
                                      </button>
                                    </div>
                                  </div>

                                  {/* Verification findings card */}
                                  {verifResult && (
                                    <div className="mt-3 pt-3 border-t border-slate-200/80 space-y-3">
                                      {verifResult.summary_explanation && (
                                        <div
                                          className={`p-3 rounded-xl text-xs ${
                                            verifResult.verification_status === 'completed'
                                              ? 'bg-emerald-50/70 text-emerald-950 border border-emerald-200/80'
                                              : verifResult.verification_status === 'flagged'
                                              ? 'bg-rose-50/70 text-rose-950 border border-rose-200/80'
                                              : 'bg-amber-50/70 text-amber-950 border border-amber-200/80'
                                          }`}
                                        >
                                          <div className="flex items-start space-x-2">
                                            <Sparkle size={14} className="mt-0.5 shrink-0" weight="bold" />
                                            <div>
                                              <p className="font-semibold">AI Auditor Finding:</p>
                                              <p className="mt-0.5 leading-relaxed">{verifResult.summary_explanation}</p>
                                            </div>
                                          </div>
                                        </div>
                                      )}

                                      {/* Cross-document consistency checks */}
                                      {verifResult.consistency_findings && verifResult.consistency_findings.length > 0 && (
                                        <div>
                                          <p className="text-[11px] font-semibold uppercase tracking-wider text-slate-500 mb-1.5">
                                            Cross-Document Consistency Audits
                                          </p>
                                          <div className="space-y-1.5">
                                            {verifResult.consistency_findings.map((f: ConsistencyFinding, fIdx: number) => (
                                              <div
                                                key={fIdx}
                                                className="p-2.5 rounded-xl bg-white border border-slate-200/90 text-xs flex flex-col sm:flex-row sm:items-center justify-between gap-2"
                                              >
                                                <div>
                                                  <span className="font-semibold text-slate-800">{f.field_name}</span>
                                                  <p className="text-[11px] text-slate-500 mt-0.5">{f.explanation}</p>
                                                </div>
                                                <span
                                                  className={`px-2 py-0.5 rounded-md text-[10px] font-semibold uppercase shrink-0 ${
                                                    f.status === 'match'
                                                      ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                                                      : f.status === 'mismatch'
                                                      ? 'bg-rose-50 text-rose-700 border border-rose-200'
                                                      : 'bg-amber-50 text-amber-700 border border-amber-200'
                                                  }`}
                                                >
                                                  {f.status}
                                                </span>
                                              </div>
                                            ))}
                                          </div>
                                        </div>
                                      )}

                                      {/* Deterministic checks */}
                                      {verifResult.field_validations && verifResult.field_validations.length > 0 && (
                                        <div>
                                          <p className="text-[11px] font-semibold uppercase tracking-wider text-slate-500 mb-1.5">
                                            Format & Checksum Verifications
                                          </p>
                                          <div className="grid grid-cols-1 sm:grid-cols-2 gap-1.5 text-xs">
                                            {verifResult.field_validations.map((v: FieldValidationFinding, vIdx: number) => (
                                              <div
                                                key={vIdx}
                                                className="p-2 rounded-xl bg-white border border-slate-200 text-[11px] flex items-center justify-between"
                                              >
                                                <div>
                                                  <span className="font-semibold text-slate-700">{v.field_name}</span>
                                                  <span className="text-slate-400 block text-[10px]">{v.details}</span>
                                                </div>
                                                {v.is_valid ? (
                                                  <CheckCircle size={16} weight="fill" className="text-emerald-600 shrink-0 ml-2" />
                                                ) : (
                                                  <XCircle size={16} weight="fill" className="text-rose-600 shrink-0 ml-2" />
                                                )}
                                              </div>
                                            ))}
                                          </div>
                                        </div>
                                      )}

                                      {/* Extracted Fields */}
                                      {verifResult.extracted_fields && Object.keys(verifResult.extracted_fields).length > 0 && (
                                        <div className="p-2.5 rounded-xl bg-slate-100/70 border border-slate-200/60 text-[11px] font-mono">
                                          <span className="text-[10px] uppercase font-semibold text-slate-500 font-sans block mb-1">
                                            Extracted Attributes (Nemotron 3.5 Parse)
                                          </span>
                                          <div className="flex flex-wrap gap-2">
                                            {Object.entries(verifResult.extracted_fields).map(([k, val]) => (
                                              <span
                                                key={k}
                                                className="bg-white px-2 py-0.5 rounded border border-slate-200 text-slate-800"
                                              >
                                                <strong className="text-slate-500">{k}:</strong> {String(val || 'null')}
                                              </span>
                                            ))}
                                          </div>
                                        </div>
                                      )}
                                    </div>
                                  )}
                                </div>
                              );
                            })}
                          </div>
                        )}
                      </div>
                    </div>
                  )}

                  {/* TAB 3: CLARIFICATION REQUESTS */}
                  {detailTab === 'clarifications' && (
                    <div className="bg-white p-6 rounded-[32px] space-y-4 text-left">
                      <div className="flex items-center justify-between border-b border-slate-100 pb-3">
                        <div>
                          <h3 className="text-sm font-semibold text-slate-900">
                            Clarification Requests ({appDetail.clarifications?.length || 0})
                          </h3>
                          <p className="text-[11px] text-slate-500">
                            Formal inquiries and document correction requests sent to the vendor
                          </p>
                        </div>
                        <button
                          type="button"
                          onClick={() => setIsClarificationOpen(true)}
                          className="px-3 py-1.5 rounded-full bg-amber-600 hover:bg-amber-700 text-white text-xs font-semibold cursor-pointer"
                        >
                          + Request Clarification
                        </button>
                      </div>

                      {(!appDetail.clarifications || appDetail.clarifications.length === 0) ? (
                        <div className="p-8 text-center text-slate-400 text-xs">
                          <ChatCircleDots size={24} className="mx-auto mb-2 text-slate-300" />
                          <p>No clarification requests recorded for this application.</p>
                        </div>
                      ) : (
                        <div className="space-y-3">
                          {appDetail.clarifications.map((item: ClarificationItem) => (
                            <div
                              key={item.id}
                              className="border border-slate-200 rounded-2xl p-4 bg-slate-50/50 space-y-2 text-xs"
                            >
                              <div className="flex items-center justify-between">
                                <span className="font-semibold text-slate-800">
                                  {item.related_document_name
                                    ? `Document: ${item.related_document_name}`
                                    : item.related_field
                                    ? `Field: ${item.related_field}`
                                    : 'General Application Clarification'}
                                </span>
                                <span
                                  className={`px-2 py-0.5 rounded-full text-[10px] font-semibold uppercase border ${
                                    item.status === 'resolved'
                                      ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
                                      : 'bg-amber-50 text-amber-800 border-amber-300'
                                  }`}
                                >
                                  {item.status}
                                </span>
                              </div>

                              <div className="p-3 rounded-xl bg-white border border-slate-200/80">
                                <span className="text-[10px] font-semibold uppercase text-slate-400 block">Admin Message:</span>
                                <p className="text-slate-800 font-medium mt-0.5">{item.clarification_message}</p>
                              </div>

                              {item.vendor_response && (
                                <div className="p-3 rounded-xl bg-blue-50/60 border border-blue-200/80">
                                  <span className="text-[10px] font-semibold uppercase text-blue-700 block">Vendor Response:</span>
                                  <p className="text-slate-800 font-medium mt-0.5">{item.vendor_response}</p>
                                  {item.replaced_document_id && (
                                    <span className="text-[10px] font-mono text-blue-800 block mt-1">
                                      Attached Replacement Doc ID: {item.replaced_document_id}
                                    </span>
                                  )}
                                </div>
                              )}
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  )}

                  {/* TAB 4: INTERNAL ADMIN REVIEW NOTES */}
                  {detailTab === 'comments' && (
                    <div className="bg-white p-6 rounded-[32px] space-y-4 text-left">
                      <div className="border-b border-slate-100 pb-3">
                        <h3 className="text-sm font-semibold text-slate-900">
                          Internal Compliance Notes ({appDetail.comments?.length || 0})
                        </h3>
                        <p className="text-[11px] text-slate-500">
                          Private notes and internal observations. Strictly hidden from vendor visibility.
                        </p>
                      </div>

                      {/* Add comment form */}
                      <form onSubmit={handleAddComment} className="space-y-2">
                        <textarea
                          rows={2}
                          placeholder="Add an internal note or observation..."
                          value={newComment}
                          onChange={(e) => setNewComment(e.target.value)}
                          className="w-full p-3 rounded-xl border border-slate-200 text-xs focus:outline-none focus:border-[#1F211F] bg-slate-50/50 resize-none"
                        />
                        <div className="flex justify-end">
                          <button
                            type="submit"
                            disabled={commentLoading || !newComment.trim()}
                            className="px-3.5 py-1.5 rounded-full bg-[#1F211F] hover:bg-[#3A3D39] text-white text-xs font-semibold cursor-pointer shadow-xs disabled:opacity-50"
                          >
                            {commentLoading ? 'Saving...' : 'Add Note'}
                          </button>
                        </div>
                      </form>

                      {/* Notes list */}
                      {appDetail.comments?.length === 0 ? (
                        <div className="p-6 text-center text-slate-400 text-xs">
                          <p>No internal notes added yet.</p>
                        </div>
                      ) : (
                        <div className="space-y-2.5 pt-2">
                          {appDetail.comments.map((c: AdminComment) => (
                            <div
                              key={c.id}
                              className="p-3.5 rounded-2xl bg-slate-50 border border-slate-200 text-xs space-y-1"
                            >
                              <div className="flex items-center justify-between text-[11px]">
                                <span className="font-semibold text-slate-800">{c.author_name}</span>
                                <span className="text-slate-400 font-mono">
                                  {new Date(c.created_at).toLocaleString('en-US', {
                                    month: 'short',
                                    day: 'numeric',
                                    hour: '2-digit',
                                    minute: '2-digit',
                                  })}
                                </span>
                              </div>
                              <p className="text-slate-700 leading-relaxed">{c.comment}</p>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  )}

                  {/* TAB 5: APPLICATION ACTIVITY TIMELINE */}
                  {detailTab === 'timeline' && (
                    <div className="bg-white p-6 rounded-[32px] space-y-4 text-left">
                      <div className="border-b border-slate-100 pb-3">
                        <h3 className="text-sm font-semibold text-slate-900">
                          Application Activity Timeline ({appDetail.activity?.length || 0})
                        </h3>
                        <p className="text-[11px] text-slate-500">
                          Chronological immutable record of status changes, AI verifications, and compliance milestones
                        </p>
                      </div>

                      <ActivityTimeline events={appDetail.activity} />
                    </div>
                  )}
                </div>
              ) : null}
            </div>
          )}
        </div>
      </div>

      {/* Modals */}
      {selectedAppId && vendor && (
        <>
          <ApprovalModal
            isOpen={isApprovalOpen}
            onClose={() => setIsApprovalOpen(false)}
            onConfirm={handleConfirmApproval}
            companyName={vendor.company_info?.legal_company_name || 'Vendor'}
            referenceNumber={vendor.reference_number || 'DRAFT'}
          />

          <RejectionModal
            isOpen={isRejectionOpen}
            onClose={() => {
              setIsRejectionOpen(false);
              setRejectPrefill('');
            }}
            initialReason={rejectPrefill}
            onConfirm={handleConfirmRejection}
            companyName={vendor.company_info?.legal_company_name || 'Vendor'}
            referenceNumber={vendor.reference_number || 'DRAFT'}
          />

          <ClarificationModal
            isOpen={isClarificationOpen}
            onClose={() => setIsClarificationOpen(false)}
            onConfirm={handleConfirmClarification}
            documents={vendor.documents || []}
            companyName={vendor.company_info?.legal_company_name || 'Vendor'}
            referenceNumber={vendor.reference_number || 'DRAFT'}
          />
        </>
      )}
    </div>
  );
};
