"""
Script to safely export enriched posts and real account creation dates to sample_posts.jsonl.
Reads from SQLite database after enrichment worker has fetched real registration dates.
"""

from datetime import datetime, timezone
import json
import logging
from pathlib import Path
import sys

# Ensure backend can be imported
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.app.config import settings
from backend.app.db import get_connection

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def export_sample_dataset(output_path: Path = None, topic_id: int = None, limit: int = 500) -> int:
    target_path = output_path or settings.sample_jsonl_path
    target_path.parent.mkdir(parents=True, exist_ok=True)

    conn = get_connection()
    try:
        query = """
        SELECT
            p.id, p.topic_id, p.did, p.text, p.created_at, p.links, p.hashtags, p.source,
            a.handle, a.alias, a.created_at as author_created_at, a.enriched,
            t.keyword as topic_keyword
        FROM posts p
        JOIN accounts a ON p.did = a.did
        LEFT JOIN topics t ON p.topic_id = t.id
        WHERE (a.created_at IS NOT NULL OR a.enriched = 1)
        """
        params = []
        if topic_id:
            query += " AND p.topic_id = ?"
            params.append(topic_id)

        query += " ORDER BY p.created_at ASC LIMIT ?"
        params.append(limit)

        rows = conn.execute(query, tuple(params)).fetchall()
        logger.info(f"Fetched {len(rows)} enriched post records from database.")

        count = 0
        with target_path.open("w", encoding="utf-8") as f:
            for r in rows:
                try:
                    links = json.loads(r["links"])
                except Exception:
                    links = []
                try:
                    hashtags = json.loads(r["hashtags"])
                except Exception:
                    hashtags = []

                record = {
                    "id": r["id"],
                    "topicKeyword": r["topic_keyword"] or "general",
                    "did": r["did"],
                    "handle": r["handle"],
                    "alias": r["alias"],
                    "authorCreatedAt": r["author_created_at"],
                    "text": r["text"],
                    "createdAt": r["created_at"],
                    "links": links,
                    "hashtags": hashtags,
                    "source": r["source"],
                }
                f.write(json.dumps(record) + "\n")
                count += 1

        logger.info(f"Successfully exported {count} enriched posts to {target_path}")
        return count
    finally:
        conn.close()


if __name__ == "__main__":
    export_sample_dataset()
