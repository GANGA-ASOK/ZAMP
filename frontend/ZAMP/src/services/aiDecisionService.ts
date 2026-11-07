/**
 * AI Decision Engine API client.
 *
 * The engine cross-checks name, PAN, GSTIN, CIN, mobile, address and bank
 * details across the application form and every uploaded document, then
 * recommends approve / review / reject with explicit reasons.
 */

import apiClient from './api';

export type DecisionOutcome = 'approve' | 'review' | 'reject';
export type Severity = 'critical' | 'major' | 'warning' | 'info' | 'pass';
export type StageStatus = 'pending' | 'running' | 'passed' | 'warning' | 'flagged' | 'failed' | 'skipped';
export type RunStatus = 'queued' | 'running' | 'completed' | 'failed';

export interface DecisionFinding {
  code: string;
  category: string;
  field: string;
  severity: Severity;
  title: string;
  detail: string;
  form_value?: string | null;
  document_value?: string | null;
  document_id?: string | null;
  document_name?: string | null;
  vendor_action?: string | null;
  source: 'rules' | 'nemotron' | 'policy' | string;
}

export interface MatrixCell {
  document_id: string;
  document_label: string;
  value: string | null;
  status: 'match' | 'minor' | 'mismatch' | 'not_found';
  note: string;
}

export interface MatrixRow {
  attribute: string;
  label: string;
  form_value: string | null;
  status: 'verified' | 'minor' | 'conflict' | 'unverified' | 'missing' | 'not_applicable';
  cells: MatrixCell[];
}

export interface RunStage {
  key: string;
  label: string;
  status: StageStatus;
  summary: string;
  details: unknown;
  started_at: string | null;
  completed_at: string | null;
  duration_ms: number | null;
}

export interface DocumentIdentity {
  document_id: string;
  file_name: string;
  category: string;
  label: string;
  readable: boolean;
  extraction_method: string;
  error?: string | null;
  fields: Record<string, string | string[]>;
}

export interface Decision {
  outcome: DecisionOutcome;
  label: string;
  confidence: number;
  risk_score: number;
  coverage: number;
  headline: string;
  narrative: string;
  decided_by: string;
  reasons: DecisionFinding[];
  observations: DecisionFinding[];
  counts: Record<Severity, number>;
  required_actions: string[];
  vendor_message: string | null;
}

export interface AIReview {
  used_llm: boolean;
  model: string | null;
  assessment: string | null;
  recommended_outcome: string | null;
  concerns: Array<Record<string, unknown>>;
  note: string;
}

export interface DecisionRun {
  id: string;
  vendor_id: string;
  vendor_name: string;
  reference_number: string;
  status: RunStatus;
  trigger: string;
  triggered_by: string;
  engine_version?: string;
  started_at: string;
  completed_at: string | null;
  duration_ms: number | null;
  stages: RunStage[];
  decision: Decision | null;
  findings: DecisionFinding[];
  evidence_matrix: MatrixRow[];
  documents: DocumentIdentity[];
  ai_review: AIReview | null;
  models?: { parse: string | null; reasoning: string | null; llm_enabled: boolean };
  error: string | null;
}

export type DecisionRunSummary = Pick<
  DecisionRun,
  'id' | 'vendor_id' | 'vendor_name' | 'reference_number' | 'status' | 'trigger' | 'triggered_by' | 'started_at' | 'completed_at' | 'duration_ms' | 'error'
> & { decision?: Pick<Decision, 'outcome' | 'label' | 'risk_score' | 'confidence' | 'headline' | 'counts'> | null };

export interface AIDecisionSummary {
  run_id: string;
  outcome: DecisionOutcome;
  label: string;
  risk_score: number;
  confidence: number;
  headline: string;
  completed_at: string;
}

export async function startDecisionRun(applicationId: string, forceReparse = false): Promise<DecisionRun> {
  const res = await apiClient.post<DecisionRun>(
    `/admin/applications/${applicationId}/ai-decision/run`,
    null,
    { params: { force_reparse: forceReparse } }
  );
  return res.data;
}

export async function getLatestDecision(applicationId: string): Promise<DecisionRun | null> {
  const res = await apiClient.get<{ run: DecisionRun | null }>(`/admin/applications/${applicationId}/ai-decision`);
  return res.data.run;
}

export async function getDecisionRun(runId: string): Promise<DecisionRun> {
  const res = await apiClient.get<DecisionRun>(`/admin/ai-decision/runs/${runId}`);
  return res.data;
}

export async function listApplicationRuns(applicationId: string): Promise<DecisionRunSummary[]> {
  const res = await apiClient.get<{ items: DecisionRunSummary[] }>(`/admin/applications/${applicationId}/ai-decision/runs`);
  return res.data.items;
}

export async function listRecentRuns(limit = 30): Promise<DecisionRunSummary[]> {
  const res = await apiClient.get<{ items: DecisionRunSummary[] }>('/admin/ai-decision/runs', { params: { limit } });
  return res.data.items;
}

export async function sendDecisionToVendor(applicationId: string, message?: string) {
  const res = await apiClient.post(`/admin/applications/${applicationId}/ai-decision/send-to-vendor`, { message });
  return res.data;
}
