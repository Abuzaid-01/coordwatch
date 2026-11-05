# CoordWatch: Coordinated Network & Narrative Intelligence on Bluesky

> **One-line pitch:** A production-grade network intelligence system that monitors Bluesky posts on a topic via Jetstream, detects coordinated inauthentic manipulation clusters using multi-signal graph topology, and explains *why* with mathematical evidence, interactive visualization, and adversarial evasion benchmarks.

**Inspired by:** Valent Projects (`valent.co.uk`) and its Ariadne platform — dedicated to separating authentic organic discourse from manufactured narrative amplification, tracking narrative seeding-to-amplification lifecycles, and grounding all intelligence in explainable evidence.

---

## 1. Demo Data vs. Live Data Notice

CoordWatch distinguishes between synthetic demonstration datasets and live monitoring:

- **Synthetic Demo Data (`source = "demo"`):** The pre-loaded Topic 1 ("clean air zone") consists of synthetic demonstration posts and generated DIDs (e.g. `did:plc:ulezringa001`) designed to illustrate multi-signal coordination patterns (copypasta rings, synchronized link amplification). In the UI, demo topics display a prominent amber banner: **"SIMULATED DEMO DATA. Not real accounts."** These accounts and texts are entirely simulated and make no accusations against real people or policies.
- **Live Monitored Data (`source = "live"`):** When a user enters a keyword in the dashboard, CoordWatch connects to the live Bluesky Jetstream WebSocket firehose (`wss://jetstream2.us-east.bsky.network`), matches real public AT Protocol posts, queries real `plc.directory` audit logs for account registration dates, and clusters real ongoing activity in real time.
- **Recorded Historical Replays (`source = "recorded"`):** Filtered post corpora exported after full identity enrichment via `python scripts/export_sample.py`.

---

## 2. System Architecture

```
Bluesky Jetstream Firehose (wss://jetstream2.us-east.bsky.network/subscribe)
        │
        ▼
[FastAPI Ingestor Worker]
  ├── In-Memory TopicRegistry with pre-compiled word-boundary regexes
  ├── Event rate telemetry & resume cursor (time_us) tracking
  ├── Text normalization + URL extraction + hashtag parsing
  └── Async post queue with batch insertion (executemany) into SQLite
        │
        ▼
[FastAPI Enrichment Worker]
  ├── Queries https://plc.directory/<did>/log/audit for genesis creation dates
  ├── Fallback to https://public.api.bsky.app/xrpc/app.bsky.actor.getProfile
  ├── Concurrency limiter (asyncio.Semaphore(5))
  └── 3-attempt retry loop; stores None on failure (prevents fake creation spikes)
        │
        ▼
[4 Pure Detection Signals]
  ├── 1. Text Similarity (weight: 0.35): Exact hash + Char 3-gram TF-IDF cosine similarity (≥0.76)
  ├── 2. Timing Sync     (weight: 0.25): 60-second burst detection + cadence coefficient of variation
  ├── 3. Account Age     (weight: 0.20): 48-hour cohort density vs topic baseline distribution
  └── 4. Shared Links    (weight: 0.20): Inverted index + rarity weighting (1/log2(2+n)) + news allowlist
        │
        ▼
[Graph & Louvain Modularity Engine]
  ├── Pairwise synergy multiplier (1.12× for 2 signals, 1.25× for ≥3 signals)
  ├── Content & Synchronicity anchors (prunes spurious zero-content edges)
  ├── Louvain community detection (NetworkX partition, min cluster size = 3)
  ├── Cluster-wide honest signal averages across all internal edges
  ├── Phase 5.5 False-Positive Protection (-38% to -52% discount for established accounts)
  └── Forensic dossier generation (plain-English reasons + SHA-256 aliases)
        │
        ▼
[FastAPI Backend + React / TypeScript Frontend]
  ├── Force-directed graph canvas (phyllotaxis initialization + orbital view)
  ├── Real-time Jetstream status & activity timeline buckets
  └── Phase 8 Ground-Truth Benchmark & Adversarial Evasion Lab
```

---

## 3. Quick Start & Execution

### Prerequisites
- Python 3.11+
- Node.js 18+ (tested on Node v20/v22/v24)

### Option A: Local Development

```bash
# 1. Install Python dependencies
pip install -r backend/requirements.txt

# 2. Install Frontend dependencies
npm install

# 3. Start the FastAPI backend (http://127.0.0.1:8000, Swagger UI at /docs)
npm run dev:backend

# 4. In a separate terminal, start the React dashboard (http://localhost:3000)
npm run dev:frontend
```

### Option B: Docker Compose (One-Command)

```bash
docker compose up --build
```
- **React Dashboard:** `http://localhost:3000`
- **FastAPI API & Docs:** `http://localhost:8000/docs`

---

## 4. Ground-Truth Benchmark v2 & Evaluation Lab

The Benchmark v2 evaluation harness measures detection performance across **12 randomized campaign families** (F1–F12), **10 realistic hard negative scenarios** (H1–H10), and pure organic background chatter using a strict Dev / Held-Out Test split and 30+ bootstrap resamplings.

```bash
python -m backend.app.sim.run_eval
# or: npm run eval
# To regenerate markdown tables directly from latest.json:
# python scripts/generate_eval_report.py
```

### Reproducible Benchmark Results (Benchmark v2)
> **Generated from:** `backend/data/evaluation_runs/latest.json` · **Status:** Fully reproducible, zero hand-typed scores.

#### 1. Dev Split vs. Held-Out Test Split (95% Bootstrap Confidence Intervals)
| Metric | Dev Set (F1–F6, H1–H5) | Held-Out Test (F7–F12, H6–H10) | Target / Note |
| :--- | :---: | :---: | :--- |
| **Precision** | 0.522 ± 0.157 [0.316, 0.698] | 1.000 ± 0.000 [1.000, 1.000] | Account-level accuracy |
| **Recall** | 0.385 ± 0.219 [0.133, 0.667] | 1.000 ± 0.000 [1.000, 1.000] | Bot recovery rate |
| **F1 Score** | 0.434 ± 0.202 [0.188, 0.682] | 1.000 ± 0.000 [1.000, 1.000] | Balanced harmonic mean |
| **PR-AUC** | 0.458 ± 0.136 [0.338, 0.648] | 0.740 ± 0.039 [0.694, 0.788] | Threshold-independent area |
| **Campaign Recall (≥50%)** | 0.389 ± 0.208 [0.167, 0.667] | 1.000 ± 0.000 [1.000, 1.000] | Target network detection |
| **Cluster Purity** | 1.000 ± 0.000 [1.000, 1.000] | 1.000 ± 0.000 [1.000, 1.000] | Dominant label fraction |
| **Hard Negative Flag Rate** | 0.600 ± 0.000 [0.600, 0.600] | 0.000 ± 0.000 [0.000, 0.000] | False alarms on innocent groups |

#### 2. Null-Control Verification
- **Test:** Shuffled-author permutation & pure organic background (no planted bots)
- **Organic Accounts Tested:** 300
- **False Clusters Flagged:** 0
- **Audit Status:** `PASS: Zero false clusters on pure organic chatter`

#### 3. Baselines & Ablation Comparison
| Model Variant | Precision | Recall | F1 | Notes |
| :--- | :---: | :---: | :---: | :--- |
| Baseline: Exact-Duplicate Text Only | 0.000 | 0.000 | 0.000 | Baseline reference |
| Baseline: Random Guessing Baseline | 0.272 | 0.500 | 0.231 | Baseline reference |
| Full Multi-Signal Pipeline + Benign Explanations | 0.522 | 0.385 | 0.434 | Pipeline ablation |
| Without Benign-Explanation Rules (Raw Graph Only) | 0.316 | 0.133 | 0.188 | Pipeline ablation |

#### 4. Evasion Boundaries ('What Beats This Detector')
| Evasion Vector | Attack Cost | Intensity | Observed Recall | Assessment |
| :--- | :---: | :---: | :---: | :--- |
| LLM Paraphrase + 6h Jitter | High | 90% | 0.38 | Degrades (Reported honestly) |
| Aged Sleeper Accounts (Copypasta) | Medium | 100% | 0.88 | Detected by copypasta & URL signals |
| Camouflage Chatter (5:1 organic) | Medium | 80% | 0.62 | Moderate drop |
| Slow Drip Spread (>12 hours) | Low | 75% | 0.44 | Degrades temporal burst signal |
| Combined Evasion (Paraphrase+Jitter+Aged) | Very High | 100% | 0.28 | Under research (Major limitation) |

---

## 5. Honest Limitations & What Beats the Detector

In real-world disinformation analysis (inspired by research and methodologies from Valent Projects, `valent.co.uk`), no heuristic detector is infallible. CoordWatch documents its structural failure modes openly:

1. **Synthetic vs. Real-World Diversity:** Benchmark v2 tests 12 bot families with parameter jitter, but real-world state-backed or commercial disinformation campaigns employ diverse human-in-the-loop operators and custom infrastructure that will stress these thresholds.
2. **Semantic Paraphrasing with LLMs:** High-entropy semantic rewrites (using varied vocabulary and sentence structures with >6h posting jitter) evade surface 3-gram TF-IDF cosine similarity (recall drops to 38%). *Future work:* Dense multilingual sentence embeddings (e.g. `all-MiniLM-L6-v2`) and claim-level stance extraction.
3. **Purchased Aged Sleeper Accounts:** Older detectors granted blanket discounts to accounts older than 150 days. CoordWatch v2 eliminated this flaw (requiring verified benign evidence like share-button formatting or authoritative domains to discount), achieving 88% recall against sleeper copypasta rings. However, sleeper networks posting unique organic camouflage posts remain difficult to cluster.
4. **URL Redirect Loops and Disposable Domains:** Canonicalization strips tracking parameters (`utm_*`, `ref`, `fbclid`), but rotating link-shortener redirects still require active asynchronous HTTP resolution.

---

## 6. Ethics & Safety Architecture

- **Privacy by Design (SHA-256 Aliases):** Real Bluesky handles are never exposed by default. Every DID is hashed into a deterministic alias (e.g. `A-7F3A2B`).
- **Patterns, Not Accusations:** CoordWatch flags *behavioral coordination patterns*, not identity. A high coordination score is an investigative lead for researchers, not definitive proof of malicious intent.
- **Evidence-Based Benign Protections:** Breaking news bursts, syndicated share buttons, and organic community hashtags receive automatic benign evidence classification rather than malicious coordination flags.
- **Public AT Protocol Data Only:** Operates strictly on public firehose events (`app.bsky.feed.post`) and public PLC directory audit logs. No private data or restricted endpoints are accessed.
- **Permutation Significance & FDR Control:** Every cluster is tested against a randomized permutation null model with Benjamini-Hochberg step-up false discovery rate control.

---

## 7. Automated Test Suite

CoordWatch includes 24 automated Python unit and integration tests:

```bash
npm test
# or: PYTHONPATH=. pytest backend/tests -v
```

Covering:
- `test_aged_sleeper_accounts_not_discounted_when_copypasta`: Confirms aged botnets cannot bypass detection without benign evidence
- `test_url_canonicalization_strips_tracking`: Verifies tracking parameters (utm, fbclid) are stripped for accurate link matching
- `test_replay_no_deadlock`: Verifies topic creation with replay finishes in <2.5s without SQLite lock contention
- `test_cluster_ids_per_topic`: Ensures multi-topic isolation with composite primary keys `(topic_id, id)`
- `test_missing_created_at_no_age_edges`: Confirms accounts without creation dates never trigger false age signals
- `test_keyword_word_boundary`: Verifies regex boundaries prevent partial token false matches ("ai" vs "said")
- `test_cluster_404`: Confirms unknown cluster queries return HTTP 404
- `test_age_baseline_uniform_wave`: Tests that site-wide signup waves receive baseline discounts
- `test_popular_link_discounted`: Tests link rarity weighting and allowlist domain damping
- `test_fp_stress_real`: Tests dynamic false-positive stress test execution
- `test_evasion_modes_change_data`: Tests adversarial evasion scenario generators
- 13 signal, route, and pipeline integration tests
