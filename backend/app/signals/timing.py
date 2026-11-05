"""
Phase 4.2: Pure Timing Synchronization Signal in Python.
Measures how tightly posts cluster in time (within 60s) and checks inter-arrival cadence regularity.
"""

from datetime import datetime
import math
from typing import Any, Dict, List, Tuple


def _parse_ts(iso_str: str) -> float:
    try:
        return datetime.fromisoformat(iso_str.replace("Z", "+00:00")).timestamp()
    except Exception:
        return 0.0


def _pair_key(did1: str, did2: str) -> Tuple[str, str]:
    return (did1, did2) if did1 < did2 else (did2, did1)


def compute_timing_sync_signal(
    posts: List[Dict[str, Any]],
    tight_window_sec: float = 60.0,
    max_burst_window_sec: float = 180.0,
) -> List[Dict[str, Any]]:
    timed = [
        {**p, "_ts": _parse_ts(p.get("created_at") or p.get("createdAt", ""))}
        for p in posts
    ]
    timed = [p for p in timed if p["_ts"] > 0]
    timed.sort(key=lambda x: x["_ts"])
    if len(timed) < 2:
        return []

    # Per-account cadence regularity check
    by_did: Dict[str, List[float]] = {}
    for p in timed:
        by_did.setdefault(p["did"], []).append(p["_ts"])

    cadence_bonus_by_did: Dict[str, float] = {}
    for did, times in by_did.items():
        if len(times) < 3:
            continue
        gaps = [times[i] - times[i - 1] for i in range(1, len(times)) if times[i] > times[i - 1]]
        if len(gaps) >= 2:
            mean = sum(gaps) / len(gaps)
            variance = sum((g - mean) ** 2 for g in gaps) / len(gaps)
            cv = math.sqrt(variance) / (mean or 1.0)
            if cv < 0.2:
                cadence_bonus_by_did[did] = min(0.25, (0.2 - cv) * 1.25)

    pair_bursts: Dict[Tuple[str, str], Dict[str, Any]] = {}
    for i in range(len(timed)):
        p_a = timed[i]
        for j in range(i + 1, len(timed)):
            p_b = timed[j]
            delta = abs(p_b["_ts"] - p_a["_ts"])
            if delta > max_burst_window_sec:
                break
            if p_a["did"] == p_b["did"]:
                continue

            key = _pair_key(p_a["did"], p_b["did"])
            existing = pair_bursts.get(key)
            if existing:
                existing["min_delta"] = min(existing["min_delta"], delta)
                existing["count"] += 1
            else:
                pair_bursts[key] = {
                    "did_a": key[0],
                    "did_b": key[1],
                    "min_delta": delta,
                    "count": 1,
                }

    results: List[Dict[str, Any]] = []
    for entry in pair_bursts.values():
        min_d = entry["min_delta"]
        if min_d <= tight_window_sec:
            base = 1.0 - 0.35 * (min_d / tight_window_sec)
        else:
            ratio = (min_d - tight_window_sec) / (max_burst_window_sec - tight_window_sec)
            base = 0.65 - 0.45 * ratio

        repeat_bonus = min(0.18, (entry["count"] - 1) * 0.08)
        cadence_bonus = (
            cadence_bonus_by_did.get(entry["did_a"], 0.0)
            + cadence_bonus_by_did.get(entry["did_b"], 0.0)
        ) / 2.0
        strength = round(min(1.0, base + repeat_bonus + cadence_bonus), 4)
        if strength < 0.25:
            continue

        results.append(
            {
                "did_a": entry["did_a"],
                "did_b": entry["did_b"],
                "strength": strength,
                "reason": f"Synchronized posting within {int(round(min_d))}s ({entry['count']} co-timed event)",
                "signal_type": "timing",
            }
        )

    results.sort(key=lambda r: r["strength"], reverse=True)
    return results
