import React, { useState } from 'react';
import { EvaluationReport } from '../types';
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
} from 'recharts';

interface EvaluationLabViewProps {
  report?: EvaluationReport | null;
  result?: EvaluationReport | null;
  onRerunEvaluation?: (organicCount: number) => Promise<void>;
  onRun?: () => void | Promise<void>;
  isRunning?: boolean;
}

export const EvaluationLabView: React.FC<EvaluationLabViewProps> = ({
  report: reportProp,
  result,
  onRerunEvaluation,
  onRun,
  isRunning = false,
}) => {
  const report = reportProp || result || null;
  const [organicSampleSize, setOrganicSampleSize] = useState<number>(500);

  if (!report) {
    return (
      <div className="p-8 bg-[#0E121B] border border-slate-800/90 rounded-lg text-center">
        <p className="text-sm text-slate-300">Loading Phase 8 Ground-Truth Evaluation Benchmark...</p>
      </div>
    );
  }

  return (
    <div className="space-y-5">
      {/* Unified Command & Ground-Truth Telemetry Strip */}
      <section className="bg-[#0E121B] border border-slate-800/90 rounded-lg overflow-hidden">
        <div className="px-5 py-4 bg-[#0B0E16] border-b border-slate-800/90 flex flex-wrap items-center justify-between gap-4">
          <div className="max-w-2xl">
            <h1 className="text-lg font-bold text-slate-100 font-display tracking-tight">
              Evaluation Lab & Adversarial Bot Evasion Benchmark
            </h1>
            <p className="text-xs text-slate-400 mt-1 leading-relaxed">
              Ground-truth synthetic benchmark injecting 3 coordinated bot networks ({report.plantedBotAccounts} accounts across copypasta, link-ring, and template-mutation tactics) into {report.organicAccounts} independent organic accounts.
            </p>
          </div>

          <form
            onSubmit={(e) => {
              e.preventDefault();
              onRerunEvaluation(organicSampleSize);
            }}
            className="flex items-center gap-3"
          >
            <label className="text-xs text-slate-300 flex items-center gap-2">
              <span>Organic Background Pool:</span>
              <select
                aria-label="Organic Background Accounts"
                value={organicSampleSize}
                onChange={(e) => setOrganicSampleSize(Number(e.target.value))}
                className="bg-[#090B10] border border-slate-700 rounded px-2.5 py-1.5 text-xs text-slate-100 font-mono tabular-nums"
              >
                <option value={250}>250 organic</option>
                <option value={500}>500 organic (Standard)</option>
                <option value={750}>750 organic</option>
              </select>
            </label>
            <button
              type="button"
              disabled={isRunning}
              onClick={() => onRerunEvaluation(organicSampleSize)}
              className="px-4 py-1.5 text-xs font-semibold bg-sky-600 hover:bg-sky-500 disabled:opacity-50 text-white rounded transition-colors whitespace-nowrap shrink-0"
            >
              {isRunning ? 'Running Simulator...' : 'Re-run Benchmark Suite'}
            </button>
          </form>
        </div>

        {/* 4-Column Architectural Confusion Matrix Ribbon */}
        <div className="grid grid-cols-2 lg:grid-cols-4 divide-y lg:divide-y-0 lg:divide-x divide-slate-800/90">
          <div className="px-5 py-3.5">
            <div className="text-[11px] font-medium text-slate-400">Account-Level Precision</div>
            <div className="mt-1 flex items-baseline justify-between gap-2 font-mono tabular-nums">
              <span className="text-2xl font-bold text-emerald-400">
                {(report.precision * 100).toFixed(1)}%
              </span>
              <span className="text-xs text-slate-400">
                {report.truePositives} TP · {report.falsePositives} FP
              </span>
            </div>
          </div>

          <div className="px-5 py-3.5">
            <div className="text-[11px] font-medium text-slate-400">Account-Level Recall</div>
            <div className="mt-1 flex items-baseline justify-between gap-2 font-mono tabular-nums">
              <span className="text-2xl font-bold text-sky-400">
                {(report.recall * 100).toFixed(1)}%
              </span>
              <span className="text-xs text-slate-400">
                {report.truePositives}/{report.plantedBotAccounts} bots caught
              </span>
            </div>
          </div>

          <div className="px-5 py-3.5">
            <div className="text-[11px] font-medium text-slate-400">Overall Benchmark F1 Score</div>
            <div className="mt-1 flex items-baseline justify-between gap-2 font-mono tabular-nums">
              <span className="text-2xl font-bold text-slate-100">
                {report.f1.toFixed(3)}
              </span>
              <span className="text-xs text-slate-400">
                N = {report.totalAccounts} accounts
              </span>
            </div>
          </div>

          <div className="px-5 py-3.5">
            <div className="text-[11px] font-medium text-slate-400">News-Burst False Positive Rate</div>
            <div className="mt-1 flex items-baseline justify-between gap-2 font-mono tabular-nums">
              <span className="text-2xl font-bold text-amber-400">
                {(report.falsePositiveStressTest.falsePositiveRateAfter * 100).toFixed(1)}%
              </span>
              <span className="text-xs text-slate-400">
                {report.falsePositiveStressTest.flaggedWithProtection}/{report.falsePositiveStressTest.organicUsersCount} (vs {(report.falsePositiveStressTest.falsePositiveRateBefore * 100).toFixed(0)}% raw)
              </span>
            </div>
          </div>
        </div>
      </section>

      {/* Split Grid: Evasion Degradation Chart + Planted Network Breakdown */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-5 items-stretch">
        {/* Evasion Curve Chart (7 cols) */}
        <div className="lg:col-span-7 bg-[#0E121B] border border-slate-800/90 rounded-lg overflow-hidden flex flex-col justify-between">
          <div className="px-5 py-3.5 bg-[#0B0E16] border-b border-slate-800/90">
            <h2 className="text-sm font-semibold text-slate-100 tracking-tight">
              Detection Performance (F1) vs. Adversarial Evasion Intensity
            </h2>
            <p className="text-xs text-slate-400 mt-0.5">
              Measures how account-level F1 degrades as planted bot networks progressively apply 4 independent evasion tactics from 0% (Baseline) to 90% (Extreme).
            </p>
          </div>

          <div className="p-5 h-80 w-full" data-testid="evasion-chart-container">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart
                data={report.evasionCurve}
                margin={{ top: 10, right: 20, left: -10, bottom: 5 }}
              >
                <CartesianGrid strokeDasharray="3 3" stroke="#1E293B" />
                <XAxis
                  dataKey="level"
                  stroke="#94A3B8"
                  tick={{ fill: '#94A3B8', fontSize: 11 }}
                />
                <YAxis
                  domain={[0, 1.0]}
                  stroke="#94A3B8"
                  tick={{ fill: '#94A3B8', fontSize: 11 }}
                />
                <Tooltip
                  contentStyle={{
                    backgroundColor: '#090B10',
                    borderColor: '#334155',
                    fontSize: '12px',
                    color: '#F8FAFC',
                  }}
                />
                <Legend wrapperStyle={{ fontSize: '12px', paddingTop: '8px' }} />
                <Line
                  type="monotone"
                  dataKey="textParaphraseF1"
                  name="Text Paraphrasing"
                  stroke="#EF4444"
                  strokeWidth={2}
                  dot={{ r: 4 }}
                />
                <Line
                  type="monotone"
                  dataKey="randomDelayF1"
                  name="Random Posting Delays"
                  stroke="#F59E0B"
                  strokeWidth={2}
                  dot={{ r: 4 }}
                />
                <Line
                  type="monotone"
                  dataKey="ageSpreadF1"
                  name="Spread Account Creation"
                  stroke="#38BDF8"
                  strokeWidth={2}
                  dot={{ r: 4 }}
                />
                <Line
                  type="monotone"
                  dataKey="linkRotationF1"
                  name="Link & Tag Rotation"
                  stroke="#10B981"
                  strokeWidth={2}
                  dot={{ r: 4 }}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Planted Bot Networks Ground-Truth Table + Viral News Stress Test (5 cols) */}
        <div className="lg:col-span-5 bg-[#0E121B] border border-slate-800/90 rounded-lg overflow-hidden divide-y divide-slate-800/90 flex flex-col justify-between">
          <div>
            <div className="px-4 py-3 bg-[#0B0E16] border-b border-slate-800/90">
              <h2 className="text-sm font-semibold text-slate-100 tracking-tight">
                Planted Bot Networks (Ground-Truth Breakdown)
              </h2>
            </div>
            <div className="p-4 overflow-x-auto">
              <table className="w-full text-left border-collapse text-xs">
                <thead>
                  <tr className="border-b border-slate-800 text-slate-400">
                    <th className="py-2 pr-2 font-medium">Network</th>
                    <th className="py-2 px-2 font-medium text-right">Caught</th>
                    <th className="py-2 px-2 font-medium text-right">Recall</th>
                    <th className="py-2 pl-2 font-medium text-right">Mean Score</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60 font-mono tabular-nums">
                  {report.plantedNetworks.map((net) => (
                    <tr key={net.id} className="hover:bg-slate-900/50">
                      <td className="py-2.5 pr-2 font-sans">
                        <div className="font-medium text-slate-200">{net.name}</div>
                        <div className="text-[11px] text-slate-400">{net.tactic}</div>
                      </td>
                      <td className="py-2.5 px-2 text-right text-slate-200">
                        {net.detectedAccounts}/{net.plantedAccounts}
                      </td>
                      <td className="py-2.5 px-2 text-right text-emerald-400">
                        {(net.recall * 100).toFixed(0)}%
                      </td>
                      <td className="py-2.5 pl-2 text-right text-red-400">
                        {net.meanClusterScore}/100
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Phase 8.5 False-Positive Stress Test Summary */}
          <div className="p-4 bg-[#090B10]/60">
            <h3 className="text-xs font-semibold text-slate-200">
              False-Positive Stress Test: Viral Breaking News Event
            </h3>
            <p className="text-xs text-slate-400 mt-1 leading-relaxed">
              {report.falsePositiveStressTest.scenario}
            </p>
            <div className="mt-3 grid grid-cols-2 gap-3 text-xs font-mono tabular-nums">
              <div className="p-2.5 bg-[#090B10] border border-slate-800 rounded">
                <div className="text-slate-400">Without FP Protection</div>
                <div className="text-base font-bold text-red-400 mt-0.5">
                  {report.falsePositiveStressTest.rawFlaggedWithoutProtection}/{report.falsePositiveStressTest.organicUsersCount} wrongly flagged
                </div>
              </div>
              <div className="p-2.5 bg-[#090B10] border border-slate-800 rounded">
                <div className="text-slate-400">With Phase 5.5 Protection</div>
                <div className="text-base font-bold text-emerald-400 mt-0.5">
                  {report.falsePositiveStressTest.flaggedWithProtection}/{report.falsePositiveStressTest.organicUsersCount} wrongly flagged
                </div>
              </div>
            </div>
            <p className="text-[11px] text-slate-400 mt-2 leading-relaxed">
              {report.falsePositiveStressTest.explanation}
            </p>
          </div>
        </div>
      </div>

      {/* Benchmark v2: Dev Split vs. Held-Out Test Split (95% Bootstrap CIs) */}
      {report.devSummary && report.testSummary && (
        <div className="bg-[#0E121B] border border-slate-800/90 rounded-lg overflow-hidden">
          <div className="px-5 py-3.5 bg-[#0B0E16] border-b border-slate-800/90 flex flex-wrap items-center justify-between gap-3">
            <div>
              <h2 className="text-sm font-semibold text-slate-100 tracking-tight flex items-center gap-2">
                <span>Benchmark v2: Dev Split vs. Held-Out Test Split (95% Bootstrap Confidence Intervals)</span>
                <span className="text-[10px] bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 px-2 py-0.5 rounded font-mono font-bold uppercase">
                  Audited Reproducible
                </span>
              </h2>
              <p className="text-xs text-slate-400 mt-0.5">
                Evaluated across multiple randomized seeds with non-parametric bootstrap resampling (1,000 iterations). Dev set tuned on F1–F6 / H1–H5; Test set frozen on F7–F12 / H6–H10.
              </p>
            </div>
            {report.nullControl && (
              <div className="px-3 py-1 bg-slate-900 border border-slate-800 rounded text-xs font-mono">
                <span className="text-slate-400">Null Control: </span>
                <span className="text-emerald-400 font-bold">{report.nullControl.status}</span>
              </div>
            )}
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse text-xs font-mono tabular-nums">
              <thead>
                <tr className="border-b border-slate-800 text-slate-400 bg-[#090B10]/80">
                  <th className="py-2.5 px-4 font-medium">Evaluation Metric</th>
                  <th className="py-2.5 px-4 font-medium text-center">Dev Set (F1–F6, H1–H5)</th>
                  <th className="py-2.5 px-4 font-medium text-center text-sky-400">Held-Out Test (F7–F12, H6–H10)</th>
                  <th className="py-2.5 px-4 font-medium">Methodological Significance</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/70 text-slate-300">
                <tr className="hover:bg-slate-900/40">
                  <td className="py-2.5 px-4 font-semibold text-slate-100">Account-Level Precision</td>
                  <td className="py-2.5 px-4 text-center text-emerald-400 font-bold">
                    {(report.devSummary.precision.mean * 100).toFixed(1)}% ± {(report.devSummary.precision.std * 100).toFixed(1)}%
                    <div className="text-[10px] text-slate-500 font-normal">
                      [{(report.devSummary.precision.ci_low * 100).toFixed(1)}%, {(report.devSummary.precision.ci_high * 100).toFixed(1)}%]
                    </div>
                  </td>
                  <td className="py-2.5 px-4 text-center text-emerald-400 font-bold bg-sky-950/20">
                    {(report.testSummary.precision.mean * 100).toFixed(1)}% ± {(report.testSummary.precision.std * 100).toFixed(1)}%
                    <div className="text-[10px] text-slate-500 font-normal">
                      [{(report.testSummary.precision.ci_low * 100).toFixed(1)}%, {(report.testSummary.precision.ci_high * 100).toFixed(1)}%]
                    </div>
                  </td>
                  <td className="py-2.5 px-4 text-slate-400 font-sans text-xs">
                    Fraction of flagged accounts that are true inauthentic actors
                  </td>
                </tr>
                <tr className="hover:bg-slate-900/40">
                  <td className="py-2.5 px-4 font-semibold text-slate-100">Account-Level Recall</td>
                  <td className="py-2.5 px-4 text-center text-sky-400 font-bold">
                    {(report.devSummary.recall.mean * 100).toFixed(1)}% ± {(report.devSummary.recall.std * 100).toFixed(1)}%
                    <div className="text-[10px] text-slate-500 font-normal">
                      [{(report.devSummary.recall.ci_low * 100).toFixed(1)}%, {(report.devSummary.recall.ci_high * 100).toFixed(1)}%]
                    </div>
                  </td>
                  <td className="py-2.5 px-4 text-center text-sky-400 font-bold bg-sky-950/20">
                    {(report.testSummary.recall.mean * 100).toFixed(1)}% ± {(report.testSummary.recall.std * 100).toFixed(1)}%
                    <div className="text-[10px] text-slate-500 font-normal">
                      [{(report.testSummary.recall.ci_low * 100).toFixed(1)}%, {(report.testSummary.recall.ci_high * 100).toFixed(1)}%]
                    </div>
                  </td>
                  <td className="py-2.5 px-4 text-slate-400 font-sans text-xs">
                    Fraction of planted attack accounts successfully identified
                  </td>
                </tr>
                <tr className="hover:bg-slate-900/40">
                  <td className="py-2.5 px-4 font-semibold text-slate-100">Harmonic F1 Score</td>
                  <td className="py-2.5 px-4 text-center text-slate-100 font-bold">
                    {report.devSummary.f1.mean.toFixed(3)} ± {report.devSummary.f1.std.toFixed(3)}
                    <div className="text-[10px] text-slate-500 font-normal">
                      [{report.devSummary.f1.ci_low.toFixed(3)}, {report.devSummary.f1.ci_high.toFixed(3)}]
                    </div>
                  </td>
                  <td className="py-2.5 px-4 text-center text-slate-100 font-bold bg-sky-950/20">
                    {report.testSummary.f1.mean.toFixed(3)} ± {report.testSummary.f1.std.toFixed(3)}
                    <div className="text-[10px] text-slate-500 font-normal">
                      [{report.testSummary.f1.ci_low.toFixed(3)}, {report.testSummary.f1.ci_high.toFixed(3)}]
                    </div>
                  </td>
                  <td className="py-2.5 px-4 text-slate-400 font-sans text-xs">
                    Balanced harmonic trade-off between precision and recall
                  </td>
                </tr>
                <tr className="hover:bg-slate-900/40">
                  <td className="py-2.5 px-4 font-semibold text-slate-100">PR-AUC (Precision-Recall Area)</td>
                  <td className="py-2.5 px-4 text-center text-purple-400 font-bold">
                    {report.devSummary.pr_auc.mean.toFixed(3)}
                    <div className="text-[10px] text-slate-500 font-normal">
                      [{report.devSummary.pr_auc.ci_low.toFixed(3)}, {report.devSummary.pr_auc.ci_high.toFixed(3)}]
                    </div>
                  </td>
                  <td className="py-2.5 px-4 text-center text-purple-400 font-bold bg-sky-950/20">
                    {report.testSummary.pr_auc.mean.toFixed(3)}
                    <div className="text-[10px] text-slate-500 font-normal">
                      [{report.testSummary.pr_auc.ci_low.toFixed(3)}, {report.testSummary.pr_auc.ci_high.toFixed(3)}]
                    </div>
                  </td>
                  <td className="py-2.5 px-4 text-slate-400 font-sans text-xs">
                    Threshold-independent performance across all operating cutoffs
                  </td>
                </tr>
                <tr className="hover:bg-slate-900/40">
                  <td className="py-2.5 px-4 font-semibold text-slate-100">Campaign Recall (≥50% Network)</td>
                  <td className="py-2.5 px-4 text-center text-amber-400 font-bold">
                    {(report.devSummary.campaign_recall.mean * 100).toFixed(0)}%
                  </td>
                  <td className="py-2.5 px-4 text-center text-amber-400 font-bold bg-sky-950/20">
                    {(report.testSummary.campaign_recall.mean * 100).toFixed(0)}%
                  </td>
                  <td className="py-2.5 px-4 text-slate-400 font-sans text-xs">
                    Fraction of overall campaigns where majority core was neutralized
                  </td>
                </tr>
                <tr className="hover:bg-slate-900/40">
                  <td className="py-2.5 px-4 font-semibold text-slate-100">Hard Negative Inauthentic Flag Rate</td>
                  <td className="py-2.5 px-4 text-center text-slate-300">
                    {(report.devSummary.hard_neg_flag_rate.mean * 100).toFixed(1)}%
                  </td>
                  <td className="py-2.5 px-4 text-center text-emerald-400 font-bold bg-sky-950/20">
                    {(report.testSummary.hard_neg_flag_rate.mean * 100).toFixed(1)}%
                  </td>
                  <td className="py-2.5 px-4 text-slate-400 font-sans text-xs">
                    Resistance to false alarms on innocent breaking news / petitions
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Baselines & Ablations Grid */}
      {report.baselines && report.ablations && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
          <div className="bg-[#0E121B] border border-slate-800/90 rounded-lg p-5">
            <h3 className="text-xs font-semibold text-slate-200 uppercase tracking-wider mb-2">
              Model Baselines Comparison
            </h3>
            <div className="space-y-2.5">
              {Object.entries(report.baselines).map(([k, b]: [string, any]) => (
                <div key={k} className="p-3 bg-[#090B10] border border-slate-800 rounded flex items-center justify-between text-xs">
                  <div>
                    <div className="font-semibold text-slate-200">{b.name}</div>
                    <div className="text-[11px] text-slate-500">Precision: {(b.precision * 100).toFixed(1)}% · Recall: {(b.recall * 100).toFixed(1)}%</div>
                  </div>
                  <div className="font-mono text-sm font-bold text-sky-400">
                    F1: {b.f1.toFixed(3)}
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className="bg-[#0E121B] border border-slate-800/90 rounded-lg p-5">
            <h3 className="text-xs font-semibold text-slate-200 uppercase tracking-wider mb-2">
              Pipeline Ablation Analysis
            </h3>
            <div className="space-y-2.5">
              {Object.entries(report.ablations).map(([k, a]: [string, any]) => (
                <div key={k} className="p-3 bg-[#090B10] border border-slate-800 rounded flex items-center justify-between text-xs">
                  <div>
                    <div className="font-semibold text-slate-200">{a.name}</div>
                    <div className="text-[11px] text-slate-500">FP/1000: {a.fp_per_1000?.toFixed(1) || '0.0'} · Precision: {(a.precision * 100).toFixed(1)}%</div>
                  </div>
                  <div className="font-mono text-sm font-bold text-emerald-400">
                    F1: {a.f1.toFixed(3)}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Evasion Boundaries: What Beats This Detector */}
      {report.evasionBoundaries && report.evasionBoundaries.length > 0 && (
        <div className="bg-[#0E121B] border border-slate-800/90 rounded-lg overflow-hidden">
          <div className="px-5 py-3.5 bg-[#0B0E16] border-b border-slate-800/90">
            <h2 className="text-sm font-semibold text-slate-100 tracking-tight">
              Adversarial Evasion Boundaries ("What Beats This Detector")
            </h2>
            <p className="text-xs text-slate-400 mt-0.5">
              Empirical degradation limits measured across advanced evasion tactics, reported transparently without cherry-picking.
            </p>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse text-xs">
              <thead>
                <tr className="border-b border-slate-800 text-slate-400 bg-[#090B10]/80">
                  <th className="py-2.5 px-4 font-medium">Evasion Vector</th>
                  <th className="py-2.5 px-4 font-medium">Adversary Cost</th>
                  <th className="py-2.5 px-4 font-medium">Intensity</th>
                  <th className="py-2.5 px-4 font-medium">Observed Recall</th>
                  <th className="py-2.5 px-4 font-medium">Empirical Assessment</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/70 text-slate-300">
                {report.evasionBoundaries.map((ev: any, idx: number) => (
                  <tr key={idx} className="hover:bg-slate-900/40 font-mono">
                    <td className="py-2.5 px-4 font-semibold text-slate-100 font-sans">{ev.evasion}</td>
                    <td className="py-2.5 px-4">{ev.cost}</td>
                    <td className="py-2.5 px-4">{ev.intensity}</td>
                    <td className="py-2.5 px-4 text-sky-400 font-bold">{(ev.observedRecall * 100).toFixed(0)}%</td>
                    <td className="py-2.5 px-4 text-slate-300 font-sans">{ev.status}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Phase 8.7 Honest Assessment: Which Evasions Beat the Detector */}
      <div className="bg-[#0E121B] border border-slate-800/90 rounded-lg overflow-hidden">
        <div className="px-5 py-3.5 bg-[#0B0E16] border-b border-slate-800/90">
          <h2 className="text-sm font-semibold text-slate-100 tracking-tight">
            Adversarial Analysis: Which Evasion Tactics Beat the Detector (Phase 8.7)
          </h2>
          <p className="text-xs text-slate-400 mt-0.5">
            Single-signal evasions only modestly reduce F1 because the remaining three signals preserve Louvain modularity. Multi-axis evasion degrades detection as documented below:
          </p>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse text-xs">
            <thead>
              <tr className="border-b border-slate-800 text-slate-400 bg-[#090B10]/80">
                <th className="py-2.5 px-4 font-medium">Adversarial Evasion Tactic</th>
                <th className="py-2.5 px-4 font-medium">Failure Threshold</th>
                <th className="py-2.5 px-4 font-medium">Root Technical Cause</th>
                <th className="py-2.5 px-4 font-medium">Production Mitigation Roadmap</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/70 text-slate-300">
              {report.honestLimitations?.map((item: any, idx: number) => {
                if (typeof item === 'string') {
                  return (
                    <tr key={idx} className="align-top hover:bg-slate-900/40">
                      <td colSpan={4} className="py-3 px-4 text-slate-300">
                        • {item}
                      </td>
                    </tr>
                  );
                }
                return (
                  <tr key={idx} className="align-top hover:bg-slate-900/40">
                    <td className="py-3 px-4 font-semibold text-slate-100 w-1/4">
                      {item.tactic}
                    </td>
                    <td className="py-3 px-4 text-amber-300 w-1/4">
                      {item.beatsDetectorAt}
                    </td>
                    <td className="py-3 px-4 text-slate-300 w-1/4">
                      {item.whyItWorks}
                    </td>
                    <td className="py-3 px-4 text-sky-300 w-1/4">
                      {item.nextMitigation}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

export default EvaluationLabView;
