# CoordWatch: Coordinated Network & Narrative Intelligence on Bluesky

> **One-line pitch:** A research prototype that watches public Bluesky posts for a keyword, groups accounts that post like a coordinated network, and shows the evidence. The score is a lead for a person. It is not a production intelligence system.

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
  ├── News-burst rule: an aged cohort sharing an allowlisted headline is benign before the hard-coordination check
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

## 4. Measured benchmark

Dev and test use the same 12 families and all 10 hard negatives. The seeds differ: dev is 42–51, test is 142–151. An account counts as a detection only when it sits in a cluster labeled `coordinated_inauthentic` with score at least 50.

The previous tables in this section reported perfect held-out recall. That split reused easy copy-paste families and the recalls were not measured by this detector. Those figures are withdrawn.

```bash
PYTHONPATH=. python3 -m backend.app.sim.run_eval
PYTHONPATH=. python3 scripts/generate_eval_report.py
```

The block below is the script output from that published run. The runner also prints true positives and false positives. Those two counts are the first dev seed. The means are in the table.

### Measured benchmark
> **Generated from:** `backend/data/evaluation_runs/latest.json` · **Git commit:** `a023456-dirty` · **Computed:** `2026-11-09 14:44:40 UTC`
> **Label:** `published` · **Split:** same 12 families and all 10 hard negatives; dev and test differ by seed
> **Dev seeds:** `[42, 43, 44, 45, 46, 47, 48, 49, 50, 51]` · **Test seeds:** `[142, 143, 144, 145, 146, 147, 148, 149, 150, 151]` · **Organic per seed:** `200` · **Permutations:** `200`

#### Dev seeds and unseen seeds
| Metric | Dev seeds | Unseen seeds | Note |
| :--- | :---: | :---: | :--- |
| **Precision** | 0.935 ± 0.045 [0.907, 0.964] | 0.869 ± 0.063 [0.823, 0.902] | Account-level |
| **Recall** | 0.534 ± 0.182 [0.410, 0.632] | 0.472 ± 0.152 [0.378, 0.570] | Planted bots flagged |
| **F1** | 0.657 ± 0.182 [0.522, 0.746] | 0.602 ± 0.141 [0.512, 0.692] | Harmonic mean |
| **PR-AUC** | 0.742 ± 0.079 [0.693, 0.785] | 0.673 ± 0.104 [0.608, 0.733] | Outside an inauthentic cluster scores 0 |
| **Campaign recall** | 0.525 ± 0.179 [0.408, 0.617] | 0.467 ± 0.155 [0.375, 0.567] | At least half the members flagged |
| **Cluster purity** | 1.000 ± 0.000 [1.000, 1.000] | 1.000 ± 0.000 [1.000, 1.000] | n/a when no inauthentic cluster |
| **Hard-negative flag rate** | 0.070 ± 0.046 [0.040, 0.100] | 0.110 ± 0.030 [0.100, 0.130] | Scenarios with any inauthentic member |
| **Organic FP per 1,000** | 0.000 ± 0.000 [0.000, 0.000] | 0.000 ± 0.000 [0.000, 0.000] | Hard negatives are not in this rate |

#### Null control
- **Organic accounts:** 120
- **Inauthentic clusters:** 0
- **Organic false positives:** 0
- **Shuffled-author campaign recall:** 0.0
- **Status:** `PASS`

#### Baselines and ablation
| Variant | Precision | Recall | F1 |
| :--- | :---: | :---: | :---: |
| Exact-duplicate text, three accounts inside 6h | 0.404 | 0.832 | 0.544 |
| Seeded coin-flip at 0.5 | 0.383 | 0.526 | 0.443 |
| Full pipeline with benign news rule | 0.935 | 0.534 | 0.657 |
| Same seeds with benign news rule off | 0.775 | 0.543 | 0.626 |

#### Measured evasion
| Evasion | Family | Seed | Organic | Permutations | Observed recall |
| :--- | :---: | :---: | :---: | :---: | :---: |
| Paraphrase plus 6h jitter | F3 | 42 | 80 | 50 | 0.000 |
| Aged sleeper copypasta | F7 | 42 | 80 | 50 | 1.000 |
| Camouflage chatter | F10 | 42 | 80 | 50 | 1.000 |
| Slow drip over 12h | F8 | 42 | 80 | 50 | 0.000 |
| Paraphrase plus jitter plus aged accounts | F7 | 42 | 80 | 50 | 0.000 |
| Paraphrase plus 6h jitter | F3 | 43 | 80 | 50 | 1.000 |
| Aged sleeper copypasta | F7 | 43 | 80 | 50 | 1.000 |
| Camouflage chatter | F10 | 43 | 80 | 50 | 1.000 |
| Slow drip over 12h | F8 | 43 | 80 | 50 | 0.000 |
| Paraphrase plus jitter plus aged accounts | F7 | 43 | 80 | 50 | 0.000 |
| Paraphrase plus 6h jitter | F3 | 44 | 80 | 50 | 1.000 |
| Aged sleeper copypasta | F7 | 44 | 80 | 50 | 1.000 |
| Camouflage chatter | F10 | 44 | 80 | 50 | 1.000 |
| Slow drip over 12h | F8 | 44 | 80 | 50 | 0.000 |
| Paraphrase plus jitter plus aged accounts | F7 | 44 | 80 | 50 | 0.000 |
| Paraphrase plus 6h jitter | F3 | 45 | 80 | 50 | 0.000 |
| Aged sleeper copypasta | F7 | 45 | 80 | 50 | 1.000 |
| Camouflage chatter | F10 | 45 | 80 | 50 | 1.000 |
| Slow drip over 12h | F8 | 45 | 80 | 50 | 0.000 |
| Paraphrase plus jitter plus aged accounts | F7 | 45 | 80 | 50 | 0.000 |
| Paraphrase plus 6h jitter | F3 | 46 | 80 | 50 | 1.000 |
| Aged sleeper copypasta | F7 | 46 | 80 | 50 | 1.000 |
| Camouflage chatter | F10 | 46 | 80 | 50 | 1.000 |
| Slow drip over 12h | F8 | 46 | 80 | 50 | 0.000 |
| Paraphrase plus jitter plus aged accounts | F7 | 46 | 80 | 50 | 1.000 |
| Paraphrase plus 6h jitter | F3 | 47 | 80 | 50 | 0.000 |
| Aged sleeper copypasta | F7 | 47 | 80 | 50 | 1.000 |
| Camouflage chatter | F10 | 47 | 80 | 50 | 1.000 |
| Slow drip over 12h | F8 | 47 | 80 | 50 | 0.000 |
| Paraphrase plus jitter plus aged accounts | F7 | 47 | 80 | 50 | 0.000 |
| Paraphrase plus 6h jitter | F3 | 48 | 80 | 50 | 1.000 |
| Aged sleeper copypasta | F7 | 48 | 80 | 50 | 1.000 |
| Camouflage chatter | F10 | 48 | 80 | 50 | 1.000 |
| Slow drip over 12h | F8 | 48 | 80 | 50 | 0.000 |
| Paraphrase plus jitter plus aged accounts | F7 | 48 | 80 | 50 | 0.000 |
| Paraphrase plus 6h jitter | F3 | 49 | 80 | 50 | 1.000 |
| Aged sleeper copypasta | F7 | 49 | 80 | 50 | 1.000 |
| Camouflage chatter | F10 | 49 | 80 | 50 | 1.000 |
| Slow drip over 12h | F8 | 49 | 80 | 50 | 0.000 |
| Paraphrase plus jitter plus aged accounts | F7 | 49 | 80 | 50 | 0.000 |
| Paraphrase plus 6h jitter | F3 | 50 | 80 | 50 | 1.000 |
| Aged sleeper copypasta | F7 | 50 | 80 | 50 | 1.000 |
| Camouflage chatter | F10 | 50 | 80 | 50 | 1.000 |
| Slow drip over 12h | F8 | 50 | 80 | 50 | 0.000 |
| Paraphrase plus jitter plus aged accounts | F7 | 50 | 80 | 50 | 0.000 |
| Paraphrase plus 6h jitter | F3 | 51 | 80 | 50 | 0.000 |
| Aged sleeper copypasta | F7 | 51 | 80 | 50 | 1.000 |
| Camouflage chatter | F10 | 51 | 80 | 50 | 1.000 |
| Slow drip over 12h | F8 | 51 | 80 | 50 | 0.000 |
| Paraphrase plus jitter plus aged accounts | F7 | 51 | 80 | 50 | 0.000 |

#### News-burst stress
- **Accounts in the burst:** 65
- **Inauthentic with the news rule off:** 65
- **Inauthentic with the news rule on:** 0

#### Limitations recorded with this run
- Character 3-gram similarity misses a rewrite that shares little surface form with the source sentence.
- Aged accounts that copy an allowlisted headline are classified as news sharing.
- The ingestor reads the public post firehose in one process and filters keywords locally.
- Account creation time comes from plc.directory, with getProfile as the fallback. A failed lookup stores no creation time.
- A confidence interval is published only when at least 10 seeds were run.

The lab button runs a smaller sample (two seeds, at most 80 organic accounts, 50 permutations). It does not replace the published run.

---

## 5. Limits of this prototype

1. Character 3-gram similarity misses a rewrite that shares little surface form with the source sentence.
2. Aged accounts that copy an allowlisted headline are classified as news sharing.
3. One process reads the public post firehose and filters keywords locally.
4. A failed plc.directory lookup stores no account creation time.
5. A confidence interval is published only when at least 10 seeds were run.

---

## 6. Ethics & Safety Architecture

- **Privacy by Design (SHA-256 Aliases):** Real Bluesky handles are never exposed by default. Every DID is hashed into a deterministic alias (e.g. `A-7F3A2B`).
- **Patterns, Not Accusations:** CoordWatch flags *behavioral coordination patterns*, not identity. A high coordination score is an investigative lead for researchers, not definitive proof of malicious intent.
- **Evidence-Based Benign Protections:** Breaking news bursts, syndicated share buttons, and organic community hashtags receive automatic benign evidence classification rather than malicious coordination flags.
- **Public AT Protocol Data Only:** Operates strictly on public firehose events (`app.bsky.feed.post`) and public PLC directory audit logs. No private data or restricted endpoints are accessed.
- **Permutation Significance & FDR Control:** Every cluster is tested against a randomized permutation null model with Benjamini-Hochberg step-up false discovery rate control.

---

## 7. Automated Test Suite

CoordWatch includes a Python unit and integration suite. It does not run the published 10-seed benchmark:

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
