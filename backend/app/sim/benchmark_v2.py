"""Benchmark that measures the detector. Dev and test use the same 12 families.

Seeds differ. No recall in this file is a literal. Rows that were not run are omitted.
"""

from datetime import datetime, timezone
import json
import logging
import math
from pathlib import Path
import random
from typing import Any, Dict, List, Optional, Set

from ..analysis.engine import run_topic_analysis
from .families import generate_bot_family
from .hard_negatives import generate_hard_negative
from .organic import generate_organic_background
from .metrics import (
    bootstrap_ci,
    compute_account_metrics,
    compute_campaign_level_recall,
    compute_cluster_purity,
    compute_pr_auc,
)

logger = logging.getLogger(__name__)

ALL_FAMILIES = [
    ("F1", "F1_Copypasta", 18),
    ("F2", "F2_Template", 16),
    ("F3", "F3_Paraphrase", 16),
    ("F4", "F4_Hashtags", 14),
    ("F5", "F5_Links", 14),
    ("F6", "F6_Reposts", 12),
    ("F7", "F7_Sleepers", 16),
    ("F8", "F8_SlowDrip", 14),
    ("F9", "F9_Hybrid", 16),
    ("F10", "F10_Camo", 14),
    ("F11", "F11_SybilScattered", 16),
    ("F12", "F12_SmallCell", 5),
]
ALL_HARD_NEGATIVES = [f"H{i}" for i in range(1, 11)]

EVASION_SPECS = [
    {
        "id": "paraphrase_6h",
        "evasion": "Paraphrase plus 6h jitter",
        "family": "F3",
        "size": 12,
        "burst_span_override": 6 * 3600 + 60,
    },
    {
        "id": "sleeper_copypasta",
        "evasion": "Aged sleeper copypasta",
        "family": "F7",
        "size": 12,
    },
    {
        "id": "camouflage",
        "evasion": "Camouflage chatter",
        "family": "F10",
        "size": 12,
    },
    {
        "id": "slow_drip_12h",
        "evasion": "Slow drip over 12h",
        "family": "F8",
        "size": 12,
        "burst_span_override": 12 * 3600 + 60,
    },
    {
        "id": "combined",
        "evasion": "Paraphrase plus jitter plus aged accounts",
        "family": "F7",
        "size": 12,
        "burst_span_override": 6 * 3600 + 60,
        "age_days_override": 400.0,
        "force_paraphrase": True,
    },
]


def _parse_ts(iso_str: str) -> float:
    try:
        return datetime.fromisoformat(iso_str.replace("Z", "+00:00")).timestamp()
    except Exception:
        return 0.0


def build_scenario_v2(
    split: str = "dev",
    organic_count: int = 200,
    seed: int = 42,
    base_time: float = 1793850000.0,
    include_campaigns: Optional[bool] = None,
    include_hard_negatives: Optional[bool] = None,
) -> Dict[str, Any]:
    """Plant all 12 families and all 10 hard negatives. split only labels the seed group."""
    plant_campaigns = include_campaigns if include_campaigns is not None else split != "null_organic"
    plant_hard_neg = include_hard_negatives if include_hard_negatives is not None else split != "null_organic"

    accounts, posts = generate_organic_background(
        count=organic_count,
        seed=seed,
        base_time=base_time,
        window_hours=24.0,
    )
    organic_dids = {a["did"] for a in accounts}
    campaigns = []
    hard_negatives = []
    ground_truth_bot_dids: Set[str] = set()

    if plant_campaigns:
        for offset, (fam_id, camp_id, size) in enumerate(ALL_FAMILIES):
            camp = generate_bot_family(
                family_id=fam_id,
                campaign_id=f"{camp_id}_{seed}",
                size=size,
                base_time=base_time + random.Random(seed + offset).uniform(1800.0, 7200.0),
                seed=seed + offset,
            )
            campaigns.append(camp)
            accounts.extend(camp["accounts"])
            posts.extend(camp["posts"])
            ground_truth_bot_dids.update(camp["dids"])

    if plant_hard_neg:
        for offset, hn_id in enumerate(ALL_HARD_NEGATIVES):
            hn = generate_hard_negative(
                scenario_id=hn_id,
                base_time=base_time + random.Random(seed + offset + 100).uniform(3600.0, 10800.0),
                seed=seed + offset + 100,
                size=10,
            )
            hard_negatives.append(hn)
            accounts.extend(hn["accounts"])
            posts.extend(hn["posts"])

    rng = random.Random(seed)
    rng.shuffle(posts)
    hard_neg_dids = {did for hn in hard_negatives for did in hn["dids"]}
    return {
        "split": split,
        "seed": seed,
        "accounts": accounts,
        "posts": posts,
        "campaigns": campaigns,
        "hard_negatives": hard_negatives,
        "ground_truth_bot_dids": ground_truth_bot_dids,
        "organic_dids": organic_dids,
        "hard_neg_dids": hard_neg_dids,
        "organic_count": organic_count,
    }


def _inauthentic_dids(analysis: Dict[str, Any], score_threshold: int) -> Set[str]:
    detected: Set[str] = set()
    for cluster in analysis["clusters"]:
        if cluster["score"] >= score_threshold and cluster.get("classification") == "coordinated_inauthentic":
            detected.update(cluster["memberDids"])
    return detected


def evaluate_scenario_v2(
    scenario: Dict[str, Any],
    score_threshold: int = 50,
    enable_fp_protection: bool = True,
    n_permutations: int = 50,
) -> Dict[str, Any]:
    analysis = run_topic_analysis(
        posts=scenario["posts"],
        accounts=scenario["accounts"],
        topic_id=1,
        enable_fp_protection=enable_fp_protection,
        n_permutations=n_permutations,
    )
    detected_clusters = [
        c for c in analysis["clusters"]
        if c["score"] >= score_threshold and c.get("classification") == "coordinated_inauthentic"
    ]
    detected_bot_dids = _inauthentic_dids(analysis, score_threshold)
    organic_dids = set(scenario.get("organic_dids") or [])
    hard_neg_dids = set(scenario.get("hard_neg_dids") or [])
    acct_metrics = compute_account_metrics(
        detected_dids=detected_bot_dids,
        ground_truth_bot_dids=scenario["ground_truth_bot_dids"],
        organic_dids=organic_dids,
        hard_neg_dids=hard_neg_dids,
        organic_count=scenario["organic_count"],
    )

    all_dids = {a["did"] for a in scenario["accounts"]}
    node_scores = {did: 0.0 for did in all_dids}
    for cluster in detected_clusters:
        for did in cluster["memberDids"]:
            node_scores[did] = max(node_scores.get(did, 0.0), float(cluster["score"]))
    pr_auc = compute_pr_auc(
        node_scores=node_scores,
        ground_truth_bot_dids=scenario["ground_truth_bot_dids"],
        all_dids=all_dids,
    )
    camp_metrics = compute_campaign_level_recall(
        detected_dids=detected_bot_dids,
        campaigns=scenario["campaigns"],
        threshold_fraction=0.50,
    )
    cluster_purity = compute_cluster_purity(
        clusters=detected_clusters,
        ground_truth_bot_dids=scenario["ground_truth_bot_dids"],
    )

    hn_flag_count = 0
    hn_results = []
    for hn in scenario["hard_negatives"]:
        hn_dids = set(hn["dids"])
        flagged_members = len(hn_dids & detected_bot_dids)
        is_flagged = flagged_members > 0
        if is_flagged:
            hn_flag_count += 1
        hn_results.append({
            "id": hn["id"],
            "name": hn["name"],
            "class": hn["class"],
            "flaggedAsInauthentic": is_flagged,
            "memberFlagRatio": round(flagged_members / max(1, len(hn_dids)), 3),
        })
    hn_flag_rate = (
        round(hn_flag_count / len(scenario["hard_negatives"]), 4)
        if scenario["hard_negatives"]
        else 0.0
    )
    return {
        "acct": acct_metrics,
        "pr_auc": pr_auc,
        "campaign_recall": camp_metrics["campaign_recall"],
        "campaign_breakdown": camp_metrics["breakdown"],
        "cluster_purity": cluster_purity,
        "hard_negatives_flag_rate": hn_flag_rate,
        "hard_negatives_breakdown": hn_results,
        "clusters_detected": len(detected_clusters),
        "total_clusters": len(analysis["clusters"]),
        "detected_bot_dids": list(detected_bot_dids),
    }


def coin_flip_detected(accounts: List[Dict[str, Any]], seed: int) -> Set[str]:
    """Seeded coin flip. A different seed flags a different set of accounts."""
    rng = random.Random(seed + 9000)
    return {account["did"] for account in accounts if rng.random() >= 0.5}


def exact_duplicate_detected(posts: List[Dict[str, Any]], window_sec: float = 6 * 3600) -> Set[str]:
    """Flag an account that shares text_norm with at least two other accounts inside 6 hours."""
    groups: Dict[str, List[Dict[str, Any]]] = {}
    for post in posts:
        norm = post.get("text_norm") or ""
        if len(norm) < 12:
            continue
        groups.setdefault(norm, []).append(post)
    flagged: Set[str] = set()
    for items in groups.values():
        stamped = [( _parse_ts(p.get("created_at") or ""), p) for p in items]
        stamped = [(ts, p) for ts, p in stamped if ts > 0]
        stamped.sort(key=lambda item: item[0])
        for ts, post in stamped:
            others = {
                other["did"]
                for other_ts, other in stamped
                if other["did"] != post["did"] and abs(other_ts - ts) <= window_sec
            }
            if len(others) >= 2:
                flagged.add(post["did"])
                flagged.update(others)
    return flagged


def _shuffle_post_authors(scenario: Dict[str, Any], seed: int) -> Dict[str, Any]:
    posts = [dict(post) for post in scenario["posts"]]
    dids = [post["did"] for post in posts]
    rng = random.Random(seed)
    rng.shuffle(dids)
    for post, did in zip(posts, dids):
        post["did"] = did
    shuffled = dict(scenario)
    shuffled["posts"] = posts
    return shuffled


def _agg(runs: List[Dict[str, Any]], key_path: str) -> Dict[str, Any]:
    values: List[float] = []
    for run in runs:
        current: Any = run
        missing = False
        for part in key_path.split("."):
            if not isinstance(current, dict) or part not in current or current[part] is None:
                missing = True
                break
            current = current[part]
        if missing:
            continue
        values.append(float(current))
    if not values:
        return {
            "mean": None,
            "std": None,
            "ci_low": None,
            "ci_high": None,
            "n": 0,
            "ci_withheld": True,
            "values": [],
            "note": "n/a (no clusters)",
        }
    mean, ci_low, ci_high = bootstrap_ci(values)
    std = round(math.sqrt(sum((v - mean) ** 2 for v in values) / len(values)), 4)
    return {
        "mean": mean,
        "std": std,
        "ci_low": ci_low,
        "ci_high": ci_high,
        "n": len(values),
        "ci_withheld": ci_low is None,
        "values": [round(v, 4) for v in values],
        "note": "CI withheld (n < 10)" if ci_low is None else "",
    }


def _mean_metric(runs: List[Dict[str, Any]], key: str) -> Optional[float]:
    summary = _agg(runs, key)
    mean = summary["mean"]
    return None if mean is None else float(mean)


def measure_evasion(seed: int, organic_count: int, n_permutations: int) -> List[Dict[str, Any]]:
    rows = []
    base_time = 1793850000.0
    for spec in EVASION_SPECS:
        accounts, posts = generate_organic_background(
            count=organic_count,
            seed=seed,
            base_time=base_time,
            window_hours=36.0,
        )
        organic_dids = {a["did"] for a in accounts}
        camp = generate_bot_family(
            family_id=spec["family"],
            campaign_id=f"{spec['id']}_{seed}",
            size=spec["size"],
            base_time=base_time + 3600,
            seed=seed + 17,
            burst_span_override=spec.get("burst_span_override"),
            age_days_override=spec.get("age_days_override"),
            force_paraphrase=bool(spec.get("force_paraphrase")),
        )
        accounts.extend(camp["accounts"])
        posts.extend(camp["posts"])
        scenario = {
            "accounts": accounts,
            "posts": posts,
            "campaigns": [camp],
            "hard_negatives": [],
            "ground_truth_bot_dids": set(camp["dids"]),
            "organic_dids": organic_dids,
            "hard_neg_dids": set(),
            "organic_count": organic_count,
        }
        evaluated = evaluate_scenario_v2(scenario, n_permutations=n_permutations)
        detected = set(evaluated["detected_bot_dids"])
        recall = round(len(detected & set(camp["dids"])) / max(1, len(camp["dids"])), 4)
        rows.append({
            "id": spec["id"],
            "evasion": spec["evasion"],
            "familyId": spec["family"],
            "seed": seed,
            "organicCount": organic_count,
            "nPermutations": n_permutations,
            "observedRecall": recall,
        })
    return rows


def run_benchmark_v2_suite(
    seeds: Optional[List[int]] = None,
    test_seeds: Optional[List[int]] = None,
    organic_count: int = 200,
    n_permutations: int = 200,
    evasion_seeds: Optional[List[int]] = None,
    label: str = "published",
) -> Dict[str, Any]:
    eval_seeds = list(seeds or list(range(42, 52)))
    heldout_seeds = list(test_seeds or list(range(142, 152)))
    evasion_seed_list = list(evasion_seeds if evasion_seeds is not None else eval_seeds)
    evasion_organic = min(80, organic_count)

    dev_runs = []
    no_fp_runs = []
    test_runs = []
    dev_scenarios = []

    for seed in eval_seeds:
        logger.info("Dev seed %s", seed)
        scenario = build_scenario_v2(split="dev", organic_count=organic_count, seed=seed)
        dev_scenarios.append(scenario)
        dev_runs.append(evaluate_scenario_v2(scenario, enable_fp_protection=True, n_permutations=n_permutations))
        no_fp_runs.append(evaluate_scenario_v2(scenario, enable_fp_protection=False, n_permutations=n_permutations))

    for seed in heldout_seeds:
        logger.info("Test seed %s", seed)
        scenario = build_scenario_v2(split="test", organic_count=organic_count, seed=seed)
        test_runs.append(evaluate_scenario_v2(scenario, enable_fp_protection=True, n_permutations=n_permutations))

    def pack(runs: List[Dict[str, Any]]) -> Dict[str, Any]:
        return {
            "precision": _agg(runs, "acct.precision"),
            "recall": _agg(runs, "acct.recall"),
            "f1": _agg(runs, "acct.f1"),
            "fp_per_1000": _agg(runs, "acct.fp_per_1000_organic"),
            "fp_per_1000_organic": _agg(runs, "acct.fp_per_1000_organic"),
            "pr_auc": _agg(runs, "pr_auc"),
            "campaign_recall": _agg(runs, "campaign_recall"),
            "cluster_purity": _agg(runs, "cluster_purity"),
            "hard_neg_flag_rate": _agg(runs, "hard_negatives_flag_rate"),
        }

    dev_summary = pack(dev_runs)
    test_summary = pack(test_runs)
    no_fp_summary = pack(no_fp_runs)

    # Baselines on the same dev scenarios. Random is a seeded coin flip.
    random_runs = []
    exact_runs = []
    for scenario in dev_scenarios:
        guessed = coin_flip_detected(scenario["accounts"], scenario["seed"])
        random_runs.append(compute_account_metrics(
            guessed,
            scenario["ground_truth_bot_dids"],
            scenario["organic_dids"],
            scenario["hard_neg_dids"],
            scenario["organic_count"],
        ))
        exact_hits = exact_duplicate_detected(scenario["posts"])
        exact_runs.append(compute_account_metrics(
            exact_hits,
            scenario["ground_truth_bot_dids"],
            scenario["organic_dids"],
            scenario["hard_neg_dids"],
            scenario["organic_count"],
        ))

    def baseline_from(runs: List[Dict[str, Any]], name: str) -> Dict[str, Any]:
        return {
            "name": name,
            "precision": _mean_metric([{"acct": r} for r in runs], "acct.precision"),
            "recall": _mean_metric([{"acct": r} for r in runs], "acct.recall"),
            "f1": _mean_metric([{"acct": r} for r in runs], "acct.f1"),
        }

    baselines = {
        "exact_duplicate_only": baseline_from(exact_runs, "Exact-duplicate text, three accounts inside 6h"),
        "random_baseline": baseline_from(random_runs, "Seeded coin-flip at 0.5"),
    }
    ablations = {
        "full_pipeline": {
            "name": "Full pipeline with benign news rule",
            "precision": dev_summary["precision"]["mean"],
            "recall": dev_summary["recall"]["mean"],
            "f1": dev_summary["f1"]["mean"],
            "fp_per_1000": dev_summary["fp_per_1000_organic"]["mean"],
            "fp_per_1000_organic": dev_summary["fp_per_1000_organic"]["mean"],
            "hard_neg_flag_rate": dev_summary["hard_neg_flag_rate"]["mean"],
        },
        "without_benign_explanations": {
            "name": "Same seeds with benign news rule off",
            "precision": no_fp_summary["precision"]["mean"],
            "recall": no_fp_summary["recall"]["mean"],
            "f1": no_fp_summary["f1"]["mean"],
            "fp_per_1000": no_fp_summary["fp_per_1000_organic"]["mean"],
            "fp_per_1000_organic": no_fp_summary["fp_per_1000_organic"]["mean"],
            "hard_neg_flag_rate": no_fp_summary["hard_neg_flag_rate"]["mean"],
        },
    }

    null_scenario = build_scenario_v2(split="null_organic", organic_count=min(120, organic_count), seed=eval_seeds[0])
    null_eval = evaluate_scenario_v2(null_scenario, n_permutations=n_permutations)
    shuffled = _shuffle_post_authors(dev_scenarios[0], seed=eval_seeds[0] + 5000)
    shuffled_eval = evaluate_scenario_v2(shuffled, n_permutations=n_permutations)
    null_status = "PASS" if null_eval["clusters_detected"] == 0 else "FLAGGED"

    evasion_rows: List[Dict[str, Any]] = []
    for seed in evasion_seed_list:
        logger.info("Evasion seed %s", seed)
        evasion_rows.extend(measure_evasion(seed, evasion_organic, n_permutations=min(50, n_permutations)))
    evasion_rows = [row for row in evasion_rows if row.get("seed") is not None]

    from .simulator import _run_real_fp_stress_test
    fp_stress = _run_real_fp_stress_test(seed=eval_seeds[0])

    first = dev_runs[0]
    bot_count = len(dev_scenarios[0]["ground_truth_bot_dids"])
    report = {
        "computedAt": datetime.now(timezone.utc).isoformat(),
        "label": label,
        "splitDescription": "same 12 families and all 10 hard negatives; dev and test differ by seed",
        "seedsEvaluated": eval_seeds,
        "testSeeds": heldout_seeds,
        "organicCountPerSeed": organic_count,
        "nPermutations": n_permutations,
        "organicAccounts": organic_count,
        "plantedBotAccounts": bot_count,
        "totalAccounts": organic_count + bot_count + len(dev_scenarios[0]["hard_neg_dids"]),
        "precision": dev_summary["precision"]["mean"],
        "recall": dev_summary["recall"]["mean"],
        "f1": dev_summary["f1"]["mean"],
        "truePositives": first["acct"]["tp"],
        "falsePositives": first["acct"]["fp"],
        "falseNegatives": first["acct"]["fn"],
        "devSummary": dev_summary,
        "testSummary": test_summary,
        "baselines": baselines,
        "ablations": ablations,
        "nullControl": {
            "organicAccounts": null_scenario["organic_count"],
            "falsePositivesDetected": null_eval["acct"]["fp_organic"],
            "clustersFlagged": null_eval["clusters_detected"],
            "shuffledAuthorCampaignRecall": shuffled_eval["campaign_recall"],
            "unshuffledCampaignRecall": dev_runs[0]["campaign_recall"],
            "status": null_status,
        },
        "evasionBoundaries": evasion_rows,
        "falsePositiveStress": fp_stress,
        "falsePositiveStressTest": fp_stress,
        "hardNegatives": {
            "dev": dev_runs[0]["hard_negatives_breakdown"],
            "test": test_runs[0]["hard_negatives_breakdown"] if test_runs else [],
        },
        "honestLimitations": [
            "Character 3-gram similarity misses a rewrite that shares little surface form with the source sentence.",
            "Aged accounts that copy an allowlisted headline are classified as news sharing.",
            "The ingestor reads the public post firehose in one process and filters keywords locally.",
            "Account creation time comes from plc.directory, with getProfile as the fallback. A failed lookup stores no creation time.",
            "A confidence interval is published only when at least 10 seeds were run.",
        ],
    }

    report_dir = Path("backend/data/evaluation_runs")
    report_dir.mkdir(parents=True, exist_ok=True)
    report_file = report_dir / "latest.json"
    with report_file.open("w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2)
    logger.info("Saved evaluation report to %s", report_file)
    return report
