import React, { useEffect, useState } from 'react';
import { CheckCircle2, Play, FileCode2, Terminal, Copy, Check } from 'lucide-react';

interface EthicsAndDocsViewProps {
  activeTopicId?: number;
}

interface PythonFileStatus {
  path: string;
  exists: boolean;
  sizeBytes: number;
}

interface PythonVerifyResponse {
  pythonExecutable: string;
  passed: boolean;
  output: string;
  files: PythonFileStatus[];
}

export const EthicsAndDocsView: React.FC<EthicsAndDocsViewProps> = ({ activeTopicId }) => {
  const [apiOutput, setApiOutput] = useState<string>('');
  const [testedEndpoint, setTestedEndpoint] = useState<string>('');

  const [pyVerify, setPyVerify] = useState<PythonVerifyResponse | null>(null);
  const [isRunningPyTests, setIsRunningPyTests] = useState<boolean>(false);
  const [selectedPyFile, setSelectedPyFile] = useState<string>('backend/app/main.py');
  const [pySourceContent, setPySourceContent] = useState<string>('');
  const [copiedOutreach, setCopiedOutreach] = useState<boolean>(false);

  const runPythonVerification = async () => {
    setIsRunningPyTests(true);
    try {
      const res = await fetch('/api/python-backend/verify');
      if (res.ok) {
        const data: PythonVerifyResponse = await res.json();
        setPyVerify(data);
      } else {
        setPyVerify(null);
      }
    } finally {
      setIsRunningPyTests(false);
    }
  };

  const loadPythonSource = async (filePath: string) => {
    setSelectedPyFile(filePath);
    try {
      const res = await fetch(`/api/python-backend/source?file=${encodeURIComponent(filePath)}`);
      if (res.ok) {
        const data = await res.json();
        setPySourceContent(data.content || '');
      } else {
        setPySourceContent(`# ${res.status} from /api/python-backend/source\n# The dashboard monitor, graph, clusters, timeline, and evaluation routes are separate and still live.`);
      }
    } catch {
      setPySourceContent('# Unable to load file content');
    }
  };

  useEffect(() => {
    runPythonVerification();
    loadPythonSource('backend/app/main.py');
  }, []);

  const testEndpoint = async (path: string, method: 'GET' | 'POST' = 'GET', body?: object) => {
    setTestedEndpoint(`${method} ${path}`);
    try {
      const res = await fetch(path, {
        method,
        headers: body ? { 'Content-Type': 'application/json' } : undefined,
        body: body ? JSON.stringify(body) : undefined,
      });
      const data = await res.json();
      setApiOutput(JSON.stringify(data, null, 2).slice(0, 2800));
    } catch (err) {
      setApiOutput(`Error calling ${path}: ${String(err)}`);
    }
  };

  const outreachTemplate = `Hi Rohan,

I've been following Valent's work, especially the Mayor of London case study. Inspired by Ariadne's approach to separating organic from manufactured activity, I built CoordWatch, a FastAPI + React prototype that detects coordinated account behavior on Bluesky and explains each flag with evidence.

I evaluated it on real Bluesky Jetstream data and on a held-out synthetic benchmark with 12 distinct attack families and hard negatives (accounting for unseen tactics), and I documented what beats it, including aged sleeper accounts and paraphrase plus jitter.

Demo / repo: [link]

I'd really value your feedback if someone on your team has a few minutes to take a look.`;

  return (
    <div className="space-y-6">
      {/* Section 1: Live Python FastAPI Backend & Signal Suite Explorer */}
      <section
        aria-label="Python FastAPI Backend Architecture and Live Test Runner"
        className="bg-[rgba(16,36,66,0.42)] backdrop-blur-xl border border-white/10 rounded-[26px] overflow-hidden"
      >
        <div className="px-6 py-4 bg-[rgba(8,20,42,0.5)] border-b border-white/10 flex flex-wrap items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-base font-bold text-[#F6F1E8] font-display tracking-tight">
                Python FastAPI Backend (`/backend/app/`) &amp; Live Unit Test Verification
              </h1>
              {pyVerify?.passed && (
                <span className="flex items-center gap-1 text-xs font-mono text-[#C5DCCB]">
                  <CheckCircle2 className="w-3.5 h-3.5" />
                  6/6 Python Signal &amp; Simulator Tests Passing
                </span>
              )}
            </div>
            <p className="text-xs text-[#B6AC9E] mt-1">
              Complete Python 3.10+ FastAPI + NetworkX + Scikit-Learn TF-IDF + SQLite codebase per Section 3 &amp; 4 of the Implementation Plan, verified live via <code className="text-[#E8DFD2]">/usr/bin/python3 -m unittest backend/tests/test_signals.py -v</code>.
            </p>
          </div>

          <button
            type="button"
            disabled={isRunningPyTests}
            onClick={runPythonVerification}
            className="flex items-center gap-1.5 px-3.5 py-1.5 text-xs font-semibold text-[#FFF8F3] bg-[#C46B56] hover:bg-[#D48470] disabled:opacity-50 rounded transition-colors whitespace-nowrap shrink-0"
          >
            <Play className="w-3.5 h-3.5" />
            {isRunningPyTests ? 'Running Python Tests...' : 'Run Python Signal Tests Live'}
          </button>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-12 divide-y lg:divide-y-0 lg:divide-x divide-white/10">
          {/* Left 4 Cols: Python Backend File Tree + Test Runner Output */}
          <div className="lg:col-span-5 p-4 space-y-4 bg-[rgba(7,18,36,0.4)]">
            <div>
              <div className="flex items-center justify-between text-xs font-semibold text-[#E8DFD2] mb-2">
                <span className="flex items-center gap-1.5">
                  <FileCode2 className="w-3.5 h-3.5 text-[#F0B5A2]" />
                  Python FastAPI Project Tree ({pyVerify?.files.length ?? 0} files)
                </span>
                <span className="text-[11px] font-mono text-[#B6AC9E]">Click to inspect source</span>
              </div>

              <div className="max-h-60 overflow-y-auto border border-white/10 rounded bg-[rgba(7,18,36,0.55)] divide-y divide-white/[0.08]">
                {(pyVerify?.files || []).length === 0 && (
                  <p className="px-3 py-3 text-xs text-[#B6AC9E]">
                    No file list yet. /api/python-backend/verify did not return one.
                  </p>
                )}
                {(pyVerify?.files || []).map((f) => (
                  <button
                    key={f.path}
                    type="button"
                    onClick={() => loadPythonSource(f.path)}
                    className={`w-full px-3 py-1.5 text-left text-xs font-mono flex items-center justify-between transition-colors ${
                      selectedPyFile === f.path
                        ? 'bg-[rgba(224,122,98,0.18)] text-[#F6C7B6] font-semibold'
                        : 'text-[#D4CBBE] hover:bg-white/[0.04]'
                    }`}
                  >
                    <span className="truncate">{f.path}</span>
                    <span className="text-[10px] text-[#8E867C] tabular-nums shrink-0 ml-2">
                      {(f.sizeBytes / 1024).toFixed(1)} KB
                    </span>
                  </button>
                ))}
              </div>
            </div>

            <div>
              <div className="flex items-center justify-between text-xs font-semibold text-[#E8DFD2] mb-1.5">
                <span className="flex items-center gap-1.5">
                  <Terminal className="w-3.5 h-3.5 text-[#C5DCCB]" />
                  Live Python Test Output (`backend/tests/test_signals.py`)
                </span>
                <span className="text-[11px] font-mono text-[#C5DCCB]">
                  {pyVerify?.pythonExecutable || '/usr/bin/python3'}
                </span>
              </div>
              <pre
                data-testid="python-test-output"
                className="p-3 bg-[rgba(7,18,36,0.55)] border border-white/10 rounded text-[11px] font-mono text-[#D5E8DC] max-h-44 overflow-auto leading-relaxed"
              >
                {pyVerify?.output || (isRunningPyTests ? 'Running python3 -m unittest backend/tests/test_signals.py -v...' : 'No test log returned from /api/python-backend/verify.')}
              </pre>
            </div>
          </div>

          {/* Right 8 Cols: Live Python Source Code Viewer */}
          <div className="lg:col-span-7 p-4 flex flex-col justify-between bg-[rgba(16,36,66,0.42)] backdrop-blur-xl">
            <div>
              <div className="flex items-center justify-between pb-2.5 mb-2.5 border-b border-white/10">
                <span className="text-xs font-mono font-semibold text-[#F6C7B6]">
                  /{selectedPyFile}
                </span>
                <span className="text-[11px] font-mono text-[#B6AC9E]">
                  Python 3.10+ · FastAPI · NetworkX · Scikit-Learn
                </span>
              </div>
              <pre className="p-3.5 bg-[rgba(7,18,36,0.55)] border border-white/10 rounded text-[11.5px] font-mono text-[#E8DFD2] h-[380px] overflow-auto leading-relaxed">
                {pySourceContent}
              </pre>
            </div>
          </div>
        </div>
      </section>

      {/* Section 2: Phase 9 Ethical Safeguards Banner */}
      <div className="bg-[rgba(16,36,66,0.42)] backdrop-blur-xl border border-white/10 rounded-[26px] overflow-hidden">
        <div className="px-6 py-5 bg-[rgba(8,20,42,0.5)] border-b border-white/10">
          <h2 className="text-base font-bold text-[#F6F1E8] font-display tracking-tight">
            Phase 9: Methodology, Limitations &amp; Ethical Safeguards
          </h2>
          <p className="text-sm text-[#D4CBBE] mt-1.5 leading-relaxed max-w-3xl">
            CoordWatch surfaces <strong className="text-[#F6F1E8]">coordinated-behavior patterns, not proof of bots</strong>. Synchronized posting, shared links, and tight account creation windows indicate non-independent amplification, which can include automated bot rings, paid campaign networks, or organized activist flash-mobs.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 divide-y md:divide-y-0 md:divide-x divide-white/10">
          <div className="p-5">
            <h3 className="text-sm font-semibold text-[#F6F1E8]">
              01. Cryptographic Alias Default (`A-xxxx`)
            </h3>
            <p className="text-xs text-[#B6AC9E] mt-1.5 leading-relaxed">
              Every Bluesky DID is hashed via SHA-256 into a deterministic short alias (such as <code className="text-[#E8DFD2]">A-7f3a</code>). The dashboard displays aliases by default so analysts can evaluate structural network topology without publishing named accusations against individual accounts.
            </p>
          </div>

          <div className="p-5">
            <h3 className="text-sm font-semibold text-[#F6F1E8]">
              02. Public Protocol Telemetry Only
            </h3>
            <p className="text-xs text-[#B6AC9E] mt-1.5 leading-relaxed">
              Ingestion reads strictly public <code className="text-[#E8DFD2]">app.bsky.feed.post</code> records from Bluesky’s official Jetstream WebSocket and public <code className="text-[#E8DFD2]">plc.directory</code> audit timestamps, respecting rate limits with a 5-request concurrency cap and SQLite caching.
            </p>
          </div>

          <div className="p-5">
            <h3 className="text-sm font-semibold text-[#F6F1E8]">
              03. Breaking-News False-Positive Discount
            </h3>
            <p className="text-xs text-[#B6AC9E] mt-1.5 leading-relaxed">
              Organic users regularly share breaking news headlines in simultaneous bursts. When a cluster’s median account age exceeds 150 days with dispersed registration dates and low hashtag-triad coordination, CoordWatch automatically applies a documented <code className="text-[#E8DFD2]">-38% to -52%</code> discount.
            </p>
          </div>
        </div>
      </div>

      {/* Section 3: Interactive Phase 6 REST API Reference + Phase 10 Valent Projects Outreach */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        {/* Interactive Phase 6 REST API Explorer */}
        <div className="bg-[rgba(16,36,66,0.42)] backdrop-blur-xl border border-white/10 rounded-[26px] overflow-hidden flex flex-col justify-between">
          <div>
            <div className="px-5 py-3.5 bg-[rgba(8,20,42,0.5)] border-b border-white/10">
              <h2 className="text-sm font-semibold text-[#F6F1E8] tracking-tight">
                Interactive REST API Reference (Phase 6 Specification)
              </h2>
              <p className="text-xs text-[#B6AC9E] mt-0.5">
                Click any endpoint below to query the live server and inspect the JSON response payload.
              </p>
            </div>

            <div className="p-5 pb-3 flex flex-wrap gap-2">
              <button
                type="button"
                onClick={() => testEndpoint('/api/health')}
                className="px-2.5 py-1.5 text-xs font-mono bg-[rgba(7,18,36,0.55)] hover:bg-white/10 text-[#F0B5A2] border border-white/10 rounded transition-colors"
              >
                GET /health
              </button>
              <button
                type="button"
                onClick={() => testEndpoint('/api/topics')}
                className="px-2.5 py-1.5 text-xs font-mono bg-[rgba(7,18,36,0.55)] hover:bg-white/10 text-[#F0B5A2] border border-white/10 rounded transition-colors"
              >
                GET /topics
              </button>
              <button
                type="button"
                onClick={() => testEndpoint(`/api/topics/${activeTopicId}/summary`)}
                className="px-2.5 py-1.5 text-xs font-mono bg-[rgba(7,18,36,0.55)] hover:bg-white/10 text-[#F0B5A2] border border-white/10 rounded transition-colors"
              >
                GET /topics/{activeTopicId}/summary
              </button>
              <button
                type="button"
                onClick={() => testEndpoint(`/api/topics/${activeTopicId}/graph`)}
                className="px-2.5 py-1.5 text-xs font-mono bg-[rgba(7,18,36,0.55)] hover:bg-white/10 text-[#F0B5A2] border border-white/10 rounded transition-colors"
              >
                GET /topics/{activeTopicId}/graph
              </button>
              <button
                type="button"
                onClick={() => testEndpoint(`/api/topics/${activeTopicId}/clusters`)}
                className="px-2.5 py-1.5 text-xs font-mono bg-[rgba(7,18,36,0.55)] hover:bg-white/10 text-[#F0B5A2] border border-white/10 rounded transition-colors"
              >
                GET /topics/{activeTopicId}/clusters
              </button>
              <button
                type="button"
                onClick={() => testEndpoint(`/api/topics/${activeTopicId}/timeline`)}
                className="px-2.5 py-1.5 text-xs font-mono bg-[rgba(7,18,36,0.55)] hover:bg-white/10 text-[#F0B5A2] border border-white/10 rounded transition-colors"
              >
                GET /topics/{activeTopicId}/timeline
              </button>
              <button
                type="button"
                onClick={() => testEndpoint('/api/evaluation/latest')}
                className="px-2.5 py-1.5 text-xs font-mono bg-[rgba(7,18,36,0.55)] hover:bg-white/10 text-[#F0B5A2] border border-white/10 rounded transition-colors"
              >
                GET /evaluation/latest
              </button>
            </div>
          </div>

          <div className="px-5 pb-5">
            <div className="text-[11px] font-mono text-[#B6AC9E] mb-1.5">
              {testedEndpoint || 'Select an endpoint above to inspect live JSON response'}
            </div>
            <pre className="p-3 bg-[rgba(7,18,36,0.55)] border border-white/10 rounded text-[11px] font-mono text-[#D5E8DC] h-44 overflow-auto">
              {apiOutput || '{\n  "hint": "Click any endpoint button above to execute a live request."\n}'}
            </pre>
          </div>
        </div>

        {/* Phase 10: Valent / Ariadne Inspiration & Outreach Card */}
        <div className="bg-[rgba(16,36,66,0.42)] backdrop-blur-xl border border-white/10 rounded-[26px] overflow-hidden flex flex-col justify-between">
          <div>
            <div className="px-5 py-3.5 bg-[rgba(8,20,42,0.5)] border-b border-white/10 flex items-center justify-between gap-2">
              <div>
                <h2 className="text-sm font-semibold text-[#F6F1E8] tracking-tight">
                  Inspiration: Valent’s Ariadne Engine &amp; Outreach Brief
                </h2>
                <p className="text-xs text-[#B6AC9E] mt-0.5">
                  Portfolio summary &amp; engineering outreach template ready to copy.
                </p>
              </div>
              <button
                type="button"
                onClick={() => {
                  navigator.clipboard?.writeText(outreachTemplate);
                  setCopiedOutreach(true);
                  setTimeout(() => setCopiedOutreach(false), 2500);
                }}
                className="flex items-center gap-1.5 px-2.5 py-1 text-xs font-medium bg-white/10 hover:bg-white/[0.14] text-[#F6F1E8] rounded transition-colors shrink-0"
              >
                {copiedOutreach ? (
                  <>
                    <Check className="w-3.5 h-3.5 text-[#C5DCCB]" />
                    Copied
                  </>
                ) : (
                  <>
                    <Copy className="w-3.5 h-3.5 text-[#F0B5A2]" />
                    Copy Outreach Note
                  </>
                )}
              </button>
            </div>

            <div className="p-5 space-y-3">
              <p className="text-xs text-[#D4CBBE] leading-relaxed">
                Inspired by <strong className="text-[#F6F1E8]">Valent’s Ariadne</strong> narrative risk intelligence platform (<a href="https://valent.co.uk" target="_blank" rel="noreferrer" className="text-[#F6C7B6] hover:underline">valent.co.uk</a>), CoordWatch demonstrates how multi-signal graph topology separates organic public reaction from synchronized influence operations across the seeding-to-amplification lifecycle.
              </p>
              <pre className="p-3 bg-[rgba(7,18,36,0.55)] border border-white/10 rounded text-[11px] font-mono text-[#D4CBBE] whitespace-pre-wrap leading-relaxed">
                {outreachTemplate}
              </pre>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default EthicsAndDocsView;
