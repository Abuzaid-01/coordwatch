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
from .benchmark_v2 import run_benchmark_v2_suite

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("eval_runner")


def run_and_store_evaluation(seeds=None, organic_count: int = 200) -> dict:
    init_db()
    dev_seeds = list(seeds or list(range(42, 52)))
    test_seeds = [seed + 100 for seed in dev_seeds]
    logger.info(
        "Published benchmark: dev seeds %s, test seeds %s, organic=%s",
        dev_seeds, test_seeds, organic_count,
    )
    final_report = run_benchmark_v2_suite(
        seeds=dev_seeds,
        test_seeds=test_seeds,
        organic_count=organic_count,
        n_permutations=200,
        evasion_seeds=dev_seeds,
        label="published",
    )
    avg_p = final_report.get("precision") or 0
    avg_r = final_report.get("recall") or 0
    avg_f1 = final_report.get("f1") or 0

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
    print(f"Seeds evaluated: {dev_seeds}")
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

