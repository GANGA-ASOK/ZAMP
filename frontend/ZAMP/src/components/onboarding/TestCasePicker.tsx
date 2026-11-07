import type { FC } from 'react';
import { useEffect, useState } from 'react';
import { CircleNotch, Flask, Info, WarningCircle, X } from '@phosphor-icons/react';
import { listTestCases, type TestCase } from '../../services/testCaseService';

interface TestCasePickerProps {
  /** Load the case into the form. Resolves once fields and documents are filled. */
  onLoad: (testCase: TestCase) => Promise<void>;
}

const EXPECTED_STYLE: Record<TestCase['expected'], string> = {
  approve: 'bg-emerald-50 text-emerald-700 border-emerald-200',
  review: 'bg-amber-50 text-amber-800 border-amber-300',
  reject: 'bg-rose-50 text-rose-700 border-rose-200',
};

const EXPECTED_LABEL: Record<TestCase['expected'], string> = {
  approve: 'Approve',
  review: 'Needs Review',
  reject: 'Reject',
};

/**
 * Testing helper: pick one of the AI Decision Engine test cases to pre-fill
 * all four steps and upload that case's documents.
 */
export const TestCasePicker: FC<TestCasePickerProps> = ({ onLoad }) => {
  const [cases, setCases] = useState<TestCase[]>([]);
  const [unavailable, setUnavailable] = useState(false);
  const [selected, setSelected] = useState('');
  const [loaded, setLoaded] = useState<TestCase | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    listTestCases()
      .then(setCases)
      .catch(() => setUnavailable(true));
  }, []);

  if (unavailable) return null;

  const handleChange = async (key: string) => {
    setSelected(key);
    setError(null);
    const tc = cases.find((c) => c.key === key);
    if (!tc) return;
    setLoading(true);
    try {
      await onLoad(tc);
      setLoaded(tc);
    } catch (e: any) {
      setError(e?.message || 'Failed to load the test case.');
      setLoaded(null);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="mb-5 rounded-2xl border border-dashed border-sky-300 bg-sky-50/60 p-3 text-xs space-y-2">
      <div className="flex flex-wrap items-center gap-2">
        <span className="inline-flex items-center gap-1 font-semibold text-[#07569B]">
          <Flask size={14} weight="fill" />
          Test case
        </span>
        <select
          value={selected}
          disabled={loading || cases.length === 0}
          onChange={(e) => handleChange(e.target.value)}
          className="flex-1 min-w-[220px] px-2.5 py-1.5 rounded-lg border border-sky-200 bg-white text-slate-800 focus:outline-none focus:border-[#07569B] cursor-pointer disabled:opacity-60"
        >
          <option value="" disabled>
            {cases.length ? 'Select a case to pre-fill the form and upload its documents…' : 'Loading test cases…'}
          </option>
          {cases.map((c, i) => (
            <option key={c.key} value={c.key}>
              {i + 1}. {c.title} — expected: {EXPECTED_LABEL[c.expected]}
            </option>
          ))}
        </select>
        {loading && (
          <span className="inline-flex items-center gap-1 text-slate-500">
            <CircleNotch size={13} className="animate-spin" /> Creating draft & uploading documents…
          </span>
        )}
        {loaded && !loading && (
          <button
            type="button"
            onClick={() => setLoaded(null)}
            className="p-1 rounded-md text-slate-400 hover:text-slate-600 hover:bg-white cursor-pointer"
            title="Hide details"
          >
            <X size={12} weight="bold" />
          </button>
        )}
      </div>

      {error && (
        <p className="flex items-center gap-1.5 text-rose-700">
          <WarningCircle size={14} weight="bold" className="shrink-0" /> {error}
        </p>
      )}

      {loaded && !loading && (
        <div className="rounded-xl bg-white border border-sky-200 p-2.5 space-y-1.5">
          <div className="flex flex-wrap items-center gap-2">
            <span className="font-semibold text-slate-800">{loaded.title}</span>
            <span className={`px-2 py-0.5 rounded-full border text-[10px] font-bold uppercase ${EXPECTED_STYLE[loaded.expected]}`}>
              Expected AI decision: {EXPECTED_LABEL[loaded.expected]}
            </span>
          </div>
          <p className="text-slate-600 leading-relaxed">{loaded.story}</p>
          <p className="text-slate-500">
            Uploaded: {loaded.documents.map((d) => d.file_name).join(', ')}. All steps are filled — click through and
            submit, then open the application in the admin portal.
          </p>
          {loaded.requires_first && (
            <p className="flex items-start gap-1.5 text-amber-800 bg-amber-50 border border-amber-200 rounded-lg px-2 py-1.5">
              <Info size={14} weight="bold" className="shrink-0 mt-px" />
              <span>
                This case only gives the expected result if <b>{loaded.requires_first}</b> was submitted first — its
                bank account is reused here.
              </span>
            </p>
          )}
        </div>
      )}
    </div>
  );
};

export default TestCasePicker;
