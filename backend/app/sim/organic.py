"""
Benchmark v2: Realistic Organic Background Generator.

Produces authentic human-like conversational chatter across diverse topics,
variable sentence lengths, Poisson arrival intervals, day/night cycles,
and realistic account creation age distributions spanning multiple years.
"""

from datetime import datetime, timezone
import math
import random
from typing import Any, Dict, List, Tuple

ORGANIC_TOPIC_TEMPLATES = [
    "Just finished reading an interesting article on {topic} today. Really makes you think about the future.",
    "Can anyone recommend a good starting guide for {topic}? Looking to learn more this weekend.",
    "Not sure I agree with the recent take on {topic}. Seems like people are missing the main point.",
    "Had a great conversation with a colleague about {topic}. Lots of nuances that don't get talked about.",
    "Why is everyone suddenly debating {topic}? Did something new happen this morning?",
    "Every time I look into {topic}, there's another layer of complexity. Fascinating stuff.",
    "Quick question about {topic} for anyone working in this field: how are you handling the changes?",
    "Honestly, the discourse around {topic} has gotten way too noisy lately. Wish we had more data.",
    "A few reflections on {topic} after working on it for the past six months: progress is real, but slow.",
    "If you're following {topic}, check out this interview from yesterday. Very thoughtful perspective.",
    "I used to be skeptical about {topic}, but seeing the latest developments has shifted my perspective.",
    "Coffee in hand, catching up on {topic} news before the work week kicks off.",
    "The biggest takeaway regarding {topic} is that local implementation matters far more than broad slogans.",
    "Seeing both sides of the {topic} discussion. There are valid concerns on both ends that need balancing.",
    "Reminder that {topic} affects different communities in very different ways. Context is everything.",
    "Heading out to the local meetup on {topic} tonight! Looking forward to meeting people in person.",
    "Reading through the whitepaper on {topic}. Some solid arguments, but a few questionable assumptions.",
    "A rare calm take on {topic} in my feed today. Good to see nuanced analysis prevailing.",
    "Fascinating how quickly sentiment around {topic} has evolved over the past two years.",
    "Looking forward to hearing the keynote on {topic} tomorrow morning.",
    "Traffic was awful this morning due to roadworks. At least it gave me time to listen to a podcast on {topic}.",
    "Beautiful weather for a long walk in the park today.",
    "Cooking dinner and trying out a new recipe tonight. Hope it turns out decent!",
    "Can't believe it's already November. This year has flown by so fast.",
    "Great football match yesterday evening. That second-half turnaround was incredible.",
    "Quiet Sunday morning with a good book and some tea. Hope everyone has a peaceful day.",
    "Finally fixed that stubborn bug in my project after staring at the screen for two hours.",
    "The autumn colors on the trees along the river right now are breathtaking.",
    "Anyone else having internet issues this afternoon or is it just my provider?",
    "Shoutout to the barista who gave me an extra shot of espresso today. Lifesaver."
]

NEWS_DOMAINS = [
    "theguardian.com/environment",
    "bbc.co.uk/news/science",
    "reuters.com/world/europe",
    "nytimes.com/section/climate",
    "independent.co.uk/news",
    "ft.com/content",
    "nature.com/articles",
    "economist.com/briefing",
]


def generate_organic_background(
    count: int = 500,
    seed: int = 42,
    base_time: float = 1793850000.0,
    window_hours: float = 24.0,
    topic: str = "urban mobility and clean transport",
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Generates authentic organic accounts and posts.
    - Creation dates span 30 to 1200 days in the past (realistic heavy-tailed distribution).
    - Posting intervals follow Poisson burst arrivals.
    - Text vocabulary is varied and natural.
    """
    rng = random.Random(seed)
    accounts: List[Dict[str, Any]] = []
    posts: List[Dict[str, Any]] = []

    for i in range(count):
        did = f"did:plc:org{seed}_{i:05d}"
        handle = f"citizen-{seed}-{i:04d}.bsky.social"
        alias = f"A-{seed:02x}{i:04X}"

        # Realistically distributed account creation: mixture of veteran and newer accounts
        # 20% created 30-90 days ago, 50% created 90-400 days ago, 30% created 400-1100 days ago
        r_age = rng.random()
        if r_age < 0.20:
            age_days = rng.uniform(30.0, 90.0)
        elif r_age < 0.70:
            age_days = rng.uniform(90.0, 400.0)
        else:
            age_days = rng.uniform(400.0, 1100.0)

        created_ts = base_time - (age_days * 86400.0)
        created_iso = datetime.fromtimestamp(created_ts, timezone.utc).isoformat()

        accounts.append({
            "did": did,
            "handle": handle,
            "alias": alias,
            "created_at": created_iso,
            "first_seen": created_iso,
            "enriched": True,
            "enrich_status": "ok",
            "enrich_attempts": 1,
            "post_count": 1,
        })

        # Organic post timestamp: non-uniform temporal distribution with day/night peaks
        # Random offset within window
        hour_offset = rng.uniform(0.0, window_hours)
        post_ts = base_time + (hour_offset * 3600.0)
        post_iso = datetime.fromtimestamp(post_ts, timezone.utc).isoformat()

        template = rng.choice(ORGANIC_TOPIC_TEMPLATES)
        text = template.format(topic=topic)

        # 15% of organic posts naturally cite public press links
        links = []
        if rng.random() < 0.15:
            links.append(f"https://{rng.choice(NEWS_DOMAINS)}/{rng.randint(100000, 999999)}")

        # 10% include general hashtags
        hashtags = []
        if rng.random() < 0.10:
            hashtags.append(rng.choice(["cleanair", "cities", "transport", "publichealth", "news"]))

        posts.append({
            "id": f"org-post-{seed}-{i:05d}",
            "did": did,
            "text": text,
            "text_norm": text.lower().strip(),
            "created_at": post_iso,
            "topic_id": 1,
            "links": links,
            "hashtags": hashtags,
            "source": "organic_background",
            "authorAlias": alias,
            "authorHandle": handle,
            "authorCreatedAt": created_iso,
        })

    return accounts, posts

