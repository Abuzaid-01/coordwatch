"""Account metrics, purity, confidence intervals, and the two baselines. No detector run."""
from backend.app.sim.benchmark_v2 import coin_flip_detected, exact_duplicate_detected
from backend.app.sim.metrics import bootstrap_ci, compute_account_metrics, compute_cluster_purity


def test_precision_separates_organic_false_positives_from_hard_negatives():
    bots = {"bot1", "bot2"}
    organic = {"org1", "org2", "org3"}
    hard = {"hn1"}
    metrics = compute_account_metrics({"bot1", "org1", "hn1"}, bots, organic, hard, organic_count=3)
    assert metrics["tp"] == 1
    assert metrics["fp_organic"] == 1
    assert metrics["fp_hard_neg"] == 1
    assert metrics["fn"] == 1
    assert metrics["precision"] == round(1 / 3, 4)
    assert metrics["recall"] == 0.5
    assert metrics["fp_per_1000_organic"] == round(1000 / 3, 2)
    assert metrics["fp_per_1000"] == metrics["fp_per_1000_organic"]


def test_empty_cluster_purity_is_null_and_small_samples_withhold_ci():
    assert compute_cluster_purity([], {"bot1"}) is None
    mean, low, high = bootstrap_ci([0.2, 0.4, 0.8])
    assert low is None and high is None
    assert mean == round((0.2 + 0.4 + 0.8) / 3, 4)
    _, wide_low, wide_high = bootstrap_ci([0.5] * 10)
    assert wide_low is not None and wide_high is not None
    assert bootstrap_ci([]) == (0.0, None, None)


def test_coin_flip_changes_with_seed_and_exact_duplicate_needs_three_accounts():
    accounts = [{"did": f"did:plc:acct{i:02d}"} for i in range(40)]
    first = coin_flip_detected(accounts, seed=42)
    second = coin_flip_detected(accounts, seed=43)
    assert first != second
    assert coin_flip_detected(accounts, seed=42) == first
    bots = {accounts[i]["did"] for i in range(8)}
    organic = {accounts[i]["did"] for i in range(8, 40)}
    one = compute_account_metrics(first, bots, organic, set(), organic_count=32)
    two = compute_account_metrics(second, bots, organic, set(), organic_count=32)
    assert one["recall"] != two["recall"] or one["precision"] != two["precision"]

    same = "breaking audit proves the municipal grid report is being buried"
    close = [
        {"did": "did:plc:e1", "text_norm": same, "created_at": "2026-04-20T12:00:00Z"},
        {"did": "did:plc:e2", "text_norm": same, "created_at": "2026-04-20T12:10:00Z"},
        {"did": "did:plc:e3", "text_norm": same, "created_at": "2026-04-20T13:00:00Z"},
    ]
    assert exact_duplicate_detected(close) == {"did:plc:e1", "did:plc:e2", "did:plc:e3"}
    pair_only = close[:2]
    assert exact_duplicate_detected(pair_only) == set()
    spread = [
        {"did": "did:plc:e1", "text_norm": same, "created_at": "2026-04-20T12:00:00Z"},
        {"did": "did:plc:e2", "text_norm": same, "created_at": "2026-04-20T20:00:00Z"},
        {"did": "did:plc:e3", "text_norm": same, "created_at": "2026-04-21T04:00:00Z"},
    ]
    assert exact_duplicate_detected(spread) == set()
