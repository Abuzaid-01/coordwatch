"""
Phase 8: Ground-Truth Evaluation Benchmark, Real Evasion Sweeps & Real FP Stress Test.
All benchmarks are physically executed with run_topic_analysis (B1, B2).
No hardcoded formula curves or fake stress counts.
"""

from datetime import datetime, timezone
import math
import random
from typing import Any, Dict, List, Set, Tuple

from ..analysis.engine import run_topic_analysis
from ..textutil import apply_prepare


def run_full_evaluation_suite(organic_count: int = 500, seed: int = 42) -> Dict[str, Any]:
    """Lab-sized sample of the same benchmark the published runner uses.

    Two dev seeds and two test seeds, 80 organic accounts, 50 permutations.
    The published 10-seed run is `python -m backend.app.sim.run_eval`.
    """
    from .benchmark_v2 import run_benchmark_v2_suite

    count = min(80, max(40, organic_count))
    return run_benchmark_v2_suite(
        seeds=[seed, seed + 1],
        test_seeds=[seed + 100, seed + 101],
        organic_count=count,
        n_permutations=50,
        evasion_seeds=[seed],
        label="lab sample",
    )


def _evaluate_scenario(sim: Dict[str, Any]) -> Dict[str, Any]:
    analysis = run_topic_analysis(
        topic_id=999,
        posts=sim["posts"],
        accounts=sim["accounts"],
        min_edge_weight=0.18,
        min_cluster_size=3,
        enable_fp_protection=True,
    )

    detected_bot_dids = set()
    for c in analysis["clusters"]:
        if c["score"] >= 50 and c.get("classification") == "coordinated_inauthentic":
            detected_bot_dids.update(c["memberDids"])

    tp, fp, fn, tn = 0, 0, 0, 0
    gt_bots = sim["ground_truth_bot_dids"]

    for acc in sim["accounts"]:
        did = acc["did"]
        is_bot = did in gt_bots
        is_det = did in detected_bot_dids
        if is_bot and is_det:
            tp += 1
        elif not is_bot and is_det:
            fp += 1
        elif is_bot and not is_det:
            fn += 1
        else:
            tn += 1

    precision = round(tp / max(1, tp + fp), 3)
    recall = round(tp / max(1, tp + fn), 3)
    f1 = round((2 * precision * recall) / max(1e-9, precision + recall), 3)

    return {
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "tn": tn,
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "detected_bot_dids": detected_bot_dids,
        "analysis": analysis,
    }


def _run_real_fp_stress_test(seed: int = 42) -> Dict[str, Any]:
    """
    B2: Generates 65 established accounts (ages 100-900 days) who all share
    the exact same headline and official link within 4 minutes.
    Runs analysis with enable_fp_protection=False and True, measuring real counts.
    """
    rng = random.Random(seed)
    base_ts = datetime(2026, 11, 4, 15, 0, 0, tzinfo=timezone.utc).timestamp()
    headline = "BREAKING: Transport for London confirms new Outer Orbital Express bus loops opening across 14 boroughs https://tfl.gov.uk/news #LondonTransport"
    link = "https://tfl.gov.uk/news"

    fp_accounts = []
    fp_posts = []

    # Background chatter spread across the day. Without it, every timestamp
    # belongs to the burst and a permutation test cannot call the burst unusual.
    for i in range(120):
        did = f"did:plc:fp_bg_{i:03d}"
        age_days = 80 + rng.randint(0, 900)
        c_ts = datetime.fromtimestamp(base_ts - age_days * 86400, tz=timezone.utc).isoformat()
        fp_accounts.append({
            "did": did,
            "handle": f"resident-{i}.bsky.social",
            "alias": f"A-BG{i:03d}",
            "created_at": c_ts,
            "first_seen": c_ts,
            "enriched": True,
        })
        p_ts = datetime.fromtimestamp(base_ts + rng.uniform(0, 20 * 3600), tz=timezone.utc).isoformat()
        text = f"Ordinary note {i} about the bus timetable and the weather on the high street."
        fp_posts.append({
            "id": f"fp-bg-{i}",
            "did": did,
            "text": text,
            "text_norm": text.lower(),
            "created_at": p_ts,
            "topic_id": 888,
            "links": [],
            "hashtags": [],
        })

    for i in range(65):
        did = f"did:plc:fp_user_{i:03d}"
        # Established accounts: 100 to 900 days old with dispersed creation dates
        age_days = 120 + rng.randint(0, 780)
        c_ts = datetime.fromtimestamp(base_ts - age_days * 86400, tz=timezone.utc).isoformat()
        fp_accounts.append({
            "did": did,
            "handle": f"londoner-{i+100}.bsky.social",
            "alias": f"A-{did[-6:].upper()}",
            "created_at": c_ts,
            "first_seen": c_ts,
            "enriched": True,
        })
        # All burst share within 240 seconds (4 minutes)
        p_ts = datetime.fromtimestamp(base_ts + rng.uniform(0, 240), tz=timezone.utc).isoformat()
        fp_posts.append({
            "id": f"fp-post-{i}",
            "did": did,
            "text": headline,
            "text_norm": headline.lower(),
            "created_at": p_ts,
            "topic_id": 888,
            "links": [link],
            "hashtags": ["#londontransport"],
        })

    for post in fp_posts:
        apply_prepare(post)

    def _flagged(result: Dict[str, Any]) -> set:
        found = set()
        for cluster in result["clusters"]:
            if cluster["score"] >= 50 and cluster.get("classification") == "coordinated_inauthentic":
                found.update(cluster["memberDids"])
        return found

    # Run 1: WITHOUT False-Positive Protection
    res_without = run_topic_analysis(
        topic_id=888,
        posts=fp_posts,
        accounts=fp_accounts,
        min_edge_weight=0.18,
        min_cluster_size=3,
        enable_fp_protection=False,
    )
    flagged_without = _flagged(res_without)

    # Run 2: WITH False-Positive Protection
    res_with = run_topic_analysis(
        topic_id=888,
        posts=fp_posts,
        accounts=fp_accounts,
        min_edge_weight=0.18,
        min_cluster_size=3,
        enable_fp_protection=True,
    )
    flagged_with = _flagged(res_with)

    raw_count = len(flagged_without)
    prot_count = len(flagged_with)
    fp_rate_before = round(raw_count / 65.0, 3)
    fp_rate_after = round(prot_count / 65.0, 3)

    return {
        "scenario": "Major Breaking Infrastructure Announcement (TfL Orbital Route Launch)",
        "organicNewsAccounts": 65,
        "organicUsersCount": 65,
        "sharedHeadline": headline,
        "rawFlaggedWithoutProtection": raw_count,
        "flaggedWithProtection": prot_count,
        "falsePositiveRateBefore": fp_rate_before,
        "falsePositiveRateAfter": fp_rate_after,
        "explanation": (
            f"65 established accounts shared one TfL headline inside 4 minutes, against 120 background posts. "
            f"Accounts called coordinated_inauthentic at score >= 50: {raw_count} with the news rule off, {prot_count} with it on."
        ),
    }


def _build_simulated_scenario(
    organic_count: int,
    seed: int,
    evasion_mode: str,
    evasion_intensity: float,
) -> Dict[str, Any]:
    """
    Builds organic background and 3 planted bot networks (Alpha, Beta, Gamma).
    Implements 4 real adversarial evasion modes:
    - paraphrase: alters wording to evade char n-gram similarity
    - delay: increases temporal jitter beyond tight burst window
    - age_spread: staggers account creation dates across months
    - link_rotation: uses unique per-account domains
    """
    rng = random.Random(seed)
    base_ts = datetime(2026, 11, 4, 12, 0, 0, tzinfo=timezone.utc).timestamp()
    accounts = []
    posts = []
    ground_truth_bot_dids = set()

    # 1. Organic Accounts
    openers = ["Commuting through south London", "Reading the transport committee report", "Checking roadside sensor data", "Waiting for the orbital bus near Croydon", "Speaking with local delivery couriers"]
    clauses = ["shows particulate readings dropped twelve percent", "makes it clear that suburban rail frequency matters most", "while electric cargo bikes have replaced half the short runs", "even though weekend engineering works slowed down lines"]
    closers = ["according to the peer-reviewed report.", "based on living near the junction for five years.", "so practical facts matter more than slogans.", "and the acoustic noise reduction is noticeable."]

    for i in range(organic_count):
        did = f"did:plc:sim_org_{i:04d}"
        age_days = 60 + rng.randint(0, 950)
        c_ts = datetime.fromtimestamp(base_ts - age_days * 86400, tz=timezone.utc).isoformat()
        accounts.append({
            "did": did,
            "handle": f"citizen-{i+100}.bsky.social",
            "alias": f"A-{did[-6:].upper()}",
            "created_at": c_ts,
            "first_seen": c_ts,
            "enriched": True,
        })
        p_ts = datetime.fromtimestamp(base_ts + rng.randint(0, 18000), tz=timezone.utc).isoformat()
        text = f"{openers[i % len(openers)]} {clauses[(i // len(openers)) % len(clauses)]} {closers[(i // (len(openers)*len(clauses))) % len(closers)]}"
        posts.append({
            "id": f"sim-post-org-{i}",
            "did": did,
            "text": text,
            "text_norm": text.lower(),
            "created_at": p_ts,
            "topic_id": 999,
            "links": [],
            "hashtags": [],
        })

    # Helper for paraphrase evasion
    def apply_paraphrase(text: str) -> str:
        words = text.split()
        if len(words) > 6:
            # Word reordering / rewording
            shuffled = list(words)
            cut = len(shuffled) // 2
            shuffled = shuffled[cut:] + shuffled[:cut]
            return " ".join(shuffled)
        return text + " [additional distinct context notes]"

    # 2. Planted Botnet Alpha (24 accounts): Copypasta burst + 24h batch creation + 30s timing
    alpha_dids = []
    alpha_batch_ts = base_ts - 5 * 86400
    alpha_text = "Emergency audit exposes how municipal camera pricing schemes penalize suburban shift workers and small delivery vans https://cleanair-truth.org/alert #ScrapTheGrid #TaxAlert"
    for i in range(24):
        did = f"did:plc:bot_alpha_{i:02d}"
        alpha_dids.append(did)
        ground_truth_bot_dids.add(did)

        # Age evasion
        if evasion_mode == "age_spread" and rng.random() < evasion_intensity:
            c_ts = datetime.fromtimestamp(base_ts - (150 + rng.randint(0, 600)) * 86400, tz=timezone.utc).isoformat()
        else:
            c_ts = datetime.fromtimestamp(alpha_batch_ts + i * 35 * 60, tz=timezone.utc).isoformat()

        accounts.append({
            "did": did,
            "handle": f"alpha-{i:02d}.bsky.social",
            "alias": f"A-{did[-6:].upper()}",
            "created_at": c_ts,
            "first_seen": c_ts,
            "enriched": True,
        })

        # Delay evasion
        delay_sec = 600 + i * 1.5
        if evasion_mode == "delay":
            delay_sec += rng.random() * evasion_intensity * 9600.0

        p_ts = datetime.fromtimestamp(base_ts + delay_sec, tz=timezone.utc).isoformat()

        # Text paraphrase evasion
        t = alpha_text
        if evasion_mode == "paraphrase" and rng.random() < evasion_intensity:
            t = apply_paraphrase(alpha_text)

        # Link rotation evasion
        links = ["cleanair-truth.org/alert"]
        if evasion_mode == "link_rotation" and rng.random() < evasion_intensity:
            links = [f"domain-{i}.info/report"]

        posts.append({
            "id": f"sim-alpha-{i}",
            "did": did,
            "text": t,
            "text_norm": t.lower(),
            "created_at": p_ts,
            "topic_id": 999,
            "links": links,
            "hashtags": ["#scrapthegrid", "#taxalert"],
        })

    # 3. Planted Botnet Beta (18 accounts): Shared external URL + synchronized hashtag triad
    beta_dids = []
    beta_batch_ts = base_ts - 12 * 86400
    beta_text = "Reviewing the leaked council minutes regarding camera zoning expansion https://zone-leak.org/dossier #TaxTrap #LondonReview #CouncilVote"
    for i in range(18):
        did = f"did:plc:bot_beta_{i:02d}"
        beta_dids.append(did)
        ground_truth_bot_dids.add(did)

        if evasion_mode == "age_spread" and rng.random() < evasion_intensity:
            c_ts = datetime.fromtimestamp(base_ts - (150 + rng.randint(0, 600)) * 86400, tz=timezone.utc).isoformat()
        else:
            c_ts = datetime.fromtimestamp(beta_batch_ts + i * 40 * 60, tz=timezone.utc).isoformat()

        accounts.append({
            "did": did,
            "handle": f"beta-{i:02d}.bsky.social",
            "alias": f"A-{did[-6:].upper()}",
            "created_at": c_ts,
            "first_seen": c_ts,
            "enriched": True,
        })

        delay_sec = 1800 + i * 2.2
        if evasion_mode == "delay":
            delay_sec += rng.random() * evasion_intensity * 9600.0

        p_ts = datetime.fromtimestamp(base_ts + delay_sec, tz=timezone.utc).isoformat()

        t = beta_text
        if evasion_mode == "paraphrase" and rng.random() < evasion_intensity:
            t = apply_paraphrase(beta_text)

        links = ["zone-leak.org/dossier"]
        if evasion_mode == "link_rotation" and rng.random() < evasion_intensity:
            links = [f"independent-news-{i}.org/leak"]

        posts.append({
            "id": f"sim-beta-{i}",
            "did": did,
            "text": t,
            "text_norm": t.lower(),
            "created_at": p_ts,
            "topic_id": 999,
            "links": links,
            "hashtags": ["#taxtrap", "#londonreview", "#councilvote"],
        })

    # 4. Planted Botnet Gamma (14 accounts): Template variations
    gamma_dids = []
    gamma_batch_ts = base_ts - 20 * 86400
    gamma_templates = [
        "Small local businesses in outer boroughs face closure due to newly proposed driving charges https://save-highstreet.org/plea #SaveLocalJobs",
        "Independent traders in outer boroughs face closure due to newly proposed vehicle charges https://save-highstreet.org/plea #SaveLocalJobs",
    ]
    for i in range(14):
        did = f"did:plc:bot_gamma_{i:02d}"
        gamma_dids.append(did)
        ground_truth_bot_dids.add(did)

        if evasion_mode == "age_spread" and rng.random() < evasion_intensity:
            c_ts = datetime.fromtimestamp(base_ts - (150 + rng.randint(0, 600)) * 86400, tz=timezone.utc).isoformat()
        else:
            c_ts = datetime.fromtimestamp(gamma_batch_ts + i * 50 * 60, tz=timezone.utc).isoformat()

        accounts.append({
            "did": did,
            "handle": f"gamma-{i:02d}.bsky.social",
            "alias": f"A-{did[-6:].upper()}",
            "created_at": c_ts,
            "first_seen": c_ts,
            "enriched": True,
        })

        delay_sec = 3200 + i * 3.1
        if evasion_mode == "delay":
            delay_sec += rng.random() * evasion_intensity * 9600.0

        p_ts = datetime.fromtimestamp(base_ts + delay_sec, tz=timezone.utc).isoformat()

        t = gamma_templates[i % len(gamma_templates)]
        if evasion_mode == "paraphrase" and rng.random() < evasion_intensity:
            t = apply_paraphrase(t)

        links = ["save-highstreet.org/plea"]
        if evasion_mode == "link_rotation" and rng.random() < evasion_intensity:
            links = [f"petition-mirror-{i}.org/campaign"]

        posts.append({
            "id": f"sim-gamma-{i}",
            "did": did,
            "text": t,
            "text_norm": t.lower(),
            "created_at": p_ts,
            "topic_id": 999,
            "links": links,
            "hashtags": ["#savelocaljobs"],
        })

    networks = [
        {"id": "alpha", "name": "Botnet Alpha", "tactic": "Copypasta burst + 24h batch creation + 30s timing", "dids": alpha_dids},
        {"id": "beta", "name": "Botnet Beta", "tactic": "Shared external URL + synchronized hashtag triad", "dids": beta_dids},
        {"id": "gamma", "name": "Botnet Gamma", "tactic": "Template prefix/suffix variations + 36h cohort", "dids": gamma_dids},
    ]

    for post in posts:
        apply_prepare(post)

    return {
        "accounts": accounts,
        "posts": posts,
        "ground_truth_bot_dids": ground_truth_bot_dids,
        "networks": networks,
    }
