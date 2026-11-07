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

type SummaryStat = {
  mean?: number | null;
  std?: number | null;
  ci_low?: number | null;
  ci_high?: number | null;
  note?: string;
};

function formatMaybe(value: number | null | undefined, digits: number, percent = false): string {
  if (value == null || Number.isNaN(value)) return 'n/a';
  return percent ? `${(value * 100).toFixed(digits)}%` : value.toFixed(digits);
}

function formatStat(stat: SummaryStat | undefined, percent: boolean, digits: number): { headline: string; interval: string } {
  if (!stat || stat.mean == null) {
    return { headline: 'n/a', interval: stat?.note || 'n/a' };
  }
  const scale = percent ? 100 : 1;
  const suffix = percent ? '%' : '';
  const std = stat.std == null ? '' : ` ± ${(stat.std * scale).toFixed(digits)}${suffix}`;
  const interval =
    stat.ci_low == null || stat.ci_high == null
      ? stat.note || 'CI withheld (n < 10)'
      : `[${(stat.ci_low * scale).toFixed(digits)}${suffix}, ${(stat.ci_high * scale).toFixed(digits)}${suffix}]`;
  return { headline: `${(stat.mean * scale).toFixed(digits)}${suffix}${std}`, interval };
}

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
  const [organicSampleSize, setOrganicSampleSize] = useState<number>(80);
  const rerun = onRerunEvaluation
    ? () => onRerunEvaluation(organicSampleSize)
    : onRun
      ? () => onRun()
      : undefined;

  if (!report || report.status === 'not_run') {
    return (
      <div className="p-8 bg-[rgba(16,36,66,0.42)] backdrop-blur-xl border border-white/10 rounded-[26px] text-center space-y-3">
        <p className="text-sm text-[#D4CBBE]">No benchmark is stored.</p>
        <p className="text-xs text-[#8E867C]">{report?.detail || 'The lab button runs two seeds. The 10-seed run is python -m backend.app.sim.run_eval.'}</p>
        <button
          type="button"
          disabled={!rerun || isRunning}
          onClick={() => rerun && rerun()}
          className="px-4 py-1.5 text-xs font-semibold bg-[#E07A62] hover:bg-[#E8927C] disabled:opacity-50 text-[#FFF8F3] rounded"
        >
          {isRunning ? 'Running lab sample...' : 'Run lab sample'}
        </button>
      </div>
    );
  }

  const stress = report.falsePositiveStressTest ?? report.falsePositiveStress;
  const planted = report.plantedNetworks ?? [];

  return (
    <div className="space-y-5">
      {/* Unified Command & Ground-Truth Telemetry Strip */}
      <section className="bg-[rgba(16,36,66,0.42)] backdrop-blur-xl border border-white/10 rounded-[26px] overflow-hidden">
        <div className="px-5 py-4 bg-[rgba(8,20,42,0.5)] border-b border-white/10 flex flex-wrap items-center justify-between gap-4">
          <div className="max-w-2xl">
            <h1 className="text-lg font-bold text-[#F6F1E8] font-display tracking-tight">
              Evaluation Lab & Adversarial Bot Evasion Benchmark
            </h1>
            <p className="text-xs text-[#B6AC9E] mt-1 leading-relaxed">
              {report.splitDescription || 'Same 12 families on the dev seeds and the unseen seeds.'}
              {report.label ? ` Label: ${report.label}.` : ''}
              {report.organicAccounts != null ? ` Organic accounts per seed: ${report.organicAccounts}.` : ''}
            </p>
            {!report.splitDescription && (
              <p className="text-xs text-[#F0D7B4] mt-1">This cached report came from the previous runner. Regenerate it with python -m backend.app.sim.run_eval.</p>
            )}
          </div>

          <form
            onSubmit={(e) => {
              e.preventDefault();
              if (rerun) rerun();
            }}
            className="flex items-center gap-3"
          >
            <label className="text-xs text-[#D4CBBE] flex items-center gap-2">
              <span>Lab sample organic cap:</span>
              <select
                aria-label="Organic Background Accounts"
                value={organicSampleSize}
                onChange={(e) => setOrganicSampleSize(Number(e.target.value))}
                className="bg-[rgba(7,18,36,0.55)] border border-white/15 rounded px-2.5 py-1.5 text-xs text-[#F6F1E8] font-mono tabular-nums"
              >
                <option value={40}>40 organic</option>
                <option value={80}>80 organic</option>
              </select>
            </label>
            <button
              type="button"
              disabled={!rerun || isRunning}
              onClick={() => rerun && rerun()}
              className="px-4 py-1.5 text-xs font-semibold bg-[#E07A62] hover:bg-[#E8927C] disabled:opacity-50 text-[#FFF8F3] rounded transition-colors whitespace-nowrap shrink-0"
            >
              {isRunning ? 'Running lab sample...' : 'Run lab sample'}
            </button>
          </form>
        </div>

        {/* 4-Column Architectural Confusion Matrix Ribbon */}
        <div className="grid grid-cols-2 lg:grid-cols-4 divide-y lg:divide-y-0 lg:divide-x divide-white/10">
          <div className="px-5 py-3.5">
            <div className="text-[11px] font-medium text-[#B6AC9E]">Account-Level Precision</div>
            <div className="mt-1 flex items-baseline justify-between gap-2 font-mono tabular-nums">
              <span className="text-2xl font-bold text-[#C5DCCB]">
                {formatMaybe(report.precision, 1, true)}
              </span>
              <span className="text-xs text-[#B6AC9E]">
                {report.truePositives ?? 'n/a'} TP · {report.falsePositives ?? 'n/a'} FP
              </span>
            </div>
          </div>

          <div className="px-5 py-3.5">
            <div className="text-[11px] font-medium text-[#B6AC9E]">Account-Level Recall</div>
            <div className="mt-1 flex items-baseline justify-between gap-2 font-mono tabular-nums">
              <span className="text-2xl font-bold text-[#F0B5A2]">
                {formatMaybe(report.recall, 1, true)}
              </span>
              <span className="text-xs text-[#B6AC9E]">
                {report.truePositives ?? 'n/a'}/{report.plantedBotAccounts ?? 'n/a'} on the first dev seed
              </span>
            </div>
          </div>

          <div className="px-5 py-3.5">
            <div className="text-[11px] font-medium text-[#B6AC9E]">Overall Benchmark F1 Score</div>
            <div className="mt-1 flex items-baseline justify-between gap-2 font-mono tabular-nums">
              <span className="text-2xl font-bold text-[#F6F1E8]">
                {formatMaybe(report.f1, 3)}
              </span>
              <span className="text-xs text-[#B6AC9E]">
                N = {report.totalAccounts} accounts
              </span>
            </div>
          </div>

          <div className="px-5 py-3.5">
            <div className="text-[11px] font-medium text-[#B6AC9E]">News-Burst False Positive Rate</div>
            <div className="mt-1 flex items-baseline justify-between gap-2 font-mono tabular-nums">
              <span className="text-2xl font-bold text-[#E8C9A4]">
                {stress ? formatMaybe(stress.falsePositiveRateAfter, 1, true) : 'n/a'}
              </span>
              <span className="text-xs text-[#B6AC9E]">
                {stress ? `${stress.flaggedWithProtection}/${stress.organicNewsAccounts ?? stress.organicUsersCount} with the news rule (vs ${formatMaybe(stress.falsePositiveRateBefore, 0, true)} without)` : 'not in this report'}
              </span>
            </div>
          </div>
        </div>
      </section>

      {/* Split Grid: Evasion Degradation Chart + Planted Network Breakdown */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-5 items-stretch">
        {/* Evasion Curve Chart (7 cols) */}
        <div className="lg:col-span-7 bg-[rgba(16,36,66,0.42)] backdrop-blur-xl border border-white/10 rounded-[26px] overflow-hidden flex flex-col justify-between">
          <div className="px-5 py-3.5 bg-[rgba(8,20,42,0.5)] border-b border-white/10">
            <h2 className="text-sm font-semibold text-[#F6F1E8] tracking-tight">
              Detection Performance (F1) vs. Adversarial Evasion Intensity
            </h2>
            <p className="text-xs text-[#B6AC9E] mt-0.5">
              Measures how account-level F1 degrades as planted bot networks progressively apply 4 independent evasion tactics from 0% (Baseline) to 90% (Extreme).
            </p>
          </div>

          <div className="p-5 h-80 w-full" data-testid="evasion-chart-container">
            {report.evasionCurve && report.evasionCurve.length > 0 ? (
            <ResponsiveContainer width="100%" height="100%">
              <LineChart
                data={report.evasionCurve}
                margin={{ top: 10, right: 20, left: -10, bottom: 5 }}
              >
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(246,241,232,0.08)" />
                <XAxis
                  dataKey="level"
                  stroke="#B6AC9E"
                  tick={{ fill: '#B6AC9E', fontSize: 11 }}
                />
                <YAxis
                  domain={[0, 1.0]}
                  stroke="#B6AC9E"
                  tick={{ fill: '#B6AC9E', fontSize: 11 }}
                />
                <Tooltip
                  contentStyle={{
                    backgroundColor: '#10243F',
                    borderColor: 'rgba(246,241,232,0.16)',
                    fontSize: '12px',
                    color: '#F6F1E8',
                  }}
                />
                <Legend wrapperStyle={{ fontSize: '12px', paddingTop: '8px', color: '#E8DFD2' }} />
                <Line
                  type="monotone"
                  dataKey="textParaphraseF1"
                  name="Text Paraphrasing"
                  stroke="#E07A62"
                  strokeWidth={2}
                  dot={{ r: 4 }}
                />
                <Line
                  type="monotone"
                  dataKey="randomDelayF1"
                  name="Random Posting Delays"
                  stroke="#E8B86D"
                  strokeWidth={2}
                  dot={{ r: 4 }}
                />
                <Line
                  type="monotone"
                  dataKey="ageSpreadF1"
                  name="Spread Account Creation"
                  stroke="#F6F1E8"
                  strokeWidth={2}
                  dot={{ r: 4 }}
                />
                <Line
                  type="monotone"
                  dataKey="linkRotationF1"
                  name="Link & Tag Rotation"
                  stroke="#B7D4C4"
                  strokeWidth={2}
                  dot={{ r: 4 }}
                />
              </LineChart>
            </ResponsiveContainer>
            ) : (
              <p className="text-xs text-[#B6AC9E]">This run has no evasion-intensity curve. Measured rows, when present, are in the table below.</p>
            )}
          </div>
        </div>

        {/* Planted Bot Networks Ground-Truth Table + Viral News Stress Test (5 cols) */}
        <div className="lg:col-span-5 bg-[rgba(16,36,66,0.42)] backdrop-blur-xl border border-white/10 rounded-[26px] overflow-hidden divide-y divide-white/10 flex flex-col justify-between">
          <div>
            <div className="px-4 py-3 bg-[rgba(8,20,42,0.5)] border-b border-white/10">
              <h2 className="text-sm font-semibold text-[#F6F1E8] tracking-tight">
                Planted Bot Networks (Ground-Truth Breakdown)
              </h2>
            </div>
            <div className="p-4 overflow-x-auto">
              <table className="w-full text-left border-collapse text-xs">
                <thead>
                  <tr className="border-b border-white/10 text-[#B6AC9E]">
                    <th className="py-2 pr-2 font-medium">Network</th>
                    <th className="py-2 px-2 font-medium text-right">Caught</th>
                    <th className="py-2 px-2 font-medium text-right">Recall</th>
                    <th className="py-2 pl-2 font-medium text-right">Mean Score</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/[0.08] font-mono tabular-nums">
                  {planted.length === 0 ? (
                    <tr>
                      <td colSpan={4} className="py-3 text-[#8E867C] font-sans">This report has no per-network breakdown.</td>
                    </tr>
                  ) : planted.map((net) => (
                    <tr key={net.id || net.name} className="hover:bg-white/[0.04]">
                      <td className="py-2.5 pr-2 font-sans">
                        <div className="font-medium text-[#E8DFD2]">{net.name}</div>
                        <div className="text-[11px] text-[#B6AC9E]">{net.tactic}</div>
                      </td>
                      <td className="py-2.5 px-2 text-right text-[#E8DFD2]">
                        {net.detectedAccounts ?? 'n/a'}/{net.plantedAccounts ?? 'n/a'}
                      </td>
                      <td className="py-2.5 px-2 text-right text-[#C5DCCB]">
                        {formatMaybe(net.recall, 0, true)}
                      </td>
                      <td className="py-2.5 pl-2 text-right text-[#F0A898]">
                        {net.meanClusterScore ?? 'n/a'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Phase 8.5 False-Positive Stress Test Summary */}
          <div className="p-4 bg-[rgba(7,18,36,0.45)]">
            <h3 className="text-xs font-semibold text-[#E8DFD2]">
              False-Positive Stress Test: Viral Breaking News Event
            </h3>
            {stress ? (
              <>
            <p className="text-xs text-[#B6AC9E] mt-1 leading-relaxed">
              {stress.scenario}
            </p>
            <div className="mt-3 grid grid-cols-2 gap-3 text-xs font-mono tabular-nums">
              <div className="p-2.5 bg-[rgba(7,18,36,0.55)] border border-white/10 rounded">
                <div className="text-[#B6AC9E]">News rule off</div>
                <div className="text-base font-bold text-[#F0A898] mt-0.5">
                  {stress.rawFlaggedWithoutProtection}/{stress.organicNewsAccounts ?? stress.organicUsersCount} inauthentic
                </div>
              </div>
              <div className="p-2.5 bg-[rgba(7,18,36,0.55)] border border-white/10 rounded">
                <div className="text-[#B6AC9E]">News rule on</div>
                <div className="text-base font-bold text-[#C5DCCB] mt-0.5">
                  {stress.flaggedWithProtection}/{stress.organicNewsAccounts ?? stress.organicUsersCount} inauthentic
                </div>
              </div>
            </div>
            <p className="text-[11px] text-[#B6AC9E] mt-2 leading-relaxed">
              {stress.explanation}
            </p>
              </>
            ) : (
              <p className="text-xs text-[#8E867C] mt-1">This report has no news-burst stress test.</p>
            )}
          </div>
        </div>
      </div>

      {/* Benchmark v2: Dev Split vs. Held-Out Test Split (95% Bootstrap CIs) */}
      {report.devSummary && report.testSummary && (
        <div className="bg-[rgba(16,36,66,0.42)] backdrop-blur-xl border border-white/10 rounded-[26px] overflow-hidden">
          <div className="px-5 py-3.5 bg-[rgba(8,20,42,0.5)] border-b border-white/10 flex flex-wrap items-center justify-between gap-3">
            <div>
              <h2 className="text-sm font-semibold text-[#F6F1E8] tracking-tight flex items-center gap-2">
                <span>Same families, unseen seeds</span>
                <span className="text-[10px] bg-[rgba(183,212,196,0.16)] text-[#D5E8DC] border border-[rgba(183,212,196,0.38)] px-2 py-0.5 rounded font-mono font-bold uppercase">
                  Audited Reproducible
                </span>
              </h2>
              <p className="text-xs text-[#B6AC9E] mt-0.5">
                Dev and test plant the same 12 families and all 10 hard negatives. The seeds differ. A confidence interval is shown only when at least 10 seeds were run.
              </p>
            </div>
            {report.nullControl && (
              <div className="px-3 py-1 bg-[rgba(7,18,36,0.45)] border border-white/10 rounded text-xs font-mono">
                <span className="text-[#B6AC9E]">Null Control: </span>
                <span className="text-[#C5DCCB] font-bold">{report.nullControl.status}</span>
              </div>
            )}
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse text-xs font-mono tabular-nums">
              <thead>
                <tr className="border-b border-white/10 text-[#B6AC9E] bg-[rgba(7,18,36,0.62)]">
                  <th className="py-2.5 px-4 font-medium">Evaluation Metric</th>
                  <th className="py-2.5 px-4 font-medium text-center">Dev seeds</th>
                  <th className="py-2.5 px-4 font-medium text-center text-[#F0B5A2]">Unseen seeds</th>
                  <th className="py-2.5 px-4 font-medium">Methodological Significance</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/10 text-[#D4CBBE]">
                {([
                  ['precision', 'Account-level precision', true, 1, 'Flagged accounts that are planted bots'],
                  ['recall', 'Account-level recall', true, 1, 'Planted bots that were flagged'],
                  ['f1', 'F1', false, 3, 'Harmonic mean of precision and recall'],
                  ['pr_auc', 'PR-AUC', false, 3, 'Accounts outside an inauthentic cluster score 0'],
                  ['campaign_recall', 'Campaign recall', true, 0, 'Campaigns with at least half their members flagged'],
                  ['cluster_purity', 'Cluster purity', false, 3, 'n/a when a seed produced no inauthentic cluster'],
                  ['hard_neg_flag_rate', 'Hard-negative flag rate', true, 1, 'Hard-negative scenarios with any inauthentic member'],
                ] as [string, string, boolean, number, string][]).map(([key, label, percent, digits, note]) => {
                  const devStat = formatStat(report.devSummary[key], percent, digits);
                  const testStat = formatStat(report.testSummary[key], percent, digits);
                  return (
                    <tr key={key} className="hover:bg-white/[0.04]">
                      <td className="py-2.5 px-4 font-semibold text-[#F6F1E8]">{label}</td>
                      <td className="py-2.5 px-4 text-center text-[#C5DCCB] font-bold">
                        {devStat.headline}
                        <div className="text-[10px] text-[#8E867C] font-normal">{devStat.interval}</div>
                      </td>
                      <td className="py-2.5 px-4 text-center text-[#F0B5A2] font-bold bg-[rgba(224,122,98,0.1)]">
                        {testStat.headline}
                        <div className="text-[10px] text-[#8E867C] font-normal">{testStat.interval}</div>
                      </td>
                      <td className="py-2.5 px-4 text-[#B6AC9E] font-sans text-xs">{note}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Baselines & Ablations Grid */}
      {report.baselines && report.ablations && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
          <div className="bg-[rgba(16,36,66,0.42)] backdrop-blur-xl border border-white/10 rounded-[26px] p-5">
            <h3 className="text-xs font-semibold text-[#E8DFD2] uppercase tracking-wider mb-2">
              Model Baselines Comparison
            </h3>
            <div className="space-y-2.5">
              {Object.entries(report.baselines).map(([k, b]: [string, any]) => (
                <div key={k} className="p-3 bg-[rgba(7,18,36,0.55)] border border-white/10 rounded flex items-center justify-between text-xs">
                  <div>
                    <div className="font-semibold text-[#E8DFD2]">{b.name}</div>
                    <div className="text-[11px] text-[#8E867C]">Precision: {formatMaybe(b.precision, 1, true)} · Recall: {formatMaybe(b.recall, 1, true)}</div>
                  </div>
                  <div className="font-mono text-sm font-bold text-[#F0B5A2]">
                    F1: {formatMaybe(b.f1, 3)}
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className="bg-[rgba(16,36,66,0.42)] backdrop-blur-xl border border-white/10 rounded-[26px] p-5">
            <h3 className="text-xs font-semibold text-[#E8DFD2] uppercase tracking-wider mb-2">
              Pipeline Ablation Analysis
            </h3>
            <div className="space-y-2.5">
              {Object.entries(report.ablations).map(([k, a]: [string, any]) => (
                <div key={k} className="p-3 bg-[rgba(7,18,36,0.55)] border border-white/10 rounded flex items-center justify-between text-xs">
                  <div>
                    <div className="font-semibold text-[#E8DFD2]">{a.name}</div>
                    <div className="text-[11px] text-[#8E867C]">FP/1000 organic: {formatMaybe(a.fp_per_1000, 1)} · Precision: {formatMaybe(a.precision, 1, true)}</div>
                  </div>
                  <div className="font-mono text-sm font-bold text-[#C5DCCB]">
                    F1: {formatMaybe(a.f1, 3)}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Evasion Boundaries: What Beats This Detector */}
      {report.evasionBoundaries && report.evasionBoundaries.length > 0 && (
        <div className="bg-[rgba(16,36,66,0.42)] backdrop-blur-xl border border-white/10 rounded-[26px] overflow-hidden">
          <div className="px-5 py-3.5 bg-[rgba(8,20,42,0.5)] border-b border-white/10">
            <h2 className="text-sm font-semibold text-[#F6F1E8] tracking-tight">
              Adversarial Evasion Boundaries ("What Beats This Detector")
            </h2>
            <p className="text-xs text-[#B6AC9E] mt-0.5">
              Empirical degradation limits measured across advanced evasion tactics, reported transparently without cherry-picking.
            </p>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse text-xs">
              <thead>
                <tr className="border-b border-white/10 text-[#B6AC9E] bg-[rgba(7,18,36,0.62)]">
                  <th className="py-2.5 px-4 font-medium">Evasion</th>
                  <th className="py-2.5 px-4 font-medium">Family</th>
                  <th className="py-2.5 px-4 font-medium">Seed</th>
                  <th className="py-2.5 px-4 font-medium">Organic</th>
                  <th className="py-2.5 px-4 font-medium">Observed recall</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/10 text-[#D4CBBE]">
                {report.evasionBoundaries.map((ev: any, idx: number) => (
                  <tr key={idx} className="hover:bg-white/[0.04] font-mono">
                    <td className="py-2.5 px-4 font-semibold text-[#F6F1E8] font-sans">{ev.evasion}</td>
                    <td className="py-2.5 px-4">{ev.familyId || '—'}</td>
                    <td className="py-2.5 px-4">{ev.seed ?? 'missing seed'}</td>
                    <td className="py-2.5 px-4">{ev.organicCount ?? '—'}</td>
                    <td className="py-2.5 px-4 text-[#F0B5A2] font-bold">{formatMaybe(ev.observedRecall, 0, true)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Phase 8.7 Honest Assessment: Which Evasions Beat the Detector */}
      <div className="bg-[rgba(16,36,66,0.42)] backdrop-blur-xl border border-white/10 rounded-[26px] overflow-hidden">
        <div className="px-5 py-3.5 bg-[rgba(8,20,42,0.5)] border-b border-white/10">
          <h2 className="text-sm font-semibold text-[#F6F1E8] tracking-tight">
            Adversarial Analysis: Which Evasion Tactics Beat the Detector (Phase 8.7)
          </h2>
          <p className="text-xs text-[#B6AC9E] mt-0.5">
            Limits stored with the report. A measured recall appears only in the evasion table above.
          </p>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse text-xs">
            <thead>
              <tr className="border-b border-white/10 text-[#B6AC9E] bg-[rgba(7,18,36,0.62)]">
                <th className="py-2.5 px-4 font-medium">Adversarial Evasion Tactic</th>
                <th className="py-2.5 px-4 font-medium">Failure Threshold</th>
                <th className="py-2.5 px-4 font-medium">Root Technical Cause</th>
                <th className="py-2.5 px-4 font-medium">Production Mitigation Roadmap</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/10 text-[#D4CBBE]">
              {report.honestLimitations?.map((item: any, idx: number) => {
                if (typeof item === 'string') {
                  return (
                    <tr key={idx} className="align-top hover:bg-white/[0.04]">
                      <td colSpan={4} className="py-3 px-4 text-[#D4CBBE]">
                        • {item}
                      </td>
                    </tr>
                  );
                }
                return (
                  <tr key={idx} className="align-top hover:bg-white/[0.04]">
                    <td className="py-3 px-4 font-semibold text-[#F6F1E8] w-1/4">
                      {item.tactic}
                    </td>
                    <td className="py-3 px-4 text-[#F0D7B4] w-1/4">
                      {item.beatsDetectorAt}
                    </td>
                    <td className="py-3 px-4 text-[#D4CBBE] w-1/4">
                      {item.whyItWorks}
                    </td>
                    <td className="py-3 px-4 text-[#F6C7B6] w-1/4">
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
