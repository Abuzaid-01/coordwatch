"""One text and URL pipeline for live posts, the demo seed, replay, and the simulator."""
import re

from backend.app.db import get_connection, init_db, upsert_account
from backend.app.textutil import (
    apply_prepare,
    canonicalize_url,
    generate_hash_alias,
    host_in_set,
    prepare_post,
    prepare_text,
    urls_from_at_record,
    AUTHORITATIVE_DOMAINS,
)


def test_prepare_text_strips_tracked_url():
    prepared = prepare_post("Hello https://evil.example/a?utm_source=x")
    assert prepared["text_norm"] == "hello"
    assert prepared["links"] == ["https://evil.example/a"]
    assert prepare_text("Hello https://evil.example/a?utm_source=x") == "hello"


def test_scheme_less_bbc_url_matches_tracked_https_url():
    tracked = canonicalize_url("https://bbc.co.uk/news/1?utm_campaign=a")
    bare = canonicalize_url("bbc.co.uk/news/1?fbclid=z")
    www = canonicalize_url("https://www.bbc.co.uk/news/1?ref=homepage")
    assert tracked == "https://bbc.co.uk/news/1"
    assert bare == tracked
    assert www == tracked


def test_seed_shaped_and_live_shaped_events_match():
    raw = "Mayor confirms the fleet plan https://bbc.co.uk/news/1?utm_campaign=a&fbclid=z #CleanAir"
    seed_post = apply_prepare({"text": raw, "links": ["bbc.co.uk/news/1?fbclid=z"], "hashtags": ["#CleanAir"]})
    record = {
        "text": raw,
        "facets": [
            {
                "features": [
                    {
                        "$type": "app.bsky.richtext.facet#link",
                        "uri": "https://www.bbc.co.uk/news/1?utm_source=bsky",
                    }
                ]
            }
        ],
        "embed": {"external": {"uri": "https://bbc.co.uk/news/1?ref=share"}},
    }
    live = prepare_post(raw, extra_urls=urls_from_at_record(record))
    assert seed_post["text_norm"] == live["text_norm"]
    assert seed_post["links"] == live["links"]
    assert "cleanair" in seed_post["hashtags"]
    assert "https://bbc.co.uk/news/1" in live["links"]


def test_hash_alias_is_stable_and_stored_by_the_writer():
    init_db()
    did = "did:plc:textutil-alias-check"
    first = generate_hash_alias(did)
    assert generate_hash_alias("did:plc:abc") == generate_hash_alias("did:plc:abc")
    assert re.fullmatch(r"A-[0-9A-F]{6}", generate_hash_alias("did:plc:abc"))
    assert first == generate_hash_alias(did)
    assert re.fullmatch(r"A-[0-9A-F]{6}", first)
    upsert_account({"did": did, "handle": "alias-check.bsky.social"})
    conn = get_connection()
    try:
        row = conn.execute("SELECT alias FROM accounts WHERE did = ?", (did,)).fetchone()
    finally:
        conn.close()
    assert row["alias"] == first


def test_social_hosts_are_not_newsroom_domains():
    assert host_in_set("https://youtube.com/watch?v=abc", AUTHORITATIVE_DOMAINS) is False
    assert host_in_set("https://www.bbc.co.uk/news/1", AUTHORITATIVE_DOMAINS) is True
    assert host_in_set("https://news.bbc.co.uk/story", AUTHORITATIVE_DOMAINS) is True
    assert host_in_set("https://notbbc.co.uk/story", AUTHORITATIVE_DOMAINS) is False
