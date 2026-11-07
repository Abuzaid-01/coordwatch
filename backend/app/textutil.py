"""One text and URL pipeline for live posts, demo seed, replay, and the simulator.

Every writer calls prepare_post. Analysis reads the same fields, so the
benchmark measures the detector the dashboard runs.
"""

from __future__ import annotations

import hashlib
import re
from typing import Any, Dict, Iterable, List, Optional
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

URL_REGEX = re.compile(
    r"(?:https?://[^\s<>\"')\]]+|\b(?:[a-z0-9-]+\.)+(?:co\.uk|uk|org|com|net|io|gov|edu|info|news)/[^\s<>\"')\]]*)",
    re.IGNORECASE,
)
MENTION_REGEX = re.compile(r"@[a-z0-9._-]+", re.IGNORECASE)
HASHTAG_REGEX = re.compile(r"#[a-z0-9_]{2,50}", re.IGNORECASE)
NON_ALNUM_REGEX = re.compile(r"[^a-z0-9\s#]+", re.IGNORECASE)
MULTISPACE_REGEX = re.compile(r"\s+")

TRACKING_PARAMS = {
    "utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content",
    "ref", "ref_src", "source", "fbclid", "gclid", "mc_cid", "mc_eid",
    "igshid", "t", "s", "si", "feature",
}

# Newsroom and government hosts. A shared headline on one of these, from
# accounts whose creation dates are spread out, is classified as news sharing.
AUTHORITATIVE_DOMAINS = {
    "bbc.co.uk",
    "bbc.com",
    "tfl.gov.uk",
    "theguardian.com",
    "reuters.com",
    "gov.uk",
    "wikipedia.org",
    "nytimes.com",
    "ft.com",
    "nature.com",
}

# Rarity discount also covers social and video hosts. Those hosts do not
# qualify a cluster as a news burst. AUTHORITATIVE_DOMAINS stays the single
# newsroom list; this set only adds the social hosts.
POPULAR_DOMAINS = AUTHORITATIVE_DOMAINS | {
    "youtube.com",
    "youtu.be",
    "sky.com",
    "bsky.app",
    "x.com",
    "twitter.com",
}


def generate_hash_alias(did: str) -> str:
    """Stable public alias. Six hex characters, 16.7M values, from SHA-256."""
    digest = hashlib.sha256((did or "").strip().encode("utf-8")).hexdigest()
    return f"A-{digest[:6].upper()}"


def prepare_text(text: str) -> str:
    """Lowercase, strip URLs and mentions, drop punctuation, collapse spaces."""
    if not text:
        return ""
    cleaned = text.lower()
    cleaned = URL_REGEX.sub(" ", cleaned)
    cleaned = MENTION_REGEX.sub(" ", cleaned)
    cleaned = NON_ALNUM_REGEX.sub(" ", cleaned)
    cleaned = MULTISPACE_REGEX.sub(" ", cleaned)
    return cleaned.strip()


def _host_matches(host: str, domain: str) -> bool:
    return host == domain or host.endswith("." + domain)


def host_of(url: str) -> str:
    canonical = canonicalize_url(url)
    if not canonical:
        return ""
    return urlparse(canonical).netloc.lower()


def host_in_set(url: str, domains: Iterable[str]) -> bool:
    host = host_of(url)
    if not host:
        return False
    return any(_host_matches(host, domain) for domain in domains)


def canonicalize_url(url: str) -> str:
    """Absolute URL with tracking parameters removed.

    Scheme-less hosts (bbc.co.uk/news/1?fbclid=z) are accepted. urlparse
    treats those as a path, so a missing netloc is retried with https://.
    """
    if not url or not isinstance(url, str):
        return ""
    raw = url.strip().strip(".,;!?)>]\"'")
    if not raw:
        return ""
    try:
        parsed = urlparse(raw)
        if not parsed.netloc:
            parsed = urlparse("https://" + raw)
        if not parsed.netloc or "." not in parsed.netloc:
            return ""
        scheme = (parsed.scheme or "https").lower()
        if scheme not in ("http", "https"):
            scheme = "https"
        netloc = parsed.netloc.lower()
        if netloc.startswith("www."):
            netloc = netloc[4:]
        if "@" in netloc:
            netloc = netloc.split("@", 1)[1]
        if ":" in netloc:
            host, port = netloc.rsplit(":", 1)
            if port.isdigit() and (
                (scheme == "http" and port == "80") or (scheme == "https" and port == "443")
            ):
                netloc = host
        path = parsed.path or "/"
        if path != "/":
            path = path.rstrip("/")
        pairs = parse_qsl(parsed.query, keep_blank_values=False)
        clean_pairs = [(k, v) for k, v in pairs if k.lower() not in TRACKING_PARAMS and not k.lower().startswith("utm_")]
        clean_pairs.sort()
        return urlunparse((scheme, netloc, path, "", urlencode(clean_pairs), ""))
    except Exception:
        return ""


def extract_links(text: str) -> List[str]:
    if not text:
        return []
    found: List[str] = []
    for match in URL_REGEX.findall(text):
        canonical = canonicalize_url(match)
        if canonical and canonical not in found:
            found.append(canonical)
    return found


def extract_hashtags(text: str) -> List[str]:
    if not text:
        return []
    found: List[str] = []
    for tag in HASHTAG_REGEX.findall(text):
        low = tag.lower().lstrip("#")
        if low and low not in found:
            found.append(low)
    return found


def urls_from_at_record(record: Optional[Dict[str, Any]]) -> List[str]:
    """Link facets and external embeds. Bluesky often omits the URL from text."""
    if not isinstance(record, dict):
        return []
    urls: List[str] = []

    def add(value: Any) -> None:
        if isinstance(value, str) and value and value not in urls:
            urls.append(value)

    for facet in record.get("facets") or []:
        if not isinstance(facet, dict):
            continue
        for feature in facet.get("features") or []:
            if isinstance(feature, dict):
                add(feature.get("uri"))
    embed = record.get("embed") or {}
    if isinstance(embed, dict):
        external = embed.get("external") or {}
        if isinstance(external, dict):
            add(external.get("uri"))
        media = embed.get("media") or {}
        if isinstance(media, dict):
            media_external = media.get("external") or {}
            if isinstance(media_external, dict):
                add(media_external.get("uri"))
    return urls


def prepare_post(text: str, extra_urls: Optional[Iterable[str]] = None) -> Dict[str, Any]:
    """Normalized text plus canonical links and hashtags for one raw post."""
    links: List[str] = extract_links(text or "")
    for raw_url in extra_urls or []:
        canonical = canonicalize_url(raw_url)
        if canonical and canonical not in links:
            links.append(canonical)
    return {
        "text_norm": prepare_text(text or ""),
        "links": links,
        "hashtags": extract_hashtags(text or ""),
    }


def apply_prepare(post: Dict[str, Any]) -> Dict[str, Any]:
    """Overwrite text_norm, links, and hashtags from the raw text and any stored URLs."""
    prepared = prepare_post(post.get("text") or "", extra_urls=post.get("links") or [])
    explicit_tags = []
    for tag in post.get("hashtags") or []:
        if not isinstance(tag, str):
            continue
        low = tag.lower().lstrip("#")
        if low and low not in explicit_tags:
            explicit_tags.append(low)
    hashtags = list(prepared["hashtags"])
    for tag in explicit_tags:
        if tag not in hashtags:
            hashtags.append(tag)
    post["text_norm"] = prepared["text_norm"]
    post["links"] = prepared["links"]
    post["hashtags"] = hashtags
    return post
