/

# CoordWatch improvement implementation plan

This is the plan for fixing the current prototype. The original build plan (`../coordwatch_implementation_plan.md`) describes how the project was created. This file describes what is wrong now and the exact work that makes it honest, consistent, and safe to show.

Read this top to bottom. Implement the phases in order. Do not start Phase 4 until Phases 1–3 are merged, because the benchmark must measure the fixed detector.

**What this project is:** a prototype that watches public Bluesky posts for a keyword, groups accounts that behave like a coordinated network, and shows the evidence. It is a research demo. It is not a production intelligence platform, and the README must say that after Phase 6.

**Rule for every change:** a number in the README, the Evaluation Lab, or `latest.json` comes from a function that ran the detector. If a mode is not implemented, leave the row out. Do not type a recall, a p-value, or a confidence interval by hand.

---

## How to use this file

1. Pick the next phase that is not checked off in the status table.
2. Read that phase only. Each phase lists the files, the bug, the change, and the test that proves it.
3. Keep the diff inside that phase. Do not retune weights, rename the UI, or add embeddings in the same change.
4. Run the tests named in that phase before moving on.
5. After Phase 4, regenerate the report with the script. Paste the script output into the README. Do not edit the digits.

Suggested branch per phase: `fix/text-pipeline`, `fix/benign-news`, `fix/significance`, `fix/benchmark`, `fix/persist-ui`, `fix/run-and-readme`.

---

## Status


| Phase | Name                                      | Depends on  | Status                                      |
| ------- | ------------------------------------------- | ------------- | --------------------------------------------- |
| 1     | One text and URL pipeline                 | none        | done                                        |
| 2     | Benign news sharing                       | Phase 1     | done                                        |
| 3     | Real significance, and save the decision  | Phase 2     | done                                        |
| 4     | Honest benchmark                          | Phases 1–3 | done                                        |
| 5     | Dashboard shows the saved decision        | Phase 3     | done                                        |
| 6     | One database, a working Docker UI, README | Phases 4–5 | done                                        |
| 7     | Scale follow-ups                          | Phase 6     | done                                        |

---

## Phase 1 — One text and URL pipeline

### Problem

Live posts, the demo seed, replayed JSONL, and the simulator each prepare text and links differently. The benchmark therefore measures a different detector from the one the dashboard runs.

Evidence:

- `backend/app/ingest/jetstream.py` `normalize_text()` lowercases text, strips URLs, strips mentions, and collapses spaces. Only the live ingestor calls it (around the insert path near line 280).
- `backend/app/db.py` `_ensure_seed_dataset()` stores `text_norm` as `ev["text"].lower().strip()`. Shared URLs stay inside the demo text, so character 3-gram similarity treats a shared link as shared wording.
- `backend/app/sim/families.py`, `hard_negatives.py`, and `organic.py` set `text_norm` themselves, usually `post_text.lower().strip()`.
- `extract_links()` returns hosts with the scheme removed (`bbc.co.uk/news/...`).
- `backend/app/signals/links.py` `canonicalize_url()` uses `urllib.parse.urlparse`. A string with no scheme is parsed as a path, so the host is lost. Simulated posts keep `https://...`, so link matching works in the benchmark and breaks on live posts.
- Demo aliases use the last six characters of the DID (`db.py` seed insert). Live aliases use SHA-256 via `generate_hash_alias()`. The same account can show two aliases.

### Solution

Add `backend/app/textutil.py` with three functions, and make every writer call them.

`prepare_text(text) -> str`

- Move the body of `normalize_text()` here.
- `jetstream.normalize_text` becomes a one-line wrapper so existing imports keep working.

`canonicalize_url(url) -> str`

- Move the current function out of `signals/links.py`.
- If `urlparse` finds no netloc, and the string contains a dot, prepend `https://` and parse again.
- Then apply the existing tracking-parameter strip (`utm_*`, `fbclid`, `gclid`, `ref`, and the rest of `TRACKING_PARAMS`).
- Return a full URL: scheme, host without `www.`, path, cleaned query. Empty input returns `""`.

`prepare_post(text) -> {text_norm, links, hashtags}`

- `text_norm = prepare_text(text)`.
- `links` is the list of `canonicalize_url()` results from the raw text, duplicates removed.
- `hashtags` is the existing hashtag extractor, stored without a leading `#`, lowercased.

Call `prepare_post` from:

- the Jetstream insert path
- `_ensure_seed_dataset`
- `_replay_jsonl_for_topic`
- `generate_bot_family`, `generate_hard_negative`, and `generate_organic_background` (set `text_norm`, `links`, and `hashtags` from the raw `text` only)

Call `generate_hash_alias()` for every account insert, including the demo seed. Delete the `A-{did[-6:]}` fallback in the seed writer. Display fallbacks in the API may stay for old rows already in the database.

`signals/links.py` imports `canonicalize_url` from `textutil.py`. Do not keep a second copy.

### Tests

Add `backend/tests/test_textutil.py`:

- `"Hello https://evil.example/a?utm_source=x"` normalizes to `"hello"` and canonicalizes to `https://evil.example/a`.
- `"https://bbc.co.uk/news/1?utm_campaign=a"` and `"bbc.co.uk/news/1?fbclid=z"` canonicalize to the same string.
- A demo-seed event and a live-shaped event with the same raw text produce the same `text_norm` and the same `links`.
- Two calls to `generate_hash_alias("did:plc:abc")` return the same `A-` plus 6 hex characters, and that value is what the seed writer stores.

### Done when

A copied headline plus a tracked BBC URL has the same normalized text and the same canonical link whether it arrived from Jetstream, the demo seed, or the simulator.

---

## Phase 2 — Benign news sharing

### Problem

`backend/app/analysis/scoring.py` treats high text similarity as proof of inauthentic coordination before it looks at the news exception.

```python
is_hard_coordinated = (t_sig >= 0.48 and s_sig >= 0.40) or (t_sig >= 0.65)
if is_hard_coordinated:
    discount = 0.0
    classification = "coordinated_inauthentic"
elif enable_fp_protection:
    # authoritative-domain discount is only reachable here
```

Hard negative H1 in `backend/app/sim/hard_negatives.py` is the case this discount was written for: the same BBC headline, the same `bbc.co.uk` link, a three-minute burst, accounts created 200–900 days ago. Identical text sets `t_sig` near 1.0, so the function returns `coordinated_inauthentic` and the discount never runs. That is why the dev hard-negative flag rate is 0.60.

The other benign checks (open hashtag with low text similarity, burst timing with diverse wording) can stay. They already sit behind the hard-coordination branch and they match low-text cases.

### Solution

Decide the news-burst case first.

A cluster is a **news burst** when all of these are true:

- `enable_fp_protection` is true
- at least one link host is in the authoritative set already listed in `scoring.py` (`bbc.co.uk`, `bbc.com`, `reuters.com`, `theguardian.com`, `gov.uk`, and the rest of that set)
- `median_age_days > 120`
- `cohort_48h_count / cluster_size < 0.35` (creation dates are spread out, so this is an established population)
- `t_sig >= 0.30` (the shared headline is allowed to be identical)

For a news burst:

- `classification = "coordinated_benign"`
- `discount = 0.45`
- `discount_reason` names the matched domain and says the accounts have spread creation dates

Then keep the existing hard-coordination branch for everything else:

- fresh accounts that copy each other stay `coordinated_inauthentic` even if they attach a BBC link, because `cohort_ratio` is high or the median age is low
- aged accounts that copy a **non-allowlist** campaign URL stay `coordinated_inauthentic` (this is family F7, the sleeper copypasta)

Move the allowlist to `backend/app/textutil.py` as `AUTHORITATIVE_DOMAINS` and import it from `scoring.py` and `signals/links.py`, so the news rule and the link-rarity rule share one set.

Document this limit in the function docstring, in one sentence: an aged network that copies an allowlisted headline is classified as news sharing. That is a remaining evasion, and Phase 4 must report it as a measured row only if a generator exists for it. Do not invent a recall for it.

### Tests

Add cases to `backend/tests/test_improvements.py`:


| Fixture                                                                                                                                       | Expected `classification`                            |
| ----------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------ |
| H1 shape: identical headline, `https://bbc.co.uk/...`, median age about 400 days, creation dates spread over months, posts inside 180 seconds | `coordinated_benign`, `discount_applied == 0.45`     |
| F7 shape: identical copypasta, `https://cleanair-truth-london.org/dossier`, accounts older than 180 days                                      | `coordinated_inauthentic`, `discount_applied == 0.0` |
| Fresh batch: identical text, BBC link, all accounts created inside 24 hours                                                                   | `coordinated_inauthentic`                            |
| Existing open-hashtag case (`links` high, `text` under 0.25)                                                                                  | still `coordinated_benign`                           |

Build these fixtures by calling `compute_cluster_score_and_reasons` with explicit signal averages and post dicts. Phase 2 does not need a full graph run.

### Done when

The H1 fixture is benign, the aged non-allowlist copypasta fixture is inauthentic, and a brand-new BBC-link batch is inauthentic.

---

## Phase 3 — Real significance, and save the decision

### Problem A — the p-value uses the wrong score

`backend/app/analysis/engine.py` calls `compute_cluster_significance` before `raw_score` exists for this cluster:

```python
cluster_score=raw_score if "raw_score" in locals() else 50.0
```

The first cluster is tested at 50. Every later cluster is tested at the previous cluster's score. `raw_score` is assigned a few lines later from `scored["raw_score"]`.

Inside `backend/app/analysis/significance.py`:

- `combined_obs = obs_stat + (cluster_score * 0.1)` is computed and never compared. The p-value uses `obs_stat` only. The score argument currently does not affect the result, which hides the bug and also means the argument is misleading.
- When there are fewer parsed timestamps than cluster members, the function returns `p_value = 0.05` and `significant = True` without shuffling anything.

### Problem B — FDR does not change a decision

`apply_benjamini_hochberg_fdr` writes `fdr_q_value` and `fdr_significant`. Nothing reads them. A cluster that fails the false-discovery check is still returned, saved, and counted.

### Problem C — the decision is thrown away

`analyze_and_persist_topic` inserts score, signals, and reasons. It does not insert `classification`, `significance`, or `benign_checks`. `get_stored_clusters` does not return them. `src/components/ClusterInspector.tsx` then invents the label:

```tsx
cluster.classification || (score >= 60 ? 'coordinated_inauthentic' : score >= 40 ? 'coordinated_benign' : 'organic')
```

The Evaluation Lab, which calls the engine in memory, sees the real class. The dashboard sees a score band.

`Base.metadata.create_all` will not add columns to a database that already exists.

### Solution

**Order in `run_topic_analysis`:**

1. Call `compute_cluster_score_and_reasons` with `empirical_p_value=None`.
2. Call `compute_cluster_significance` with `cluster_score=scored["raw_score"]`.
3. Append the p-value sentence from `sig_result` after scoring returns.
4. Delete the `raw_score if "raw_score" in locals()` expression completely.

**`compute_cluster_significance` return shape:**

```text
{
  "p_value": float or null,
  "status": "tested" or "not_tested",
  "stat_observed": float,
  "stat_null_mean": float,
  "stat_null_std": float,
  "n_permutations": int,
  "significant": bool
}
```

- The test statistic is the count of cross-account post pairs inside the cluster whose timestamps fall within 90 seconds. Compare that count with the shuffled-author null. Delete `combined_obs`.
- If the test cannot run (fewer than 2 members, fewer than 2 timed posts, or fewer timestamps than members), return `status: "not_tested"`, `p_value: null`, `significant: false`. Do not substitute 0.05 or 0.50.
- Live analysis keeps `n_permutations=50`. The benchmark in Phase 4 passes `n_permutations=200`. The UI must show the permutation count next to the p-value.

**FDR:**

- Run `apply_benjamini_hochberg_fdr` only over clusters whose `status == "tested"`.
- A cluster with `fdr_significant == false`, or `status == "not_tested"`, keeps its evidence payload and changes `classification` to `insufficient_evidence` when the previous class was `coordinated_inauthentic`.
- `coordinated_benign` stays benign. FDR is about the inauthentic claim.
- Benchmark detection (Phase 4) counts an account only when it sits in a cluster with `classification == "coordinated_inauthentic"` and `score >= 50`.

**Schema.** Add a `migrate_schema(conn)` in `backend/app/db.py`, called from `init_db` after `create_all`:

```sql
ALTER TABLE clusters ADD COLUMN classification TEXT NOT NULL DEFAULT 'insufficient_evidence';
ALTER TABLE clusters ADD COLUMN significance_json TEXT NOT NULL DEFAULT '{}';
ALTER TABLE clusters ADD COLUMN benign_checks_json TEXT NOT NULL DEFAULT '{}';
```

Catch "duplicate column" and continue. Update `models.py` `Cluster` so the ORM description matches. Persist all three fields in `analyze_and_persist_topic`. Return them from `get_stored_clusters` as `classification`, `significance`, and `benignChecks`.

### Tests

- Two hand-built clusters in one `run_topic_analysis` call, with different raw scores. Spy on `compute_cluster_significance` (or wrap it) and assert each call receives that cluster's own `raw_score`, never `50.0` from a missing variable.
- A cluster with no parseable timestamps returns `status == "not_tested"` and `p_value is None`.
- A tiny copypasta burst of 4 accounts inside 30 seconds, plus 20 unrelated posts spread over a day, returns `status == "tested"` and `p_value < 0.05` at 200 permutations.
- After `analyze_and_persist_topic`, `GET /clusters/{id}?topicId=` returns the same `classification` the engine produced.
- An inauthentic cluster whose q-value is above 0.05 is stored as `insufficient_evidence`.

### Done when

The p-value describes this cluster, a missing test is labeled `not_tested`, and the dashboard API returns the class the engine chose.

---

## Phase 4 — Honest benchmark

### Problem

`backend/app/sim/benchmark_v2.py` and the README disagree with the detector.

Published dev F1 is about 0.43. Published held-out precision, recall, and F1 are 1.00 with a confidence interval of `[1.000, 1.000]`. The split causes that:

- Dev families F1–F6 include templates, paraphrase, varied hashtag text, and mutated links.
- Test families F7–F12 are mostly the same sentence, the same URL, and the same hashtag (`families.py` branches F7, F9, F10, F11, F12).
- Hard negatives H1–H5 are scored on dev. H6–H10 are scored on test. The two flag rates are not comparable.
- The bootstrap resamples 3 seed-level means (often `[42, 43, 44]` via `simulator.py`) 1,000 times. Three identical easy runs produce a zero-width interval. The README calls this 30+ resamplings.

Hand-typed or broken comparisons in `run_benchmark_v2_suite`:

- `evasionBoundaries` is a Python list with fixed recalls `0.38`, `0.88`, `0.62`, `0.44`, `0.28`. `scripts/generate_eval_report.py` copies that list and its own docstring says the numbers are not hand-typed.
- `random_baseline` sets recall to `0.50` and computes F1 from `0.15`, which is a third number.
- `exact_duplicate_only` keeps full-pipeline clusters whose average text signal is at least 0.90. The published result is 0.00 / 0.00 / 0.00, so the table compares the pipeline with a detector that found nothing.
- The ablation runs `enable_fp_protection=False` on the last seed only, then compares it with the mean of all seeds. Recall moves the wrong way, and `fp_per_1000` stays 130 for both rows.
- `compute_account_metrics` divides false positives by `organic_count` only. Hard-negative accounts are in the numerator and outside the denominator, so `fp_per_1000` can read 130 while the pure-organic null flags nothing.
- `compute_cluster_purity` returns `1.0` when `clusters` is empty.

`backend/tests/test_signals.py` `test_phase_8_simulator_precision_recall` calls `run_full_evaluation_suite()` and requires precision at least 0.85 and recall at least 0.80. That test freezes the easy simulator and will fail the moment the benchmark tells the truth. It also makes the unit suite run the entire eval.

### Solution

**One scenario builder.** `build_scenario_v2` takes a seed and always plants all 12 families and all 10 hard negatives. Dev and test differ by seed, not by family id.

- Published dev seeds: `42` through `51` (10 seeds).
- Published test seeds: `142` through `151`.
- Unit tests do not call this builder. They use the small fixtures from Phases 2 and 3.

There is no "held-out family" claim. The report label is "same families, unseen seeds."

**Who counts as a detection.** An account is flagged only if it is a member of a cluster with `classification == "coordinated_inauthentic"` and `score >= 50`. Benign and `insufficient_evidence` clusters are shown in the UI and excluded from precision and recall.

**Account metrics** in `backend/app/sim/metrics.py`:

- `tp` = flagged accounts that are planted bots
- `fp_organic` = flagged accounts that are in the organic background
- `fp_hard_neg` = flagged accounts that belong to a hard negative
- `fn` = planted bots that were not flagged
- `precision = tp / (tp + fp_organic + fp_hard_neg)`
- `recall = tp / (tp + fn)`
- `fp_per_1000_organic = fp_organic / organic_count * 1000`
- Keep `hard_neg_flag_rate` as a separate field: fraction of the 10 scenarios with any member in an inauthentic cluster
- `cluster_purity` returns `null` when no inauthentic cluster was produced. The aggregator skips nulls. The report prints `n/a` when every run was null.

**Random baseline.** For each seed, assign every account `rng.random()`, flag accounts at or above 0.5, and call `compute_account_metrics`. Average the seed results. Delete the constants `0.50` and `0.15`.

**Exact-duplicate baseline.** A separate function, not a filter on pipeline clusters. Flag an account when its `text_norm` equals the `text_norm` of at least two other accounts inside a 6-hour window. Score that set with `compute_account_metrics`.

**Ablation.** For every dev seed, run twice: `enable_fp_protection=True` and `False`. Aggregate each arm across the same seeds. The report shows both means. Protection is working on H1 when the `True` arm has a lower `hard_neg_flag_rate` and the aged non-allowlist copypasta family still has high recall.

**Evasion rows.** Delete the literal list. Add `measure_evasion(seed)` which builds one campaign at a time against the organic background and records the recall of that run:


| Row id              | How to build it                                           | Keep the row only if                     |
| --------------------- | ----------------------------------------------------------- | ------------------------------------------ |
| `paraphrase_6h`     | F3 wording with `burst_span_sec` of at least 6 hours      | the generator accepts a span argument    |
| `sleeper_copypasta` | F7 as it exists                                           | always, this generator exists            |
| `camouflage`        | F10 as it exists                                          | always                                   |
| `slow_drip_12h`     | F8 with span forced above 12 hours                        | the generator accepts a span argument    |
| `combined`          | aged accounts, per-bot paraphrase, and span above 6 hours | all three knobs exist on one family call |

Add the span and age knobs to `generate_bot_family` as explicit arguments with the current random draw as the default. Each saved row includes `seed`, `familyId`, `observedRecall`, `organicCount`, and `nPermutations`. `generate_eval_report.py` prints those fields and refuses to print a row that lacks `seed`.

**Confidence intervals.** `bootstrap_ci` returns a CI only when `len(values) >= 10`. Below that, the report prints each seed's value and the sentence `CI withheld (n < 10)`.

**Null control.** Keep the pure-organic run. Also add a shuffled-author run: take one planted scenario, permute `did` across posts, and expect campaign recall to fall. Record both. The status string is `PASS` only when the pure-organic inauthentic cluster count is 0. Do not hardcode the word `PASS`.

**Suite entry.** `backend/app/sim/run_eval.py` calls `run_benchmark_v2_suite` directly. `run_full_evaluation_suite` in `simulator.py` should call the same suite once, not a second private scenario plus the v2 suite. One report shape.

**API.** `POST /evaluation/run` stays for the lab, and it uses the unit-sized organic count (80) unless the body asks for the published size. The published command remains:

```bash
PYTHONPATH=. python3 -m backend.app.sim.run_eval
```

Default published organic count: 200. Document the runtime. Do not block the API process on the 10-seed published suite; the lab button runs 2 seeds and labels the result `lab sample`.

### Tests to change

- Delete `test_phase_8_simulator_precision_recall` from `backend/tests/test_signals.py`.
- Add `backend/tests/test_metrics.py` with fixed sets of ids (no engine): precision, the organic-only false-positive rate, null purity, and a random baseline that changes when the seed changes.
- Add one engine-level case, organic count under 40, one F1 copypasta, one H1 news burst: the copypasta accounts are flagged, the H1 accounts are not in `detected_bot_dids`.

### Done when

`latest.json` contains no key whose value was a literal in `benchmark_v2.py`. Dev and test use the same 12 families. The evasion table, if present, has a seed on every row. The unit suite finishes without calling the published suite.

---

## Phase 5 — Dashboard shows the saved decision

### Problem

`src/App.tsx` fetches clusters, graph, and timeline, then drops errors (`catch { /* silent */ }`). `ClusterInspector.tsx` substitutes a score band when `classification` is missing. Phase 3 puts the field on the API. The UI still needs to render it, including `insufficient_evidence` and `not_tested`.

`src/main.tsx` creates a TanStack Query client. `App.tsx` does not use it. Leave the dependency alone in this phase. Switching fetch libraries is out of scope.

### Solution

- Extend `src/types.ts` `ClusterResult` so `classification` includes `insufficient_evidence`, and `significance.status` is `'tested' | 'not_tested'`.
- In `ClusterInspector.tsx`, render `cluster.classification` whenever it is present. Use the score-band fallback only when the field is absent, and show the word `unlabeled` in that fallback so old rows are visible.
- Show the p-value only when `status === 'tested'`, with the permutation count. When status is `not_tested`, show `Not tested` and no p-value.
- Show `fdr_q_value` and whether it passed.
- In `App.tsx`, if a fetch fails, set a visible `loadError` string on the dashboard. Clear it on the next success.
- Evaluation Lab: read the new metric names (`fp_per_1000_organic`, null purity, seed lists). Hide a chart series when the array is empty. Do not draw a point for a missing evasion row.

### Done when

A demo cluster and a live cluster show the class stored in SQLite, a failed API call leaves a message on screen, and the lab renders a report that has no evasion rows without inventing a zero.

---

## Phase 6 — One database, a working Docker UI, an honest README

### Problem A — two database paths

`backend/app/config.py`:

- `database_path` honors `COORDWATCH_DB_PATH`
- `database_url` defaults from `DEFAULT_DB_PATH` and ignores `COORDWATCH_DB_PATH` unless `DATABASE_URL` is set

`models.py` creates the SQLAlchemy engine from `database_url`. `db.get_connection()` opens `database_path`. Docker sets `COORDWATCH_DB_PATH` and does not set `DATABASE_URL`. The repo also contains both `data/coordwatch.db` and `backend/data/coordwatch.db`, plus `data/coordwatch.db-wal` and `data/coordwatch.db-shm`.

Queries are raw `sqlite3`. The ORM models are a second schema description. Phase 3 already requires them to match. This phase makes them point at one file.

### Problem B — Docker UI cannot reach the API

`src/App.tsx` sets `const API_BASE = ''`. `docker-compose.yml` sets `VITE_API_BASE_URL`, and the frontend never reads it. Vite inlines env vars at build time. The compose command builds and then runs `vite preview`. `vite.config.ts` puts the proxy on `server` only. Preview does not use `server.proxy`, so the browser requests `/api` from port 3000 and gets the static file server.

### Problem C — the analyzer drops work after an error

`backend/app/main.py` `_periodic_analyzer` copies `dirty_topics` and clears the set before `analyze_and_persist_topic`. On exception the topic is not put back, so new posts that arrived earlier are not analyzed until another post marks the topic dirty.

### Problem D — the README overclaims

`README.md` and the FastAPI description in `main.py` call the system production-grade and say the score tables contain zero hand-typed numbers. Phase 4 is what makes the second sentence true. The first sentence should be removed either way.

### Solution

**Database**

- Set `database_url` from the resolved path: `sqlite:///` plus `database_path`.
- At startup, log that path once.
- `init_db` and `get_connection` both use `settings.database_path`.
- Add `.gitignore` entries: `node_modules/`, `dist/`, `__pycache__/`, `*.db-wal`, `*.db-shm`, `backend/data/*.db`.
- Keep `data/coordwatch.db` as the local demo file, or document that the first run creates it. Delete the duplicate under `backend/data/` from the working tree when you next clean generated files.
- Do not commit WAL sidecars.

**Docker and the frontend base URL**

- In `vite.config.ts`, set `preview.proxy` to the same `/api` and `/health` rules as `server.proxy`.
- In `App.tsx`, `const API_BASE = import.meta.env.VITE_API_BASE_URL ?? ''`.
- Compose already passes `VITE_API_BASE_URL=http://localhost:8000` into the frontend container. That value is correct for a browser on the host, and it must be present when `npm run build` runs. The preview proxy is the backup when the env var is empty.
- Confirm with curl: `GET http://localhost:3000/api/health` returns the FastAPI health JSON, and `GET http://localhost:8000/health` returns the same service name.

**Analyzer**

- On analysis exception, `ingest_state.dirty_topics.add(t_id)`.
- On success, leave it clear.
- Posts that arrive during the run already add the topic again; keep that behavior.

**README**

Rewrite the opening paragraph to the prototype description at the top of this file. Delete "production-grade" from `main.py`'s FastAPI description too.

Replace section 4 (the metric tables) by running:

```bash
PYTHONPATH=. python3 -m backend.app.sim.run_eval
python3 scripts/generate_eval_report.py
```

Commit the generated markdown into the README under a heading `Measured benchmark`. Above the tables, print `computedAt`, the seed lists, and the organic count from `latest.json`.

Keep the limitations section, and add these four, each as a fact:

- Character 3-gram similarity misses a rewrite that shares little surface form with the source sentence.
- Aged accounts that copy an allowlisted headline are classified as news sharing (Phase 2).
- The ingestor reads the public post firehose in one process and filters keywords locally.
- Account creation time comes from `plc.directory`, with `getProfile` as the fallback, and a failed lookup stores no creation time.

### Done when

One path is logged at startup. `GET /api/health` through port 3000 returns the API. A failed analysis run puts the topic back on the dirty set. The README's metric section matches `latest.json` byte for byte in the numbers.

---

## Phase 7 — Scale follow-ups (after the demo is honest)

Do this phase only after Phases 1–6. These are real limits. They are not required for the README to be truthful.

### Text comparison is quadratic

`backend/app/signals/text.py` builds a full TF-IDF similarity matrix, then skips pairs outside 6 hours. On a live topic with thousands of posts the matrix is the cost.

**Change:** bucket posts into 6-hour windows first. Fit TF-IDF inside each bucket. Compare pairs only inside the bucket. Keep the 0.76 threshold.

**Done when:** a fixture of 2,000 short posts spread over 48 hours finishes `compute_text_similarity_signal` in a few seconds on a laptop, and the Phase 1 copypasta test still returns one edge.

### The firehose has no backpressure story

`run_jetstream_ingestor` updates `last_cursor` when `time_us` arrives, before the batch insert commits. The queue max is 5000. A full queue or a crash moves the cursor past posts that were never written.

**Change:** `put_nowait`. On `asyncio.QueueFull`, increment `dropped_events` in the telemetry and leave the cursor where the last successful batch commit left it. Advance `last_cursor` inside `_batch_insert_worker` after `conn.commit()`, using the max `time_us` in that batch.

**Done when:** telemetry shows `droppedEvents`, and a forced insert error does not move the cursor.

### Evaluation can pin the API

`POST /evaluation/run` runs the suite inside the request. Phase 4 already limits the button to a lab sample. If that sample still takes longer than a few seconds, move it to a background task and return `202` with a status URL. Do not hold the ingest loop behind it.

---

## File map


| File                                                                                                         | Phases                         |
| -------------------------------------------------------------------------------------------------------------- | -------------------------------- |
| `backend/app/textutil.py`                                                                                    | 1, 2 (new)                     |
| `backend/app/ingest/jetstream.py`                                                                            | 1, 7                           |
| `backend/app/signals/links.py`                                                                               | 1, 2                           |
| `backend/app/signals/text.py`                                                                                | 7                              |
| `backend/app/db.py`                                                                                          | 1, 3, 6                        |
| `backend/app/models.py`                                                                                      | 3                              |
| `backend/app/config.py`                                                                                      | 6                              |
| `backend/app/sim/families.py`                                                                                | 1, 4                           |
| `backend/app/sim/hard_negatives.py`                                                                          | 1                              |
| `backend/app/sim/organic.py`                                                                                 | 1                              |
| `backend/app/analysis/scoring.py`                                                                            | 2                              |
| `backend/app/analysis/engine.py`                                                                             | 3                              |
| `backend/app/analysis/significance.py`                                                                       | 3                              |
| `backend/app/sim/benchmark_v2.py`                                                                            | 4                              |
| `backend/app/sim/metrics.py`                                                                                 | 4                              |
| `backend/app/sim/simulator.py`                                                                               | 4                              |
| `backend/app/sim/run_eval.py`                                                                                | 4                              |
| `backend/app/api/routes.py`                                                                                  | 3, 4                           |
| `backend/app/main.py`                                                                                        | 6                              |
| `backend/tests/test_textutil.py`                                                                             | 1 (new)                        |
| `backend/tests/test_improvements.py`                                                                         | 2, 3                           |
| `backend/tests/test_signals.py`                                                                              | 4 (delete the full-suite test) |
| `backend/tests/test_metrics.py`                                                                              | 4 (new)                        |
| `scripts/generate_eval_report.py`                                                                            | 4, 6                           |
| `src/types.ts`, `src/App.tsx`, `src/components/ClusterInspector.tsx`, `src/components/EvaluationLabView.tsx` | 5                              |
| `vite.config.ts`, `docker-compose.yml`, `.gitignore`                                                         | 6                              |
| `README.md`                                                                                                  | 6                              |

---

## Out of scope

Leave these alone while implementing this plan:

- Sentence embeddings, stance detection, and multilingual models. The README may name them as future work in one line.
- A new graph library. `react-force-graph-2d` already draws the network.
- Rewriting fetches onto TanStack Query.
- Auth, multi-user accounts, and deployment to Render or Vercel.
- Renaming the project folder. The `&` and em dash are awkward in shells. Rename only in a dedicated change, after the tests are green.

---

## Definition of done

The work in this file is complete when all of the following are true:

1. Demo, replay, simulator, and live posts use `prepare_post`.
2. An H1-style BBC burst is `coordinated_benign`. An aged copypasta that links to a non-allowlist domain is `coordinated_inauthentic`. A fresh batch that links to BBC is `coordinated_inauthentic`.
3. Significance receives this cluster's raw score. Untestable clusters store `not_tested` and no fabricated p-value. Failed FDR changes an inauthentic label to `insufficient_evidence`.
4. The cluster detail endpoint returns `classification` and `significance`, and the inspector shows those fields.
5. The published benchmark uses 10 dev seeds and 10 test seeds of the same 12 families. Every evasion row includes a seed. Purity is `n/a` when there are no clusters. The random baseline is a seeded coin flip run through `compute_account_metrics`.
6. `pytest backend/tests -v` does not call the published suite, and it passes.
7. Docker preview serves `/api/health` from the backend. Startup logs one database path.
8. The README describes a prototype, and its tables match `backend/data/evaluation_runs/latest.json`.
