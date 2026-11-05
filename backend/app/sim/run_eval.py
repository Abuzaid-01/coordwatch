"""
Offline evaluation runner script for CoordWatch.
Run via: python -m backend.app.sim.run_eval
Measures precision, recall, F1 across seeds, runs real evasion sweeps and real FP stress tests,
and persists the report into the evaluation_runs SQLite table.
"""

from datetime import datetime, timezone
import json
import logging
from pathlib import Path
import sys

from ..config import settings
from ..db import get_connection, init_db
from .simulator import run_full_evaluation_suite

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("eval_runner")


def run_and_store_evaluation(seeds=(42, 43, 44), organic_count: int = 500) -> dict:
    init_db()
    logger.info(f"Starting CoordWatch Ground-Truth Benchmark across seeds {seeds} with {organic_count} organic accounts...")

    all_results = []
    for s in seeds:
        logger.info(f"Running benchmark with seed={s}...")
        res = run_full_evaluation_suite(organic_count=organic_count, seed=s)
        all_results.append(res)

    # Average metrics over seeds
    avg_p = sum(r["precision"] for r in all_results) / len(all_results)
    avg_r = sum(r["recall"] for r in all_results) / len(all_results)
    avg_f1 = sum(r["f1"] for r in all_results) / len(all_results)

    final_report = all_results[0]
    final_report["multiSeedSummary"] = {
        "seeds": list(seeds),
        "meanPrecision": round(avg_p, 3),
        "meanRecall": round(avg_r, 3),
        "meanF1": round(avg_f1, 3),
        "date": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
    }

    # Store into evaluation_runs table
    conn = get_connection()
    try:
        now = datetime.now(timezone.utc).isoformat()
        conn.execute(
            "INSERT INTO evaluation_runs (report_json, computed_at) VALUES (?, ?)",
            (json.dumps(final_report), now),
        )
        conn.commit()
        logger.info(f"Evaluation persisted to evaluation_runs table.")
    finally:
        conn.close()

    print("\n" + "=" * 60)
    print("COORDWATCH EVALUATION BENCHMARK RESULTS")
    print("=" * 60)
    print(f"Seeds evaluated: {seeds}")
    print(f"Precision:       {avg_p:.3f}")
    print(f"Recall:          {avg_r:.3f}")
    print(f"F1 Score:        {avg_f1:.3f}")
    print(f"Planted bots:    {final_report['plantedBotAccounts']}")
    print(f"Organic users:   {final_report['organicAccounts']}")
    print(f"True Positives:  {final_report['truePositives']}")
    print(f"False Positives: {final_report['falsePositives']}")
    print("-" * 60)
    print("False Positive Stress Test:")
    fps = final_report["falsePositiveStress"]
    print(f"  Raw flagged without protection: {fps['rawFlaggedWithoutProtection']} / {fps['organicNewsAccounts']} ({fps['falsePositiveRateBefore']*100:.1f}%)")
    print(f"  Flagged with protection:        {fps['flaggedWithProtection']} / {fps['organicNewsAccounts']} ({fps['falsePositiveRateAfter']*100:.1f}%)")
    print("=" * 60 + "\n")

    return final_report


if __name__ == "__main__":
    run_and_store_evaluation()

