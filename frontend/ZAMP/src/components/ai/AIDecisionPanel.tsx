import type { FC, ReactNode } from 'react';
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  ArrowClockwise,
  ArrowsClockwise,
  Brain,
  CheckCircle,
  CircleNotch,
  Circle,
  ClockCounterClockwise,
  FileMagnifyingGlass,
  MinusCircle,
  PaperPlaneTilt,
  ShieldCheck,
  ShieldWarning,
  Sparkle,
  Table,
  WarningCircle,
  XCircle,
} from '@phosphor-icons/react';
import {
  getDecisionRun,
  getLatestDecision,
  listApplicationRuns,
  sendDecisionToVendor,
  startDecisionRun,
  type DecisionFinding,
  type DecisionOutcome,
  type DecisionRun,
  type DecisionRunSummary,
  type MatrixRow,
  type RunStage,
  type Severity,
} from '../../services/aiDecisionService';

interface AIDecisionPanelProps {
  applicationId: string;
  applicationStatus: string;
  /** Called when a run completes or a clarification is sent, so the parent can refresh. */
  onChanged?: () => void;
  /** Opens the parent's rejection modal pre-filled with the AI reasons. */
  onRejectWithReasons?: (reason: string) => void;
  /** Opens the parent's approval modal. */
  onApprove?: () => void;
}

const OUTCOME_STYLE: Record<DecisionOutcome, { box: string; chip: string; icon: ReactNode; bar: string }> = {
  approve: {
    box: 'bg-emerald-50/80 border-emerald-200 text-emerald-950',
    chip: 'bg-emerald-600 text-white',
    bar: 'bg-emerald-500',
    icon: <ShieldCheck size={26} weight="fill" className="text-emerald-600" />,
  },
  review: {
    box: 'bg-amber-50/80 border-amber-200 text-amber-950',
    chip: 'bg-amber-500 text-white',
    bar: 'bg-amber-500',
    icon: <ShieldWarning size={26} weight="fill" className="text-amber-600" />,
  },
  reject: {
    box: 'bg-rose-50/80 border-rose-200 text-rose-950',
    chip: 'bg-rose-600 text-white',
    bar: 'bg-rose-500',
    icon: <XCircle size={26} weight="fill" className="text-rose-600" />,
  },
};

const SEVERITY_STYLE: Record<Severity, { card: string; badge: string; label: string }> = {
  critical: { card: 'border-rose-300 bg-rose-50/70', badge: 'bg-rose-600 text-white', label: 'Critical' },
  major: { card: 'border-amber-300 bg-amber-50/60', badge: 'bg-amber-500 text-white', label: 'Major' },
  warning: { card: 'border-slate-200 bg-slate-50', badge: 'bg-slate-500 text-white', label: 'Minor' },
  info: { card: 'border-slate-200 bg-white', badge: 'bg-slate-200 text-slate-700', label: 'Info' },
  pass: { card: 'border-emerald-200 bg-emerald-50/50', badge: 'bg-emerald-600 text-white', label: 'Pass' },
};

const CELL_STYLE: Record<string, string> = {
  match: 'bg-emerald-50 text-emerald-900 border-emerald-200',
  minor: 'bg-amber-50 text-amber-900 border-amber-200',
  mismatch: 'bg-rose-50 text-rose-900 border-rose-300',
  not_found: 'bg-slate-50 text-slate-400 border-slate-200',
};

const ROW_STATUS: Record<MatrixRow['status'], { label: string; cls: string }> = {
  verified: { label: 'Verified', cls: 'text-emerald-700 bg-emerald-50 border-emerald-200' },
  minor: { label: 'Minor variation', cls: 'text-amber-800 bg-amber-50 border-amber-200' },
  conflict: { label: 'Conflict', cls: 'text-rose-700 bg-rose-50 border-rose-200' },
  unverified: { label: 'Not in documents', cls: 'text-slate-600 bg-slate-100 border-slate-200' },
  missing: { label: 'Missing on form', cls: 'text-amber-800 bg-amber-50 border-amber-200' },
  not_applicable: { label: 'N/A', cls: 'text-slate-400 bg-slate-50 border-slate-200' },
};

const CLARIFIABLE = new Set(['submitted', 'under_review', 'resubmitted']);

function StageIcon({ status }: { status: RunStage['status'] }) {
  switch (status) {
    case 'running':
      return <CircleNotch size={18} weight="bold" className="text-[#07569B] animate-spin" />;
    case 'passed':
      return <CheckCircle size={18} weight="fill" className="text-emerald-600" />;
    case 'warning':
      return <WarningCircle size={18} weight="fill" className="text-slate-500" />;
    case 'flagged':
      return <WarningCircle size={18} weight="fill" className="text-amber-500" />;
    case 'failed':
      return <XCircle size={18} weight="fill" className="text-rose-600" />;
    case 'skipped':
      return <MinusCircle size={18} weight="fill" className="text-slate-300" />;
    default:
      return <Circle size={18} className="text-slate-300" />;
  }
}

function Section({ icon, title, subtitle, right, children }: { icon: ReactNode; title: string; subtitle?: string; right?: ReactNode; children: ReactNode }) {
  return (
    <div className="bg-white p-5 rounded-3xl shadow-xl shadow-slate-200/70 border border-slate-200/80 space-y-3 text-left">
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center space-x-2.5">
          <div className="w-8 h-8 rounded-xl bg-indigo-50 text-indigo-700 flex items-center justify-center shrink-0">{icon}</div>
          <div>
            <h3 className="text-sm font-bold text-slate-900">{title}</h3>
            {subtitle && <p className="text-[11px] text-slate-500">{subtitle}</p>}
          </div>
        </div>
        {right}
      </div>
      {children}
    </div>
  );
}

function Metric({ label, value, hint, barPct, barCls }: { label: string; value: string; hint?: string; barPct?: number; barCls?: string }) {
  return (
    <div className="p-3 rounded-2xl bg-white/80 border border-white shadow-2xs min-w-[110px] flex-1">
      <p className="text-[10px] uppercase tracking-wider font-semibold text-slate-500">{label}</p>
      <p className="text-lg font-bold text-slate-900 leading-tight mt-0.5">{value}</p>
      {barPct !== undefined && (
        <div className="h-1.5 rounded-full bg-slate-200 mt-1.5 overflow-hidden">
          <div className={`h-full rounded-full ${barCls}`} style={{ width: `${Math.max(3, Math.min(100, barPct))}%` }} />
        </div>
      )}
      {hint && <p className="text-[10px] text-slate-500 mt-1">{hint}</p>}
    </div>
  );
}

function FindingCard({ f }: { f: DecisionFinding }) {
  const s = SEVERITY_STYLE[f.severity] ?? SEVERITY_STYLE.info;
  return (
    <div className={`p-3 rounded-2xl border text-xs space-y-1.5 ${s.card}`}>
      <div className="flex items-start justify-between gap-2">
        <p className="font-bold text-slate-900">{f.title}</p>
        <div className="flex items-center gap-1 shrink-0">
          {f.source === 'nemotron' && (
            <span className="px-1.5 py-0.5 rounded-md text-[9px] font-bold uppercase bg-indigo-600 text-white inline-flex items-center gap-0.5">
              <Sparkle size={9} weight="fill" /> Nemotron
            </span>
          )}
          <span className={`px-1.5 py-0.5 rounded-md text-[9px] font-bold uppercase ${s.badge}`}>{s.label}</span>
        </div>
      </div>
      <p className="text-slate-700 leading-relaxed">{f.detail}</p>
      {(f.form_value || f.document_value) && (
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-1.5 pt-0.5">
          {f.form_value && (
            <div className="px-2 py-1 rounded-lg bg-white/90 border border-slate-200">
              <span className="text-[9px] uppercase font-bold text-slate-400 block">Form</span>
              <span className="font-mono text-[11px] text-slate-800 break-words">{f.form_value}</span>
            </div>
          )}
          {f.document_value && (
            <div className="px-2 py-1 rounded-lg bg-white/90 border border-slate-200">
              <span className="text-[9px] uppercase font-bold text-slate-400 block">{f.document_name || 'Document'}</span>
              <span className="font-mono text-[11px] text-slate-800 break-words">{f.document_value}</span>
            </div>
          )}
        </div>
      )}
      {f.vendor_action && (
        <p className="text-[11px] text-slate-600">
          <span className="font-semibold text-slate-700">Ask vendor: </span>
          {f.vendor_action}
        </p>
      )}
    </div>
  );
}

export const AIDecisionPanel: FC<AIDecisionPanelProps> = ({ applicationId, applicationStatus, onChanged, onRejectWithReasons, onApprove }) => {
  const [run, setRun] = useState<DecisionRun | null>(null);
  const [history, setHistory] = useState<DecisionRunSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [starting, setStarting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState('');
  const [sending, setSending] = useState(false);
  const [sentNote, setSentNote] = useState<string | null>(null);
  const [showObservations, setShowObservations] = useState(false);
  const onChangedRef = useRef(onChanged);
  useEffect(() => {
    onChangedRef.current = onChanged;
  }, [onChanged]);

  const isActive = run?.status === 'queued' || run?.status === 'running';

  const loadHistory = useCallback(async () => {
    try {
      setHistory(await listApplicationRuns(applicationId));
    } catch {
      /* non-critical */
    }
  }, [applicationId]);

  // Initial load whenever the selected application changes.
  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    setSentNote(null);
    setRun(null);
    getLatestDecision(applicationId)
      .then((r) => {
        if (!cancelled) setRun(r);
      })
      .catch((e) => !cancelled && setError(e.message || 'Failed to load AI decision.'))
      .finally(() => !cancelled && setLoading(false));
    loadHistory();
    return () => {
      cancelled = true;
    };
  }, [applicationId, loadHistory]);

  // Live polling while a run is executing.
  useEffect(() => {
    if (!run || !isActive) return;
    const timer = setInterval(async () => {
      try {
        const fresh = await getDecisionRun(run.id);
        setRun(fresh);
        if (fresh.status === 'completed' || fresh.status === 'failed') {
          loadHistory();
          onChangedRef.current?.();
        }
      } catch {
        /* keep polling */
      }
    }, 900);
    return () => clearInterval(timer);
  }, [run?.id, isActive, loadHistory]);

  // Seed the editable vendor message from each completed decision.
  useEffect(() => {
    setMessage(run?.decision?.vendor_message || '');
  }, [run?.id, run?.decision?.vendor_message]);

  const handleRun = async (forceReparse = false) => {
    setStarting(true);
    setError(null);
    setSentNote(null);
    try {
      setRun(await startDecisionRun(applicationId, forceReparse));
    } catch (e: any) {
      setError(e.message || 'Failed to start the AI Decision Engine.');
    } finally {
      setStarting(false);
    }
  };

  const handleSend = async () => {
    setSending(true);
    setError(null);
    try {
      await sendDecisionToVendor(applicationId, message.trim() || undefined);
      setSentNote('Request sent. The application is now awaiting the vendor’s clarification.');
      onChangedRef.current?.();
    } catch (e: any) {
      setError(e.message || 'Failed to send the request to the vendor.');
    } finally {
      setSending(false);
    }
  };

  const decision = run?.status === 'completed' ? run.decision : null;
  const matrix = useMemo(() => (run?.evidence_matrix || []).filter((r) => r.status !== 'not_applicable'), [run]);
  const matrixDocs = useMemo(() => {
    const seen = new Map<string, string>();
    for (const row of matrix) for (const c of row.cells) if (!seen.has(c.document_id)) seen.set(c.document_id, c.document_label);
    return Array.from(seen.entries());
  }, [matrix]);

  const rejectReason = useMemo(() => {
    if (!decision) return '';
    return decision.reasons
      .filter((r) => r.severity === 'critical' || r.severity === 'major')
      .map((r) => `• ${r.title}: ${r.detail}`)
      .join('\n');
  }, [decision]);

  // ---------------------------------------------------------------------------
  // Render
  // ---------------------------------------------------------------------------

  const runButton = (
    <div className="flex items-center gap-1.5 shrink-0">
      <button
        type="button"
        disabled={starting || isActive}
        onClick={() => handleRun(false)}
        className="inline-flex items-center space-x-1.5 px-3.5 py-1.5 rounded-xl bg-[#07569B] hover:bg-[#064780] text-white text-xs font-semibold cursor-pointer shadow-xs disabled:opacity-50"
      >
        {isActive || starting ? <CircleNotch size={13} className="animate-spin" /> : <Brain size={13} weight="bold" />}
        <span>{isActive ? 'Running…' : run ? 'Re-run engine' : 'Run AI Decision Engine'}</span>
      </button>
      {run && !isActive && (
        <button
          type="button"
          disabled={starting}
          onClick={() => handleRun(true)}
          title="Ignore cached Nemotron Parse output and re-read every document"
          className="p-1.5 rounded-xl border border-slate-200 bg-slate-50 hover:bg-slate-100 text-slate-600 cursor-pointer disabled:opacity-50"
        >
          <ArrowsClockwise size={14} />
        </button>
      )}
    </div>
  );

  if (loading) {
    return (
      <div className="bg-white p-10 rounded-3xl border border-slate-200/80 text-center text-xs text-slate-500">
        <ArrowClockwise size={22} className="animate-spin mx-auto mb-2 text-[#07569B]" />
        Loading AI decision…
      </div>
    );
  }

  return (
    <div className="space-y-5">
      {error && (
        <div className="p-3 rounded-2xl border border-rose-200 bg-rose-50 text-rose-900 text-xs flex items-center gap-2">
          <WarningCircle size={16} weight="bold" className="shrink-0" /> {error}
        </div>
      )}

      {/* Empty state */}
      {!run && (
        <Section
          icon={<Brain size={18} weight="bold" />}
          title="AI Decision Engine"
          subtitle="Cross-checks the application form against every uploaded document"
          right={runButton}
        >
          <div className="p-5 rounded-2xl bg-slate-50 border border-dashed border-slate-200 text-xs text-slate-600 space-y-2">
            <p className="font-semibold text-slate-800">No decision has been computed for this application yet.</p>
            <p>
              The engine reads each document with NVIDIA Nemotron Parse, extracts the company name, PAN, GSTIN, CIN, mobile
              numbers, address and bank details, compares them with the form and with each other, screens for bank
              accounts or GSTINs already used by other vendors, and recommends <b>Approve</b>, <b>Needs Review</b> or{' '}
              <b>Reject</b> with the reasons.
            </p>
          </div>
        </Section>
      )}

      {/* Decision banner */}
      {decision && (
        <div className={`p-5 rounded-3xl border shadow-xl shadow-slate-200/60 space-y-4 text-left ${OUTCOME_STYLE[decision.outcome].box}`}>
          <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-3">
            <div className="flex items-start space-x-3">
              <div className="w-11 h-11 rounded-2xl bg-white shadow-2xs flex items-center justify-center shrink-0">
                {OUTCOME_STYLE[decision.outcome].icon}
              </div>
              <div>
                <div className="flex flex-wrap items-center gap-2">
                  <span className="text-[10px] uppercase tracking-wider font-bold opacity-70">AI recommendation</span>
                  <span className={`px-2.5 py-0.5 rounded-full text-[11px] font-bold uppercase tracking-wide ${OUTCOME_STYLE[decision.outcome].chip}`}>
                    {decision.label}
                  </span>
                </div>
                <p className="text-sm font-bold mt-1 leading-snug">{decision.headline}</p>
                {decision.narrative && <p className="text-xs mt-1.5 leading-relaxed opacity-90">{decision.narrative}</p>}
              </div>
            </div>
            {runButton}
          </div>

          <div className="flex flex-wrap gap-2">
            <Metric
              label="Risk score"
              value={`${decision.risk_score}/100`}
              barPct={decision.risk_score}
              barCls={decision.risk_score >= 40 ? 'bg-rose-500' : decision.risk_score >= 15 ? 'bg-amber-500' : 'bg-emerald-500'}
            />
            <Metric label="Confidence" value={`${decision.confidence}%`} barPct={decision.confidence} barCls={OUTCOME_STYLE[decision.outcome].bar} />
            <Metric label="Attributes corroborated" value={`${decision.coverage}%`} barPct={decision.coverage} barCls="bg-[#07569B]" />
            <Metric
              label="Issues"
              value={`${decision.counts.critical ?? 0} · ${decision.counts.major ?? 0} · ${decision.counts.warning ?? 0}`}
              hint="critical · major · minor"
            />
          </div>

          <div className="flex flex-wrap items-center justify-between gap-2 pt-1 text-[11px]">
            <span className="opacity-75">
              Decided by {decision.decided_by} · run {run?.trigger} by {run?.triggered_by} ·{' '}
              {run?.completed_at ? new Date(run.completed_at).toLocaleString() : ''}
              {run?.duration_ms ? ` · ${(run.duration_ms / 1000).toFixed(1)}s` : ''}
            </span>
            <div className="flex items-center gap-2">
              {decision.outcome === 'reject' && onRejectWithReasons && applicationStatus !== 'rejected' && applicationStatus !== 'approved' && (
                <button
                  type="button"
                  onClick={() => onRejectWithReasons(rejectReason)}
                  className="px-3 py-1.5 rounded-xl bg-rose-600 hover:bg-rose-700 text-white text-xs font-semibold cursor-pointer"
                >
                  Reject with these reasons
                </button>
              )}
              {decision.outcome === 'approve' && onApprove && applicationStatus !== 'rejected' && applicationStatus !== 'approved' && (
                <button
                  type="button"
                  onClick={onApprove}
                  className="px-3 py-1.5 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-semibold cursor-pointer"
                >
                  Approve application
                </button>
              )}
            </div>
          </div>
        </div>
      )}

      {run?.status === 'failed' && (
        <div className="p-4 rounded-2xl border border-rose-200 bg-rose-50 text-xs text-rose-900 flex items-start justify-between gap-3">
          <div>
            <p className="font-bold">The engine run failed.</p>
            <p className="mt-0.5">{run.error}</p>
          </div>
          {runButton}
        </div>
      )}

      {/* Live pipeline */}
      {run && (
        <Section
          icon={<FileMagnifyingGlass size={18} weight="bold" />}
          title={isActive ? 'Live run' : 'Pipeline stages'}
          subtitle={isActive ? 'Each stage updates as it executes' : `Engine v${run.engine_version ?? ''} · ${run.models?.llm_enabled ? `reasoning model ${run.models?.reasoning}` : 'NVIDIA reasoning disabled (rules only)'}`}
          right={!decision && !isActive && run.status !== 'failed' ? runButton : undefined}
        >
          <ol className="relative space-y-0.5">
            {run.stages.map((s, i) => (
              <li key={s.key} className="flex items-start gap-3 py-1.5">
                <div className="flex flex-col items-center pt-0.5">
                  <StageIcon status={s.status} />
                  {i < run.stages.length - 1 && <span className="w-px flex-1 min-h-[14px] bg-slate-200 mt-1" />}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between gap-2">
                    <p className={`text-xs font-semibold ${s.status === 'pending' ? 'text-slate-400' : 'text-slate-800'}`}>{s.label}</p>
                    {s.duration_ms !== null && s.status !== 'pending' && s.status !== 'running' && (
                      <span className="text-[10px] font-mono text-slate-400 shrink-0">{s.duration_ms} ms</span>
                    )}
                  </div>
                  {s.summary && <p className="text-[11px] text-slate-500 leading-relaxed break-words">{s.summary}</p>}
                </div>
              </li>
            ))}
          </ol>
        </Section>
      )}

      {/* Reasons */}
      {decision && (
        <Section
          icon={<WarningCircle size={18} weight="bold" />}
          title={`Reasons (${decision.reasons.length})`}
          subtitle="Every finding that affected the recommendation, most severe first"
          right={
            decision.observations.length > 0 ? (
              <button
                type="button"
                onClick={() => setShowObservations((v) => !v)}
                className="text-[11px] font-semibold text-[#07569B] hover:underline cursor-pointer shrink-0"
              >
                {showObservations ? 'Hide' : 'Show'} {decision.observations.length} observation(s)
              </button>
            ) : undefined
          }
        >
          {decision.reasons.length === 0 ? (
            <p className="text-xs text-emerald-700 font-semibold flex items-center gap-1.5">
              <CheckCircle size={15} weight="fill" /> No issues — every checked attribute is consistent.
            </p>
          ) : (
            <div className="space-y-2">{decision.reasons.map((f, i) => <FindingCard key={`${f.code}-${i}`} f={f} />)}</div>
          )}
          {showObservations && (
            <div className="space-y-2 pt-1">{decision.observations.map((f, i) => <FindingCard key={`o-${f.code}-${i}`} f={f} />)}</div>
          )}
        </Section>
      )}

      {/* Cross-reference matrix */}
      {decision && matrix.length > 0 && (
        <Section
          icon={<Table size={18} weight="bold" />}
          title="Cross-reference matrix"
          subtitle="Form value vs. what each document says"
        >
          <div className="overflow-x-auto -mx-1">
            <table className="w-full text-[11px] border-separate border-spacing-1 min-w-[560px]">
              <thead>
                <tr className="text-slate-500 uppercase tracking-wider text-[10px]">
                  <th className="text-left font-semibold px-1">Attribute</th>
                  <th className="text-left font-semibold px-1">Form</th>
                  {matrixDocs.map(([id, label]) => (
                    <th key={id} className="text-left font-semibold px-1">{label}</th>
                  ))}
                  <th className="text-left font-semibold px-1">Result</th>
                </tr>
              </thead>
              <tbody>
                {matrix.map((row) => (
                  <tr key={row.attribute} className="align-top">
                    <td className="px-1.5 py-1 font-semibold text-slate-700 whitespace-nowrap">{row.label}</td>
                    <td className="px-2 py-1 rounded-lg bg-slate-50 border border-slate-200 font-mono text-slate-800 break-words max-w-[180px]">
                      {row.form_value || <span className="text-slate-400 font-sans">—</span>}
                    </td>
                    {matrixDocs.map(([docId]) => {
                      const cell = row.cells.find((c) => c.document_id === docId);
                      if (!cell) return <td key={docId} className="px-2 py-1 text-slate-300">·</td>;
                      return (
                        <td key={docId} className={`px-2 py-1 rounded-lg border break-words max-w-[180px] ${CELL_STYLE[cell.status]}`} title={cell.note}>
                          <span className="font-mono">{cell.value || 'not found'}</span>
                          {cell.note && cell.status !== 'not_found' && <span className="block text-[9px] opacity-70 font-sans">{cell.note}</span>}
                        </td>
                      );
                    })}
                    <td className="px-1 py-1">
                      <span className={`px-1.5 py-0.5 rounded-md border text-[10px] font-bold whitespace-nowrap ${ROW_STATUS[row.status].cls}`}>
                        {ROW_STATUS[row.status].label}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Section>
      )}

      {/* Vendor communication */}
      {decision && decision.outcome !== 'approve' && decision.vendor_message && (
        <Section
          icon={<PaperPlaneTilt size={18} weight="bold" />}
          title="What the vendor needs to do"
          subtitle="Drafted from the findings — edit before sending if needed"
        >
          <textarea
            rows={Math.min(14, message.split('\n').length + 1)}
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            className="w-full p-3 rounded-xl border border-slate-200 text-xs focus:outline-none focus:border-[#07569B] bg-slate-50/50 font-sans leading-relaxed"
          />
          <div className="flex flex-wrap items-center justify-between gap-2">
            <p className="text-[11px] text-slate-500">
              {CLARIFIABLE.has(applicationStatus)
                ? 'Sends a clarification request and moves the application to “Clarification required”.'
                : `Clarification can't be requested while the application is '${applicationStatus.replace(/_/g, ' ')}'.`}
            </p>
            <button
              type="button"
              disabled={sending || !message.trim() || !CLARIFIABLE.has(applicationStatus)}
              onClick={handleSend}
              className="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-xl bg-amber-600 hover:bg-amber-700 text-white text-xs font-semibold cursor-pointer disabled:opacity-50"
            >
              {sending ? <CircleNotch size={13} className="animate-spin" /> : <PaperPlaneTilt size={13} weight="bold" />}
              <span>Send to vendor</span>
            </button>
          </div>
          {sentNote && <p className="text-[11px] font-semibold text-emerald-700">{sentNote}</p>}
        </Section>
      )}

      {/* Extracted identity per document */}
      {decision && run && run.documents.length > 0 && (
        <Section icon={<Sparkle size={18} weight="bold" />} title="Extracted identity per document" subtitle="What the engine read from each file">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
            {run.documents.map((d) => (
              <div key={d.document_id} className={`p-3 rounded-2xl border text-[11px] ${d.readable ? 'border-slate-200 bg-slate-50/60' : 'border-rose-200 bg-rose-50/60'}`}>
                <div className="flex items-center justify-between gap-2">
                  <p className="font-bold text-slate-800">{d.label}</p>
                  <span className="text-[9px] uppercase font-bold text-slate-400">{d.readable ? d.extraction_method : 'unreadable'}</span>
                </div>
                <p className="text-slate-400 font-mono text-[10px] mb-1.5">{d.file_name}</p>
                {d.readable ? (
                  <dl className="grid grid-cols-[auto_1fr] gap-x-2 gap-y-0.5">
                    {Object.entries(d.fields).map(([k, v]) => (
                      <div key={k} className="contents">
                        <dt className="text-slate-500">{k.replace(/_/g, ' ')}</dt>
                        <dd className="font-mono text-slate-800 break-words">{Array.isArray(v) ? v.join(', ') : v}</dd>
                      </div>
                    ))}
                  </dl>
                ) : (
                  <p className="text-rose-800">{d.error || 'No text could be extracted.'}</p>
                )}
              </div>
            ))}
          </div>
        </Section>
      )}

      {/* History */}
      {history.length > 1 && (
        <Section icon={<ClockCounterClockwise size={18} weight="bold" />} title={`Run history (${history.length})`}>
          <div className="space-y-1">
            {history.map((h) => (
              <button
                key={h.id}
                type="button"
                onClick={async () => setRun(await getDecisionRun(h.id))}
                className={`w-full flex items-center justify-between gap-2 px-3 py-2 rounded-xl border text-[11px] text-left cursor-pointer hover:bg-slate-50 ${h.id === run?.id ? 'border-[#07569B] bg-blue-50/50' : 'border-slate-200'}`}
              >
                <span className="text-slate-600">
                  {new Date(h.started_at).toLocaleString()} · {h.trigger}
                </span>
                {h.decision ? (
                  <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold uppercase ${OUTCOME_STYLE[h.decision.outcome].chip}`}>
                    {h.decision.label} · {h.decision.risk_score}
                  </span>
                ) : (
                  <span className="text-slate-400 uppercase text-[10px] font-bold">{h.status}</span>
                )}
              </button>
            ))}
          </div>
        </Section>
      )}
    </div>
  );
};

export default AIDecisionPanel;
