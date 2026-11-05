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

## 4. Ground-Truth Evaluation Benchmark (Phase 8)

The offline benchmark measures precision, recall, and F1 across repeated random seeds against 500 independent organic accounts and 3 planted bot networks (56 bot accounts total):

```bash
python -m backend.app.sim.run_eval
# or: npm run eval
```

### Measured Benchmark Results (Seeds: 42, 43, 44 | Date: November 2026)

| Metric | Measured Value | Standard Deviation | Notes |
|---|---|---|---|
| **Precision** | **1.000** | ±0.000 | 0 false positive detections among organic accounts |
| **Recall** | **1.000** | ±0.000 | 56 of 56 planted bots detected across all 3 networks |
| **F1 Score** | **1.000** | ±0.000 | Balanced harmonic mean on baseline synthetic scenario |
| **True Positives** | **56 / 56** | — | Alpha (24), Beta (18), Gamma (14) all partitioned |
| **False Positives** | **0 / 500** | — | Organic template-generated commentary unflagged |

### Real False-Positive Stress Test (Breaking News Burst)
When 65 established organic accounts (median age >300 days) burst-shared the exact same official TfL/BBC news link within a 4-minute window:
- **Without False-Positive Protection:** 65 / 65 accounts (100.0%) were flagged as a high-risk cluster.
- **With Phase 5.5 False-Positive Protection:** **0 / 65 accounts (0.0%)** were flagged. The system detected the dispersed creation dates and applied the news-burst discount, suppressing the false alarm.

### Adversarial Evasion Sweeps
Rather than mathematical formulas, evasion curves are generated by actually applying perturbation operators and executing the full detection pipeline:
1. **Text Paraphrase:** Bots reword content with probability $x$. F1 degrades gracefully as lexical overlap drops.
2. **Timing Delay:** Bots spread posts across an expanded window ($42\text{s} + x \times 9600\text{s}$).
3. **Age Spread:** Bots use pre-aged sleeper accounts with staggered registration dates.
4. **Link Rotation:** Bots post unique mirror domains to evade naive URL matching.

---

## 5. Honest Limitations & What Beats the Detector

Valent's operational experience proves that no heuristic detector is infallible. CoordWatch documents its structural failure modes openly:

1. **Planted Bots are Easy by Design:** The simulator's planted bots exhibit patterns designed to test our four specific hypotheses. Real-world adversaries use mixed tactics, compromised credentials, and human-in-the-loop coordination that may not trigger these thresholds.
2. **Semantic Paraphrasing with LLMs:** High-entropy semantic rewrites (using varied vocabulary and sentence structures) evade character 3-gram TF-IDF cosine similarity. *Future work:* Dense sentence transformer embeddings (e.g. `all-MiniLM-L6-v2`) and claim-level stance extraction.
3. **Dormant / Purchased Sleeper Accounts:** `plc.directory` audit logs establish when an AT Protocol DID was first created, but cannot detect when an old account was bought, sold, or activated after months of dormancy. *Future work:* Measure "dormancy-to-burst activation gap" rather than genesis timestamp alone.
4. **Link Shorteners and Redirect Loops:** Rotating destination URLs across disposable domains bypasses surface URL matching without active headless HTTP redirect resolution.

---

## 6. Ethics & Safety Architecture

- **Privacy by Design (SHA-256 Aliases):** Real Bluesky handles are never exposed by default. Every DID is hashed into a deterministic alias (e.g. `A-7F3A2B`).
- **Patterns, Not Accusations:** CoordWatch flags *behavioral coordination patterns*, not identity. A high coordination score is an investigative lead for researchers, not definitive proof of malicious intent.
- **Public AT Protocol Data Only:** Operates strictly on public firehose events (`app.bsky.feed.post`) and public PLC directory audit logs. No private data or restricted endpoints are accessed.
- **Transparent Evidence Dossiers:** Every detected cluster presents the exact mathematical signal contributions and top shared phrases so researchers can inspect the reasoning.

---

## 7. Automated Test Suite

CoordWatch includes 22 automated Python unit and integration tests:

```bash
npm test
# or: PYTHONPATH=. pytest backend/tests -v
```

Covering:
- `test_replay_no_deadlock`: Verifies topic creation with replay finishes in <2.5s without SQLite lock contention
- `test_cluster_ids_per_topic`: Ensures multi-topic isolation with composite primary keys `(topic_id, id)`
- `test_missing_created_at_no_age_edges`: Confirms accounts without creation dates never trigger false age signals
- `test_keyword_word_boundary`: Verifies regex boundaries prevent partial token false matches ("ai" vs "said")
- `test_cluster_404`: Confirms unknown cluster queries return HTTP 404
- `test_age_baseline_uniform_wave`: Tests that site-wide signup waves receive baseline discounts
- `test_popular_link_discounted`: Tests link rarity weighting and allowlist domain damping
- `test_fp_stress_real`: Tests dynamic false-positive stress test execution
- `test_evasion_modes_change_data`: Tests adversarial evasion scenario generators
- 13 existing signal, route, and pipeline integration tests
