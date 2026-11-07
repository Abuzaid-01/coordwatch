"""
Markdown tables for the measured benchmark.

Every figure comes from backend/data/evaluation_runs/latest.json.
A row without a seed is refused. A missing mean prints n/a.
A missing confidence interval prints CI withheld (n < 10).

Run:
  PYTHONPATH=. python3 -m backend.app.sim.run_eval
  PYTHONPATH=. python3 scripts/generate_eval_report.py
"""

from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys

REPORT_PATH = Path("backend/data/evaluation_runs/latest.json")


def get_git_commit() -> str:
    try:
        out = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], stderr=subprocess.DEVNULL)
        commit = out.decode("utf-8").strip()
    except Exception:
        return "uncommitted"
    try:
        dirty = subprocess.check_output(["git", "status", "--porcelain"], stderr=subprocess.DEVNULL)
    except Exception:
        return commit
    if dirty.strip():
        return f"{commit}-dirty"
    return commit


def fmt_num(value) -> str:
    if value is None:
        return "n/a"
    return f"{float(value):.3f}"


def fmt_stat(stat_dict) -> str:
    if not stat_dict or stat_dict.get("mean") is None:
        return "n/a"
    mean = float(stat_dict["mean"])
    std = stat_dict.get("std")
    std_part = "n/a" if std is None else f"{float(std):.3f}"
    low = stat_dict.get("ci_low")
    high = stat_dict.get("ci_high")
    if low is None or high is None:
        note = stat_dict.get("note") or "CI withheld (n < 10)"
        return f"{mean:.3f} ± {std_part} ({note})"
    return f"{mean:.3f} ± {std_part} [{float(low):.3f}, {float(high):.3f}]"


def render_report(data: dict) -> str:
    dev = data.get("devSummary") or {}
    test = data.get("testSummary") or {}
    null_ctrl = data.get("nullControl") or {}
    baselines = data.get("baselines") or {}
    ablations = data.get("ablations") or {}
    evasions = data.get("evasionBoundaries") or []
    for row in evasions:
        if row.get("seed") is None:
            raise ValueError(f"Evasion row {row.get('id') or row.get('evasion')} has no seed.")

    commit = get_git_commit()
    date_str = str(data.get("computedAt") or datetime.now(timezone.utc).isoformat())[:19].replace("T", " ")
    lines = [
        "### Measured benchmark",
        f"> **Generated from:** `{REPORT_PATH}` · **Git commit:** `{commit}` · **Computed:** `{date_str} UTC`",
        f"> **Label:** `{data.get('label', 'unknown')}` · **Split:** {data.get('splitDescription', 'same families, unseen seeds')}",
        f"> **Dev seeds:** `{data.get('seedsEvaluated')}` · **Test seeds:** `{data.get('testSeeds')}` · **Organic per seed:** `{data.get('organicCountPerSeed')}` · **Permutations:** `{data.get('nPermutations')}`",
        "",
        "#### Dev seeds and unseen seeds",
        "| Metric | Dev seeds | Unseen seeds | Note |",
        "| :--- | :---: | :---: | :--- |",
        f"| **Precision** | {fmt_stat(dev.get('precision'))} | {fmt_stat(test.get('precision'))} | Account-level |",
        f"| **Recall** | {fmt_stat(dev.get('recall'))} | {fmt_stat(test.get('recall'))} | Planted bots flagged |",
        f"| **F1** | {fmt_stat(dev.get('f1'))} | {fmt_stat(test.get('f1'))} | Harmonic mean |",
        f"| **PR-AUC** | {fmt_stat(dev.get('pr_auc'))} | {fmt_stat(test.get('pr_auc'))} | Outside an inauthentic cluster scores 0 |",
        f"| **Campaign recall** | {fmt_stat(dev.get('campaign_recall'))} | {fmt_stat(test.get('campaign_recall'))} | At least half the members flagged |",
        f"| **Cluster purity** | {fmt_stat(dev.get('cluster_purity'))} | {fmt_stat(test.get('cluster_purity'))} | n/a when no inauthentic cluster |",
        f"| **Hard-negative flag rate** | {fmt_stat(dev.get('hard_neg_flag_rate'))} | {fmt_stat(test.get('hard_neg_flag_rate'))} | Scenarios with any inauthentic member |",
        f"| **Organic FP per 1,000** | {fmt_stat(dev.get('fp_per_1000_organic'))} | {fmt_stat(test.get('fp_per_1000_organic'))} | Hard negatives are not in this rate |",
        "",
        "#### Null control",
        f"- **Organic accounts:** {null_ctrl.get('organicAccounts', 'n/a')}",
        f"- **Inauthentic clusters:** {null_ctrl.get('clustersFlagged', 'n/a')}",
        f"- **Organic false positives:** {null_ctrl.get('falsePositivesDetected', 'n/a')}",
        f"- **Shuffled-author campaign recall:** {null_ctrl.get('shuffledAuthorCampaignRecall', 'n/a')}",
        f"- **Status:** `{null_ctrl.get('status', 'n/a')}`",
        "",
        "#### Baselines and ablation",
        "| Variant | Precision | Recall | F1 |",
        "| :--- | :---: | :---: | :---: |",
    ]
    for item in list(baselines.values()) + list(ablations.values()):
        lines.append(
            f"| {item.get('name', 'unnamed')} | {fmt_num(item.get('precision'))} | {fmt_num(item.get('recall'))} | {fmt_num(item.get('f1'))} |"
        )
    lines.extend([
        "",
        "#### Measured evasion",
        "| Evasion | Family | Seed | Organic | Permutations | Observed recall |",
        "| :--- | :---: | :---: | :---: | :---: | :---: |",
    ])
    if not evasions:
        lines.append("| n/a | n/a | n/a | n/a | n/a | n/a |")
    for row in evasions:
        lines.append(
            f"| {row.get('evasion')} | {row.get('familyId')} | {row.get('seed')} | {row.get('organicCount')} | {row.get('nPermutations')} | {fmt_num(row.get('observedRecall'))} |"
        )
    stress = data.get("falsePositiveStressTest") or data.get("falsePositiveStress") or {}
    if stress:
        lines.extend([
            "",
            "#### News-burst stress",
            f"- **Accounts in the burst:** {stress.get('organicNewsAccounts', 'n/a')}",
            f"- **Inauthentic with the news rule off:** {stress.get('rawFlaggedWithoutProtection', 'n/a')}",
            f"- **Inauthentic with the news rule on:** {stress.get('flaggedWithProtection', 'n/a')}",
        ])
    limitations = data.get("honestLimitations") or []
    if limitations:
        lines.extend(["", "#### Limitations recorded with this run"])
        for item in limitations:
            if isinstance(item, str):
                lines.append(f"- {item}")
    return "\n".join(lines)


def generate_markdown() -> str:
    if not REPORT_PATH.exists():
        print(f"Error: {REPORT_PATH} was not found. Run python -m backend.app.sim.run_eval first.", file=sys.stderr)
        sys.exit(1)
    with REPORT_PATH.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    try:
        return render_report(data)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    print(generate_markdown())
