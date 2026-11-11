import React, { useState } from 'react';
import { Copy, Check } from 'lucide-react';

interface EthicsAndDocsViewProps {
  activeTopicId?: number;
}

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? '';

export const EthicsAndDocsView: React.FC<EthicsAndDocsViewProps> = ({ activeTopicId = 1 }) => {
  const [apiOutput, setApiOutput] = useState<string>('');
  const [testedEndpoint, setTestedEndpoint] = useState<string>('');
  const [copiedOutreach, setCopiedOutreach] = useState<boolean>(false);

  const testEndpoint = async (path: string, method: 'GET' | 'POST' = 'GET', body?: object) => {
    setTestedEndpoint(`${method} ${path}`);
    try {
      const url = `${API_BASE}${path}`;
      const res = await fetch(url, {
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
      {/* Section 1: Methodology, Limitations & Ethical Safeguards */}
      <div className="bg-[rgba(16,36,66,0.42)] backdrop-blur-xl border border-white/10 rounded-[26px] overflow-hidden">
        <div className="px-6 py-5 bg-[rgba(8,20,42,0.5)] border-b border-white/10">
          <h2 className="text-base font-bold text-[#F6F1E8] font-display tracking-tight">
            Methodology, Limitations &amp; Ethical Safeguards
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

      {/* Section 2: Interactive REST API Reference + Inspiration */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        {/* Interactive REST API Explorer */}
        <div className="bg-[rgba(16,36,66,0.42)] backdrop-blur-xl border border-white/10 rounded-[26px] overflow-hidden flex flex-col justify-between">
          <div>
            <div className="px-5 py-3.5 bg-[rgba(8,20,42,0.5)] border-b border-white/10">
              <h2 className="text-sm font-semibold text-[#F6F1E8] tracking-tight">
                Interactive REST API Reference
              </h2>
              <p className="text-xs text-[#B6AC9E] mt-0.5">
                Click any endpoint below to query the live FastAPI server and inspect the JSON response payload.
              </p>
            </div>

            <div className="p-5 pb-3 flex flex-wrap gap-2">
              <button
                type="button"
                onClick={() => testEndpoint('/api/health')}
                className="px-2.5 py-1.5 text-xs font-mono bg-[rgba(7,18,36,0.55)] hover:bg-white/10 text-[#F0B5A2] border border-white/10 rounded transition-colors"
              >
                GET /api/health
              </button>
              <button
                type="button"
                onClick={() => testEndpoint('/api/topics')}
                className="px-2.5 py-1.5 text-xs font-mono bg-[rgba(7,18,36,0.55)] hover:bg-white/10 text-[#F0B5A2] border border-white/10 rounded transition-colors"
              >
                GET /api/topics
              </button>
              <button
                type="button"
                onClick={() => testEndpoint(`/api/topics/${activeTopicId}/summary`)}
                className="px-2.5 py-1.5 text-xs font-mono bg-[rgba(7,18,36,0.55)] hover:bg-white/10 text-[#F0B5A2] border border-white/10 rounded transition-colors"
              >
                GET /api/topics/{activeTopicId}/summary
              </button>
              <button
                type="button"
                onClick={() => testEndpoint(`/api/topics/${activeTopicId}/graph`)}
                className="px-2.5 py-1.5 text-xs font-mono bg-[rgba(7,18,36,0.55)] hover:bg-white/10 text-[#F0B5A2] border border-white/10 rounded transition-colors"
              >
                GET /api/topics/{activeTopicId}/graph
              </button>
              <button
                type="button"
                onClick={() => testEndpoint(`/api/topics/${activeTopicId}/clusters`)}
                className="px-2.5 py-1.5 text-xs font-mono bg-[rgba(7,18,36,0.55)] hover:bg-white/10 text-[#F0B5A2] border border-white/10 rounded transition-colors"
              >
                GET /api/topics/{activeTopicId}/clusters
              </button>
              <button
                type="button"
                onClick={() => testEndpoint(`/api/topics/${activeTopicId}/timeline`)}
                className="px-2.5 py-1.5 text-xs font-mono bg-[rgba(7,18,36,0.55)] hover:bg-white/10 text-[#F0B5A2] border border-white/10 rounded transition-colors"
              >
                GET /api/topics/{activeTopicId}/timeline
              </button>
              <button
                type="button"
                onClick={() => testEndpoint('/api/evaluation/latest')}
                className="px-2.5 py-1.5 text-xs font-mono bg-[rgba(7,18,36,0.55)] hover:bg-white/10 text-[#F0B5A2] border border-white/10 rounded transition-colors"
              >
                GET /api/evaluation/latest
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

        {/* Valent / Ariadne Inspiration & Outreach Card */}
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

      {/* Section 2: Interactive REST API Reference + Inspiration */}
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
