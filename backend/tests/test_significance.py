"""Permutation score, FDR decisions, and the classification the API stores."""
from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from backend.app.analysis.engine import run_topic_analysis
from backend.app.analysis.significance import apply_detection_decisions, compute_cluster_significance
from backend.app.db import (
    analyze_and_persist_topic,
    create_or_get_topic,
    get_connection,
    init_db,
    insert_live_post,
    upsert_account,
)
from backend.app.main import app
from backend.app.sim.benchmark_v2 import evaluate_scenario_v2
from backend.app.sim.families import generate_bot_family
from backend.app.sim.hard_negatives import generate_hard_negative


def test_missing_timestamps_are_not_tested():
    posts = [
        {"did": "did:plc:a", "text": "same sentence without a clock"},
        {"did": "did:plc:b", "text": "same sentence without a clock"},
    ]
    result = compute_cluster_significance(
        ["did:plc:a", "did:plc:b"],
        cluster_score=70.0,
        all_topic_posts=posts,
        n_permutations=20,
    )
    assert result["status"] == "not_tested"
    assert result["p_value"] is None
    assert result["significant"] is False


def test_tight_copypasta_beats_a_shuffled_author_null():
    base = datetime(2026, 6, 1, 12, 0, tzinfo=timezone.utc)
    dids = [f"did:plc:burst{i}" for i in range(4)]
    posts = [
        {
            "did": did,
            "created_at": (base + timedelta(seconds=i * 8)).isoformat(),
            "text_norm": "identical campaign sentence about the leaked dossier",
        }
        for i, did in enumerate(dids)
    ]
    for i in range(20):
        posts.append({
            "did": f"did:plc:org{i}",
            "created_at": (base + timedelta(hours=2 + i * 1.05)).isoformat(),
            "text_norm": f"unrelated personal note number {i} about the weather today",
        })
    result = compute_cluster_significance(dids, 80.0, posts, n_permutations=200, seed=3)
    assert result["status"] == "tested"
    assert result["p_value"] is not None and result["p_value"] < 0.05
    assert result["n_permutations"] == 200
    assert result["cluster_score_used"] == 80.0


def test_organic_clusters_do_not_inflate_the_inauthentic_fdr():
    clusters = [
        {
            "classification": "coordinated_inauthentic",
            "reasons": [],
            "significance": {"status": "tested", "p_value": 0.02},
        },
        {
            "classification": "organic",
            "reasons": [],
            "significance": {"status": "tested", "p_value": 0.9},
        },
        {
            "classification": "organic",
            "reasons": [],
            "significance": {"status": "tested", "p_value": 0.8},
        },
    ]
    decided = apply_detection_decisions(clusters)
    assert decided[0]["classification"] == "coordinated_inauthentic"
    assert decided[0]["significance"]["fdr_significant"] is True
    assert decided[1]["classification"] == "organic"


def test_fdr_withholds_inauthentic_labels_and_keeps_benign():
    clusters = [
        {
            "classification": "coordinated_inauthentic",
            "reasons": [],
            "significance": {"status": "tested", "p_value": 0.8},
        },
        {
            "classification": "coordinated_inauthentic",
            "reasons": [],
            "significance": {"status": "tested", "p_value": 0.001},
        },
        {
            "classification": "coordinated_benign",
            "reasons": ["news"],
            "significance": {"status": "tested", "p_value": 0.8},
        },
        {
            "classification": "coordinated_inauthentic",
            "reasons": [],
            "significance": {"status": "not_tested", "p_value": None},
        },
    ]
    decided = apply_detection_decisions(clusters)
    assert decided[0]["classification"] == "insufficient_evidence"
    assert decided[1]["classification"] == "coordinated_inauthentic"
    assert decided[1]["significance"]["fdr_significant"] is True
    assert decided[2]["classification"] == "coordinated_benign"
    assert decided[3]["classification"] == "insufficient_evidence"
    assert decided[0]["significance"]["fdr_q_value"] is not None
    assert decided[3]["significance"]["fdr_q_value"] is None


def test_each_cluster_is_tested_at_its_own_raw_score(monkeypatch):
    calls = []

    def fake_score(cluster_dids, signal_averages, **kwargs):
        raw = 61 if any("grpA" in did for did in cluster_dids) else 88
        return {
            "score": raw,
            "raw_score": raw,
            "discount_applied": 0.0,
            "discount_reason": None,
            "classification": "coordinated_inauthentic",
            "benign_checks": {},
            "reasons": ["spy"],
        }

    def fake_significance(**kwargs):
        calls.append(kwargs["cluster_score"])
        return {
            "p_value": 0.001,
            "status": "tested",
            "stat_observed": 6.0,
            "stat_null_mean": 0.0,
            "stat_null_std": 0.0,
            "n_permutations": kwargs["n_permutations"],
            "cluster_score_used": kwargs["cluster_score"],
            "significant": True,
        }

    monkeypatch.setattr("backend.app.analysis.engine.compute_cluster_score_and_reasons", fake_score)
    monkeypatch.setattr("backend.app.analysis.engine.compute_cluster_significance", fake_significance)

    def group(prefix, created, posted, text, link):
        accounts = []
        posts = []
        for i in range(4):
            did = f"did:plc:{prefix}{i}"
            accounts.append({
                "did": did,
                "handle": f"{prefix}{i}.bsky.social",
                "alias": f"A-{prefix}{i}",
                "created_at": created,
                "enriched": True,
            })
            stamp = datetime.fromisoformat(posted) + timedelta(seconds=i * 5)
            posts.append({
                "id": f"{prefix}-{i}",
                "did": did,
                "text": text,
                "text_norm": text,
                "created_at": stamp.isoformat(),
                "links": [link],
                "hashtags": [prefix],
            })
        return accounts, posts

    accounts_a, posts_a = group(
        "grpA",
        "2024-01-01T10:00:00+00:00",
        "2026-04-20T12:00:00+00:00",
        "breaking independent audit proves municipal grids are draining faster than forecast",
        "https://campaign-dossier.example/a",
    )
    accounts_b, posts_b = group(
        "grpB",
        "2025-08-01T10:00:00+00:00",
        "2026-04-20T21:00:00+00:00",
        "sourdough bread needs a long cold ferment and a very hot dutch oven tonight",
        "https://recipes.example/bread",
    )
    result = run_topic_analysis(
        topic_id=4242,
        posts=posts_a + posts_b,
        accounts=accounts_a + accounts_b,
        n_permutations=5,
    )
    assert len(result["clusters"]) == 2
    assert sorted(calls) == [61, 88]
    assert 50.0 not in calls
    for cluster in result["clusters"]:
        assert cluster["significance"]["cluster_score_used"] == cluster["rawScore"]


def test_saved_classification_matches_the_engine():
    init_db()
    topic = create_or_get_topic("phase3 persist probe", mode="live", source="live")
    topic_id = topic["id"]
    conn = get_connection()
    try:
        conn.execute("DELETE FROM cluster_members WHERE topic_id = ?", (topic_id,))
        conn.execute("DELETE FROM clusters WHERE topic_id = ?", (topic_id,))
        conn.execute("DELETE FROM posts WHERE topic_id = ?", (topic_id,))
        conn.commit()
    finally:
        conn.close()

    base = datetime(2026, 6, 2, 9, 0, tzinfo=timezone.utc)
    dids = [f"did:plc:persist{i}" for i in range(4)]
    conn = get_connection()
    try:
        for i, did in enumerate(dids):
            created = (base - timedelta(days=12)).isoformat()
            upsert_account({
                "did": did,
                "handle": f"persist{i}.bsky.social",
                "created_at": created,
                "enriched": True,
                "enrich_status": "ok",
            }, conn=conn)
            insert_live_post({
                "id": f"persist-post-{i}",
                "did": did,
                "text": "Stop this terrible policy now. Read the full leaked report https://cleanair-truth-london.org/dossier",
                "text_norm": "",
                "created_at": (base + timedelta(seconds=i * 6)).isoformat(),
                "topic_id": topic_id,
                "links": ["https://cleanair-truth-london.org/dossier"],
                "hashtags": ["axethetax"],
                "source": "test",
            }, conn=conn)
        for i in range(20):
            did = f"did:plc:persistorg{i}"
            created = (base - timedelta(days=200 + i)).isoformat()
            upsert_account({
                "did": did,
                "handle": f"persistorg{i}.bsky.social",
                "created_at": created,
                "enriched": True,
                "enrich_status": "ok",
            }, conn=conn)
            insert_live_post({
                "id": f"persist-org-{i}",
                "did": did,
                "text": f"Ordinary commute note {i} about the bus and the weather on a quiet street.",
                "text_norm": "",
                "created_at": (base + timedelta(hours=3 + i)).isoformat(),
                "topic_id": topic_id,
                "links": [],
                "hashtags": [],
                "source": "test",
            }, conn=conn)
        conn.commit()
    finally:
        conn.close()

    result = analyze_and_persist_topic(topic_id)
    assert result["clusters"]
    saved = result["clusters"][0]
    client = TestClient(app)
    response = client.get(f"/clusters/{saved['id']}?topicId={topic_id}")
    assert response.status_code == 200
    body = response.json()["cluster"]
    assert body["classification"] == saved["classification"]
    assert body["classification"] in {
        "coordinated_inauthentic",
        "coordinated_benign",
        "organic",
        "insufficient_evidence",
    }
    assert body["significance"]["status"] == saved["significance"]["status"]
    assert body["significance"].get("cluster_score_used") == saved["rawScore"]


def test_copypasta_is_flagged_and_aged_bbc_burst_is_not():
    base = datetime(2026, 7, 1, 12, 0, tzinfo=timezone.utc).timestamp()
    campaign = generate_bot_family("F1", "F1CELL", 6, base, seed=7)
    news = generate_hard_negative("H1", base + 12 * 3600, seed=7, size=8)
    accounts = list(campaign["accounts"]) + list(news["accounts"])
    posts = list(campaign["posts"]) + list(news["posts"])
    organic_dids = []
    for i in range(24):
        did = f"did:plc:smallorg{i:02d}"
        organic_dids.append(did)
        created = datetime.fromtimestamp(base - (180 + i * 15) * 86400, tz=timezone.utc).isoformat()
        accounts.append({
            "did": did,
            "handle": f"smallorg{i}.bsky.social",
            "alias": f"A-ORG{i:02d}",
            "created_at": created,
            "enriched": True,
        })
        posted = datetime.fromtimestamp(base - 6 * 3600 + i * 3600, tz=timezone.utc).isoformat()
        posts.append({
            "id": f"small-org-{i}",
            "did": did,
            "text": f"Personal note {i} about a different bus stop and a different afternoon.",
            "created_at": posted,
            "links": [],
            "hashtags": [],
        })
    from backend.app.textutil import apply_prepare
    for post in posts:
        apply_prepare(post)
    scenario = {
        "accounts": accounts,
        "posts": posts,
        "campaigns": [campaign],
        "hard_negatives": [news],
        "ground_truth_bot_dids": set(campaign["dids"]),
        "organic_dids": set(organic_dids),
        "hard_neg_dids": set(news["dids"]),
        "organic_count": len(organic_dids),
    }
    measured = evaluate_scenario_v2(scenario, n_permutations=40)
    detected = set(measured["detected_bot_dids"])
    assert set(campaign["dids"]) <= detected
    assert detected.isdisjoint(news["dids"])
