import React, { useState } from 'react';
import { ClusterResult } from '../types';

interface ClusterInspectorProps {
  cluster: ClusterResult | null;
  clusters?: ClusterResult[];
  onSelectCluster?: (clusterId: string) => void;
  revealHandles?: boolean;
  onToggleRevealHandles?: () => void;
  onBack?: () => void;
}

export const ClusterInspector: React.FC<ClusterInspectorProps> = ({
  cluster,
  clusters = [],
  onSelectCluster = () => {},
  revealHandles = false,
  onToggleRevealHandles,
  onBack,
}) => {
  const [dossierTab, setDossierTab] = useState<'evidence' | 'posts' | 'cohort'>('evidence');
  const [showNormalizedText, setShowNormalizedText] = useState(false);

  if (!cluster) {
    return (
      <aside
        aria-label="Cluster Evidence Inspector"
        className="bg-[#0E121B] border border-slate-800/90 rounded-lg p-6 flex flex-col justify-between h-full"
      >
        <div>
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-semibold text-slate-100">
              Forensic Cluster Dossier
            </h2>
            {onBack && (
              <button
                type="button"
                onClick={onBack}
                className="px-2.5 py-1 text-xs font-semibold bg-slate-800 hover:bg-slate-700 text-slate-200 rounded transition-colors"
              >
                ✕ Close
              </button>
            )}
          </div>
          <p className="text-xs text-slate-400 mt-2 leading-relaxed">
            Select any Louvain community in the network graph or table to inspect its mathematical signal weights, plain-English evidence chain, and SHA-256 actor cohort.
          </p>
        </div>
      </aside>
    );
  }

  const score = cluster.score ?? (cluster as any).coordinationScore ?? 0;
  const rawScore = cluster.rawScore ?? score;
  const discountApplied = cluster.discountApplied ?? 0;
  const size = cluster.size ?? cluster.members?.length ?? (cluster as any).memberCount ?? 0;
  const signals = cluster.signals || { text: 0, timing: 0, age: 0, links: 0 };
  const examplePosts = cluster.examplePosts || [];
  const members = cluster.members || [];
  const reasons = cluster.reasons || (cluster as any).evidence || [];

  const severityLabel =
    score >= 70
      ? 'High-Confidence Coordinated Network'
      : score >= 50
        ? 'Elevated Coordination Pattern'
        : 'Discounted Organic News Burst';

  const classification = cluster.classification || (score >= 60 ? 'coordinated_inauthentic' : score >= 40 ? 'coordinated_benign' : 'organic');

  const classBadge =
    classification === 'coordinated_inauthentic' ? (
      <span className="text-[10px] bg-red-500/20 text-red-300 border border-red-500/40 px-2 py-0.5 rounded font-mono font-bold uppercase tracking-wider">
        ⚠️ Coordinated Inauthentic
      </span>
    ) : classification === 'coordinated_benign' ? (
      <span className="text-[10px] bg-purple-500/20 text-purple-300 border border-purple-500/40 px-2 py-0.5 rounded font-mono font-bold uppercase tracking-wider">
        🛡️ Coordinated Benign
      </span>
    ) : (
      <span className="text-[10px] bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 px-2 py-0.5 rounded font-mono font-bold uppercase tracking-wider">
        🌱 Organic Discourse
      </span>
    );

  const severityColor =
    score >= 70
      ? 'text-red-400'
      : score >= 50
        ? 'text-orange-400'
        : 'text-amber-300';

  const gaugeStrokeColor =
    score >= 70
      ? '#EF4444'
      : score >= 50
        ? '#F97316'
        : '#EAB308';

  const textPts = (35 * (signals.text || 0)).toFixed(1);
  const timingPts = (25 * (signals.timing || 0)).toFixed(1);
  const agePts = (20 * (signals.age || 0)).toFixed(1);
  const linksPts = (20 * (signals.links || 0)).toFixed(1);

  const signalRows = [
    {
      name: 'Text Similarity',
      weightLabel: '0.35 weight',
      value: signals.text || 0,
      pts: textPts,
      maxPts: 35,
      desc: 'Exact text_norm hash + char 3-gram TF-IDF cosine',
    },
    {
      name: 'Timing Synchronization',
      weightLabel: '0.25 weight',
      value: signals.timing || 0,
      pts: timingPts,
      maxPts: 25,
      desc: 'Co-posting burst (<60s) + interval cadence regularity',
    },
    {
      name: 'Account Age Cohort',
      weightLabel: '0.20 weight',
      value: signals.age || 0,
      pts: agePts,
      maxPts: 20,
      desc: '48-hour registration batch density via plc.directory',
    },
    {
      name: 'Shared Links & Hashtags',
      weightLabel: '0.20 weight',
      value: signals.links || 0,
      pts: linksPts,
      maxPts: 20,
      desc: 'Canonical URL & campaign hashtag Jaccard overlap',
    },
  ];

  // Radial gauge geometry
  const radius = 28;
  const circumference = 2 * Math.PI * radius;
  const strokeDashoffset =
    circumference - (Math.min(100, Math.max(0, score)) / 100) * circumference;

  return (
    <aside
      aria-label="Cluster Evidence Inspector"
      className="bg-[#0E121B] border border-slate-800/90 rounded-lg flex flex-col justify-between h-full overflow-hidden"
    >
      <div>
        {/* Top Cluster Switcher Bar */}
        <div className="px-4 py-3 bg-[#0B0E16] border-b border-slate-800/90 flex flex-wrap items-center justify-between gap-2">
          <div className="flex items-center gap-3">
            {onBack && (
              <button
                type="button"
                onClick={onBack}
                className="px-2.5 py-1 text-xs font-semibold bg-slate-800 hover:bg-slate-700 text-slate-200 rounded transition-colors flex items-center gap-1.5"
              >
                ← Back to Dashboard
              </button>
            )}
            <span className="text-xs font-semibold text-slate-200 tracking-tight">
              Forensic Cluster Dossier
            </span>
          </div>
          <div
            className="flex flex-wrap items-center gap-1"
            role="group"
            aria-label="Switch active cluster"
          >
            {(clusters || []).slice(0, 8).map((c) => {
              const cScore = c.score ?? (c as any).coordinationScore ?? 0;
              return (
                <button
                  key={c.id}
                  type="button"
                  onClick={() => onSelectCluster(c.id)}
                  className={`px-2.5 py-1 text-xs font-mono rounded transition-colors whitespace-nowrap shrink-0 ${
                    c.id === cluster.id
                      ? 'bg-sky-600 text-white font-semibold'
                      : 'bg-[#090B10] text-slate-400 hover:text-slate-200 border border-slate-800'
                  }`}
                >
                  {c.id} ({cScore})
                </button>
              );
            })}
          </div>
        </div>

        {/* Cluster Score & Radial Gauge Header */}
        <div className="p-4 border-b border-slate-800/90 bg-[#090B10]/60">
          <div className="flex items-center justify-between gap-4">
            <div>
              <div className="flex flex-wrap items-center gap-2">
                <h2 className="text-xl font-bold text-slate-100 font-display tracking-tight whitespace-nowrap shrink-0">
                  Cluster {cluster.id}
                </h2>
                {classBadge}
                <span className="text-xs text-slate-500">·</span>
                <span className={`text-xs font-medium ${severityColor}`}>
                  {severityLabel}
                </span>
              </div>
              <p className="text-xs text-slate-400 mt-1 font-mono tabular-nums">
                {size} accounts · {examplePosts.length} captured posts · Raw Score {rawScore}/100
              </p>
              {discountApplied > 0 ? (
                <div className="text-[11px] font-mono text-amber-400 mt-1 tabular-nums">
                  -{Math.round(discountApplied * 100)}% Organic News-Burst Discount Applied
                </div>
              ) : (
                <div className="text-[11px] font-mono text-slate-400 mt-1 tabular-nums">
                  Full Multi-Signal Weighting Active (No FP Discount)
                </div>
              )}
            </div>

            {/* Phase 7.4 Coordination Score Radial Gauge (0-100) */}
            <div className="relative w-16 h-16 flex items-center justify-center shrink-0">
              <svg className="w-16 h-16 -rotate-90" viewBox="0 0 68 68">
                <circle
                  cx="34"
                  cy="34"
                  r={radius}
                  fill="none"
                  stroke="#1E293B"
                  strokeWidth="5.5"
                />
                <circle
                  cx="34"
                  cy="34"
                  r={radius}
                  fill="none"
                  stroke={gaugeStrokeColor}
                  strokeWidth="5.5"
                  strokeLinecap="round"
                  strokeDasharray={circumference}
                  strokeDashoffset={strokeDashoffset}
                />
              </svg>
              <div className="absolute inset-0 flex flex-col items-center justify-center font-mono tabular-nums">
                <span className={`text-lg font-bold leading-none ${severityColor}`}>
                  {score}
                </span>
                <span className="text-[9px] text-slate-500 mt-0.5">/100</span>
              </div>
            </div>
          </div>

          {/* Mathematical Decomposition Strip */}
          <div className="mt-3 pt-2.5 border-t border-slate-800/70 flex flex-wrap items-center justify-between gap-2 text-[11px] font-mono text-slate-400 tabular-nums">
            <span>Score = 100 × (0.35·T + 0.25·S + 0.20·A + 0.20·L)</span>
            <span className="text-slate-200">
              {textPts} + {timingPts} + {agePts} + {linksPts} = {rawScore} pts
            </span>
          </div>
        </div>

        {/* Dossier Internal Navigation Tabs */}
        <div className="px-4 pt-2.5 bg-[#0B0E16] border-b border-slate-800/90 flex items-center justify-between gap-2">
          <div className="flex items-center gap-4 text-xs font-medium">
            <button
              type="button"
              onClick={() => setDossierTab('evidence')}
              className={`pb-2.5 border-b-2 transition-colors whitespace-nowrap ${
                dossierTab === 'evidence'
                  ? 'border-sky-500 text-slate-100 font-semibold'
                  : 'border-transparent text-slate-400 hover:text-slate-200'
              }`}
            >
              Explainable Evidence &amp; Signals
            </button>
            <button
              type="button"
              onClick={() => setDossierTab('posts')}
              className={`pb-2.5 border-b-2 transition-colors whitespace-nowrap ${
                dossierTab === 'posts'
                  ? 'border-sky-500 text-slate-100 font-semibold'
                  : 'border-transparent text-slate-400 hover:text-slate-200'
              }`}
            >
              Captured Posts ({examplePosts.length})
            </button>
            <button
              type="button"
              onClick={() => setDossierTab('cohort')}
              className={`pb-2.5 border-b-2 transition-colors whitespace-nowrap ${
                dossierTab === 'cohort'
                  ? 'border-sky-500 text-slate-100 font-semibold'
                  : 'border-transparent text-slate-400 hover:text-slate-200'
              }`}
            >
              Actor Cohort ({members.length})
            </button>
          </div>

          {onToggleRevealHandles && (
            <button
              type="button"
              onClick={onToggleRevealHandles}
              className="mb-2 px-2.5 py-1 text-[11px] font-medium bg-[#090B10] hover:bg-slate-800 text-slate-300 border border-slate-700 rounded transition-colors whitespace-nowrap shrink-0"
            >
              {revealHandles ? 'Hide Handles (Use Aliases)' : 'Reveal Handles'}
            </button>
          )}
        </div>

        {/* Tab 1: Explainable Evidence & 4-Signal Breakdown */}
        {dossierTab === 'evidence' && (
          <div className="p-4 space-y-4">
            {/* 4-Signal Bars */}
            <div className="space-y-3">
              {signalRows.map((row) => {
                const pct = Math.round(row.value * 100);
                return (
                  <div key={row.name} className="space-y-1">
                    <div className="flex items-baseline justify-between text-xs">
                      <div>
                        <span className="font-medium text-slate-200">{row.name}</span>
                        <span className="text-slate-500 ml-1.5">· {row.weightLabel}</span>
                      </div>
                      <span className="font-mono text-slate-200 tabular-nums">
                        {row.value.toFixed(2)} ({row.pts}/{row.maxPts} pts)
                      </span>
                    </div>
                    <div className="w-full h-1.5 bg-[#090B10] border border-slate-800/80 rounded-sm overflow-hidden">
                      <div
                        className={`h-full ${
                          pct >= 70
                            ? 'bg-red-500'
                            : pct >= 45
                              ? 'bg-orange-500'
                              : 'bg-sky-500'
                        }`}
                        style={{ width: `${Math.max(3, pct)}%` }}
                      />
                    </div>
                  </div>
                );
              })}
            </div>

            {/* Plain-English Evidence List */}
            <div className="pt-3 border-t border-slate-800/80">
              <h3 className="text-xs font-semibold text-slate-200">
                Why Flagged (Plain-English Evidence Chain)
              </h3>
              <ul className="mt-2.5 space-y-2 text-xs text-slate-300 leading-relaxed">
                {reasons.map((reason, idx) => (
                  <li
                    key={idx}
                    className="p-2.5 bg-[#090B10] border border-slate-800/80 rounded flex items-start gap-2.5"
                  >
                    <span className="font-mono text-sky-400 font-semibold select-none tabular-nums">
                      0{idx + 1}
                    </span>
                    <span>{reason}</span>
                  </li>
                ))}
              </ul>
            </div>

            {/* Benign Explanations Evaluated (D1 Evidence Protection) */}
            <div className="pt-3 border-t border-slate-800/80">
              <div className="flex items-center justify-between mb-2">
                <h3 className="text-xs font-semibold text-slate-200">
                  Benign Explanations Evaluated (D1 Evidence Protection)
                </h3>
                {cluster.significance && (
                  <span className="text-[11px] font-mono text-slate-400">
                    Permutation Null-Model: <strong className={cluster.significance.significant ? "text-amber-400" : "text-emerald-400"}>p = {cluster.significance.p_value.toFixed(4)}</strong>
                  </span>
                )}
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-2 text-xs">
                <div className="p-2 bg-[#090B10] border border-slate-800/80 rounded flex items-center justify-between">
                  <span className="text-slate-400">Share-Button Headline Match</span>
                  <span className={cluster.benignChecks?.share_button_match ? "text-emerald-400 font-mono text-[11px]" : "text-slate-500 font-mono text-[11px]"}>
                    {cluster.benignChecks?.share_button_match ? "✓ MATCHED" : "✗ Disproven"}
                  </span>
                </div>
                <div className="p-2 bg-[#090B10] border border-slate-800/80 rounded flex items-center justify-between">
                  <span className="text-slate-400">Authoritative Press Source</span>
                  <span className={cluster.benignChecks?.authoritative_news_source ? "text-emerald-400 font-mono text-[11px]" : "text-slate-500 font-mono text-[11px]"}>
                    {cluster.benignChecks?.authoritative_news_source ? "✓ VERIFIED" : "✗ Inauthentic URL"}
                  </span>
                </div>
                <div className="p-2 bg-[#090B10] border border-slate-800/80 rounded flex items-center justify-between">
                  <span className="text-slate-400">Open Community Movement</span>
                  <span className={cluster.benignChecks?.open_community_hashtag ? "text-emerald-400 font-mono text-[11px]" : "text-slate-500 font-mono text-[11px]"}>
                    {cluster.benignChecks?.open_community_hashtag ? "✓ CONFIRMED" : "✗ Astroturfed"}
                  </span>
                </div>
              </div>
            </div>

            {/* Preview of Top 2 Posts right inside Evidence tab */}
            <div className="pt-3 border-t border-slate-800/80">
              <div className="flex items-center justify-between text-xs mb-2">
                <span className="font-semibold text-slate-200">
                  Sample Synchronized Posts
                </span>
                <button
                  type="button"
                  onClick={() => setShowNormalizedText((v) => !v)}
                  className="text-sky-400 hover:text-sky-300 font-mono text-[11px]"
                >
                  {showNormalizedText ? 'Show Raw Post' : 'Inspect text_norm'}
                </button>
              </div>
              <div className="space-y-2">
                {examplePosts.slice(0, 2).map((post) => (
                  <div
                    key={post.id}
                    className="p-2.5 bg-[#090B10] border border-slate-800/80 rounded text-xs"
                  >
                    <div className="flex items-center justify-between text-[11px] font-mono text-slate-400 tabular-nums">
                      <span className="text-slate-200 font-semibold">
                        {revealHandles ? post.handle : post.alias}
                      </span>
                      <span>{post.createdAt ? post.createdAt.slice(11, 19) : ''} UTC</span>
                    </div>
                    <p className="mt-1 text-slate-300 leading-relaxed line-clamp-2">
                      {showNormalizedText ? (
                        <code className="text-sky-300 text-[11px]">{post.textNorm}</code>
                      ) : (
                        post.text
                      )}
                    </p>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* Tab 2: Full Captured Evidence Posts */}
        {dossierTab === 'posts' && (
          <div className="p-4 space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-xs text-slate-400">
                Comparing raw Bluesky post records against normalized{' '}
                <code className="text-slate-200">text_norm</code>
              </span>
              <button
                type="button"
                onClick={() => setShowNormalizedText((v) => !v)}
                className="px-2.5 py-1 text-xs font-medium bg-[#090B10] hover:bg-slate-800 text-sky-400 border border-slate-800 rounded transition-colors"
              >
                {showNormalizedText ? 'Show Raw Text' : 'Inspect text_norm'}
              </button>
            </div>

            <div className="space-y-2.5 max-h-[430px] overflow-y-auto pr-1">
              {examplePosts.map((post) => (
                <div
                  key={post.id}
                  className="p-3 bg-[#090B10] border border-slate-800/90 rounded text-xs space-y-1.5"
                >
                  <div className="flex items-center justify-between text-[11px] font-mono text-slate-400 tabular-nums">
                    <span className="text-slate-100 font-semibold">
                      {revealHandles ? post.handle : post.alias}
                    </span>
                    <span>{post.createdAt ? post.createdAt.slice(0, 19).replace('T', ' ') : ''} UTC</span>
                  </div>
                  <p className="text-slate-300 leading-relaxed break-words">
                    {showNormalizedText ? (
                      <code className="text-sky-300 text-[11px]">{post.textNorm}</code>
                    ) : (
                      post.text
                    )}
                  </p>
                  {(post.links && post.links.length > 0 || post.hashtags && post.hashtags.length > 0) && (
                    <div className="pt-1 border-t border-slate-800/60 text-[11px] font-mono text-slate-400">
                      {post.links && post.links.length > 0 && <span>URL: {post.links[0]} </span>}
                      {post.hashtags && post.hashtags.length > 0 && (
                        <span>· Tags: {post.hashtags.join(' ')}</span>
                      )}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Tab 3: Actor Cohort & PLC Audit Log */}
        {dossierTab === 'cohort' && (
          <div className="p-4 space-y-3">
            <div className="text-xs text-slate-400">
              {revealHandles
                ? 'Showing resolved Bluesky handles from plc.directory audit log.'
                : 'Showing deterministic SHA-256 aliases (A-xxxx) by default per Phase 9 Ethics Policy.'}
            </div>

            <div className="max-h-[430px] overflow-y-auto border border-slate-800/90 rounded bg-[#090B10]">
              <table className="w-full text-left border-collapse text-xs font-mono tabular-nums">
                <thead>
                  <tr className="border-b border-slate-800 text-slate-400 bg-[#0B0E16]">
                    <th className="py-2 px-3 font-medium">Actor</th>
                    <th className="py-2 px-3 font-medium">PLC Created Date</th>
                    <th className="py-2 px-3 font-medium text-right">Posts</th>
                    <th className="py-2 px-3 font-medium text-right">Centrality</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60">
                  {members.map((m) => (
                    <tr key={m.did} className="hover:bg-slate-900/50">
                      <td className="py-2 px-3 text-slate-200 font-semibold truncate max-w-[160px]">
                        {revealHandles ? m.handle : m.alias}
                      </td>
                      <td className="py-2 px-3 text-slate-400">
                        {m.createdAt ? m.createdAt.slice(0, 16).replace('T', ' ') : 'pending'}
                      </td>
                      <td className="py-2 px-3 text-right text-slate-300">
                        {m.postCount}
                      </td>
                      <td className="py-2 px-3 text-right text-sky-400">
                        {m.nodeScore}/100
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>

      {/* Dossier Footer Note */}
      <div className="px-4 py-2.5 bg-[#0B0E16] border-t border-slate-800/90 flex items-center justify-between text-[11px] text-slate-400 font-mono tabular-nums">
        <span>Community Algorithm: Louvain Modularity</span>
        <span>Updated {cluster.computedAt ? cluster.computedAt.slice(11, 19) : new Date().toISOString().slice(11, 19)} UTC</span>
      </div>
    </aside>
  );
};

export default ClusterInspector;
