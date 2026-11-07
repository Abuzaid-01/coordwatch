"""
Phase 6: REST API Endpoints for CoordWatch FastAPI Backend.
Includes fixes:
- A6: 404 on missing cluster detail; topicId scoping
- B5: Offline evaluation caching via evaluation_runs table
- Route compatibility with frontend (?topicId= and path parameters)
"""

from datetime import datetime, timezone
import json
import logging
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from ..config import settings
from ..db import (
    analyze_and_persist_topic,
    create_or_get_topic,
    get_cached_topic_analysis,
    get_connection,
    get_stored_clusters,
    get_topic_posts_and_accounts,
    get_topics_list,
)
from ..ingest.jetstream import get_ingest_telemetry, set_jsonl_recording, topic_registry
from ..sim.benchmark_v2 import run_benchmark_v2_suite

logger = logging.getLogger(__name__)
router = APIRouter()


class TopicCreatePayload(BaseModel):
    keyword: str = Field(..., min_length=2, max_length=120)


class AnalysisRunPayload(BaseModel):
    topicId: int = Field(default=1)
    replayBurst: Optional[bool] = Field(default=False)


class IngestRecordPayload(BaseModel):
    enabled: bool = Field(default=False)


class EvalRunPayload(BaseModel):
    organicCount: Optional[int] = Field(default=500, ge=100, le=1000)
    seed: Optional[int] = Field(default=42)


@router.get("/health")
def get_health() -> Dict[str, Any]:
    return {
        "status": "ok",
        "service": "coordwatch-fastapi",
        "version": settings.version,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "jetstream": get_ingest_telemetry(),
    }


@router.get("/topics")
def list_topics() -> Dict[str, Any]:
    return {
        "topics": get_topics_list(),
        "ingest": get_ingest_telemetry(),
    }


@router.post("/topics")
def create_topic(payload: TopicCreatePayload) -> Dict[str, Any]:
    kw = payload.keyword.strip()
    if len(kw) < 2:
        raise HTTPException(status_code=400, detail="Keyword must be at least 2 characters.")
    topic = create_or_get_topic(kw, source="live")
    # Refresh in-memory topic registry immediately
    topic_registry.refresh()
    return {
        "topic": topic,
        "topics": get_topics_list(),
    }


@router.get("/topics/{topic_id}/summary")
@router.get("/topics/{topic_id}/stats")
def get_topic_summary(topic_id: int) -> Dict[str, Any]:
    topics = get_topics_list()
    found = next((t for t in topics if t["id"] == topic_id), None)
    if not found:
        raise HTTPException(status_code=404, detail=f"Topic {topic_id} not found")
    clusters = get_stored_clusters(topic_id)
    top_score = clusters[0]["score"] if clusters else 0
    return {
        "topicId": found["id"],
        "keyword": found["keyword"],
        "mode": found["mode"],
        "source": found.get("source", "live"),
        "postCount": found["postCount"],
        "accountCount": found["accountCount"],
        "clusterCount": found["clusterCount"],
        "highRiskClusterCount": found["highRiskClusterCount"],
        "topClusterScore": top_score,
        "lastUpdate": found["lastAnalyzedAt"] or found["startedAt"],
        "ingest": get_ingest_telemetry(),
    }


# Support both /topics/{id}/graph and /graph?topicId=N
@router.get("/topics/{topic_id}/graph")
@router.get("/graph")
def get_topic_graph(
    topic_id: Optional[int] = None,
    topicId: Optional[int] = Query(default=None),
) -> Dict[str, Any]:
    tid = topic_id or topicId or 1
    analysis = get_cached_topic_analysis(tid)
    return analysis.get("graph", {"nodes": [], "links": []})


# Support both /topics/{id}/clusters and /clusters?topicId=N
@router.get("/topics/{topic_id}/clusters")
@router.get("/clusters")
def get_topic_clusters(
    topic_id: Optional[int] = None,
    topicId: Optional[int] = Query(default=None),
) -> Dict[str, Any]:
    tid = topic_id or topicId or 1
    clusters = get_stored_clusters(tid)
    return {"clusters": clusters}


# A6 FIX: Cluster detail returns 404 when cluster not found, never a fallback cluster
@router.get("/clusters/{cluster_id}")
def get_cluster_detail(
    cluster_id: str,
    topicId: int = Query(..., description="Topic ID required for cluster forensic lookup"),
) -> Dict[str, Any]:
    clusters = get_stored_clusters(topicId)
    found = next((c for c in clusters if c["id"] == cluster_id), None)
    if not found:
        raise HTTPException(status_code=404, detail=f"Cluster {cluster_id} not found in topic {topicId}")
    return {"cluster": found}


# Support both /topics/{id}/timeline and /timeline?topicId=N
@router.get("/topics/{topic_id}/timeline")
@router.get("/timeline")
def get_topic_timeline(
    topic_id: Optional[int] = None,
    topicId: Optional[int] = Query(default=None),
) -> Dict[str, Any]:
    tid = topic_id or topicId or 1
    analysis = get_cached_topic_analysis(tid)
    return {"timeline": analysis.get("timeline", [])}


@router.get("/topics/{topic_id}/posts")
def get_topic_posts(topic_id: int) -> Dict[str, Any]:
    posts, _ = get_topic_posts_and_accounts(topic_id)
    return {"posts": list(reversed(posts[-100:]))}


@router.post("/analysis/run")
def trigger_analysis(payload: AnalysisRunPayload) -> Dict[str, Any]:
    topics = get_topics_list()
    found = next((t for t in topics if t["id"] == payload.topicId), None)
    if not found:
        raise HTTPException(status_code=404, detail=f"Topic {payload.topicId} not found")

    result = analyze_and_persist_topic(payload.topicId)
    updated_topics = get_topics_list()
    topic = next((t for t in updated_topics if t["id"] == payload.topicId), found)
    return {
        "status": "analyzed",
        "topic": topic,
        "clusters": result["clusters"],
        "graph": result["graph"],
        "timeline": result["timeline"],
    }


@router.post("/ingest/record")
def toggle_ingest_recording(payload: IngestRecordPayload) -> Dict[str, Any]:
    return {"ingest": set_jsonl_recording(payload.enabled)}


# B5: Reads from evaluation_runs table if cached, or runs once and caches
@router.get("/evaluation/latest")
def get_evaluation_latest() -> Dict[str, Any]:
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT report_json FROM evaluation_runs ORDER BY id DESC LIMIT 1"
        ).fetchone()
        if row:
            try:
                return json.loads(row["report_json"])
            except Exception:
                pass
    finally:
        conn.close()

    return {
        "status": "not_run",
        "detail": "No benchmark is stored. Use the lab button or python -m backend.app.sim.run_eval.",
    }


@router.post("/evaluation/run")
def run_evaluation(payload: EvalRunPayload) -> Dict[str, Any]:
    count = min(80, max(40, payload.organicCount or 80))
    seed = payload.seed if payload.seed is not None else 42
    # Lab sample: two seeds. The 10-seed published run stays on the command line.
    res = run_benchmark_v2_suite(
        seeds=[seed, seed + 1],
        test_seeds=[seed + 100, seed + 101],
        organic_count=count,
        n_permutations=50,
        evasion_seeds=[seed],
        label="lab sample",
    )

    conn = get_connection()
    try:
        now = datetime.now(timezone.utc).isoformat()
        conn.execute(
            "INSERT INTO evaluation_runs (report_json, computed_at) VALUES (?, ?)",
            (json.dumps(res), now),
        )
        conn.commit()
    finally:
        conn.close()
    return res
