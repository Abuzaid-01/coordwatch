"""Phase 5: Graph Engine, Community Detection, Cluster Scoring, False-Positive Discount & Timeline."""
from datetime import datetime, timezone
import json
import math
from typing import Any, Dict, List, Optional, Set, Tuple

from ..config import settings
from ..signals.text import compute_text_similarity_signal
from ..signals.timing import compute_timing_sync_signal
from ..signals.age import compute_account_age_signal
from ..signals.links import compute_shared_links_signal
from .graph import build_and_partition_graph
from .scoring import compute_cluster_score_and_reasons
from .significance import apply_detection_decisions, compute_cluster_significance


def _pair_key(d1: str, d2: str) -> Tuple[str, str, str]:
    if d1 < d2:
        return d1, d2, f"{d1}|{d2}"
    return d2, d1, f"{d2}|{d1}"


def run_topic_analysis(
    topic_id: int,
    posts: List[Dict[str, Any]],
    accounts: List[Dict[str, Any]],
    min_edge_weight: float = settings.min_edge_weight,
    min_cluster_size: int = settings.min_cluster_size,
    enable_fp_protection: bool = True,
    max_graph_nodes: int = settings.max_graph_nodes,
    n_permutations: int = 50,
) -> Dict[str, Any]:
    """
    Executes full multi-signal detection, Louvain clustering, scoring,
    and returns clusters, graph data (nodes + links), and timeline buckets.
    """
    # 1. Account and Post Lookups
    acc_map: Dict[str, Dict[str, Any]] = {a["did"]: a for a in accounts}
    post_counts_by_did: Dict[str, int] = {}
    posts_by_did: Dict[str, List[Dict[str, Any]]] = {}

    for p in posts:
        did = p["did"]
        post_counts_by_did[did] = post_counts_by_did.get(did, 0) + 1
        posts_by_did.setdefault(did, []).append(p)
        if did not in acc_map:
            acc_map[did] = {
                "did": did,
                "handle": p.get("author_handle") or f"{did[-8:]}.bsky.social",
                "alias": p.get("author_alias") or f"A-{did[-6:].upper()}",
                "created_at": p.get("author_created_at"),
                "first_seen": p.get("created_at"),
                "enriched": bool(p.get("author_created_at")),
            }

    all_accounts = list(acc_map.values())

    # 2. Compute 4 Pure Detection Signals
    text_pairs = compute_text_similarity_signal(posts, threshold=settings.text_similarity_threshold)
    timing_pairs = compute_timing_sync_signal(posts, tight_window_sec=settings.tight_burst_seconds)
    age_pairs = compute_account_age_signal(all_accounts, max_gap_hours=settings.max_creation_cohort_hours)
    link_pairs = compute_shared_links_signal(posts)

    # 3. Combine Pair Signals
    pair_signals: Dict[str, Dict[str, Any]] = {}

    def upsert_signal(d1: str, d2: str, sig_type: str, strength: float, reason: str):
        da, db, key = _pair_key(d1, d2)
        if key not in pair_signals:
            pair_signals[key] = {
                "did_a": da,
                "did_b": db,
                "signals": {"text": 0.0, "timing": 0.0, "age": 0.0, "links": 0.0},
                "reasons": {},
                "weight": 0.0,
            }
        rec = pair_signals[key]
        if strength > rec["signals"][sig_type]:
            rec["signals"][sig_type] = strength
            rec["reasons"][sig_type] = reason

    for p in text_pairs:
        upsert_signal(p["did_a"], p["did_b"], "text", p["strength"], p.get("reason", "Text copypasta/template similarity"))
    for p in timing_pairs:
        upsert_signal(p["did_a"], p["did_b"], "timing", p["strength"], p.get("reason", "Synchronized timing"))
    for p in age_pairs:
        upsert_signal(p["did_a"], p["did_b"], "age", p["strength"], p.get("reason", "Batch creation cohort"))
    for p in link_pairs:
        upsert_signal(p["did_a"], p["did_b"], "links", p["strength"], p.get("reason", "Shared URL or hashtag campaign"))

    active_edges: List[Dict[str, Any]] = []
    for edge in pair_signals.values():
        sigs = edge["signals"]
        t, s, a, l = sigs["text"], sigs["timing"], sigs["age"], sigs["links"]

        # Content or sync-cohort anchor check
        has_content_anchor = t >= 0.45 or l >= 0.40
        has_sync_anchor = s >= 0.70 and a >= 0.65 and (t >= 0.25 or l >= 0.25)
        if not has_content_anchor and not has_sync_anchor:
            continue

        base_w = settings.weight_text * t + settings.weight_timing * s + settings.weight_age * a + settings.weight_links * l
        active_count = sum(1 for v in (t, s, a, l) if v >= 0.45)
        synergy = 1.25 if active_count >= 3 else 1.12 if active_count == 2 else 1.0
        final_w = round(min(1.0, base_w * synergy), 4)

        if final_w >= min_edge_weight:
            edge["weight"] = final_w
            active_edges.append(edge)

    # 4. Louvain Community Detection
    all_dids = list(post_counts_by_did.keys())
    communities = build_and_partition_graph(all_dids, active_edges, min_cluster_size=min_cluster_size)

    clusters: List[Dict[str, Any]] = []
    node_cluster_map: Dict[str, Dict[str, Any]] = {}
    cluster_seq = 1

    for comm_dids in communities:
        comm_set = set(comm_dids)
        internal_edges = [
            e for e in active_edges if e["did_a"] in comm_set and e["did_b"] in comm_set
        ]
        if not internal_edges:
            continue

        # C3 FIX: Average over all internal edges (honest un-inflated signal measure)
        def avg_signal(sig_name: str) -> float:
            vals = [e["signals"].get(sig_name, 0.0) for e in internal_edges]
            if not vals:
                return 0.0
            return round(sum(vals) / len(vals), 3)

        text_sig = avg_signal("text")
        timing_sig = avg_signal("timing")
        age_sig = avg_signal("age")
        links_sig = avg_signal("links")
        sig_breakdown = {"text": text_sig, "timing": timing_sig, "age": age_sig, "links": links_sig}

        cluster_posts = [p for p in posts if p["did"] in comm_set]
        cluster_posts.sort(key=lambda x: x.get("created_at", ""))

        cluster_accs = [acc_map[d] for d in comm_dids if d in acc_map]
        created_timestamps = []
        for acc in cluster_accs:
            iso = acc.get("created_at")
            if iso:
                try:
                    ts = datetime.fromisoformat(iso.replace("Z", "+00:00")).timestamp()
                    created_timestamps.append(ts)
                except Exception:
                    pass

        created_timestamps.sort()
        # Find largest 48h cohort
        max_cohort_48h = 0
        gap_sec = 48 * 3600.0
        for i in range(len(created_timestamps)):
            c = sum(1 for j in range(i, len(created_timestamps)) if created_timestamps[j] - created_timestamps[i] <= gap_sec)
            if c > max_cohort_48h:
                max_cohort_48h = c

        now_ts = datetime.now(timezone.utc).timestamp()
        if cluster_posts:
            try:
                now_ts = datetime.fromisoformat(cluster_posts[-1]["created_at"].replace("Z", "+00:00")).timestamp()
            except Exception:
                pass

        age_days_list = [max(0.0, (now_ts - ts) / 86400.0) for ts in created_timestamps]
        median_age_days = age_days_list[len(age_days_list) // 2] if age_days_list else 30.0

        # Score first so the permutation test receives THIS cluster's raw score.
        scored = compute_cluster_score_and_reasons(
            comm_dids,
            sig_breakdown,
            cohort_48h_count=max_cohort_48h,
            median_age_days=median_age_days,
            enable_fp_protection=enable_fp_protection,
            cluster_posts=cluster_posts,
            empirical_p_value=None,
        )
        raw_score = scored["raw_score"]
        sig_result = compute_cluster_significance(
            cluster_dids=comm_dids,
            cluster_score=raw_score,
            all_topic_posts=posts,
            n_permutations=n_permutations,
            seed=42 + cluster_seq,
        )

        final_score = scored["score"]
        discount_applied = scored["discount_applied"]
        reasons = list(scored["reasons"])
        p_value = sig_result.get("p_value")
        if sig_result.get("status") == "tested" and p_value is not None:
            if p_value < 0.01:
                reasons.append(
                    f"Statistically significant under permutation null-model "
                    f"(p = {p_value:.4f}, {sig_result.get('n_permutations', n_permutations)} permutations)"
                )
            else:
                reasons.append(
                    f"Permutation null-model p-value = {p_value:.4f} "
                    f"({sig_result.get('n_permutations', n_permutations)} permutations)"
                )
        else:
            reasons.append("Permutation test not run for this cluster.")

        # Detailed Evidence Reasons
        if text_sig >= 0.40:
            reasons.append(f"Median text similarity {text_sig:.2f} across cluster account pairs (copypasta/template phrasing)")
        if timing_sig >= 0.35:
            reasons.append(f"Synchronized co-posting bursts within 60s of peer accounts (timing score {timing_sig:.2f})")
        if links_sig >= 0.30:
            all_links = [l for p in cluster_posts for l in (p.get("links") or [])]
            top_link = all_links[0] if all_links else "external campaign URL"
            reasons.append(f"Coordinated amplification of target URL: {top_link[:44]}")

        cluster_id = f"CL-{cluster_seq:02d}"
        cluster_seq += 1

        # Node level scores
        members = []
        for did in comm_dids:
            a = acc_map.get(did, {})
            # Degree centrality in cluster
            deg = sum(1 for e in internal_edges if e["did_a"] == did or e["did_b"] == did)
            max_deg = max(1, len(comm_dids) - 1)
            deg_centrality = deg / max_deg
            node_score = max(10, min(100, round(final_score * 0.70 + deg_centrality * 30)))
            member_obj = {
                "did": did,
                "handle": a.get("handle") or f"{did[-8:]}.bsky.social",
                "alias": a.get("alias") or f"A-{did[-6:].upper()}",
                "createdAt": a.get("created_at"),
                "postCount": post_counts_by_did.get(did, 0),
                "nodeScore": node_score,
            }
            members.append(member_obj)
            node_cluster_map[did] = {
                "cluster_id": cluster_id,
                "score": final_score,
                "alias": member_obj["alias"],
            }

        members.sort(key=lambda m: m["nodeScore"], reverse=True)

        # Example posts (top 3)
        example_posts = [
            {
                "id": p["id"],
                "did": p["did"],
                "alias": acc_map.get(p["did"], {}).get("alias") or f"A-{p['did'][-6:].upper()}",
                "text": p["text"],
                "createdAt": p["created_at"],
            }
            for p in cluster_posts[:3]
        ]

        clusters.append({
            "id": cluster_id,
            "topicId": topic_id,
            "score": final_score,
            "rawScore": raw_score,
            "discountApplied": discount_applied,
            "discountReason": scored.get("discount_reason"),
            "classification": scored.get("classification", "coordinated_inauthentic"),
            "benignChecks": scored.get("benign_checks", {}),
            "significance": sig_result,
            "size": len(comm_dids),
            "memberDids": comm_dids,
            "members": members,
            "signals": sig_breakdown,
            "reasons": reasons,
            "examplePosts": example_posts,
            "computedAt": datetime.now(timezone.utc).isoformat(),
        })

    clusters = apply_detection_decisions(clusters)
    clusters.sort(key=lambda c: (c["score"], c["size"]), reverse=True)

    # 5. Graph Assembly (Nodes + Links with capping)
    active_dids = set(node_cluster_map.keys())
    for e in active_edges:
        active_dids.add(e["did_a"])
        active_dids.add(e["did_b"])

    # If exceeding max_graph_nodes, prioritize clustered and high-degree accounts
    selected_dids = list(active_dids)
    if len(selected_dids) > max_graph_nodes:
        def node_priority(d: str) -> Tuple[int, int]:
            in_cluster = 1 if d in node_cluster_map else 0
            score = node_cluster_map.get(d, {}).get("score", 0)
            return (in_cluster, score)

        selected_dids.sort(key=node_priority, reverse=True)
        selected_dids = selected_dids[:max_graph_nodes]

    sel_set = set(selected_dids)
    graph_nodes = []
    for did in selected_dids:
        cl_info = node_cluster_map.get(did)
        acc = acc_map.get(did, {})
        alias = cl_info["alias"] if cl_info else (acc.get("alias") or f"A-{did[-6:].upper()}")
        handle = acc.get("handle") or f"{did[-8:]}.bsky.social"
        cluster_id = cl_info["cluster_id"] if cl_info else None
        graph_nodes.append({
            "id": did,
            "alias": alias,
            "label": alias,
            "handle": handle,
            "clusterId": cluster_id,
            "cluster": cluster_id or "unassigned",
            "score": cl_info["score"] if cl_info else 0,
            "postCount": post_counts_by_did.get(did, 0),
        })

    graph_links = []
    for e in active_edges:
        if e["did_a"] in sel_set and e["did_b"] in sel_set:
            graph_links.append({
                "source": e["did_a"],
                "target": e["did_b"],
                "weight": e["weight"],
                "signals": [k for k, v in e["signals"].items() if v >= 0.20],
            })

    # 6. Timeline Histogram Generation (15-min or hourly buckets)
    timeline_buckets = _build_timeline(posts, clusters)

    return {
        "clusters": clusters,
        "graph": {"nodes": graph_nodes, "links": graph_links},
        "timeline": timeline_buckets,
    }


def _build_timeline(posts: List[Dict[str, Any]], clusters: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    if not posts:
        return []

    clustered_dids = {did for c in clusters for did in c["memberDids"]}

    # Sort posts by timestamp
    valid_posts = []
    for p in posts:
        iso = p.get("created_at") or p.get("createdAt")
        if iso:
            try:
                ts = datetime.fromisoformat(iso.replace("Z", "+00:00")).timestamp()
                valid_posts.append((ts, p["did"]))
            except Exception:
                pass

    if not valid_posts:
        return []

    valid_posts.sort(key=lambda x: x[0])
    min_ts = valid_posts[0][0]
    max_ts = valid_posts[-1][0]
    span = max_ts - min_ts

    num_buckets = 12 if span <= 3600 else 24
    bucket_sec = max(60.0, span / num_buckets)

    buckets: List[Dict[str, Any]] = []
    for b in range(num_buckets):
        b_start = min_ts + b * bucket_sec
        b_end = b_start + bucket_sec
        total_p = 0
        coord_p = 0
        for ts, did in valid_posts:
            if b_start <= ts < b_end or (b == num_buckets - 1 and ts <= b_end):
                total_p += 1
                if did in clustered_dids:
                    coord_p += 1

        dt = datetime.fromtimestamp(b_start, tz=timezone.utc)
        buckets.append({
            "bucketIndex": b,
            "startTime": dt.isoformat(),
            "label": dt.strftime("%H:%M"),
            "totalPosts": total_p,
            "coordinatedPosts": coord_p,
            "organicPosts": max(0, total_p - coord_p),
            # Keys matching frontend expectations
            "total": total_p,
            "flagged": coord_p,
        })

    return buckets
