"""
Phase 5.3, 5.4 & 5.5: Cluster Scoring, Plain-English Reasons & False-Positive Protection.
Formula:
    score = 100 * (weight_text*text + weight_timing*timing + weight_age*age + weight_links*links)
Uses configurable weights from Settings (C6).
"""

from typing import Any, Dict, List
from ..config import settings


def compute_cluster_score_and_reasons(
    cluster_dids: List[str],
    signal_averages: Dict[str, float],
    cohort_48h_count: int,
    median_age_days: float,
    enable_fp_protection: bool = True,
) -> Dict[str, Any]:
    t_sig = signal_averages.get("text", 0.0)
    s_sig = signal_averages.get("timing", 0.0)
    a_sig = signal_averages.get("age", 0.0)
    l_sig = signal_averages.get("links", 0.0)

    # C6: Use settings weights
    raw_score = round(
        100.0
        * (
            settings.weight_text * t_sig
            + settings.weight_timing * s_sig
            + settings.weight_age * a_sig
            + settings.weight_links * l_sig
        )
    )
    raw_score = min(100, max(0, raw_score))

    discount = 0.0
    discount_reason = None
    cohort_ratio = cohort_48h_count / max(1, len(cluster_dids))

    if enable_fp_protection and median_age_days > 150 and cohort_ratio < 0.35:
        # 1.0 - fp_discount gives the discount percentage
        discount = 1.0 - settings.fp_discount_established_dispersed if l_sig >= 0.45 else 1.0 - settings.fp_discount_established_only
        discount = round(discount, 2)
        discount_reason = (
            f"Organic news-burst discount (-{int(discount * 100)}%): "
            f"Median account age is {int(median_age_days)} days with dispersed creation dates."
        )

    final_score = max(5, round(raw_score * (1.0 - discount)))

    reasons: List[str] = [
        f"{len(cluster_dids)} accounts in cluster; {cohort_48h_count} created within 48 hours",
        f"Median text similarity {t_sig:.2f}; timing sync {s_sig:.2f}; shared links {l_sig:.2f}",
    ]
    if discount_reason:
        reasons.append(discount_reason)

    return {
        "score": final_score,
        "raw_score": raw_score,
        "discount_applied": discount,
        "reasons": reasons,
    }
