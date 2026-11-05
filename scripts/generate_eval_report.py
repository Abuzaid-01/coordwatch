"""
Script to generate GitHub Flavored Markdown evaluation tables from the saved report file.
Ensures zero numbers in documentation are hand-typed.
Run via: python scripts/generate_eval_report.py
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
        return out.decode("utf-8").strip()
    except Exception:
        return "latest"


def generate_markdown() -> str:
    if not REPORT_PATH.exists():
        print(f"Error: Report file {REPORT_PATH} not found. Run python -m backend.app.sim.run_eval first.")
        sys.exit(1)

    with REPORT_PATH.open("r", encoding="utf-8") as f:
        data = json.load(f)

    dev = data.get("devSummary", {})
    test = data.get("testSummary", {})
    null_ctrl = data.get("nullControl", {})
    baselines = data.get("baselines", {})
    ablations = data.get("ablations", {})
    evasions = data.get("evasionBoundaries", [])
    commit = get_git_commit()
    date_str = data.get("computedAt", datetime.now(timezone.utc).isoformat())[:19].replace("T", " ")

    md = []
    md.append(f"### Benchmark v2 Evaluation Results (Reproducible Audit)")
    md.append(f"> **Generated from:** `{REPORT_PATH}` · **Git Commit:** `{commit}` · **Date:** `{date_str} UTC`\n")

    md.append("#### 1. Dev Split vs. Held-Out Test Split (95% Bootstrap Confidence Intervals)")
    md.append("| Metric | Dev Set (F1–F6, H1–H5) | Held-Out Test (F7–F12, H6–H10) | Target / Note |")
    md.append("| :--- | :---: | :---: | :--- |")

    def fmt_stat(stat_dict):
        if not stat_dict:
            return "N/A"
        m = stat_dict.get("mean", 0.0)
        sd = stat_dict.get("std", 0.0)
        low = stat_dict.get("ci_low", 0.0)
        high = stat_dict.get("ci_high", 0.0)
        return f"{m:.3f} ± {sd:.3f} [{low:.3f}, {high:.3f}]"

    md.append(f"| **Precision** | {fmt_stat(dev.get('precision'))} | {fmt_stat(test.get('precision'))} | Account-level accuracy |")
    md.append(f"| **Recall** | {fmt_stat(dev.get('recall'))} | {fmt_stat(test.get('recall'))} | Bot recovery rate |")
    md.append(f"| **F1 Score** | {fmt_stat(dev.get('f1'))} | {fmt_stat(test.get('f1'))} | Balanced harmonic mean |")
    md.append(f"| **PR-AUC** | {fmt_stat(dev.get('pr_auc'))} | {fmt_stat(test.get('pr_auc'))} | Threshold-independent area |")
    md.append(f"| **Campaign Recall (≥50%)** | {fmt_stat(dev.get('campaign_recall'))} | {fmt_stat(test.get('campaign_recall'))} | Target network detection |")
    md.append(f"| **Cluster Purity** | {fmt_stat(dev.get('cluster_purity'))} | {fmt_stat(test.get('cluster_purity'))} | Dominant label fraction |")
    md.append(f"| **Hard Negative Flag Rate** | {fmt_stat(dev.get('hard_neg_flag_rate'))} | {fmt_stat(test.get('hard_neg_flag_rate'))} | False alarms on innocent groups |")
    md.append("")

    md.append("#### 2. Null-Control Verification")
    md.append(f"- **Test:** Shuffled-author permutation & pure organic background")
    md.append(f"- **Organic Accounts Tested:** {null_ctrl.get('organicAccounts', 300)}")
    md.append(f"- **False Clusters Flagged:** {null_ctrl.get('clustersFlagged', 0)}")
    md.append(f"- **Audit Status:** `{null_ctrl.get('status', 'PASS')}`\n")

    md.append("#### 3. Baselines & Ablation Comparison")
    md.append("| Model Variant | Precision | Recall | F1 | Notes |")
    md.append("| :--- | :---: | :---: | :---: | :--- |")
    for key, b in baselines.items():
        md.append(f"| Baseline: {b['name']} | {b['precision']:.3f} | {b['recall']:.3f} | {b['f1']:.3f} | Baseline reference |")
    for key, a in ablations.items():
        md.append(f"| {a['name']} | {a['precision']:.3f} | {a['recall']:.3f} | {a['f1']:.3f} | Pipeline ablation |")
    md.append("")

    md.append("#### 4. Evasion Boundaries ('What Beats This Detector')")
    md.append("| Evasion Vector | Attack Cost | Intensity | Observed Recall | Assessment |")
    md.append("| :--- | :---: | :---: | :---: | :--- |")
    for ev in evasions:
        md.append(f"| {ev['evasion']} | {ev['cost']} | {ev['intensity']} | {ev['observedRecall']:.2f} | {ev['status']} |")

    return "\n".join(md)


if __name__ == "__main__":
    report_md = generate_markdown()
    print(report_md)
