"""Database initialization, SQLAlchemy session management, direct connection helper, and demo seeding."""
from datetime import datetime, timezone
import json
import logging
from pathlib import Path
import sqlite3
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import text
from .config import settings
from .textutil import apply_prepare, generate_hash_alias
from .models import (
    Account,
    Base,
    Cluster,
    ClusterMember,
    EvaluationRun,
    Post,
    SessionLocal,
    Topic,
    TopicAnalysisCache,
    engine,
)
from .analysis.engine import run_topic_analysis

logger = logging.getLogger(__name__)


def get_connection() -> sqlite3.Connection:
    """Returns a raw sqlite3 connection with dict-like row factories for legacy/fast queries."""
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(settings.database_path), timeout=30.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA busy_timeout=30000;")
    return conn


def migrate_schema(conn: sqlite3.Connection) -> None:
    """Add columns create_all will not add to a database that already exists."""
    existing = {row[1] for row in conn.execute("PRAGMA table_info(clusters)").fetchall()}
    additions = {
        "classification": "ALTER TABLE clusters ADD COLUMN classification TEXT",
        "significance_json": "ALTER TABLE clusters ADD COLUMN significance_json TEXT",
        "benign_checks_json": "ALTER TABLE clusters ADD COLUMN benign_checks_json TEXT",
    }
    for column, statement in additions.items():
        if column not in existing:
            conn.execute(statement)
    conn.commit()


def init_db() -> None:
    """Initializes tables and seeds initial demonstration dataset if empty."""
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    Base.metadata.create_all(bind=engine)
    logger.info("CoordWatch database: %s", settings.database_path)
    conn = get_connection()
    try:
        migrate_schema(conn)
    finally:
        conn.close()
    _ensure_seed_dataset()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_topics_list() -> List[Dict[str, Any]]:
    conn = get_connection()
    try:
        query = """
        SELECT
            t.id, t.keyword, t.mode, t.source, t.started_at, t.last_analyzed_at,
            COUNT(DISTINCT p.id) AS post_count,
            COUNT(DISTINCT p.did) AS account_count,
            COALESCE(c.cluster_count, 0) AS cluster_count,
            COALESCE(c.high_risk_count, 0) AS high_risk_cluster_count
        FROM topics t
        LEFT JOIN posts p ON p.topic_id = t.id
        LEFT JOIN (
            SELECT topic_id,
                   COUNT(*) AS cluster_count,
                   SUM(CASE WHEN score >= 50 AND classification = 'coordinated_inauthentic' THEN 1 ELSE 0 END) AS high_risk_count
            FROM clusters
            GROUP BY topic_id
        ) c ON c.topic_id = t.id
        GROUP BY t.id
        ORDER BY t.id ASC
        """
        rows = conn.execute(query).fetchall()
        topics = []
        for r in rows:
            topics.append({
                "id": r["id"],
                "keyword": r["keyword"],
                "mode": r["mode"],
                "source": r["source"] if "source" in r.keys() else "live",
                "startedAt": r["started_at"],
                "lastAnalyzedAt": r["last_analyzed_at"],
                "postCount": r["post_count"],
                "accountCount": r["account_count"],
                "clusterCount": r["cluster_count"],
                "highRiskClusterCount": r["high_risk_cluster_count"],
            })
        return topics
    finally:
        conn.close()


def create_or_get_topic(keyword: str, mode: str = "hybrid", source: str = "live") -> Dict[str, Any]:
    conn = get_connection()
    try:
        clean_kw = keyword.strip()
        existing = conn.execute("SELECT id FROM topics WHERE lower(keyword) = lower(?)", (clean_kw,)).fetchone()
        now = datetime.now(timezone.utc).isoformat()
        if existing:
            t_id = existing["id"]
        else:
            cur = conn.execute(
                "INSERT INTO topics (keyword, mode, source, started_at, last_analyzed_at) VALUES (?, ?, ?, ?, NULL)",
                (clean_kw, mode, source, now),
            )
            conn.commit()
            t_id = cur.lastrowid
            # Only replay pre-recorded dataset if source is explicitly 'recorded' or 'demo'
            if source in ("recorded", "demo"):
                _replay_jsonl_for_topic(t_id, clean_kw)
                analyze_and_persist_topic(t_id)

        topics = get_topics_list()
        found = next((t for t in topics if t["id"] == t_id), None)
        return found or {"id": t_id, "keyword": clean_kw, "source": source, "postCount": 0, "clusterCount": 0}
    finally:
        conn.close()


def get_topic_posts_and_accounts(topic_id: int) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    conn = get_connection()
    try:
        p_rows = conn.execute(
            """
            SELECT p.id, p.did, p.text, p.text_norm, p.created_at, p.topic_id, p.links, p.hashtags, p.source,
                   a.alias as author_alias, a.handle as author_handle, a.created_at as author_created_at
            FROM posts p
            LEFT JOIN accounts a ON p.did = a.did
            WHERE p.topic_id = ?
            ORDER BY p.created_at ASC
            """,
            (topic_id,),
        ).fetchall()

        posts = []
        for r in p_rows:
            try:
                links = json.loads(r["links"])
            except Exception:
                links = []
            try:
                tags = json.loads(r["hashtags"])
            except Exception:
                tags = []
            prepared = apply_prepare({
                "text": r["text"],
                "links": links,
                "hashtags": tags,
            })
            posts.append({
                "id": r["id"],
                "did": r["did"],
                "text": r["text"],
                "text_norm": prepared["text_norm"],
                "created_at": r["created_at"],
                "topic_id": r["topic_id"],
                "links": prepared["links"],
                "hashtags": prepared["hashtags"],
                "source": r["source"] if "source" in r.keys() else "live",
                "author_alias": r["author_alias"] or generate_hash_alias(r["did"]),
                "author_handle": r["author_handle"] or f"{r['did'][-8:]}.bsky.social",
                "author_created_at": r["author_created_at"],
            })

        a_rows = conn.execute(
            """
            SELECT DISTINCT a.did, a.handle, a.alias, a.created_at, a.first_seen, a.enriched, a.enrich_status, a.enrich_attempts
            FROM accounts a
            INNER JOIN posts p ON p.did = a.did
            WHERE p.topic_id = ?
            """,
            (topic_id,),
        ).fetchall()

        accounts = [
            {
                "did": r["did"],
                "handle": r["handle"],
                "alias": r["alias"],
                "created_at": r["created_at"],
                "first_seen": r["first_seen"],
                "enriched": bool(r["enriched"]),
                "enrich_status": r["enrich_status"] if "enrich_status" in r.keys() else "pending",
                "enrich_attempts": r["enrich_attempts"] if "enrich_attempts" in r.keys() else 0,
            }
            for r in a_rows
        ]
        return posts, accounts
    finally:
        conn.close()


def analyze_and_persist_topic(topic_id: int) -> Dict[str, Any]:
    posts, accounts = get_topic_posts_and_accounts(topic_id)
    result = run_topic_analysis(
        topic_id,
        posts,
        accounts,
        min_edge_weight=settings.min_edge_weight,
        min_cluster_size=settings.min_cluster_size,
        enable_fp_protection=True,
    )

    conn = get_connection()
    try:
        now = datetime.now(timezone.utc).isoformat()
        conn.execute("DELETE FROM cluster_members WHERE topic_id = ?", (topic_id,))
        conn.execute("DELETE FROM clusters WHERE topic_id = ?", (topic_id,))

        for c in result["clusters"]:
            conn.execute(
                """
                INSERT OR REPLACE INTO clusters (
                    id, topic_id, score, raw_score, discount_applied, discount_reason,
                    size, signals_json, reasons_json, example_posts_json, computed_at,
                    classification, significance_json, benign_checks_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    c["id"],
                    topic_id,
                    c["score"],
                    c["rawScore"],
                    c["discountApplied"],
                    c.get("discountReason"),
                    c["size"],
                    json.dumps(c["signals"]),
                    json.dumps(c["reasons"]),
                    json.dumps(c["examplePosts"]),
                    now,
                    c.get("classification") or "insufficient_evidence",
                    json.dumps(c.get("significance") or {}),
                    json.dumps(c.get("benignChecks") or {}),
                ),
            )
            for m in c["members"]:
                conn.execute(
                    "INSERT OR REPLACE INTO cluster_members (cluster_id, topic_id, did, node_score) VALUES (?, ?, ?, ?)",
                    (c["id"], topic_id, m["did"], m["nodeScore"]),
                )

        conn.execute(
            """
            INSERT OR REPLACE INTO topic_analysis_cache (topic_id, graph_json, timeline_json, computed_at)
            VALUES (?, ?, ?, ?)
            """,
            (topic_id, json.dumps(result["graph"]), json.dumps(result["timeline"]), now),
        )
        conn.execute("UPDATE topics SET last_analyzed_at = ? WHERE id = ?", (now, topic_id))
        conn.commit()
    finally:
        conn.close()

    return result


def get_cached_topic_analysis(topic_id: int) -> Dict[str, Any]:
    conn = get_connection()
    try:
        row = conn.execute("SELECT graph_json, timeline_json FROM topic_analysis_cache WHERE topic_id = ?", (topic_id,)).fetchone()
        if row:
            return {
                "graph": json.loads(row["graph_json"]),
                "timeline": json.loads(row["timeline_json"]),
            }
        # If cache is missing, compute now
        res = analyze_and_persist_topic(topic_id)
        return {"graph": res["graph"], "timeline": res["timeline"]}
    finally:
        conn.close()


def get_stored_clusters(topic_id: int) -> List[Dict[str, Any]]:
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT * FROM clusters WHERE topic_id = ? ORDER BY score DESC, size DESC",
            (topic_id,),
        ).fetchall()

        if not rows:
            return []

        # Single optimized query to fetch members for this topic
        m_rows = conn.execute(
            """
            SELECT cm.cluster_id, cm.did, cm.node_score, a.alias, a.handle, a.created_at,
                   COUNT(p.id) as post_count
            FROM cluster_members cm
            LEFT JOIN accounts a ON a.did = cm.did
            LEFT JOIN posts p ON p.did = cm.did AND p.topic_id = cm.topic_id
            WHERE cm.topic_id = ?
            GROUP BY cm.cluster_id, cm.did
            ORDER BY cm.node_score DESC
            """,
            (topic_id,),
        ).fetchall()

        members_by_cluster: Dict[str, List[Dict[str, Any]]] = {}
        for m in m_rows:
            members_by_cluster.setdefault(m["cluster_id"], []).append({
                "did": m["did"],
                "alias": m["alias"] or f"A-{m['did'][-6:].upper()}",
                "handle": m["handle"] or f"{m['did'][-8:]}.bsky.social",
                "createdAt": m["created_at"],
                "postCount": m["post_count"],
                "nodeScore": m["node_score"],
            })

        clusters = []
        for r in rows:
            members = members_by_cluster.get(r["id"], [])
            keys = r.keys()
            significance = {}
            benign_checks = {}
            if "significance_json" in keys and r["significance_json"]:
                try:
                    significance = json.loads(r["significance_json"])
                except Exception:
                    significance = {}
            if "benign_checks_json" in keys and r["benign_checks_json"]:
                try:
                    benign_checks = json.loads(r["benign_checks_json"])
                except Exception:
                    benign_checks = {}
            clusters.append({
                "id": r["id"],
                "topicId": r["topic_id"],
                "score": r["score"],
                "rawScore": r["raw_score"],
                "discountApplied": r["discount_applied"],
                "discountReason": r["discount_reason"],
                "classification": r["classification"] if "classification" in keys else None,
                "significance": significance,
                "benignChecks": benign_checks,
                "size": r["size"],
                "memberDids": [m["did"] for m in members],
                "members": members,
                "signals": json.loads(r["signals_json"]),
                "reasons": json.loads(r["reasons_json"]),
                "examplePosts": json.loads(r["example_posts_json"]),
                "computedAt": r["computed_at"],
            })
        return clusters
    finally:
        conn.close()


def get_unenriched_dids(limit: int = 5) -> List[str]:
    conn = get_connection()
    try:
        rows = conn.execute(
            """
            SELECT did FROM accounts
            WHERE enriched = 0
              AND (enrich_status IS NULL OR enrich_status = 'pending')
              AND COALESCE(enrich_attempts, 0) < ?
              AND did LIKE 'did:plc:%'
            LIMIT ?
            """,
            (settings.max_enrich_attempts, limit),
        ).fetchall()
        return [r["did"] for r in rows]
    finally:
        conn.close()


def mark_account_enriched(
    did: str,
    handle: Optional[str],
    created_at: Optional[str],
    status: str = "ok",
) -> None:
    conn = get_connection()
    try:
        if status == "ok" and created_at:
            conn.execute(
                """
                UPDATE accounts
                SET handle = COALESCE(?, handle),
                    created_at = COALESCE(?, created_at),
                    enriched = 1,
                    enrich_status = 'ok',
                    enrich_attempts = COALESCE(enrich_attempts, 0) + 1
                WHERE did = ?
                """,
                (handle, created_at, did),
            )
        elif status == "failed":
            conn.execute(
                """
                UPDATE accounts
                SET handle = COALESCE(?, handle),
                    enrich_status = 'failed',
                    enrich_attempts = COALESCE(enrich_attempts, 0) + 1
                WHERE did = ?
                """,
                (handle, did),
            )
        else:
            conn.execute(
                """
                UPDATE accounts
                SET handle = COALESCE(?, handle),
                    enrich_status = CASE WHEN COALESCE(enrich_attempts, 0) + 1 >= ? THEN 'failed' ELSE 'pending' END,
                    enrich_attempts = COALESCE(enrich_attempts, 0) + 1
                WHERE did = ?
                """,
                (handle, settings.max_enrich_attempts, did),
            )
        conn.commit()
    finally:
        conn.close()


def insert_live_post(p: Dict[str, Any], conn: Optional[sqlite3.Connection] = None) -> bool:
    own_conn = False
    if conn is None:
        conn = get_connection()
        own_conn = True
    try:
        cur = conn.execute(
            """
            INSERT OR IGNORE INTO posts (id, did, text, text_norm, created_at, topic_id, links, hashtags, source)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                p["id"],
                p["did"],
                p["text"],
                p["text_norm"],
                p["created_at"],
                p["topic_id"],
                json.dumps(p.get("links") or []),
                json.dumps(p.get("hashtags") or []),
                p.get("source", "live"),
            ),
        )
        if own_conn:
            conn.commit()
        return cur.rowcount > 0
    finally:
        if own_conn:
            conn.close()


def upsert_account(acc: Dict[str, Any], conn: Optional[sqlite3.Connection] = None) -> None:
    own_conn = False
    if conn is None:
        conn = get_connection()
        own_conn = True
    try:
        conn.execute(
            """
            INSERT INTO accounts (did, handle, alias, created_at, first_seen, enriched, enrich_status, enrich_attempts)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(did) DO UPDATE SET
              handle = CASE WHEN excluded.handle != '' THEN excluded.handle ELSE accounts.handle END,
              created_at = COALESCE(excluded.created_at, accounts.created_at),
              enriched = MAX(accounts.enriched, excluded.enriched),
              enrich_status = CASE WHEN excluded.enrich_status != 'pending' THEN excluded.enrich_status ELSE accounts.enrich_status END,
              enrich_attempts = MAX(accounts.enrich_attempts, excluded.enrich_attempts)
            """,
            (
                acc["did"],
                acc.get("handle") or f"{acc['did'][-8:]}.bsky.social",
                acc.get("alias") or generate_hash_alias(acc["did"]),
                acc.get("created_at"),
                acc.get("first_seen") or datetime.now(timezone.utc).isoformat(),
                1 if acc.get("enriched") else 0,
                acc.get("enrich_status", "ok" if acc.get("enriched") else "pending"),
                acc.get("enrich_attempts", 1 if acc.get("enriched") else 0),
            ),
        )
        if own_conn:
            conn.commit()
    finally:
        if own_conn:
            conn.close()


def _ensure_seed_dataset() -> None:
    """Builds demo seed dataset and seeds Topic 1 if topics table is empty."""
    conn = get_connection()
    needs_analysis = False
    try:
        count = conn.execute("SELECT COUNT(*) FROM topics").fetchone()[0]
        if count > 0:
            return

        now = datetime.now(timezone.utc).isoformat()
        conn.execute(
            "INSERT INTO topics (id, keyword, mode, source, started_at, last_analyzed_at) VALUES (1, 'clean air zone', 'hybrid', 'demo', ?, NULL)",
            (now,),
        )

        # Build seed events
        events = _generate_seed_events()

        # Ensure demo_seed.jsonl on disk (A4: never overwrite sample_posts.jsonl!)
        settings.demo_seed_jsonl_path.parent.mkdir(parents=True, exist_ok=True)
        with settings.demo_seed_jsonl_path.open("w", encoding="utf-8") as f:
            for ev in events:
                f.write(json.dumps(ev) + "\n")

        # Insert seed posts into SQLite
        for ev in events:
            prepared = apply_prepare({"text": ev["text"], "links": ev.get("links") or [], "hashtags": ev.get("hashtags") or []})
            upsert_account({
                "did": ev["did"],
                "handle": ev["handle"],
                "alias": generate_hash_alias(ev["did"]),
                "created_at": ev["authorCreatedAt"],
                "first_seen": ev["createdAt"],
                "enriched": True,
                "enrich_status": "ok",
                "enrich_attempts": 1,
            }, conn=conn)
            conn.execute(
                """
                INSERT OR IGNORE INTO posts (id, did, text, text_norm, created_at, topic_id, links, hashtags, source)
                VALUES (?, ?, ?, ?, ?, 1, ?, ?, 'demo')
                """,
                (
                    ev["id"],
                    ev["did"],
                    ev["text"],
                    prepared["text_norm"],
                    ev["createdAt"],
                    json.dumps(prepared["links"]),
                    json.dumps(prepared["hashtags"]),
                ),
            )
        conn.commit()
        needs_analysis = True
    finally:
        conn.close()

    if needs_analysis:
        analyze_and_persist_topic(1)


def _replay_jsonl_for_topic(topic_id: int, keyword: str) -> None:
    if not settings.sample_jsonl_path.exists():
        logger.info(f"Recorded sample file {settings.sample_jsonl_path} does not exist; skipping replay.")
        return
    kw = keyword.lower()
    conn = get_connection()
    try:
        with settings.sample_jsonl_path.open("r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                try:
                    ev = json.loads(line)
                    raw_text = ev.get("text", "")
                    prepared = apply_prepare({
                        "text": raw_text,
                        "links": ev.get("links") or [],
                        "hashtags": ev.get("hashtags") or [],
                    })
                    if kw in raw_text.lower() or kw in prepared["text_norm"] or kw in ev.get("topicKeyword", "").lower():
                        upsert_account({
                            "did": ev["did"],
                            "handle": ev.get("handle") or f"{ev['did'][-8:]}.bsky.social",
                            "alias": generate_hash_alias(ev["did"]),
                            "created_at": ev.get("authorCreatedAt"),
                            "first_seen": ev.get("createdAt"),
                            "enriched": bool(ev.get("authorCreatedAt")),
                            "enrich_status": "ok" if ev.get("authorCreatedAt") else "pending",
                        }, conn=conn)
                        conn.execute(
                            """
                            INSERT OR IGNORE INTO posts (id, did, text, text_norm, created_at, topic_id, links, hashtags, source)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'recorded')
                            """,
                            (
                                f"replay-{ev.get('id', 'post')}-{topic_id}",
                                ev["did"],
                                raw_text,
                                prepared["text_norm"],
                                ev.get("createdAt") or datetime.now(timezone.utc).isoformat(),
                                topic_id,
                                json.dumps(prepared["links"]),
                                json.dumps(prepared["hashtags"]),
                            ),
                        )
                except Exception as ex:
                    logger.warning(f"Error replaying post for topic {topic_id}: {ex}")
                    continue
        conn.commit()
    finally:
        conn.close()


def _generate_seed_events() -> List[Dict[str, Any]]:
    events = []
    base_ts = datetime(2026, 11, 4, 9, 0, 0, tzinfo=timezone.utc).timestamp()

    # Cluster CL-01: 22 accounts (Copypasta + 48h batch registered cohort)
    c1_templates = [
        "Regional analysis indicates municipal clean air zone tariffs create excessive compliance friction for small logistics fleets https://cleanair-truth-london.org/dossier #StopTheTaxGrid #CleanAirZone #AuditReport",
        "Economic audit indicates municipal clean air zone tariffs create excessive compliance friction for small logistics fleets and trades https://cleanair-truth-london.org/dossier #StopTheTaxGrid #CleanAirZone #AuditReport",
        "Independent review indicates municipal clean air zone tariffs create excessive compliance friction for outer district commuters https://cleanair-truth-london.org/dossier #StopTheTaxGrid #CleanAirZone #AuditReport",
    ]
    batch_1_ts = datetime(2026, 10, 29, 14, 0, 0, tzinfo=timezone.utc).timestamp()

    for i in range(22):
        did = f"did:plc:ulezringa{i+1:03d}"
        handle = f"borough-driver-{210+i}.bsky.social"
        author_created = datetime.fromtimestamp(batch_1_ts + i * 38 * 60, tz=timezone.utc).isoformat()
        post_time = datetime.fromtimestamp(base_ts + 15 * 60 + i * 2.1, tz=timezone.utc).isoformat()

        events.append({
            "id": f"seed-caz-1a-w1-{i}",
            "topicKeyword": "clean air zone",
            "did": did,
            "handle": handle,
            "authorCreatedAt": author_created,
            "text": c1_templates[i % len(c1_templates)],
            "createdAt": post_time,
            "links": ["cleanair-truth-london.org/dossier"],
            "hashtags": ["#stopthetaxgrid", "#cleanairzone", "#auditreport"],
        })

    # Cluster CL-02: 14 accounts (Shared link + campaign hashtag triad)
    batch_2_ts = datetime(2026, 10, 22, 9, 0, 0, tzinfo=timezone.utc).timestamp()
    for i in range(14):
        did = f"did:plc:ulezringb{i+1:03d}"
        handle = f"london-voice-{300+i}.bsky.social"
        author_created = datetime.fromtimestamp(batch_2_ts + i * 45 * 60, tz=timezone.utc).isoformat()
        post_time = datetime.fromtimestamp(base_ts + 45 * 60 + i * 3.4, tz=timezone.utc).isoformat()

        events.append({
            "id": f"seed-caz-1b-w1-{i}",
            "topicKeyword": "clean air zone",
            "did": did,
            "handle": handle,
            "authorCreatedAt": author_created,
            "text": "Stakeholders should examine published transport camera monitoring reports ahead of committee reviews https://cleanair-truth-london.org/dossier #StopTheTaxGrid #CleanAirZone",
            "createdAt": post_time,
            "links": ["cleanair-truth-london.org/dossier"],
            "hashtags": ["#stopthetaxgrid", "#cleanairzone"],
        })

    # 40 Organic Posts from Established Accounts
    organic_texts = [
        "Commuting through Southwark on the railway and air quality monitors near Elephant & Castle show steady improvement.",
        "Local bike repair cooperative held a great community maintenance workshop for families this afternoon.",
        "Rain forecast across the southern boroughs for the next three hours, take care on cycleways.",
        "Checking public transport bus timetable updates for the new orbital express service.",
        "Glad to see more zero-emission electric buses operating along the main transit corridor.",
        "Primary school community garden harvest day was a wonderful local gathering.",
        "Reviewing the municipal transport budget papers: fleet electrification is making tangible progress.",
    ]
    for i in range(40):
        did = f"did:plc:citizen{i+1:03d}"
        age_days = 200 + (i * 17) % 650
        author_created = datetime.fromtimestamp(base_ts - age_days * 86400, tz=timezone.utc).isoformat()
        post_time = datetime.fromtimestamp(base_ts + (i * 140), tz=timezone.utc).isoformat()

        events.append({
            "id": f"seed-org-{i}",
            "topicKeyword": "clean air zone",
            "did": did,
            "handle": f"citizen-{i+100}.bsky.social",
            "authorCreatedAt": author_created,
            "text": f"{organic_texts[i % len(organic_texts)]} #CleanAirZone",
            "createdAt": post_time,
            "links": [],
            "hashtags": ["#cleanairzone"],
        })

    return events
