"""
Phase 3: Account Age & Handle Enrichment Worker.
Resolves registration creation date and handles via plc.directory and getProfile.
A3 Fix: If lookup fails, stores None (never now), retries up to 3 times, then marks failed.
"""

import asyncio
from datetime import datetime, timezone
import logging
from typing import Optional, Tuple

from ..config import settings
from ..db import get_unenriched_dids, mark_account_enriched
from ..ingest.jetstream import ingest_state

logger = logging.getLogger(__name__)


async def fetch_account_details(did: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Returns (handle, created_at_iso) for a Bluesky DID.
    1. Queries https://plc.directory/<did>/log/audit
    2. Falls back to https://public.api.bsky.app/xrpc/app.bsky.actor.getProfile?actor=<did>
    Returns (None, None) on complete failure.
    """
    try:
        import httpx  # type: ignore
    except ImportError:
        return None, None

    handle: Optional[str] = None
    created_at: Optional[str] = None

    async with httpx.AsyncClient(timeout=4.5) as client:
        # 1. Try plc.directory audit log
        try:
            resp = await client.get(f"{settings.plc_directory_url}/{did}/log/audit")
            if resp.status_code == 200:
                audit = resp.json()
                if isinstance(audit, list) and len(audit) > 0:
                    created_at = audit[0].get("createdAt")
                    aka = (audit[-1].get("operation") or {}).get("alsoKnownAs") or []
                    if aka and isinstance(aka[0], str) and aka[0].startswith("at://"):
                        handle = aka[0].replace("at://", "")
        except Exception as e:
            logger.debug(f"plc.directory query failed for {did}: {e}")

        # 2. Fallback to public.api.bsky.app getProfile
        if not created_at or not handle:
            try:
                resp = await client.get(
                    f"{settings.bsky_public_api_url}/xrpc/app.bsky.actor.getProfile",
                    params={"actor": did},
                )
                if resp.status_code == 200:
                    prof = resp.json()
                    handle = handle or prof.get("handle")
                    created_at = created_at or prof.get("createdAt")
            except Exception as e:
                logger.debug(f"bsky getProfile failed for {did}: {e}")

    return handle, created_at


async def run_enrichment_worker():
    """Periodic worker enriching un-enriched accounts with concurrency limit."""
    sem = asyncio.Semaphore(settings.enrich_concurrency)

    while True:
        try:
            dids = get_unenriched_dids(5)
            if not dids:
                await asyncio.sleep(8.0)
                continue

            async def process(did: str):
                async with sem:
                    handle, c_at = await fetch_account_details(did)
                    if c_at:
                        # Successful lookup - store true registration timestamp
                        mark_account_enriched(did, handle, c_at, status="ok")
                        ingest_state.accounts_enriched += 1
                    else:
                        # A3 Fix: lookup failed; do NOT set created_at to now. Mark retry/failed.
                        mark_account_enriched(did, handle, None, status="retry")

            await asyncio.gather(*(process(d) for d in dids), return_exceptions=True)
            await asyncio.sleep(6.0)
        except Exception as e:
            logger.warning(f"Enrichment worker cycle encountered error: {e}")
            await asyncio.sleep(8.0)
