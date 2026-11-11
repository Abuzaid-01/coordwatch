# CoordWatch: New Improvement Plan

This plan replaces the prototype-to-production write-up. It only includes defects that are still in this tree. The closed items at the end are already fixed, so they are not work.

A number in the README or the lab has to come from a run. Do not type a new recall or a new false-positive rate by hand. Finish each phase before the next one.

---

## Phase 1 — Graph signal filter

**Bug.** `NetworkGraphCanvas` keeps an edge when `link.dominantSignal` matches the button or `link.signals[signalFilter] >= 0.45`. `run_topic_analysis` in `backend/app/analysis/engine.py` sends `signals` as a list of names (`["text", "timing"]`) and never sets `dominantSignal`. A list has no `"text"` key, so Text, Timing, Age, and Links each remove every edge. All Signals still works.

Cached graphs in `topic_analysis_cache` will keep the old list until that topic is analyzed again.

**Change.** In the `graph_links` dict inside `run_topic_analysis`, send the numeric map and the strongest name:

- `signals`: `{text, timing, age, links}` rounded to 3 decimals, keys below 0.20 omitted
- `dominantSignal`: the key with the largest value

There is no `graph_links` table. Do not add an `INSERT`. The dict is already stored inside `graph_json`.

In `NetworkGraphCanvas`, read a number from the map. If `signals` is still a list, treat a listed name as present and an absent name as 0, so old cached graphs do not go blank. `src/types.ts` already allows `SignalBreakdown | string[]`.

**Test.** A link whose text score is 0.8 and whose timing score is 0.1 stays visible on Text and disappears on Timing. A saved list-shaped link `["links"]` stays visible on Links.

**Done when.** On the live "ai" or demo topic, Text and Links change which edges are drawn, and All Signals restores the full graph.

---

## Phase 2 — One published report, one lab sample

**Bug.** `run_benchmark_v2_suite` always opens `backend/data/evaluation_runs/latest.json` in write mode. `POST /api/evaluation/run` calls that function with two seeds and `label="lab sample"`, so the button replaces the 10-seed file. `GET /api/evaluation/latest` reads only the newest SQLite `evaluation_runs` row. A fresh database ignores the file on disk. The empty status string is `"not_run"`.

**Change.**

- Add a `persist_path` argument to `run_benchmark_v2_suite`. The command `python -m backend.app.sim.run_eval` keeps the default, `latest.json`.
- `POST /api/evaluation/run` passes `persist_path=None`. It still inserts the returned JSON into `evaluation_runs` and returns it to the button.
- `GET /api/evaluation/latest` returns the newest database row when one exists. If the table is empty, it returns the JSON file when that file exists. Otherwise it returns `{"status": "not_run", ...}` as it does now.

If the file already on disk has `"label": "lab sample"`, it has already been overwritten. Restore it by re-running `python -m backend.app.sim.run_eval`. Do not paste the old digits back from memory.

**Test.** A lab call leaves the bytes of `latest.json` unchanged. With an empty `evaluation_runs` table and a real `latest.json`, `GET /api/evaluation/latest` returns that file, including `label`.

**Done when.** The button can be clicked twice and `latest.json` is still the published run.

---

## Phase 3 — Lab cards that match `benchmark_v2`

**Bug.** `EvaluationLabView` still draws a chart from `report.evasionCurve` and a table from `report.plantedNetworks`. The suite does not emit either key, so those two cards stay on the empty copy. The same view already renders `devSummary`, `testSummary`, `baselines`, `ablations`, `evasionBoundaries`, and `honestLimitations`. Those stay.

`compute_campaign_level_recall` already builds a per-campaign breakdown, and each seed run stores it as `campaign_breakdown`, but `run_benchmark_v2_suite` does not copy it onto the saved report. The report does copy `hardNegatives.dev` and `hardNegatives.test`.

**Change.**

- Remove the `evasionCurve` chart and the `plantedNetworks` table.
- Keep the `evasionBoundaries` table that is already lower on the page.
- Show `report.hardNegatives.dev` when it is present: scenario id, class, flagged or not, member flag ratio.
- On each campaign object inside the suite, set `family` from the generator (`F1` through `F12`). Copy the first dev seed's `campaign_breakdown` onto the report as `campaignBreakdown`. The lab table reads that array. If the key is missing, leave the table out.

**Done when.** A published `latest.json` shows the 12 families and the H1–H10 rows from the file, and the two empty v1 cards are gone.

---

## Phase 4 — H5 creation dates

**Bug.** In `generate_hard_negative`, scenario `H5` sets every account to `base_time - 500 days`, the same second. The posts share a `gov.uk` URL and land within 60 seconds, which is the case the news rule is for. `compute_cluster_score_and_reasons` only treats the cluster as aged news when `cohort_48h_count / size < 0.35`. Six accounts born in the same second make that ratio 1.0, so H5 stays `coordinated_inauthentic`. Both H5 rows in the current `latest.json` have `memberFlagRatio: 1.0`.

**Change.** In `H5` only, draw each account's creation time from a spread of months, on the order of 180 to 900 days before `base_time`, with more than 48 hours between accounts. Leave the shared `gov.uk` post and the one-minute burst alone.

**Test.** Build the H5 accounts and posts with a fixed seed, run them through the same analysis path the benchmark uses, and expect `coordinated_benign`. An aged copypasta on a non-allowlist URL must still be `coordinated_inauthentic`.

**Done when.** The test passes. Then regenerate the published report with `python -m backend.app.sim.run_eval` and let `scripts/generate_eval_report.py` write the README digits. The new H5 ratio is whatever that run prints.

---

## Phase 5 — Only the misses the report already measured

Do this after Phase 3, so the family table is visible, and after Phase 4, so the new report is the baseline.

The current published evasion rows are the evidence:

- "Paraphrase plus 6h jitter" (`F3`) has observed recall 0.0.
- "Slow drip over 12h" (`F8`) has observed recall 0.0.
- "Camouflage chatter" (`F10`) has observed recall 1.0. F10 is not a miss.
- F5 is query-string mutation on one campaign URL. F6 is a 20–180 second repost burst. F12 is a small cell using the normal copypasta. None of those is a domain-rotation or mixed-modality generator.

`compute_cluster_significance` counts cross-account pairs only inside 90 seconds. `apply_detection_decisions` then turns a `coordinated_inauthentic` cluster into `insufficient_evidence` when that test fails or was not run. A slow, paraphrased campaign can be dropped there even when the link signal connected it. That is a hypothesis until a trace says so.

**Change, in this order.**

1. Add a one-seed debug print, not a new metric: for the F3 evasion case and the F8 evasion case, list each planted account as "no edge", "in a cluster labeled X", or "in the detected set".
2. Change the one gate that trace names. Do not also lower the 0.76 text threshold or widen the 180-second timing window in that same change.
3. If the trace shows the 90-second test is the drop, then a cluster whose posts have no pair inside 90 seconds should not be demoted by a timing test that cannot see them. Leave the scorer's label, and add one reason: the timing test did not apply. Clusters the test actually runs and rejects still become `insufficient_evidence`.

**Done when.** The same two evasion rows are regenerated by `run_eval`. Record their new observed recall from the file. If a row is still 0.0, leave it at 0.0 and say which gate the trace found.

---

## Phase 6 — Live topics reread their whole history

**Bug.** `get_topic_posts_and_accounts` loads every post for the topic, oldest first, with no limit. `analyze_and_persist_topic` deletes that topic's clusters and writes a new result. `_periodic_analyzer` already runs this on a worker thread, and only for topics with new posts. The cost is the full reread, not the event loop.

**Change.** Add `analysis_window_hours` to `backend/app/config.py`, default 72. For a topic whose `source` is `live`, pass only posts inside that window into `run_topic_analysis`. Demo and recorded topics stay whole, because their evidence is the fixed corpus. Say the window in the cluster dossier footer for live topics.

**Test.** A live-shaped topic with one post inside the window and one post older than the window produces clusters from the recent post only. Topic 1, the demo seed, still returns the same clusters as before the window.

**Done when.** The demo dashboard is unchanged and a live topic's analysis input is bounded by the config value.

---

## Phase 7 — Method tab stops calling missing routes

**Bug.** `EthicsAndDocsView` fetches `/api/python-backend/verify` and `/api/python-backend/source`. Those routes are not in `routes.py`. The tab now shows the 404 text instead of a blank pane.

**Change.** Remove both fetches, the file tree, the test-output panel, and the source viewer. Keep the ethics copy and the buttons that call real routes: `/api/health`, `/api/topics`, `/api/topics/{id}/summary`, `/api/topics/{id}/graph`, `/api/topics/{id}/clusters`, `/api/topics/{id}/timeline`, and `/api/evaluation/latest`. Pass `activeTopicId` from `App` as it does now.

Do not add an endpoint that runs unit tests or returns repository source.

**Done when.** Opening Method produces no request to `/api/python-backend/*`, and the health and topic buttons still render JSON.

---

## Already done

Leave these alone. The earlier plan described them as open, and the code has since moved.

- Periodic analysis uses `asyncio.to_thread` in `_periodic_analyzer`. It does not call `run_analysis_for_all_topics` on the event loop.
- `POST /api/evaluation/run` is a normal synchronous route, so FastAPI runs it on a worker thread. Phase 2 is what stops it from destroying the published file.
- Text similarity is already fit inside 6-hour buckets in `compute_text_similarity_signal`.
- The Jetstream cursor advances after a committed batch, and a full queue increments `droppedEvents`.
- Account handles are resolved in `enrich/account_age.py` through `plc.directory`, then `getProfile`. Jetstream only stores a placeholder until that worker succeeds. Reveal Handles shows the stored handle.

---

## Order

| Phase | Work | Depends on |
|---|---|---|
| 1 | Graph signal payload and filter | none |
| 2 | Lab sample must not write `latest.json` | none |
| 3 | Lab cards and family breakdown | Phase 2 |
| 4 | Spread H5 creation times and rerun the report | Phase 3 |
| 5 | Trace F3 and F8, then change the one gate the trace names | Phase 4 |
| 6 | 72-hour window for live topics | none |
| 7 | Remove the Method-tab source and test panels | none |

Phases 1, 2, 6, and 7 can be separate changes. Phase 5 waits until the new report exists, so the before and after are the same script.
