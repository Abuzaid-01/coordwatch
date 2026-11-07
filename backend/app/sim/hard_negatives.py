"""
Benchmark v2: 10 Realistic Hard Negative Scenarios (H1 - H10).

Innocent behaviors that share superficial attributes with coordinated campaigns:
- H1: Breaking news burst with share-button text (headline + canonical news link)
- H2: Fandom / community hashtag campaign (identical hashtag, distinct authentic commentary)
- H3: Signup wave after high-profile migration (same-day creation cohort, diverse organic chatter)
- H4: Legitimate news / RSS publisher bots (regular cadence, verified domains)
- H5: Brand / organization multi-account announcements (headquarters + regional accounts)
- H6: Public petition copy-paste (authentic grassroots citizens copying an appeal)
- H7: Viral meme / cultural catchphrase spreading organically across days
- H8: Quote-posts and translations of an official announcement
- H9: Live event burst (thousands reacting to a live sports goal or debate moment)
- H10: URL variations and tracking redirects pointing to the same editorial article
"""

from datetime import datetime, timezone
import random
from typing import Any, Dict, List, Tuple

from ..textutil import apply_prepare


def generate_hard_negative(
    scenario_id: str,
    base_time: float,
    seed: int,
    size: int = 15,
) -> Dict[str, Any]:
    """
    Generates authentic accounts and posts for hard negative scenarios.
    Ground truth label: 'coordinated_benign' or 'organic' (NEVER 'coordinated_inauthentic').
    """
    rng = random.Random(seed)
    accounts: List[Dict[str, Any]] = []
    posts: List[Dict[str, Any]] = []
    dids: List[str] = []

    group_label = f"hard_neg_{scenario_id.lower()}"

    if scenario_id == "H1":
        # Breaking news share-button burst: identical headline + link, veteran accounts, tight 3-minute burst
        headline = "Mayor announces £250M expansion for zero-emission city fleet: full breakdown"
        news_url = "https://bbc.co.uk/news/science-environment-6729012"
        for i in range(size):
            did = f"did:plc:hn1_{seed}_{i:03d}"
            dids.append(did)
            # Established accounts: created 200-900 days ago
            c_ts = base_time - (rng.uniform(200.0, 900.0) * 86400.0)
            c_iso = datetime.fromtimestamp(c_ts, timezone.utc).isoformat()
            accounts.append({
                "did": did, "handle": f"newsreader-{seed}-{i:03d}.bsky.social",
                "alias": f"A-HN1{i:03X}", "created_at": c_iso, "first_seen": c_iso,
                "enriched": True, "enrich_status": "ok", "enrich_attempts": 1, "post_count": 1,
            })
            # Burst timing: all within 180 seconds
            p_ts = base_time + rng.uniform(0.0, 180.0)
            posts.append({
                "id": f"hn1-post-{seed}-{i:03d}", "did": did,
                "text": f"{headline} {news_url}", "text_norm": headline.lower(),
                "created_at": datetime.fromtimestamp(p_ts, timezone.utc).isoformat(),
                "topic_id": 1, "links": [news_url], "hashtags": [],
                "source": "hard_negative_h1",
            })
        target_class = "coordinated_benign"

    elif scenario_id == "H2":
        # Fandom / community hashtag campaign: identical hashtag, but personal diverse text
        fandom_texts = [
            "Really hoping we get good news at the council vote tomorrow! We've worked so hard for this. #CleanAirForAll",
            "Walking through the city center today with the kids. Cleaner air is worth fighting for! #CleanAirForAll",
            "Huge thank you to everyone who showed up at the town hall meeting last night. #CleanAirForAll",
            "Just read the latest emissions report. The data speaks for itself. #CleanAirForAll",
            "Proud to stand with our local school community on this initiative! #CleanAirForAll",
            "Clean air should not be a political debate, it's basic healthcare for our children. #CleanAirForAll",
            "Reminder to email your local representative before Friday's deadline. Every voice counts! #CleanAirForAll",
        ]
        for i in range(size):
            did = f"did:plc:hn2_{seed}_{i:03d}"
            dids.append(did)
            c_ts = base_time - (rng.uniform(50.0, 600.0) * 86400.0)
            c_iso = datetime.fromtimestamp(c_ts, timezone.utc).isoformat()
            accounts.append({
                "did": did, "handle": f"supporter-{seed}-{i:03d}.bsky.social",
                "alias": f"A-HN2{i:03X}", "created_at": c_iso, "first_seen": c_iso,
                "enriched": True, "enrich_status": "ok", "enrich_attempts": 1, "post_count": 1,
            })
            p_ts = base_time + rng.uniform(0.0, 1800.0)
            txt = rng.choice(fandom_texts)
            posts.append({
                "id": f"hn2-post-{seed}-{i:03d}", "did": did,
                "text": txt, "text_norm": txt.lower(),
                "created_at": datetime.fromtimestamp(p_ts, timezone.utc).isoformat(),
                "topic_id": 1, "links": [], "hashtags": ["CleanAirForAll"],
                "source": "hard_negative_h2",
            })
        target_class = "coordinated_benign"

    elif scenario_id == "H3":
        # Platform signup wave: 20 accounts all created on the exact same day, but discussing diverse organic topics
        wave_created_ts = base_time - (14.0 * 86400.0)  # exactly 14 days ago
        for i in range(size):
            did = f"did:plc:hn3_{seed}_{i:03d}"
            dids.append(did)
            # All created within a 6-hour migration window
            c_ts = wave_created_ts + rng.uniform(0.0, 21600.0)
            c_iso = datetime.fromtimestamp(c_ts, timezone.utc).isoformat()
            accounts.append({
                "did": did, "handle": f"migrated-user-{seed}-{i:03d}.bsky.social",
                "alias": f"A-HN3{i:03X}", "created_at": c_iso, "first_seen": c_iso,
                "enriched": True, "enrich_status": "ok", "enrich_attempts": 1, "post_count": 1,
            })
            # Diverse posting timing across 12 hours
            p_ts = base_time + rng.uniform(0.0, 43200.0)
            txt = f"Enjoying the discussions here on Bluesky. Interesting perspectives on city policy #{i}."
            posts.append({
                "id": f"hn3-post-{seed}-{i:03d}", "did": did,
                "text": txt, "text_norm": txt.lower(),
                "created_at": datetime.fromtimestamp(p_ts, timezone.utc).isoformat(),
                "topic_id": 1, "links": [], "hashtags": [],
                "source": "hard_negative_h3",
            })
        target_class = "organic"

    elif scenario_id == "H4":
        # Legitimate news / RSS automation bots: post at clockwork regular intervals, but authoritative news
        for i in range(5):
            did = f"did:plc:hn4_{seed}_{i:03d}"
            dids.append(did)
            c_ts = base_time - (rng.uniform(300.0, 800.0) * 86400.0)
            c_iso = datetime.fromtimestamp(c_ts, timezone.utc).isoformat()
            accounts.append({
                "did": did, "handle": f"newsbot-{seed}-{i:02d}.press.bsky.social",
                "alias": f"A-RSS{i:02X}", "created_at": c_iso, "first_seen": c_iso,
                "enriched": True, "enrich_status": "ok", "enrich_attempts": 1, "post_count": 1,
            })
            p_ts = base_time + (i * 300.0)  # clockwork every 5 minutes
            txt = f"[Automated Feed] Transport update report #{i + 1} published by official press bureau: https://reuters.com/wire/city-dispatch-{i}"
            posts.append({
                "id": f"hn4-post-{seed}-{i:03d}", "did": did,
                "text": txt, "text_norm": txt.lower(),
                "created_at": datetime.fromtimestamp(p_ts, timezone.utc).isoformat(),
                "topic_id": 1, "links": [f"https://reuters.com/wire/city-dispatch-{i}"], "hashtags": [],
                "source": "hard_negative_h4",
            })
        target_class = "coordinated_benign"

    elif scenario_id == "H5":
        # Brand / organization multi-account posting (corporate + regional chapters)
        for i in range(6):
            did = f"did:plc:hn5_{seed}_{i:03d}"
            dids.append(did)
            c_ts = base_time - (500.0 * 86400.0)
            c_iso = datetime.fromtimestamp(c_ts, timezone.utc).isoformat()
            accounts.append({
                "did": did, "handle": f"green-org-branch-{i}.org.bsky.social",
                "alias": f"A-ORG{i:02X}", "created_at": c_iso, "first_seen": c_iso,
                "enriched": True, "enrich_status": "ok", "enrich_attempts": 1, "post_count": 1,
            })
            p_ts = base_time + rng.uniform(0.0, 60.0)
            txt = "We are proud to publish our annual sustainability and air quality report: https://gov.uk/sustainability-2026"
            posts.append({
                "id": f"hn5-post-{seed}-{i:03d}", "did": did,
                "text": txt, "text_norm": txt.lower(),
                "created_at": datetime.fromtimestamp(p_ts, timezone.utc).isoformat(),
                "topic_id": 1, "links": ["https://gov.uk/sustainability-2026"], "hashtags": [],
                "source": "hard_negative_h5",
            })
        target_class = "coordinated_benign"

    elif scenario_id == "H6":
        # Public petition / advocacy template: authentic citizens copying a petition letter
        petition_base = "Dear councilors: I am writing as a local resident to urge your vote in favor of neighborhood air monitoring."
        for i in range(size):
            did = f"did:plc:hn6_{seed}_{i:03d}"
            dids.append(did)
            c_ts = base_time - (rng.uniform(80.0, 700.0) * 86400.0)
            c_iso = datetime.fromtimestamp(c_ts, timezone.utc).isoformat()
            accounts.append({
                "did": did, "handle": f"resident-{seed}-{i:03d}.bsky.social",
                "alias": f"A-HN6{i:03X}", "created_at": c_iso, "first_seen": c_iso,
                "enriched": True, "enrich_status": "ok", "enrich_attempts": 1, "post_count": 1,
            })
            # Spread across 2 hours
            p_ts = base_time + rng.uniform(0.0, 7200.0)
            posts.append({
                "id": f"hn6-post-{seed}-{i:03d}", "did": did,
                "text": f"{petition_base} [Resident Ward #{i + 1}]",
                "text_norm": petition_base.lower(),
                "created_at": datetime.fromtimestamp(p_ts, timezone.utc).isoformat(),
                "topic_id": 1, "links": ["https://actionnetwork.org/petitions/cleanair"], "hashtags": [],
                "source": "hard_negative_h6",
            })
        target_class = "coordinated_benign"

    elif scenario_id == "H7":
        # Viral meme phrase spreading organically across hours
        meme_variations = [
            "can't breathe in this city without someone debating air monitors lol",
            "me trying to bike through the city without smelling exhaust fumes",
            "just checked the air quality index and well, it's certainly an index",
            "who else is checking the air pollution app every five minutes today",
        ]
        for i in range(size):
            did = f"did:plc:hn7_{seed}_{i:03d}"
            dids.append(did)
            c_ts = base_time - (rng.uniform(60.0, 800.0) * 86400.0)
            c_iso = datetime.fromtimestamp(c_ts, timezone.utc).isoformat()
            accounts.append({
                "did": did, "handle": f"memer-{seed}-{i:03d}.bsky.social",
                "alias": f"A-HN7{i:03X}", "created_at": c_iso, "first_seen": c_iso,
                "enriched": True, "enrich_status": "ok", "enrich_attempts": 1, "post_count": 1,
            })
            p_ts = base_time + rng.uniform(0.0, 14400.0)
            txt = rng.choice(meme_variations)
            posts.append({
                "id": f"hn7-post-{seed}-{i:03d}", "did": did,
                "text": txt, "text_norm": txt.lower(),
                "created_at": datetime.fromtimestamp(p_ts, timezone.utc).isoformat(),
                "topic_id": 1, "links": [], "hashtags": [],
                "source": "hard_negative_h7",
            })
        target_class = "organic"

    elif scenario_id == "H8":
        # Quote-posts and translations of official announcement
        for i in range(8):
            did = f"did:plc:hn8_{seed}_{i:03d}"
            dids.append(did)
            c_ts = base_time - (rng.uniform(100.0, 900.0) * 86400.0)
            c_iso = datetime.fromtimestamp(c_ts, timezone.utc).isoformat()
            accounts.append({
                "did": did, "handle": f"translator-{seed}-{i:02d}.bsky.social",
                "alias": f"A-HN8{i:02X}", "created_at": c_iso, "first_seen": c_iso,
                "enriched": True, "enrich_status": "ok", "enrich_attempts": 1, "post_count": 1,
            })
            p_ts = base_time + rng.uniform(60.0, 1200.0)
            txt = f"Translation/Summary of today's press release on clean air zone updates #{i + 1}"
            posts.append({
                "id": f"hn8-post-{seed}-{i:03d}", "did": did,
                "text": txt, "text_norm": txt.lower(),
                "created_at": datetime.fromtimestamp(p_ts, timezone.utc).isoformat(),
                "topic_id": 1, "links": ["https://tfl.gov.uk/clean-air-update"], "hashtags": [],
                "source": "hard_negative_h8",
            })
        target_class = "organic"

    elif scenario_id == "H9":
        # Live event reaction burst (all post within 30 seconds reacting to a live debate moment)
        reaction_phrases = [
            "WOW did anyone else just hear that question in the debate?!",
            "That answer from the council member was completely unexpected.",
            "Can't believe what was just said on the live stream right now.",
            "That was an incredible exchange during the public consultation.",
            "Watching the debate live and the tension in the room is palpable.",
        ]
        for i in range(size):
            did = f"did:plc:hn9_{seed}_{i:03d}"
            dids.append(did)
            c_ts = base_time - (rng.uniform(90.0, 850.0) * 86400.0)
            c_iso = datetime.fromtimestamp(c_ts, timezone.utc).isoformat()
            accounts.append({
                "did": did, "handle": f"watcher-{seed}-{i:03d}.bsky.social",
                "alias": f"A-HN9{i:03X}", "created_at": c_iso, "first_seen": c_iso,
                "enriched": True, "enrich_status": "ok", "enrich_attempts": 1, "post_count": 1,
            })
            # Ultra tight burst: all within 30 seconds
            p_ts = base_time + rng.uniform(0.0, 30.0)
            txt = rng.choice(reaction_phrases)
            posts.append({
                "id": f"hn9-post-{seed}-{i:03d}", "did": did,
                "text": txt, "text_norm": txt.lower(),
                "created_at": datetime.fromtimestamp(p_ts, timezone.utc).isoformat(),
                "topic_id": 1, "links": [], "hashtags": ["LondonDebateLive"],
                "source": "hard_negative_h9",
            })
        target_class = "organic"

    elif scenario_id == "H10":
        # Canonical URL differences: sharing same article via different shorteners / tracking tokens
        article_canonical = "https://theguardian.com/environment/2026/nov/city-air-report"
        for i in range(size):
            did = f"did:plc:hn10_{seed}_{i:03d}"
            dids.append(did)
            c_ts = base_time - (rng.uniform(100.0, 750.0) * 86400.0)
            c_iso = datetime.fromtimestamp(c_ts, timezone.utc).isoformat()
            accounts.append({
                "did": did, "handle": f"citizen-reader-{seed}-{i:03d}.bsky.social",
                "alias": f"A-H10{i:03X}", "created_at": c_iso, "first_seen": c_iso,
                "enriched": True, "enrich_status": "ok", "enrich_attempts": 1, "post_count": 1,
            })
            p_ts = base_time + rng.uniform(0.0, 3600.0)
            # Add diverse tracking params
            mutated_link = f"{article_canonical}?utm_source=feed_{i}&ref=share_btn"
            txt = f"Interesting piece in the Guardian today regarding urban air monitoring: {mutated_link}"
            posts.append({
                "id": f"hn10-post-{seed}-{i:03d}", "did": did,
                "text": txt, "text_norm": txt.lower(),
                "created_at": datetime.fromtimestamp(p_ts, timezone.utc).isoformat(),
                "topic_id": 1, "links": [mutated_link], "hashtags": [],
                "source": "hard_negative_h10",
            })
        target_class = "coordinated_benign"

    else:
        target_class = "organic"

    for post in posts:
        apply_prepare(post)

    return {
        "id": scenario_id,
        "name": f"Hard Negative {scenario_id}",
        "class": target_class,
        "accounts": accounts,
        "posts": posts,
        "dids": dids,
        "size": len(dids),
    }

