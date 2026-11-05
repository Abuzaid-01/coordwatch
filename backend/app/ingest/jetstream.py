"""
Phase 2: Bluesky Jetstream WebSocket Ingestor, TopicRegistry, Text Normalizer & Replay.
Connects to <JETSTREAM_URL>/subscribe?wantedCollections=app.bsky.feed.post
Includes Stage C & D improvements:
- C4: Word-boundary regex keyword matching
- C5: 6-character hash alias to eliminate collisions
- D1: In-memory TopicRegistry with pre-compiled regexes & batch queue
- D4: Structured logging and enhanced telemetry
- D5: Reconnect cursor support (time_us)
"""

import asyncio
from datetime import datetime, timezone
import hashlib
import json
import logging
from pathlib import Path
import re
from typing import Any, Dict, List, Optional, Set, Tuple

from ..config import settings
from ..db import get_connection, insert_live_post, upsert_account

logger = logging.getLogger(__name__)

URL_REGEX = re.compile(
    r"(?:https?://[^\s<>\"')\]\s]+|\b(?:[a-z0-9-]+\.)+(?:co\.uk|uk|org|com|net|io|gov|edu|info|news)/[^\s<>\"')\]\s]+)",
    re.IGNORECASE,
)
MENTION_REGEX = re.compile(r"@[a-z0-9._-]+", re.IGNORECASE)
HASHTAG_REGEX = re.compile(r"#[a-z0-9_]{2,50}", re.IGNORECASE)
NON_ALNUM_REGEX = re.compile(r"[^a-z0-9\s#]+", re.IGNORECASE)
MULTISPACE_REGEX = re.compile(r"\s+")


def normalize_text(text: str) -> str:
    """Lowercase, strip URLs and @mentions, strip punctuation noise, collapse spaces."""
    if not text:
        return ""
    cleaned = text.lower()
    cleaned = URL_REGEX.sub(" ", cleaned)
    cleaned = MENTION_REGEX.sub(" ", cleaned)
    cleaned = NON_ALNUM_REGEX.sub(" ", cleaned)
    cleaned = MULTISPACE_REGEX.sub(" ", cleaned)
    return cleaned.strip()


def extract_links(text: str) -> List[str]:
    if not text:
        return []
    matches = URL_REGEX.findall(text)
    results: List[str] = []
    for raw in matches:
        stripped = raw.strip().rstrip(".,;!?)]")
        cleaned = re.sub(r"^https?://", "", stripped, flags=re.IGNORECASE)
        cleaned = re.sub(r"^www\.", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"[?&]utm_[^&]+", "", cleaned).rstrip("/")
        if "." in cleaned and cleaned.lower() not in results:
            results.append(cleaned.lower())
    return results


def extract_hashtags(text: str) -> List[str]:
    if not text:
        return []
    matches = HASHTAG_REGEX.findall(text)
    seen: List[str] = []
    for tag in matches:
        low = tag.lower()
        if low not in seen:
            seen.append(low)
    return seen


def generate_hash_alias(did: str) -> str:
    """C5: 6 hex characters to avoid collision (16.7M unique aliases)."""
    digest = hashlib.sha256(did.strip().encode("utf-8")).hexdigest()
    return f"A-{digest[:6].upper()}"


class TopicRegistry:
    """D1: In-memory registry of active topics and compiled word-boundary regexes."""
    def __init__(self):
        self._topics: List[Dict[str, Any]] = []
        self._patterns: Dict[int, re.Pattern] = {}
        self.last_refreshed: Optional[str] = None

    def refresh(self) -> None:
        conn = get_connection()
        try:
            rows = conn.execute("SELECT id, keyword FROM topics").fetchall()
            self._topics = [{"id": r["id"], "keyword": r["keyword"]} for r in rows]
            self._patterns = {}
            for t in self._topics:
                kw = t["keyword"].strip()
                if len(kw) >= 2:
                    # C4: Word-boundary regex matching
                    try:
                        pattern = re.compile(rf"(?<!\w){re.escape(kw)}(?!\w)", re.IGNORECASE)
                        self._patterns[t["id"]] = pattern
                    except Exception as e:
                        logger.warning(f"Failed to compile regex for keyword '{kw}': {e}")
            self.last_refreshed = datetime.now(timezone.utc).isoformat()
        finally:
            conn.close()

    def match(self, text: str) -> List[Dict[str, Any]]:
        matched = []
        for t in self._topics:
            t_id = t["id"]
            pat = self._patterns.get(t_id)
            if pat and pat.search(text):
                matched.append(t)
        return matched


topic_registry = TopicRegistry()


class IngestState:
    def __init__(self):
        self.connected = False
        self.endpoint = settings.jetstream_url
        self.total_events_scanned = 0
        self.live_posts_ingested = 0
        self.accounts_enriched = 0
        self.recording_to_jsonl = False
        self.last_event_at: Optional[str] = None
        self.last_cursor: Optional[int] = None
        self.queue_size = 0
        self.events_per_sec = 0.0
        self.recent_live_sample: List[Dict[str, Any]] = []
        self.dirty_topics: Set[int] = set()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "connected": self.connected,
            "endpoint": self.endpoint,
            "totalEventsScanned": self.total_events_scanned,
            "livePostsIngested": self.live_posts_ingested,
            "accountsEnriched": self.accounts_enriched,
            "recordingToJsonl": self.recording_to_jsonl,
            "lastEventAt": self.last_event_at,
            "lastCursor": self.last_cursor,
            "queueSize": self.queue_size,
            "eventsPerSec": round(self.events_per_sec, 1),
            "recentLiveSample": self.recent_live_sample[:10],
        }


ingest_state = IngestState()


def get_ingest_telemetry() -> Dict[str, Any]:
    return ingest_state.to_dict()


def set_jsonl_recording(enabled: bool) -> Dict[str, Any]:
    ingest_state.recording_to_jsonl = enabled
    return ingest_state.to_dict()


# D1: Batch insert queue for incoming matched posts
post_queue: asyncio.Queue = asyncio.Queue(maxsize=5000)


async def _batch_insert_worker():
    """D1: Flushes matched posts from post_queue into SQLite every 1 second."""
    while True:
        try:
            batch = []
            while len(batch) < 100:
                try:
                    item = post_queue.get_nowait()
                    batch.append(item)
                except asyncio.QueueEmpty:
                    break

            ingest_state.queue_size = post_queue.qsize()

            if batch:
                conn = get_connection()
                try:
                    for item in batch:
                        upsert_account(item["account"], conn=conn)
                        insert_live_post(item["post"])
                        ingest_state.live_posts_ingested += 1
                        ingest_state.dirty_topics.add(item["post"]["topic_id"])
                finally:
                    conn.close()

            await asyncio.sleep(1.0)
        except Exception as e:
            logger.error(f"Error in batch insert worker: {e}", exc_info=True)
            await asyncio.sleep(2.0)


async def run_jetstream_ingestor():
    """Background WebSocket consumer connecting to Bluesky Jetstream."""
    try:
        import websockets  # type: ignore
    except ImportError:
        logger.warning("websockets package not available; Jetstream ingestor stopped.")
        return

    # Initialize topic registry
    topic_registry.refresh()
    # Start batch worker in background
    asyncio.create_task(_batch_insert_worker())

    backoff = 2.0
    urls = [settings.jetstream_url, settings.jetstream_fallback_url]
    url_idx = 0
    last_speed_check = datetime.now(timezone.utc).timestamp()
    events_at_check = 0

    while True:
        target_url = urls[url_idx % len(urls)]
        # D5: Append cursor if available
        connect_url = target_url
        if ingest_state.last_cursor:
            sep = "&" if "?" in target_url else "?"
            connect_url = f"{target_url}{sep}cursor={ingest_state.last_cursor}"

        ingest_state.endpoint = connect_url
        try:
            async with websockets.connect(connect_url, ping_interval=25, open_timeout=8.0) as ws:
                ingest_state.connected = True
                backoff = 2.0
                logger.info(f"Connected to Bluesky Jetstream at {target_url}")

                async for message in ws:
                    try:
                        event = json.loads(message)
                    except json.JSONDecodeError:
                        continue

                    ingest_state.total_events_scanned += 1
                    ingest_state.last_event_at = datetime.now(timezone.utc).isoformat()
                    time_us = event.get("time_us")
                    if time_us:
                        ingest_state.last_cursor = time_us

                    # Measure event speed
                    now_ts = datetime.now(timezone.utc).timestamp()
                    if now_ts - last_speed_check >= 5.0:
                        elapsed = now_ts - last_speed_check
                        ingest_state.events_per_sec = (ingest_state.total_events_scanned - events_at_check) / elapsed
                        events_at_check = ingest_state.total_events_scanned
                        last_speed_check = now_ts

                    if event.get("kind") != "commit":
                        continue
                    commit = event.get("commit") or {}
                    if (
                        commit.get("operation") != "create"
                        or commit.get("collection") != "app.bsky.feed.post"
                    ):
                        continue

                    record = commit.get("record") or {}
                    text = record.get("text", "")
                    if not isinstance(text, str) or not text.strip():
                        continue

                    # D1: Check matching topics in memory (fast)
                    matched_topics = topic_registry.match(text)
                    if not matched_topics:
                        continue

                    did = event.get("did", "")
                    created_at = record.get("createdAt") or datetime.now(timezone.utc).isoformat()
                    alias = generate_hash_alias(did)
                    norm = normalize_text(text)
                    links = extract_links(text)
                    tags = extract_hashtags(text)

                    for t in matched_topics:
                        post_id = f"live-{did[-8:]}-{commit.get('rkey', '') or int(datetime.now().timestamp())}"
                        try:
                            post_queue.put_nowait({
                                "account": {
                                    "did": did,
                                    "handle": f"{did[-8:]}.bsky.social",
                                    "alias": alias,
                                    "created_at": None,
                                    "first_seen": created_at,
                                    "enriched": False,
                                },
                                "post": {
                                    "id": post_id,
                                    "did": did,
                                    "text": text,
                                    "text_norm": norm,
                                    "created_at": created_at,
                                    "topic_id": t["id"],
                                    "links": links,
                                    "hashtags": tags,
                                    "source": "live",
                                }
                            })
                        except asyncio.QueueFull:
                            logger.warning("Post queue is full; dropping event to preserve stability.")

                        ingest_state.recent_live_sample.insert(0, {
                            "did": did,
                            "alias": alias,
                            "text": text[:180],
                            "matchedTopic": t["keyword"],
                            "createdAt": created_at,
                        })
                        if len(ingest_state.recent_live_sample) > 15:
                            ingest_state.recent_live_sample.pop()

        except Exception as e:
            ingest_state.connected = False
            logger.warning(f"Jetstream connection lost ({e}). Reconnecting in {backoff:.1f}s...")
            url_idx += 1
            await asyncio.sleep(backoff)
            backoff = min(30.0, backoff * 1.5)
