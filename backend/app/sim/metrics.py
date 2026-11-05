"""
Benchmark v2: Comprehensive Trustworthy Metrics Calculator.

Computes multi-level metrics:
- Account-Level: Precision, Recall, F1, PR-AUC, FP per 1,000 organic accounts.
- Campaign-Level: Campaign Recall@50% (fraction of campaigns with >=50% members flagged).
- Cluster-Level: Cluster Purity, Pairwise F1 (completeness), Precision@k.
- Bootstrap 95% Confidence Intervals (CI).
"""

import math
import random
from typing import Any, Dict, List, Optional, Set, Tuple


def compute_account_metrics(
    detected_dids: Set[str],
    ground_truth_bot_dids: Set[str],
    organic_count: int,
) -> Dict[str, Any]:
    tp = len(detected_dids & ground_truth_bot_dids)
    fp = len(detected_dids - ground_truth_bot_dids)
    fn = len(ground_truth_bot_dids - detected_dids)
    tn = max(0, organic_count - fp)

    precision = round(tp / max(1, tp + fp), 4)
    recall = round(tp / max(1, tp + fn), 4)
    f1 = round((2 * precision * recall) / max(1e-9, precision + recall), 4)

    # False Positives per 1,000 organic accounts
    fp_per_1000 = round((fp / max(1, organic_count)) * 1000.0, 2)

    return {
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "tn": tn,
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "fp_per_1000": fp_per_1000,
    }


def compute_pr_auc(
    node_scores: Dict[str, float],
    ground_truth_bot_dids: Set[str],
    all_dids: Set[str],
) -> float:
    """Computes Area Under the Precision-Recall Curve by sweeping threshold from 0 to 100."""
    thresholds = list(range(0, 105, 5))
    points: List[Tuple[float, float]] = []

    for t in thresholds:
        predicted = {did for did, s in node_scores.items() if s >= t}
        tp = len(predicted & ground_truth_bot_dids)
        fp = len(predicted - ground_truth_bot_dids)
        fn = len(ground_truth_bot_dids - predicted)

        prec = tp / max(1, tp + fp)
        rec = tp / max(1, tp + fn)
        points.append((rec, prec))

    # Sort by recall ascending
    points.sort(key=lambda p: p[0])

    # Trapezoidal integration for PR-AUC
    auc = 0.0
    for i in range(1, len(points)):
        r_prev, p_prev = points[i - 1]
        r_curr, p_curr = points[i]
        auc += (r_curr - r_prev) * ((p_prev + p_curr) / 2.0)

    return round(max(0.0, min(1.0, auc)), 4)


def compute_campaign_level_recall(
    detected_dids: Set[str],
    campaigns: List[Dict[str, Any]],
    threshold_fraction: float = 0.50,
) -> Dict[str, Any]:
    """Measures what fraction of planted campaigns had >=50% of their members detected."""
    if not campaigns:
        return {"campaigns_total": 0, "campaigns_detected": 0, "campaign_recall": 1.0, "breakdown": []}

    detected_count = 0
    breakdown = []
    for c in campaigns:
        members = set(c["dids"])
        detected_members = len(members & detected_dids)
        ratio = detected_members / max(1, len(members))
        found = ratio >= threshold_fraction
        if found:
            detected_count += 1
        breakdown.append({
            "campaign_id": c["id"],
            "name": c.get("name", c["id"]),
            "size": len(members),
            "detected_members": detected_members,
            "detection_ratio": round(ratio, 3),
            "flagged": found,
        })

    return {
        "campaigns_total": len(campaigns),
        "campaigns_detected": detected_count,
        "campaign_recall": round(detected_count / len(campaigns), 4),
        "breakdown": breakdown,
    }


def compute_cluster_purity(
    clusters: List[Dict[str, Any]],
    ground_truth_bot_dids: Set[str],
) -> float:
    """Cluster purity: average fraction of cluster members matching the dominant label."""
    if not clusters:
        return 1.0

    purities = []
    for c in clusters:
        members = set(c["memberDids"])
        if not members:
            continue
        bot_count = len(members & ground_truth_bot_dids)
        organic_count = len(members - ground_truth_bot_dids)
        dominant = max(bot_count, organic_count)
        purities.append(dominant / len(members))

    return round(sum(purities) / max(1, len(purities)), 4)


def bootstrap_ci(
    values: List[float],
    n_resamples: int = 1000,
    confidence: float = 0.95,
    seed: int = 42,
) -> Tuple[float, float, float]:
    """Computes (mean, ci_lower, ci_upper) via non-parametric bootstrap resampling."""
    if not values:
        return 0.0, 0.0, 0.0
    if len(values) == 1:
        v = round(values[0], 4)
        return v, v, v

    rng = random.Random(seed)
    n = len(values)
    resample_means: List[float] = []

    for _ in range(n_resamples):
        sample = [rng.choice(values) for _ in range(n)]
        resample_means.append(sum(sample) / n)

    resample_means.sort()
    alpha = (1.0 - confidence) / 2.0
    idx_low = max(0, int(alpha * n_resamples))
    idx_high = min(n_resamples - 1, int((1.0 - alpha) * n_resamples))

    mean_val = round(sum(values) / n, 4)
    ci_low = round(resample_means[idx_low], 4)
    ci_high = round(resample_means[idx_high], 4)

    return mean_val, ci_low, ci_high
