"""
Phase 5.3, 5.4, 5.5 & Detector Redesign (D1, D4):
Evidence-Based Benign Explanations, Calibrated Scoring, and 3-Class Taxonomy:
- coordinated_inauthentic: Astroturfed campaigns, sockpuppet rings, sleeper botnets.
- coordinated_benign: Open petition templates, breaking news sharing, community hashtags.
- organic: Independent authentic chatter.

Key Improvement (D1):
Eliminates the "old account = innocent" flaw where aged botnets got discounted to recall 0.
Discounts are ONLY applied when specific benign evidence is validated (e.g. share-button match,
authoritative domain, or open community hashtag).
"""

from typing import Any, Dict, List, Optional
from ..config import settings
from ..textutil import AUTHORITATIVE_DOMAINS, host_in_set, host_of


def compute_cluster_score_and_reasons(
    cluster_dids: List[str],
    signal_averages: Dict[str, float],
    cohort_48h_count: int,
    median_age_days: float,
    enable_fp_protection: bool = True,
    cluster_posts: Optional[List[Dict[str, Any]]] = None,
    empirical_p_value: Optional[float] = None,
) -> Dict[str, Any]:
    """
    Computes calibrated cluster score, 3-class classification, benign explanations,
    and plain-English evidence chain.
    """
    t_sig = signal_averages.get("text", 0.0)
    s_sig = signal_averages.get("timing", 0.0)
    a_sig = signal_averages.get("age", 0.0)
    l_sig = signal_averages.get("links", 0.0)

    # Base weighted multi-signal score (0-100)
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

    # Evaluate Specific Benign Explanations (D1)
    benign_checks = {
        "share_button_match": False,
        "authoritative_news_source": False,
        "open_community_hashtag": False,
        "diverse_lexical_chatter": False,
    }

    cohort_ratio = cohort_48h_count / max(1, len(cluster_dids))
    is_aged_cohort = median_age_days > 120 and cohort_ratio < 0.35

    matched_domains = set()
    if cluster_posts:
        for p in cluster_posts:
            for lk in p.get("links") or []:
                if host_in_set(lk, AUTHORITATIVE_DOMAINS):
                    host = host_of(lk)
                    for domain in AUTHORITATIVE_DOMAINS:
                        if host == domain or host.endswith("." + domain):
                            matched_domains.add(domain)
                            break

    has_authoritative_link = bool(matched_domains)

    # Identical headlines are the common benign case. Decide that before the
    # hard-coordination short circuit, which used to swallow every share-button burst.
    # Limit: an aged network that copies an allowlisted headline is classified as news sharing.
    news_burst = bool(
        enable_fp_protection
        and has_authoritative_link
        and is_aged_cohort
        and t_sig >= 0.30
    )

    discount = 0.0
    discount_reason = None
    classification = "coordinated_inauthentic"
    is_hard_coordinated = (t_sig >= 0.48 and s_sig >= 0.40) or (t_sig >= 0.65)

    if news_burst:
        benign_checks["authoritative_news_source"] = True
        benign_checks["share_button_match"] = True
        discount = 0.45
        classification = "coordinated_benign"
        shown = ", ".join(sorted(matched_domains)[:2]) or "press"
        discount_reason = (
            f"Benign News-Burst Discount (-45%): Verified authoritative domain ({shown}) "
            f"shared by established accounts whose creation dates are spread out."
        )
    elif is_hard_coordinated:
        discount = 0.0
        classification = "coordinated_inauthentic"
    elif enable_fp_protection:
        if is_aged_cohort and (has_authoritative_link or (not cluster_posts and l_sig >= 0.45 and t_sig <= 0.40)):
            benign_checks["authoritative_news_source"] = True
            benign_checks["share_button_match"] = True
        if l_sig >= 0.30 and t_sig < 0.25:
            benign_checks["open_community_hashtag"] = True
        if s_sig >= 0.35 and t_sig < 0.20 and l_sig < 0.20:
            benign_checks["diverse_lexical_chatter"] = True
        if benign_checks["share_button_match"] or benign_checks["authoritative_news_source"]:
            discount = 0.45
            classification = "coordinated_benign"
            shown = ", ".join(sorted(matched_domains)[:2]) or "press"
            discount_reason = (
                f"Benign News-Burst Discount (-45%): Verified authoritative domain ({shown}) "
                f"shared by established accounts whose creation dates are spread out."
            )
        elif benign_checks["open_community_hashtag"]:
            discount = 0.35
            classification = "coordinated_benign"
            discount_reason = (
                "Benign Community Movement (-35%): Open hashtag campaign with high personal lexical diversity."
            )
        elif benign_checks["diverse_lexical_chatter"]:
            discount = 0.40
            classification = "organic"
            discount_reason = (
                "Benign Event Burst (-40%): Live reaction timing with authentic diverse personal phrasing."
            )

    final_score = max(5, round(raw_score * (1.0 - discount)))

    # Determine 3-class label
    if classification == "coordinated_inauthentic":
        if final_score < 45:
            classification = "organic"
    elif classification == "coordinated_benign":
        if final_score < 30:
            classification = "organic"

    reasons: List[str] = [
        f"{len(cluster_dids)} accounts in cluster; {cohort_48h_count} created within 48 hours",
        f"Multi-signal profile: text={t_sig:.2f}, timing={s_sig:.2f}, age={a_sig:.2f}, links={l_sig:.2f}",
    ]

    # Explainable dormancy gap detection for aged sockpuppets
    if is_aged_cohort and is_hard_coordinated:
        reasons.append(
            f"Aged accounts (median {int(median_age_days)}d old) with synchronized copypasta "
            f"indicates dormant sleeper account ring or purchased aged profile pool."
        )

    if discount_reason:
        reasons.append(discount_reason)

    if empirical_p_value is not None:
        if empirical_p_value < 0.01:
            reasons.append(f"Statistically significant under permutation null-model (p = {empirical_p_value:.4f})")
        else:
            reasons.append(f"Permutation null-model p-value = {empirical_p_value:.4f}")

    return {
        "score": final_score,
        "raw_score": raw_score,
        "discount_applied": discount,
        "discount_reason": discount_reason,
        "classification": classification,
        "benign_checks": benign_checks,
        "reasons": reasons,
    }
