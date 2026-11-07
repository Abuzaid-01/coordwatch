"""
Phase 4.1: Text Similarity Signal (exact text_norm duplicate hash + char 3-gram TF-IDF cosine similarity).
D3: Uses scikit-learn TfidfVectorizer and sparse matrix multiplication for fast O(N) vectorized comparison,
with fallback to zero-dependency pure-Python char 3-gram TF-IDF vector implementation.
"""

from collections import Counter
from datetime import datetime
import math
from typing import Any, Dict, List, Tuple

try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    import scipy.sparse as sp
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False


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
    best_pairs: Dict[Tuple[str, str], Dict[str, Any]] = {}

    if SKLEARN_AVAILABLE:
        texts = [p.get("text_norm") or p.get("textNorm", "") for p in valid]
        origin = valid[0]["_ts"]
        buckets: Dict[int, List[int]] = {}
        for idx, post in enumerate(valid):
            bucket = int(max(0.0, post["_ts"] - origin) // max_window_sec)
            buckets.setdefault(bucket, []).append(idx)

        def record_pair(i: int, j: int, sim_val: float) -> None:
            p_a = valid[i]
            p_b = valid[j]
            if abs(p_b["_ts"] - p_a["_ts"]) > max_window_sec:
                return
            if p_a["did"] == p_b["did"]:
                return
            is_exact = texts[i] == texts[j]
            sim = 1.0 if is_exact else float(sim_val)
            if sim < threshold:
                return
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

        # Fit TF-IDF inside each 6-hour bucket and the next bucket.
        # Pairs more than one bucket apart are outside the window.
        for bucket, idxs in buckets.items():
            idx_set = set(idxs)
            neighbor = idxs + buckets.get(bucket + 1, [])
            if len(neighbor) < 2:
                continue
            sub_texts = [texts[i] for i in neighbor]
            vec = TfidfVectorizer(analyzer="char", ngram_range=(3, 3), min_df=1)
            tfidf_mat = vec.fit_transform(sub_texts)
            sim_mat = tfidf_mat.dot(tfidf_mat.T)
            for local_i, global_i in enumerate(neighbor):
                if global_i not in idx_set:
                    continue
                row = sim_mat.getrow(local_i)
                for local_j, sim_val in zip(row.indices, row.data):
                    if local_j <= local_i:
                        continue
                    record_pair(global_i, neighbor[local_j], float(sim_val))
    else:
        # Fallback pure-Python char 3-gram TF-IDF implementation
        grams_list = [_char_ngrams(p.get("text_norm") or p.get("textNorm", ""), 3) for p in valid]
        df: Counter = Counter()
        for g in grams_list:
            for token in g.keys():
                df[token] += 1

        tfidf_vecs: List[Tuple[Dict[str, float], float]] = []
        for g in grams_list:
            v_dict: Dict[str, float] = {}
            norm_sq = 0.0
            for token, count in g.items():
                idf = math.log(1.0 + n_docs / (1.0 + df[token]))
                val = (1.0 + math.log(count)) * idf
                v_dict[token] = val
                norm_sq += val * val
            tfidf_vecs.append((v_dict, math.sqrt(norm_sq) or 1.0))

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
