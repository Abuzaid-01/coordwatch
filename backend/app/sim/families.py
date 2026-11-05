"""
Benchmark v2: 12 Randomized Bot Campaign Generator Families (F1 - F12).

Draws parameters from random distributions on each run rather than static templates:
- F1: Copypasta Ring (identical text & campaign URL)
- F2: Slot-Filling Template Network (dynamic combinatorial grammar)
- F3: Paraphrase Farm (distinct per-bot lexical rewrites and synonym substitutions)
- F4: Coordinated Hashtag Ring (identical hashtag cascades, varied prose)
- F5: Link Amplifier Network (target domain amplification with query token mutations)
- F6: Co-Repost Ring (synchronized amplification cascades)
- F7: Sleeper Account Network (aged dormant accounts with long inactivity gap)
- F8: Slow Drip Campaign (diluted temporal coordination over hours/days with jitter)
- F9: Human-In-The-Loop Network (hybrid authentic and astroturfed posting)
- F10: Camouflage Network (bots interleave authentic chatter with narrative attack)
- F11: Scattered Sybil Network (account registration spaced out over months)
- F12: Small Covert Cell (micro-networks of 3-6 accounts)
"""

from datetime import datetime, timezone
import math
import random
from typing import Any, Dict, List, Optional, Tuple

SYNONYM_MAP = {
    "stop": ["halt", "end", "block", "cancel", "oppose", "terminate"],
    "terrible": ["disastrous", "destructive", "harmful", "corrupt", "unjust", "awful"],
    "policy": ["scheme", "mandate", "agenda", "regulation", "measure", "initiative"],
    "now": ["immediately", "today", "without delay", "right now", "urgently"],
    "scandal": ["conspiracy", "coverup", "injustice", "disaster", "betrayal"],
    "expose": ["reveal", "uncover", "show", "publish", "spotlight"],
    "report": ["dossier", "investigation", "leak", "document", "findings"],
    "truth": ["reality", "facts", "evidence", "real story", "untold story"],
}


def _per_bot_paraphrase(text: str, rng: random.Random) -> str:
    """True per-bot distinct lexical rewrite: swaps synonyms and restructures phrases."""
    words = text.split()
    new_words = []
    for w in words:
        clean = w.lower().strip(".,!?:;")
        punct = w[len(clean):] if len(w) > len(clean) else ""
        if clean in SYNONYM_MAP and rng.random() < 0.65:
            replacement = rng.choice(SYNONYM_MAP[clean])
            if w[0].isupper():
                replacement = replacement.capitalize()
            new_words.append(replacement + punct)
        else:
            new_words.append(w)
    return " ".join(new_words)


def generate_bot_family(
    family_id: str,
    campaign_id: str,
    size: int,
    base_time: float,
    seed: int,
    target_url: str = "https://cleanair-truth-london.org/dossier",
    campaign_hashtag: str = "AxeTheTaxLondon",
) -> Dict[str, Any]:
    """
    Generates accounts and posts for one of the 12 randomized campaign families.
    """
    rng = random.Random(seed)
    accounts: List[Dict[str, Any]] = []
    posts: List[Dict[str, Any]] = []
    dids: List[str] = []

    # 1. Account age parameters based on family
    if family_id in ("F7", "F8"):  # Sleeper accounts or slow drip
        # Aged accounts: created 180 to 600 days ago
        base_age_days = rng.uniform(180.0, 550.0)
        age_spread_hours = rng.uniform(24.0, 720.0)
    elif family_id == "F11":  # Scattered sybil
        # Registration spread over 6 to 12 months
        base_age_days = rng.uniform(60.0, 360.0)
        age_spread_hours = rng.uniform(240.0, 2400.0)
    else:
        # Standard fresh sybil batch created within a 12 to 48 hour window
        base_age_days = rng.uniform(5.0, 14.0)
        age_spread_hours = rng.uniform(2.0, 40.0)

    # 2. Timing parameters
    if family_id == "F8":  # Slow drip
        burst_span_sec = rng.uniform(7200.0, 86400.0)  # 2 to 24 hours
    elif family_id in ("F1", "F6"):  # Copypasta / repost burst
        burst_span_sec = rng.uniform(20.0, 180.0)  # very tight (20s - 3m)
    else:
        burst_span_sec = rng.uniform(60.0, 600.0)  # standard burst (1m - 10m)

    # Base seed narrative text
    base_narratives = [
        "Stop this terrible policy now. Read the full leaked report before it gets censored:",
        "Unbelievable scandal uncovered in the city transport plan. The real truth is out:",
        "They claimed this scheme was about health. It's actually a revenue trap. Evidence here:",
        "Official data completely contradicts the mayor's narrative. See the leaked findings:",
    ]
    core_text = rng.choice(base_narratives)

    for i in range(size):
        did = f"did:plc:{campaign_id.lower()}_{i:03d}"
        handle = f"activist-{campaign_id.lower()}-{i:03d}.bsky.social"
        alias = f"A-{campaign_id[:3].upper()}{i:03X}"
        dids.append(did)

        # Account creation timestamp
        acct_age_sec = (base_age_days * 86400.0) + rng.uniform(-age_spread_hours * 1800.0, age_spread_hours * 1800.0)
        acct_created_ts = base_time - max(86400.0, acct_age_sec)
        acct_created_iso = datetime.fromtimestamp(acct_created_ts, timezone.utc).isoformat()

        accounts.append({
            "did": did,
            "handle": handle,
            "alias": alias,
            "created_at": acct_created_iso,
            "first_seen": acct_created_iso,
            "enriched": True,
            "enrich_status": "ok",
            "enrich_attempts": 1,
            "post_count": 1,
        })

        # Post timing
        post_offset = (i / max(1, size - 1)) * burst_span_sec + rng.uniform(-5.0, 5.0)
        post_ts = base_time + post_offset
        post_iso = datetime.fromtimestamp(post_ts, timezone.utc).isoformat()

        # Text generation per family
        links = [target_url]
        hashtags = [campaign_hashtag]

        if family_id == "F1":  # Exact copypasta
            post_text = f"{core_text} {target_url} #{campaign_hashtag}"
        elif family_id == "F2":  # Slot-filling templates
            v_halt = rng.choice(SYNONYM_MAP["stop"])
            v_adj = rng.choice(SYNONYM_MAP["terrible"])
            v_pol = rng.choice(SYNONYM_MAP["policy"])
            post_text = f"We must {v_halt} this {v_adj} {v_pol} immediately! Findings: {target_url} #{campaign_hashtag}"
        elif family_id == "F3":  # True per-bot paraphrase farm
            paraphrased = _per_bot_paraphrase(core_text, rng)
            post_text = f"{paraphrased} {target_url} #{campaign_hashtag}"
        elif family_id == "F4":  # Hashtag ring
            varied_lead = rng.choice([
                "Massive news dropping today.",
                "Have you seen what's in the latest public release?",
                "The numbers simply do not add up.",
                "Pay attention to what is happening here.",
            ])
            post_text = f"{varied_lead} #{campaign_hashtag} #LondonTransport #{campaign_hashtag}Now {target_url}"
            hashtags = [campaign_hashtag, "LondonTransport", f"{campaign_hashtag}Now"]
        elif family_id == "F5":  # Link amplifier with URL mutation
            # Random query parameter mutation
            mutated_url = f"{target_url}?src=ref{i}&cid={rng.randint(1000, 9999)}"
            links = [mutated_url]
            post_text = f"Crucial evidence documented here: {mutated_url}"
        elif family_id == "F6":  # Repost ring
            post_text = f"RT: {core_text} {target_url} #{campaign_hashtag}"
        elif family_id == "F7":  # Sleeper accounts
            post_text = f"{core_text} {target_url} #{campaign_hashtag}"
        elif family_id == "F8":  # Slow drip
            paraphrased = _per_bot_paraphrase(core_text, rng)
            post_text = f"{paraphrased} {target_url} #{campaign_hashtag}"
        elif family_id == "F9":  # Human-in-the-loop (30% post conversational variations)
            if i % 3 == 0:
                post_text = f"I've been looking into this and {core_text.lower()} {target_url}"
            else:
                post_text = f"{core_text} {target_url} #{campaign_hashtag}"
        elif family_id == "F10":  # Camouflage: add a normal post first
            norm_post_ts = post_ts - rng.uniform(1800.0, 7200.0)
            posts.append({
                "id": f"camo-post-{campaign_id}-{i:03d}",
                "did": did,
                "text": "Quiet day today, just having some coffee and checking the news.",
                "text_norm": "quiet day today just having some coffee and checking the news",
                "created_at": datetime.fromtimestamp(norm_post_ts, timezone.utc).isoformat(),
                "topic_id": 1,
                "links": [],
                "hashtags": [],
                "source": "planted_bot_camo",
                "authorAlias": alias,
                "authorHandle": handle,
                "authorCreatedAt": acct_created_iso,
            })
            post_text = f"{core_text} {target_url} #{campaign_hashtag}"
        elif family_id == "F11":  # Scattered sybil
            post_text = f"{core_text} {target_url} #{campaign_hashtag}"
        elif family_id == "F12":  # Small cell
            post_text = f"URGENT: {core_text} {target_url} #{campaign_hashtag}"
        else:
            post_text = f"{core_text} {target_url} #{campaign_hashtag}"

        posts.append({
            "id": f"bot-post-{campaign_id}-{i:03d}",
            "did": did,
            "text": post_text,
            "text_norm": post_text.lower().strip(),
            "created_at": post_iso,
            "topic_id": 1,
            "links": links,
            "hashtags": hashtags,
            "source": "planted_bot",
            "authorAlias": alias,
            "authorHandle": handle,
            "authorCreatedAt": acct_created_iso,
        })

    return {
        "id": campaign_id,
        "family": family_id,
        "name": f"Family {family_id} ({campaign_id})",
        "tactic": family_id,
        "class": "coordinated_inauthentic",
        "accounts": accounts,
        "posts": posts,
        "dids": dids,
        "size": size,
    }

