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
import json
import logging
from pathlib import Path
import re
from typing import Any, Dict, List, Optional, Set, Tuple

from ..config import settings
from ..db import get_connection, insert_live_post, upsert_account
from ..textutil import generate_hash_alias, prepare_post, prepare_text, urls_from_at_record

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
    return prepare_text(text)


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
        self.dropped_events = 0
        self.high_water_us: Optional[int] = None
        # True after QueueFull until the next connection. The mark must not
        # jump past an event that was not queued.
        self.cursor_blocked = False
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
            "droppedEvents": self.dropped_events,
            "cursorBlocked": self.cursor_blocked,
            "recentLiveSample": self.recent_live_sample[:10],
        }


def begin_firehose_connection(state: IngestState) -> None:
    """A new socket replays from the durable cursor, so the in-memory mark restarts there."""
    state.connected = True
    state.cursor_blocked = False
    state.high_water_us = state.last_cursor


def note_firehose_position(
    state: IngestState,
    time_us: Optional[int],
    *,
    matched: bool,
    fully_queued: bool,
    queue_empty: bool = False,
) -> None:
    """Move the high-water mark for one firehose event.

    A post that matched no topic is fully handled, so the mark moves at once.
    A matching post moves the mark only after every topic copy was queued.
    QueueFull freezes the mark: a later event must not acknowledge past the drop.
    When the queue is empty, a non-matching event is also a durable cursor,
    because nothing earlier is still waiting to be written.
    """
    if not time_us:
        return
    if matched and not fully_queued:
        state.cursor_blocked = True
        return
    if state.cursor_blocked:
        return
    state.high_water_us = int(time_us)
    if (not matched) and queue_empty:
        state.last_cursor = state.high_water_us


def ack_durable_cursor(state: IngestState, *, queue_empty: bool, committed_us: int) -> None:
    """Advance last_cursor only through events that are stored and not past a drop."""
    if state.cursor_blocked:
        if committed_us and (state.high_water_us is None or committed_us <= state.high_water_us):
            state.last_cursor = int(committed_us)
        return
    if queue_empty and state.high_water_us:
        state.last_cursor = state.high_water_us
    elif committed_us:
        state.last_cursor = int(committed_us)


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
                    committed_us = 0
                    for item in batch:
                        upsert_account(item["account"], conn=conn)
                        insert_live_post(item["post"], conn=conn)
                        ingest_state.live_posts_ingested += 1
                        ingest_state.dirty_topics.add(item["post"]["topic_id"])
                        committed_us = max(committed_us, int(item.get("time_us") or 0))
                    conn.commit()
                    ack_durable_cursor(
                        ingest_state,
                        queue_empty=post_queue.empty(),
                        committed_us=committed_us,
                    )
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
                begin_firehose_connection(ingest_state)
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

                    # C7: Language filter (filters out non-English posts when langs is specified)
                    langs = record.get("langs") or []
                    if langs and not any(isinstance(lang, str) and lang.lower().startswith("en") for lang in langs):
                        continue

                    # D1: Check matching topics in memory (fast)
                    matched_topics = topic_registry.match(text)
                    if not matched_topics:
                        note_firehose_position(
                            ingest_state,
                            time_us,
                            matched=False,
                            fully_queued=False,
                            queue_empty=post_queue.empty(),
                        )
                        continue

                    did = event.get("did", "")
                    created_at = record.get("createdAt") or datetime.now(timezone.utc).isoformat()
                    alias = generate_hash_alias(did)
                    prepared = prepare_post(text, extra_urls=urls_from_at_record(record))

                    fully_queued = True
                    for t in matched_topics:
                        post_id = f"live-{did[-8:]}-{commit.get('rkey', '') or int(datetime.now().timestamp())}"
                        try:
                            post_queue.put_nowait({
                                "time_us": time_us,
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
                                    "text_norm": prepared["text_norm"],
                                    "created_at": created_at,
                                    "topic_id": t["id"],
                                    "links": prepared["links"],
                                    "hashtags": prepared["hashtags"],
                                    "source": "live",
                                }
                            })
                            ingest_state.recent_live_sample.insert(0, {
                                "did": did,
                                "alias": alias,
                                "text": text[:180],
                                "matchedTopic": t["keyword"],
                                "createdAt": created_at,
                            })
                            if len(ingest_state.recent_live_sample) > 15:
                                ingest_state.recent_live_sample.pop()
                        except asyncio.QueueFull:
                            ingest_state.dropped_events += 1
                            fully_queued = False
                            logger.warning("Post queue is full; dropping event without advancing the cursor.")
                    note_firehose_position(
                        ingest_state,
                        time_us,
                        matched=True,
                        fully_queued=fully_queued,
                        queue_empty=post_queue.empty(),
                    )

        except Exception as e:
            ingest_state.connected = False
            logger.warning(f"Jetstream connection lost ({e}). Reconnecting in {backoff:.1f}s...")
            url_idx += 1
            await asyncio.sleep(backoff)
            backoff = min(30.0, backoff * 1.5)
