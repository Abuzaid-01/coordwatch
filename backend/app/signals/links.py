"""
Phase 4.4: Shared Links & Hashtags Signal in Python with Rarity Weighting and Inverted Index (C2).
"""

import math
from typing import Any, Dict, List, Set, Tuple

# C2: Allowlist of high-traffic organic news/official domains that count for little
POPULAR_DOMAINS_ALLOWLIST = {
    "bbc.co.uk",
    "bbc.com",
    "tfl.gov.uk",
    "theguardian.com",
    "reuters.com",
    "gov.uk",
    "wikipedia.org",
    "youtube.com",
    "youtu.be",
    "nytimes.com",
    "ft.com",
    "sky.com",
    "bsky.app",
    "x.com",
    "twitter.com",
}


def _pair_key(did1: str, did2: str) -> Tuple[str, str]:
    return (did1, did2) if did1 < did2 else (did2, did1)


def _get_domain(url: str) -> str:
    cleaned = url.lower().split("://")[-1].split("/")[0]
    if cleaned.startswith("www."):
        cleaned = cleaned[4:]
    return cleaned


def compute_shared_links_signal(posts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    C2: Uses an inverted index (link -> set of accounts) and rarity weighting.
    Viral/common news links shared by hundreds of accounts receive discounted weights.
    """
    links_by_did: Dict[str, Set[str]] = {}
    tags_by_did: Dict[str, Set[str]] = {}

    dids_by_link: Dict[str, Set[str]] = {}
    dids_by_tag: Dict[str, Set[str]] = {}

    for p in posts:
        did = p["did"]
        for link in p.get("links") or []:
            l_clean = link.lower()
            links_by_did.setdefault(did, set()).add(l_clean)
            dids_by_link.setdefault(l_clean, set()).add(did)

        for tag in p.get("hashtags") or []:
            t_clean = tag.lower()
            tags_by_did.setdefault(did, set()).add(t_clean)
            dids_by_tag.setdefault(t_clean, set()).add(did)

    candidate_pairs: Set[Tuple[str, str]] = set()

    # Inverted index: only evaluate pairs that actually share at least one link or tag
    for link, accounts in dids_by_link.items():
        # If a single link is shared by too many accounts (>80) and domain is in allowlist, downweight
        acc_list = sorted(accounts)
        for i in range(len(acc_list)):
            for j in range(i + 1, len(acc_list)):
                candidate_pairs.add((acc_list[i], acc_list[j]))

    for tag, accounts in dids_by_tag.items():
        acc_list = sorted(accounts)
        for i in range(len(acc_list)):
            for j in range(i + 1, len(acc_list)):
                candidate_pairs.add((acc_list[i], acc_list[j]))

    results: List[Dict[str, Any]] = []

    for d1, d2 in candidate_pairs:
        l_a = links_by_did.get(d1, set())
        l_b = links_by_did.get(d2, set())
        t_a = tags_by_did.get(d1, set())
        t_b = tags_by_did.get(d2, set())

        shared_links = sorted(l_a & l_b)
        shared_tags = sorted(t_a & t_b)

        if not shared_links and not shared_tags:
            continue

        # Rarity weighting for shared links
        link_score = 0.0
        if shared_links:
            union_l = len(l_a | l_b) or 1
            jaccard = len(shared_links) / union_l

            rarity_multiplier = 1.0
            for lk in shared_links:
                domain = _get_domain(lk)
                sharing_count = len(dids_by_link.get(lk, set()))
                # Rarity weight formula: 1 / log2(2 + count)
                r_factor = 1.0 / math.log2(2.0 + sharing_count)
                if domain in POPULAR_DOMAINS_ALLOWLIST:
                    r_factor *= 0.35  # High-traffic domain discount
                rarity_multiplier = max(0.15, min(1.0, rarity_multiplier * (1.2 * r_factor)))

            link_score = min(1.0, (0.72 + 0.28 * jaccard) * rarity_multiplier)

        # Tag score
        tag_score = 0.0
        if shared_tags:
            union_t = len(t_a | t_b) or 1
            jaccard_t = len(shared_tags) / union_t
            tag_score = (
                min(0.95, 0.60 + 0.35 * jaccard_t)
                if len(shared_tags) >= 2
                else min(0.55, 0.35 + 0.20 * jaccard_t)
            )

        strength = round(min(1.0, max(link_score, tag_score, link_score * 0.75 + tag_score * 0.45)), 4)
        if strength < 0.3:
            continue

        key = _pair_key(d1, d2)
        parts = []
        if shared_links:
            parts.append(f"shared URL ({shared_links[0]})")
        if shared_tags:
            parts.append(f"shared hashtags ({', '.join(shared_tags[:3])})")

        results.append(
            {
                "did_a": key[0],
                "did_b": key[1],
                "strength": strength,
                "reason": f"Coordinated amplification of {' and '.join(parts)}",
                "signal_type": "links",
            }
        )

    results.sort(key=lambda r: r["strength"], reverse=True)
    return results
