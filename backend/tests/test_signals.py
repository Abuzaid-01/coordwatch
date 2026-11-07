"""Unit tests for all 4 CoordWatch coordination signals, Louvain graph clustering,
scoring formula, false-positive protection, and synthetic simulator in Python.

Compatible with both `pytest` and `python3 -m unittest backend/tests/test_signals.py -v`.
"""
import unittest
from backend.app.signals.text import compute_text_similarity_signal
from backend.app.signals.timing import compute_timing_sync_signal
from backend.app.signals.age import compute_account_age_signal
from backend.app.signals.links import compute_shared_links_signal
from backend.app.analysis.graph import build_and_partition_graph
from backend.app.analysis.scoring import compute_cluster_score_and_reasons


class TestCoordWatchSignals(unittest.TestCase):
    def test_signal_1_text_similarity(self):
        posts = [
            {
                "did": "did:plc:bot1",
                "created_at": "2026-04-20T12:00:00Z",
                "text_norm": "breaking independent audit proves ai hyperscale data centers are draining municipal grids by 42%",
            },
            {
                "did": "did:plc:bot2",
                "created_at": "2026-04-20T12:00:05Z",
                "text_norm": "breaking independent audit proves ai hyperscale data centers are draining municipal grids by 42%",
            },
            {
                "did": "did:plc:organic1",
                "created_at": "2026-04-20T12:00:10Z",
                "text_norm": "just finished baking sourdough bread this sunday morning",
            },
        ]
        edges = compute_text_similarity_signal(posts, threshold=0.76)
        self.assertEqual(len(edges), 1)
        self.assertEqual(edges[0]["did_a"], "did:plc:bot1")
        self.assertEqual(edges[0]["did_b"], "did:plc:bot2")
        self.assertAlmostEqual(edges[0]["strength"], 1.0, places=2)

    def test_signal_2_temporal_synchronization(self):
        posts = [
            {"did": "did:plc:bot1", "created_at": "2026-04-20T12:00:00Z"},
            {"did": "did:plc:bot2", "created_at": "2026-04-20T12:00:08Z"},
            {"did": "did:plc:organic1", "created_at": "2026-04-20T14:30:00Z"},
        ]
        edges = compute_timing_sync_signal(posts, tight_window_sec=60.0)
        self.assertEqual(len(edges), 1)
        self.assertEqual(edges[0]["did_a"], "did:plc:bot1")
        self.assertEqual(edges[0]["did_b"], "did:plc:bot2")
        self.assertGreater(edges[0]["strength"], 0.85)

    def test_text_similarity_respects_six_hour_window(self):
        sentence = "breaking independent audit proves municipal grids are draining faster than forecast"
        inside = [
            {"did": "did:plc:near1", "created_at": "2026-04-20T12:00:00Z", "text_norm": sentence},
            {"did": "did:plc:near2", "created_at": "2026-04-20T16:30:00Z", "text_norm": sentence},
        ]
        outside = [
            {"did": "did:plc:far1", "created_at": "2026-04-20T12:00:00Z", "text_norm": sentence},
            {"did": "did:plc:far2", "created_at": "2026-04-20T19:30:00Z", "text_norm": sentence},
        ]
        self.assertEqual(len(compute_text_similarity_signal(inside, threshold=0.76)), 1)
        self.assertEqual(compute_text_similarity_signal(outside, threshold=0.76), [])

    def test_signal_3_account_age_clustering(self):
        accounts = [
            {"did": "did:plc:bot1", "created_at": "2026-04-16T10:00:00Z"},
            {"did": "did:plc:bot2", "created_at": "2026-04-16T14:00:00Z"},
            {"did": "did:plc:veteran", "created_at": "2023-08-01T00:00:00Z"},
        ]
        edges = compute_account_age_signal(accounts, max_gap_hours=48.0)
        self.assertEqual(len(edges), 1)
        self.assertEqual(edges[0]["did_a"], "did:plc:bot1")
        self.assertEqual(edges[0]["did_b"], "did:plc:bot2")
        self.assertGreater(edges[0]["strength"], 0.65)

    def test_signal_4_shared_links_and_hashtags(self):
        posts = [
            {
                "did": "did:plc:bot1",
                "links": ["https://grid-truth-alert.org/report"],
                "hashtags": ["#gridtruth", "#energycrisis"],
            },
            {
                "did": "did:plc:bot2",
                "links": ["https://grid-truth-alert.org/report"],
                "hashtags": ["#gridtruth", "#energycrisis"],
            },
        ]
        edges = compute_shared_links_signal(posts)
        self.assertEqual(len(edges), 1)
        self.assertGreaterEqual(edges[0]["strength"], 0.90)

    def test_phase_5_graph_scoring_and_false_positive_protection(self):
        nodes = ["did:plc:org1", "did:plc:org2", "did:plc:org3"]
        edges = [
            {"did_a": "did:plc:org1", "did_b": "did:plc:org2", "weight": 0.62},
            {"did_a": "did:plc:org2", "did_b": "did:plc:org3", "weight": 0.58},
            {"did_a": "did:plc:org1", "did_b": "did:plc:org3", "weight": 0.60},
        ]
        communities = build_and_partition_graph(nodes, edges, min_cluster_size=3)
        self.assertEqual(len(communities), 1)

        # Older organic accounts (>150 days median age, dispersed creation dates) get discount
        scored = compute_cluster_score_and_reasons(
            cluster_dids=communities[0],
            signal_averages={"text": 0.35, "timing": 0.75, "age": 0.05, "links": 0.85},
            cohort_48h_count=0,
            median_age_days=420.0,
            enable_fp_protection=True,
        )
        self.assertGreater(scored["discount_applied"], 0.35)
        self.assertLess(scored["score"], scored["raw_score"])


if __name__ == "__main__":
    unittest.main()
