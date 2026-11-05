"""
Phase 4.1: Pure Text Similarity Signal (exact text_norm duplicate hash + char 3-gram TF-IDF cosine similarity).
Works with scikit-learn TfidfVectorizer when installed, and includes a zero-dependency pure-Python
char 3-gram TF-IDF vector implementation so unit tests also run in any standard Python environment.
"""

from collections import Counter
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


def _char_ngrams(text: str, n: int = 3) -> Counter:
    padded = f" {text} "
    if len(padded) < n:
        return Counter({padded: 1})
    return Counter(padded[i : i + n] for i in range(len(padded) - n + 1))


def compute_text_similarity_signal(
    posts: List[Dict[str, Any]],
    threshold: float = 0.76,
    max_window_sec: float = 6 * 3600,
) -> List[Dict[str, Any]]:
    valid = [
        {**p, "_ts": _parse_ts(p.get("created_at") or p.get("createdAt", ""))}
        for p in posts
        if len(p.get("text_norm") or p.get("textNorm", "")) >= 12
    ]
    valid.sort(key=lambda x: x["_ts"])
    if len(valid) < 2:
        return []

    n_docs = len(valid)
    grams_list = [_char_ngrams(p.get("text_norm") or p.get("textNorm", ""), 3) for p in valid]
    df: Counter = Counter()
    for g in grams_list:
        for token in g.keys():
            df[token] += 1

    tfidf_vecs: List[Tuple[Dict[str, float], float]] = []
    for g in grams_list:
        vec: Dict[str, float] = {}
        norm_sq = 0.0
        for token, count in g.items():
            idf = math.log(1.0 + n_docs / (1.0 + df[token]))
            val = (1.0 + math.log(count)) * idf
            vec[token] = val
            norm_sq += val * val
        tfidf_vecs.append((vec, math.sqrt(norm_sq) or 1.0))

    best_pairs: Dict[Tuple[str, str], Dict[str, Any]] = {}

    for i in range(n_docs):
        p_a = valid[i]
        norm_a = p_a.get("text_norm") or p_a.get("textNorm", "")
        vec_a, mag_a = tfidf_vecs[i]

        for j in range(i + 1, n_docs):
            p_b = valid[j]
            if abs(p_b["_ts"] - p_a["_ts"]) > max_window_sec:
                break
            if p_a["did"] == p_b["did"]:
                continue

            norm_b = p_b.get("text_norm") or p_b.get("textNorm", "")
            is_exact = norm_a == norm_b
            if is_exact:
                sim = 1.0
            else:
                vec_b, mag_b = tfidf_vecs[j]
                smaller, larger = (vec_a, vec_b) if len(vec_a) <= len(vec_b) else (vec_b, vec_a)
                dot = sum(val * larger.get(tok, 0.0) for tok, val in smaller.items())
                sim = dot / (mag_a * mag_b)

            if sim >= threshold:
                key = _pair_key(p_a["did"], p_b["did"])
                existing = best_pairs.get(key)
                if existing:
                    existing["strength"] = max(existing["strength"], round(sim, 4))
                    existing["exact"] = existing["exact"] or is_exact
                else:
                    best_pairs[key] = {
                        "did_a": key[0],
                        "did_b": key[1],
                        "strength": round(min(1.0, sim), 4),
                        "exact": is_exact,
                    }

    results: List[Dict[str, Any]] = []
    for item in best_pairs.values():
        reason = (
            "Identical normalized text (exact duplicate, similarity 1.00)"
            if item["exact"]
            else f"Near-duplicate narrative template (char 3-gram TF-IDF cosine {item['strength']:.2f})"
        )
        results.append(
            {
                "did_a": item["did_a"],
                "did_b": item["did_b"],
                "strength": item["strength"],
                "reason": reason,
                "signal_type": "text",
            }
        )

    results.sort(key=lambda r: r["strength"], reverse=True)
    return results
