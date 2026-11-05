"""
Phase 4.3: Account Age Cohort Signal in Python.
Detects accounts created within the same 48-hour window with baseline topic distribution comparison (C1).
Accounts without a creation timestamp (None) are skipped (A3).
"""

from datetime import datetime
import math
from typing import Any, Dict, List, Optional, Tuple


def _parse_ts(iso_str: Optional[str]) -> float:
    if not iso_str:
        return 0.0
    try:
        return datetime.fromisoformat(iso_str.replace("Z", "+00:00")).timestamp()
    except Exception:
        return 0.0


def _pair_key(did1: str, did2: str) -> Tuple[str, str]:
    return (did1, did2) if did1 < did2 else (did2, did1)


def compute_account_age_signal(
    accounts: List[Dict[str, Any]],
    max_gap_hours: float = 48.0,
) -> List[Dict[str, Any]]:
    """
    Computes pairwise account age synchronization.
    C1: Compares cohorts against the baseline distribution of accounts in the topic.
    If the entire topic's accounts were created in the same 48h window (e.g. site-wide signup wave),
    the signal is discounted to avoid false positives.
    """
    max_gap_sec = max_gap_hours * 3600.0
    dated = []
    for a in accounts:
        c_iso = a.get("created_at") or a.get("createdAt")
        # A3: Skip accounts without valid creation timestamp
        if c_iso:
            ts = _parse_ts(c_iso)
            if ts > 0:
                dated.append({**a, "_ts": ts})

    dated.sort(key=lambda x: x["_ts"])
    if len(dated) < 2:
        return []

    # C1: Topic baseline check
    # Measure the total timespan of account creation across all accounts in this topic
    total_span_sec = dated[-1]["_ts"] - dated[0]["_ts"]
    total_span_hours = total_span_sec / 3600.0

    # If all accounts in the topic were created within 48h (e.g. signup wave or fresh cohort),
    # there is no contrast with organic accounts.
    is_uniform_wave = len(dated) >= 6 and total_span_hours <= (max_gap_hours * 1.2)

    cohort_density: Dict[str, int] = {}
    for i, a_i in enumerate(dated):
        count = sum(1 for j, a_j in enumerate(dated) if i != j and abs(a_j["_ts"] - a_i["_ts"]) <= max_gap_sec) + 1
        cohort_density[a_i["did"]] = count

    results: List[Dict[str, Any]] = []
    for i in range(len(dated)):
        a_a = dated[i]
        for j in range(i + 1, len(dated)):
            a_b = dated[j]
            delta_sec = a_b["_ts"] - a_a["_ts"]
            if delta_sec > max_gap_sec:
                break
            if a_a["did"] == a_b["did"]:
                continue

            delta_hours = delta_sec / 3600.0
            closeness = 1.0 - 0.55 * (delta_hours / max_gap_hours)
            density = max(cohort_density.get(a_a["did"], 2), cohort_density.get(a_b["did"], 2))

            # Anomaly multiplier vs topic baseline
            if is_uniform_wave:
                # Site-wide wave: everyone joined at once, so this is not anomalous coordination
                baseline_factor = 0.22
            else:
                # Baseline comparison: cohort should be a distinct cluster compared to background span
                cohort_share = density / len(dated)
                if cohort_share < 0.85 and density >= 4:
                    baseline_factor = min(1.15, 0.90 + density * 0.03)
                elif density >= 4:
                    baseline_factor = 0.80
                else:
                    baseline_factor = 0.75

            strength = round(min(1.0, closeness * baseline_factor), 4)
            if strength < 0.3:
                continue

            key = _pair_key(a_a["did"], a_b["did"])
            results.append(
                {
                    "did_a": key[0],
                    "did_b": key[1],
                    "strength": strength,
                    "reason": f"Accounts created within {delta_hours:.1f}h of each other (cohort of {density} in 48h)",
                    "signal_type": "age",
                }
            )

    results.sort(key=lambda r: r["strength"], reverse=True)
    return results
